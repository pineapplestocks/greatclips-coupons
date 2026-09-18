import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { handleWhatsApp } from '../cloudflare-worker/whatsapp.js';

const url='https://offers.greatclips.com/test123';
function setup() {
  const db=new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../cloudflare-worker/migrations/002_whatsapp_coupon_requests.sql',import.meta.url),'utf8'));
  const env={ADMIN_TOKEN:'admin-test',WHATSAPP_BRIDGE_TOKEN:'bridge-test',WHATSAPP_COUPONS_ENABLED:'true',DB:{
    prepare(sql) { return { bind(...args) {
      const s=db.prepare(sql);
      return {first:async()=>s.get(...args),all:async()=>({results:s.all(...args)}),run:async()=>({meta:{changes:Number(s.run(...args).changes)}})};
    } }; }
  }};
  const call=async(path,data,token,origin='https://greatclipsdeal.com')=>{
    const response=await handleWhatsApp(new Request('https://worker.test/whatsapp/'+path,{method:'POST',headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.1','Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(data)}),env);
    return {status:response.status,data:await response.json()};
  };
  const bridge=b=>call('bridge',b,'bridge-test');
  const admin=b=>call('admin',b,'admin-test');
  const create=()=>call('requests',{coupon_url:url,consent:true,consent_version:'whatsapp-group-coupon-v1'});
  return {db,env,call,bridge,admin,create};
}
test('request binding, verified membership, explicit approval and at-most-once delivery',async t=>{
  t.mock.method(globalThis,'fetch',async()=>Response.json({coupons:[{url,last_verified:new Date().toISOString().slice(0,10),city:'Test City'}]}));
  const {db,call,bridge,admin,create}=setup();
  assert.equal((await create()).status,503,'offline bridge fails closed');
  await bridge({action:'heartbeat'});
  assert.equal((await call('requests',{coupon_url:url,consent:false})).status,400);
  const created=await create();assert.equal(created.status,201);
  const {id,token}=created.data;
  assert.equal((await call('status',{id},'wrong')).status,404);
  assert.equal((await call('status',{id},token)).data.status,'awaiting_message');
  assert.equal((await call('admin',{action:'approve',id,confirmed:true},token)).status,401);
  assert.equal((await bridge({action:'start-send',id})).status,409);
  assert.equal((await bridge({action:'claim',id,wa_id:'15555550123',sender_jid:'15555550123@s.whatsapp.net'})).status,200);
  assert.equal((await bridge({action:'claim',id,wa_id:'15555550124',sender_jid:'15555550124@s.whatsapp.net'})).status,409);
  assert.equal((await admin({action:'approve',id,confirmed:true})).status,409);
  await bridge({action:'membership',id,member:true});
  assert.equal((await bridge({action:'start-send',id})).status,409,'membership alone does not release coupon');
  assert.equal((await admin({action:'approve',id})).status,400);
  assert.equal((await admin({action:'approve',id,confirmed:true})).status,200);
  await bridge({action:'membership',id,member:false});
  assert.equal((await bridge({action:'start-send',id})).status,409,'leaving group revokes approval');
  await bridge({action:'membership',id,member:true});
  assert.equal((await bridge({action:'start-send',id})).status,409,'rejoining requires new approval');
  await admin({action:'approve',id,confirmed:true});
  const job=await bridge({action:'start-send',id});assert.equal(job.status,200);assert.ok(job.data.text.includes(url));
  assert.equal((await bridge({action:'start-send',id})).status,409,'cannot acquire send twice');
  await bridge({action:'result',id,result:'sent',message_id:'fake-message'});
  const status=await call('status',{id},token);assert.equal(status.data.status,'sent');assert.equal(status.data.wa_id,undefined);assert.equal(status.data.coupon_url,undefined);
  db.close();
});
test('blocked coupons, origin checks, cancellation, stale membership and rate limits',async t=>{
  t.mock.method(globalThis,'fetch',async()=>Response.json({coupons:[{url,last_verified:new Date().toISOString().slice(0,10)}]}));
  const {db,call,bridge,admin,create}=setup();await bridge({action:'heartbeat'});
  assert.equal((await call('requests',{coupon_url:url,consent:true},null,'https://evil.test')).status,403);
  for(const coupon_url of ['https://offers.greatclips.com/yMEcKko','https://evil.test/test123'])assert.equal((await call('requests',{coupon_url,consent:true,consent_version:'whatsapp-group-coupon-v1'})).status,400);
  const {id}= (await create()).data;
  await bridge({action:'claim',id,wa_id:'15555550123',sender_jid:'15555550123@s.whatsapp.net'});
  await bridge({action:'membership',id,member:true});
  db.prepare('UPDATE whatsapp_requests SET member_checked_at=? WHERE id=?').run(Date.now()-240000,id);
  assert.equal((await admin({action:'approve',id,confirmed:true})).status,409);
  await bridge({action:'stop',wa_id:'15555550123'});
  assert.equal(db.prepare('SELECT status FROM whatsapp_requests WHERE id=?').get(id).status,'cancelled');
  assert.equal((await bridge({action:'start-send',id})).status,409);
  for(let i=0;i<4;i++)assert.equal((await create()).status,201);
  assert.equal((await create()).status,429);
  db.close();
});
