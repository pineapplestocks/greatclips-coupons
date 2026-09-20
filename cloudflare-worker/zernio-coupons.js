import { experimentAction, requestAttribution, experimentReport } from './zernio-experiment.js';
import { currentOffer } from './whatsapp.js';
const SITE='https://greatclipsdeal.com', DAY=86400000;
const one=(e,s,...a)=>e.DB.prepare(s).bind(...a).first();
const run=(e,s,...a)=>e.DB.prepare(s).bind(...a).run();
const ready=e=>e.ZERNIO_COUPONS_ENABLED==='true'&&!!e.ZERNIO_API_KEY&&!!e.ZERNIO_WEBHOOK_SECRET&&!!e.ZERNIO_ACCOUNT_ID&&/^\d{8,15}$/.test(e.ZERNIO_PHONE||'')&&/^https:\/\/chat\.whatsapp\.com\/[A-Za-z0-9]+$/.test(e.ZERNIO_GROUP_INVITE||'');
const response=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','Access-Control-Allow-Origin':SITE,'Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Authorization'}});
async function mac(secret,text){const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(text))),v=>v.toString(16).padStart(2,'0')).join('');}
export async function validSignature(secret,raw,signature){if(!secret||!signature||!/^[a-f0-9]{64}$/.test(signature))return false;const expected=await mac(secret,raw);return [...expected].reduce((n,c,i)=>n|(c.charCodeAt(0)^signature.charCodeAt(i)),0)===0;}
export async function handleZernio(request,env,ctx){
 try{
  const path=new URL(request.url).pathname;
  if(request.method==='OPTIONS')return response({});
  if(path==='/zernio/config'&&request.method==='GET')return response({enabled:ready(env)});
  if(request.method!=='POST')return response({error:'Method not allowed'},405);
  const raw=await request.text();if(raw.length>65536)return response({error:'Too large'},413);
  if(path==='/zernio/experiment/report'){
   if(!env.ADMIN_TOKEN||request.headers.get('Authorization')!=='Bearer '+env.ADMIN_TOKEN)return response({error:'Unauthorized'},401);
   return response(await experimentReport(env));
  }
  if(path==='/zernio/experiment'){
   if(![SITE,'https://www.greatclipsdeal.com'].includes(request.headers.get('Origin')))return response({error:'Use the website'},403);
   return response(await experimentAction(request,env,JSON.parse(raw)));
  }
  if(path==='/zernio/webhook'){
   if(!await validSignature(env.ZERNIO_WEBHOOK_SECRET,raw,request.headers.get('X-Zernio-Signature')))return response({error:'Invalid signature'},401);
   const b=JSON.parse(raw);
   if(b.event==='webhook.test')return response({ok:true});
   if(!ready(env))return response({error:'Paused'},503);
   if(b.event!=='message.received'||b.account?.accountId!==env.ZERNIO_ACCOUNT_ID||b.message?.platform!=='whatsapp'||b.message?.direction!=='incoming'||b.metadata?.standby)return response({ok:true});
   const m=b.message,when=Date.parse(m.sentAt);
   if(!b.id||typeof b.id!=='string'||!m.platformMessageId||!m.sender?.id||!b.conversation?.id||m.conversationId!==b.conversation.id||!Number.isFinite(when)||when>Date.now()+300000||Date.now()-when>23*3600000)return response({ok:true});
   // Deduplicate by the platform message, even if the same message gets another event ID.
   const id=env.ZERNIO_ACCOUNT_ID+':'+m.platformMessageId;
   await run(env,'INSERT OR IGNORE INTO zernio_events(id,payload,created_at) VALUES(?,?,?)',id,raw,Date.now());
   ctx.waitUntil(drainZernio(env));return response({ok:true});
  }
  if(path!=='/zernio/requests')return response({error:'Not found'},404);
  if(![SITE,'https://www.greatclipsdeal.com'].includes(request.headers.get('Origin')))return response({error:'Use the website'},403);
  if(!ready(env))return response({error:'WhatsApp is unavailable. Please use email.'},503);
  const ip=request.headers.get('CF-Connecting-IP');if(!ip)return response({error:'Missing source'},400);
  const hash=await mac(env.ZERNIO_WEBHOOK_SECRET,'request:'+ip);
  if((await one(env,'SELECT COUNT(*) n FROM zernio_coupon_requests WHERE ip_hash=? AND created_at>?',hash,Date.now()-DAY)).n>=30)return response({error:'Please try again later or use email.'},429);
  const b=JSON.parse(raw),offer=await currentOffer(b.coupon_url);
  const code=Array.from(crypto.getRandomValues(new Uint8Array(8)),v=>'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'[v&31]).join('');
  let attribution=null;try{attribution=await requestAttribution(env,b);}catch{/* Analytics must never block coupons. */}
  await run(env,'INSERT INTO zernio_coupon_requests(code,coupon_url,label,created_at,ip_hash,experiment_id,experiment_visitor) VALUES(?,?,?,?,?,?,?)',code,offer.url,offer.label,Date.now(),hash,attribution?.experiment_id||null,attribution?.visitor_id||null);
  return response({whatsapp_url:'https://wa.me/'+env.ZERNIO_PHONE+'?text='+encodeURIComponent('Send me my Great Clips coupon! (GC-'+code+')')});
 }catch(error){return response({error:error.status&&error.status<500?error.message:'Unable to complete this request. Please use email.'},error.status||500);}
}
async function send(env,id,conversation,body){
 if(await one(env,'SELECT conversation_id FROM zernio_optouts WHERE conversation_id=?',conversation))return;
 await run(env,'INSERT OR IGNORE INTO zernio_outbox(id,conversation_id,payload,created_at) VALUES(?,?,?,?)',id,conversation,JSON.stringify({accountId:env.ZERNIO_ACCOUNT_ID,...body}),Date.now());
 const item=await one(env,'SELECT * FROM zernio_outbox WHERE id=?',id);if(item.sent_at)return;
 // Never reuse a provider idempotency key beyond our short retry window.
 if(Date.now()-item.created_at>20*3600000)throw new Error('Outbound retry window expired');
 const r=await fetch('https://zernio.com/api/v1/inbox/conversations/'+encodeURIComponent(conversation)+'/messages',{method:'POST',headers:{Authorization:'Bearer '+env.ZERNIO_API_KEY,'Content-Type':'application/json','Idempotency-Key':'gc-'+id},body:item.payload,signal:AbortSignal.timeout(15000)});
 if(!r.ok)throw new Error('Zernio send HTTP '+r.status);
 const data=await r.json();
 await run(env,'UPDATE zernio_outbox SET sent_at=?,message_id=? WHERE id=?',Date.now(),data.data?.messageId||null,id);
}
export async function processZernioEvent(env,b){
 const c=b.conversation.id,m=b.message,text=String(m.text||'').trim(),sender=m.sender.id;
 if(Date.now()-Date.parse(m.sentAt)>23*3600000)return;
 if(/^(stop|unsubscribe|cancel)$/i.test(text)){
  await run(env,'INSERT OR REPLACE INTO zernio_optouts(conversation_id,stopped_at) VALUES(?,?)',c,Date.now());
  await run(env,'UPDATE zernio_coupon_requests SET cancelled_at=? WHERE conversation_id=? AND sent_at IS NULL',Date.now(),c);return;
 }
 if(await one(env,'SELECT conversation_id FROM zernio_optouts WHERE conversation_id=?',c))return;
 const confirm=/^gc_joined:([A-Z2-9]{8})$/.exec(b.metadata?.interactiveId||'');
 const match=/\bGC-([A-Z2-9]{8})\b/i.exec(text);
 if(!confirm&&!match)return; // Leave ordinary chats to the owner.
 const code=(confirm||match)[1].toUpperCase();
 let r=await one(env,'SELECT * FROM zernio_coupon_requests WHERE code=?',code);
 if(!r||r.cancelled_at||Date.now()-r.created_at>7*DAY)return;
 if(confirm){
  if(r.conversation_id!==c||r.sender_id!==sender||r.sent_at)return;
  if(!await one(env,'SELECT id FROM zernio_outbox WHERE id=? AND sent_at IS NOT NULL','invite:'+code))return;
  await run(env,'UPDATE zernio_coupon_requests SET self_confirmed_at=COALESCE(self_confirmed_at,?) WHERE code=?',Date.now(),code);
  let offer;
  try{offer=await currentOffer(r.coupon_url);}catch(error){
   if(error.status&&error.status<500){await send(env,'expired:'+code,c,{message:'That coupon is no longer available. Pick another current offer at '+SITE});return;}throw error;
  }
  await send(env,'coupon:'+code,c,{message:"Here’s your Great Clips coupon! ✂️\n"+offer.url+'\nCheck the offer’s location and terms before your haircut. Reply STOP to stop coupon replies.'});
  if(await one(env,'SELECT id FROM zernio_outbox WHERE id=? AND sent_at IS NOT NULL','coupon:'+code))await run(env,'UPDATE zernio_coupon_requests SET sent_at=COALESCE(sent_at,?) WHERE code=?',Date.now(),code);
  return;
 }
 await run(env,'UPDATE zernio_coupon_requests SET conversation_id=?,sender_id=?,claimed_at=? WHERE code=? AND conversation_id IS NULL',c,sender,Date.now(),code);
 r=await one(env,'SELECT * FROM zernio_coupon_requests WHERE code=?',code);
 if(r.conversation_id!==c||r.sender_id!==sender||r.sent_at)return;
 await send(env,'invite:'+code,c,{message:"Hey, I’m Kumar! Join my deals group here:\n"+env.ZERNIO_GROUP_INVITE+"\n\nThen tap “I’ve joined” below and I’ll send your selected Great Clips coupon. Reply STOP to cancel.",buttons:[{type:'postback',title:"I’ve joined",payload:'gc_joined:'+code}]});
}
export async function drainZernio(env){
 if(!ready(env))return;
 const now=Date.now();
 const rows=(await env.DB.prepare("SELECT * FROM zernio_events WHERE state='pending' AND lease_until<? AND attempts<5 ORDER BY created_at LIMIT 10").bind(now).all()).results;
 for(const item of rows){
  const claimed=await run(env,"UPDATE zernio_events SET lease_until=?,attempts=attempts+1 WHERE id=? AND state='pending' AND lease_until<?",now+120000,item.id,now);if(!claimed.meta.changes)continue;
  try{await processZernioEvent(env,JSON.parse(item.payload));await run(env,"UPDATE zernio_events SET state='done',payload='{}' WHERE id=?",item.id);}
  catch{console.error('Zernio coupon event failed; retry queued');}
 }
}
export async function cleanupZernio(env){
 for(const table of ['zernio_events','zernio_outbox','zernio_coupon_requests'])await run(env,'DELETE FROM '+table+' WHERE created_at<?',Date.now()-90*DAY);
 // Opt-outs intentionally persist until an explicit owner-mediated resubscription.
}
