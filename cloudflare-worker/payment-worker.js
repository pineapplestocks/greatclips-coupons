import {currentOffer} from './whatsapp.js';

export const PRICE_CENTS=75, PASS_MS=24*60*60*1000;
const PRODUCT='greatclips-browser-day-pass-v1';
const one=(env,sql,...args)=>env.DB.prepare(sql).bind(...args).first();
const run=(env,sql,...args)=>env.DB.prepare(sql).bind(...args).run();
const fail=(message,status=400)=>{throw Object.assign(new Error(message),{status});};
const enabled=env=>env.DAY_PASS_ENABLED==='true'&&!!env.STRIPE_SECRET_KEY&&!!env.DB;
async function tokenHash(request){
 const token=request.headers.get('Authorization')?.replace(/^Bearer /,'');
 if(!/^[a-f0-9]{64}$/.test(token||''))fail('This browser has no day pass.',401);
 return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))),b=>b.toString(16).padStart(2,'0')).join('');
}
async function stripe(env,path,params,key){
 const response=await fetch('https://api.stripe.com/v1/'+path,{
  method:params?'POST':'GET',headers:{Authorization:'Bearer '+env.STRIPE_SECRET_KEY,
   'Stripe-Version':'2024-06-20',...(params?{'Content-Type':'application/x-www-form-urlencoded'}:{}),...(key?{'Idempotency-Key':key}:{})},
  ...(params?{body:new URLSearchParams(params).toString()}:{}),signal:AbortSignal.timeout(15000),
 });
 const data=await response.json();
 if(!response.ok)fail('Payment service is temporarily unavailable. Please try again.',503);
 return data;
}
export function verifiedPayment(session,hash,now=Date.now()){
 const charge=session.payment_intent?.latest_charge;
 if(session.metadata?.product!==PRODUCT||session.client_reference_id!==hash||session.mode!=='payment'||session.currency!=='usd'||session.amount_total!==PRICE_CENTS)fail('Payment does not match this browser pass.',403);
 if(session.payment_status!=='paid'||session.status!=='complete')return {active:false,status:session.status==='expired'?'expired':'pending'};
 if(!charge||charge.paid!==true||charge.amount!==PRICE_CENTS||charge.currency!=='usd')fail('Payment is still being verified. Try again shortly.',409);
 if(charge.refunded||charge.amount_refunded>0||charge.disputed)return {active:false,status:'revoked'};
 const paidAt=Number(charge.created)*1000;
 if(!Number.isFinite(paidAt)||paidAt<=0||paidAt>now+60000)fail('Payment date could not be verified.',409);
 const expiresAt=paidAt+PASS_MS;
 return {active:now<expiresAt,status:now<expiresAt?'active':'expired',paid_at:paidAt,expires_at:expiresAt,payment_intent:session.payment_intent.id};
}
async function status(env,hash){
 const row=await one(env,'SELECT * FROM coupon_day_passes WHERE token_hash=?',hash);
 if(!row?.checkout_id)return {active:false,status:'none'};
 // Check Stripe on each request: browser clocks, localStorage, shared session
 // IDs, refunds and previously cached success cannot grant or extend access.
 const session=await stripe(env,'checkout/sessions/'+encodeURIComponent(row.checkout_id)+'?expand%5B%5D=payment_intent.latest_charge');
 const result=verifiedPayment(session,hash);
 await run(env,'UPDATE coupon_day_passes SET status=?,paid_at=?,expires_at=?,payment_intent=? WHERE token_hash=?',result.status,result.paid_at??null,result.expires_at??null,result.payment_intent??null,hash);
 return result;
}
export default {
 async fetch(request,env){
  const site=env.SITE_ORIGIN||'https://greatclipsdeal.com';
  const origin=request.headers.get('Origin');
  const origins=new Set([site,'https://www.greatclipsdeal.com']);
  const headers={'Content-Type':'application/json','Cache-Control':'no-store','Vary':'Origin','Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Authorization',...(origins.has(origin)?{'Access-Control-Allow-Origin':origin}:{})};
  const json=(data,code=200)=>new Response(JSON.stringify(data),{status:code,headers});
  const path=new URL(request.url).pathname;
  try{
   if(request.method==='OPTIONS')return new Response(null,{status:204,headers});
   if(path==='/config'&&request.method==='GET')return json({enabled:enabled(env),amount_cents:PRICE_CENTS,currency:'usd',duration_hours:24,recurring:false});
   if(!enabled(env))return json({error:'Day passes are not available yet. Please use the free coupon option.'},503);
   if(!origins.has(origin))return json({error:'Please use the coupon website.'},403);
   if(request.method!=='POST')return json({error:'Method not allowed'},405);
   const hash=await tokenHash(request);
   const raw=await request.text();if(raw.length>4096)fail('Request too large.',413);
   let body;try{body=raw?JSON.parse(raw):{}}catch{fail('Invalid request.')}
   if(path==='/status')return json(await status(env,hash));
   if(path==='/redeem'){
    const pass=await status(env,hash);
    if(!pass.active)return json({error:'Your day pass is not active.',...pass},402);
    const offer=await currentOffer(body.coupon_url);
    return json({url:offer.url,expires_at:pass.expires_at});
   }
   if(path!=='/create-checkout')return json({error:'Not found'},404);
   // Verify the visitor's selected offer is still listed before taking payment.
   if(body.coupon_url)await currentOffer(body.coupon_url);
   const existing=await one(env,'SELECT * FROM coupon_day_passes WHERE token_hash=?',hash);
   if(existing?.checkout_id){
    const pass=await status(env,hash);
    if(pass.active)return json(pass);
    if(pass.status!=='pending')return json({error:'Start a new day pass.',status:pass.status},409);
    return json({checkout_url:existing.checkout_url});
   }
   await run(env,'INSERT OR IGNORE INTO coupon_day_passes(token_hash,created_at) VALUES(?,?)',hash,Date.now());
   const session=await stripe(env,'checkout/sessions',{
    mode:'payment',client_reference_id:hash,'metadata[product]':PRODUCT,
    'payment_method_types[0]':'card','line_items[0][quantity]':'1',
    'line_items[0][price_data][currency]':'usd','line_items[0][price_data][unit_amount]':String(PRICE_CENTS),
    'line_items[0][price_data][product_data][name]':'GreatClipsDeal.com — 24-hour browser pass',
    'line_items[0][price_data][product_data][description]':'Unlimited coupon requests in this browser for 24 hours after payment. One-time payment. No automatic renewal. Salon restrictions still apply.',
    'custom_text[submit][message]':'You are paying for website access, not a haircut. Coupon availability and salon acceptance are subject to each offer’s terms.',
    success_url:site+'/day-pass.html?payment=complete',cancel_url:site+'/day-pass.html?payment=cancelled',
   },'gcd-day-pass-'+hash);
   if(!session.id||!/^https:\/\/checkout\.stripe\.com\//.test(session.url||''))fail('Unable to open secure checkout.',503);
   await run(env,'UPDATE coupon_day_passes SET checkout_id=?,checkout_url=? WHERE token_hash=? AND checkout_id IS NULL',session.id,session.url,hash);
   return json({checkout_url:session.url});
  }catch(error){return json({error:error.status?error.message:'Unable to process your pass. Please try again.'},error.status||500)}
 }
};
