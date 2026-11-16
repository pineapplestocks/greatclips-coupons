import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import worker,{verifiedPayment,PASS_MS} from '../cloudflare-worker/payment-worker.js';
const product='greatclips-browser-day-pass-v1',url='https://offers.greatclips.com/test123';
function paid(hash,created=Math.floor(Date.now()/1000)) {return {metadata:{product},client_reference_id:hash,mode:'payment',currency:'usd',amount_total:75,payment_status:'paid',status:'complete',payment_intent:{id:'pi_test',latest_charge:{paid:true,amount:75,currency:'usd',created}}};}
test('only the correct paid browser session grants access for exactly 24 hours',()=>{
 const now=1760000000000,s=paid('browser',now/1000);
 assert.equal(verifiedPayment(s,'browser',now).active,true);
 assert.equal(verifiedPayment(s,'browser',now+PASS_MS-1).active,true);
 assert.equal(verifiedPayment(s,'browser',now+PASS_MS).active,false);
 assert.equal(verifiedPayment(s,'browser',now+3000).expires_at,now+PASS_MS);
 for(const edit of [{client_reference_id:'other'},{amount_total:1},{currency:'eur'},{mode:'subscription'},{metadata:{}}])assert.throws(()=>verifiedPayment({...s,...edit},'browser',now));
 assert.equal(verifiedPayment({...s,payment_status:'unpaid'},'browser',now).active,false);
 for(const edit of [{refunded:true},{amount_refunded:1},{disputed:true}])assert.equal(verifiedPayment({...s,payment_intent:{...s.payment_intent,latest_charge:{...s.payment_intent.latest_charge,...edit}}},'browser',now).status,'revoked');
});
function setup(){
 const db=new DatabaseSync(':memory:');db.exec(readFileSync(new URL('../cloudflare-worker/migrations/010_coupon_day_pass.sql',import.meta.url),'utf8'));
 const env={DAY_PASS_ENABLED:'true',STRIPE_SECRET_KEY:'test-only',DB:{prepare(sql){return {bind(...args){const stmt=db.prepare(sql);return {first:async()=>stmt.get(...args),run:async()=>stmt.run(...args)}}}}}};
 const call=async(path,body={},token='a'.repeat(64),origin='https://greatclipsdeal.com')=>{const r=await worker.fetch(new Request('https://worker.test'+path,{method:'POST',headers:{Origin:origin,Authorization:'Bearer '+token},body:JSON.stringify(body)}),env);return {status:r.status,data:await r.json()};};
 return {db,env,call};
}
test('retiring sales blocks new checkout while existing pass verification remains available',async()=>{
 const {db,env,call}=setup();env.DAY_PASS_SALES_ENABLED='false';
 assert.equal((await call('/create-checkout')).status,410);
 assert.equal((await call('/status')).status,200);
 const config=await(await worker.fetch(new Request('https://worker.test/config'),env)).json();
 assert.equal(config.enabled,true);assert.equal(config.sales_enabled,false);db.close();
});
test('checkout amount is fixed, retries reuse checkout, unlimited requests reverify payment',async t=>{
 const {db,call}=setup();t.after(()=>db.close());let session,creates=0,params;
 t.mock.method(globalThis,'fetch',async(input,init)=>{
  if(String(input).includes('/data/coupons.json'))return Response.json({coupons:[{url,last_verified:new Date().toISOString().slice(0,10)}]});
  if(init.method==='POST'){creates++;params=new URLSearchParams(init.body);session={...paid(params.get('client_reference_id')),id:'cs_test',url:'https://checkout.stripe.com/c/pay/test',payment_status:'unpaid',status:'open'};return Response.json(session);}
  return Response.json(session);
 });
 let result=await call('/create-checkout',{coupon_url:url,amount:1});assert.equal(result.status,200);
 assert.equal(params.get('line_items[0][price_data][unit_amount]'),'75');assert.equal(params.get('mode'),'payment');
 assert.equal((await call('/create-checkout')).data.checkout_url,result.data.checkout_url);assert.equal(creates,1);
 assert.equal((await call('/redeem',{coupon_url:url})).status,402);
 assert.equal((await call('/status',{},'b'.repeat(64))).data.active,false);
 session.payment_status='paid';session.status='complete';
 const expiry=(await call('/status')).data.expires_at;
 for(let i=0;i<10;i++)assert.equal((await call('/redeem',{coupon_url:url})).data.url,url);
 assert.equal((await call('/create-checkout')).data.active,true);assert.equal(creates,1);
 assert.equal((await call('/status')).data.expires_at,expiry);
 assert.equal((await call('/redeem',{coupon_url:'https://evil.test/'})).status,400);
 session.payment_intent.latest_charge.refunded=true;
 assert.equal((await call('/redeem',{coupon_url:url})).status,402);
 assert.equal((await call('/create-checkout')).status,409);
 assert.equal((await call('/status',{},'a'.repeat(64),'https://evil.test')).status,403);
 assert.equal((await call('/status',{},'fake')).status,401);
});
test('unconfigured service stays disabled and rejects checkout',async()=>{
 const {db,env,call}=setup();delete env.STRIPE_SECRET_KEY;
 const r=await worker.fetch(new Request('https://worker.test/config'),env);assert.equal((await r.json()).enabled,false);
 assert.equal((await call('/create-checkout')).status,503);db.close();
});
test('unknown or stale coupons cannot reach Stripe checkout',async t=>{
 const {db,call}=setup();t.after(()=>db.close());
 t.mock.method(globalThis,'fetch',async input=>{assert.ok(String(input).endsWith('/data/coupons.json'));return Response.json({coupons:[]});});
 assert.equal((await call('/create-checkout',{coupon_url:url})).status,409);
 assert.equal(db.prepare('SELECT COUNT(*) n FROM coupon_day_passes').get().n,0);
});
