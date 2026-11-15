import {SUPPORT_VARIANTS,supportVariant} from './support-message-variants.js';
const one=(e,s,...a)=>e.DB.prepare(s).bind(...a).first();
const run=(e,s,...a)=>e.DB.prepare(s).bind(...a).run();
const button=(code,title,action)=>({type:'postback',title,payload:`gc_feedback:${code}:${action}`});
const enabled=e=>e.COUPON_FEEDBACK_ENABLED==='true';
async function sent(e,id){return !!await one(e,'SELECT id FROM zernio_outbox WHERE id=? AND sent_at IS NOT NULL',id);}
export async function feedbackPilot(env,body,send){
 if(!enabled(env))return {enabled:false};
 if(body.action==='report'){
  const rows=await env.DB.prepare('SELECT variant,COUNT(*) enrolled,SUM(checkin_sent_at IS NOT NULL) checkins,SUM(feedback=\'worked\') worked,SUM(feedback=\'later\') not_yet,SUM(feedback=\'problem\') problems,SUM(support_opted_in_at IS NOT NULL) support_optins,SUM(support_sent_at IS NOT NULL) support_messages FROM coupon_feedback_pilot GROUP BY variant').bind().all();
  return {variants:rows.results};
 }
 if(!['preview','send'].includes(body.action))throw Object.assign(Error('Unknown pilot action'),{status:400});
 const now=Date.now();
 const rows=(await env.DB.prepare(`SELECT r.code,r.conversation_id,r.sender_id,q.last_inbound_at
 FROM zernio_coupon_requests r JOIN zernio_membership_checks q ON q.code=r.code
 WHERE r.sent_at>=? AND q.last_inbound_at>=? AND q.last_inbound_at<=? AND r.cancelled_at IS NULL
 AND r.conversation_id IS NOT NULL AND r.sender_id IS NOT NULL
 AND NOT EXISTS(SELECT 1 FROM zernio_optouts o WHERE o.conversation_id=r.conversation_id)
 AND NOT EXISTS(SELECT 1 FROM coupon_feedback_pilot p WHERE p.sender_id=r.sender_id OR p.conversation_id=r.conversation_id)
 ORDER BY r.sent_at DESC LIMIT 50`).bind(now-72*3600000,now-23*3600000,now).all()).results||[];
 const selected=[],seen=new Set();for(const row of rows){if(seen.has(row.sender_id)||seen.has(row.conversation_id))continue;seen.add(row.sender_id);seen.add(row.conversation_id);selected.push(row);}
 if(body.action==='preview')return {eligible_recipients:selected.length,mode:'preview'};
 // Explicit one-time pilot only. No cron automatically enrolls older recipients.
 const limit=Math.max(1,Math.min(10,Number(body.limit)||8));
 for(const row of selected.slice(0,limit))await run(env,'INSERT OR IGNORE INTO coupon_feedback_pilot(code,conversation_id,sender_id,variant,created_at,last_inbound_at) VALUES(?,?,?,?,?,?)',row.code,row.conversation_id,row.sender_id,await supportVariant(row.sender_id),now,row.last_inbound_at);
 const pending=(await env.DB.prepare(`SELECT p.* FROM coupon_feedback_pilot p WHERE checkin_sent_at IS NULL AND last_inbound_at>? AND created_at>? AND NOT EXISTS(SELECT 1 FROM zernio_optouts o WHERE o.conversation_id=p.conversation_id) LIMIT 10`).bind(now-23*3600000,now-20*3600000).all()).results||[];
 let delivered=0,failed=0;
 for(const p of pending){
  try{
   const id='feedback-check:'+p.code;
   await send(env,id,p.conversation_id,{message:'Hey! Quick check on the Great Clips coupon link we sent: have you used it, and did it work at the salon? ✂️\n\nPlease choose below. No pressure if you haven’t used it yet. Reply STOP to stop messages.',buttons:[button(p.code,'Yes, it worked','worked'),button(p.code,'Not yet','later'),button(p.code,'Had a problem','problem')]});
   if(await sent(env,id)){await run(env,'UPDATE coupon_feedback_pilot SET checkin_sent_at=? WHERE code=?',Date.now(),p.code);delivered++;}
  }catch{failed++;}
 }
 return {enrolled:selected.slice(0,limit).length,checkins_accepted:delivered,failed};
}
export async function feedbackReply(env,b,send){
 if(!enabled(env))return false;
 const match=/^gc_feedback:([A-Z2-9]{8}):(worked|later|problem|support|decline)$/.exec(b.metadata?.interactiveId||'');
 if(!match)return false;
 const [,code,action]=match,m=b.message,now=Date.now();
 const p=await one(env,'SELECT * FROM coupon_feedback_pilot WHERE code=?',code);
 if(!p||p.conversation_id!==b.conversation.id||p.sender_id!==m.sender.id||p.declined_at)return true;
 if(now-Date.parse(m.sentAt)>23*3600000||Date.parse(m.sentAt)>now+300000)return true;
 if(await one(env,'SELECT conversation_id FROM zernio_optouts WHERE conversation_id=?',p.conversation_id))return true;
 if(!await sent(env,'feedback-check:'+code))return true;
 await run(env,'UPDATE coupon_feedback_pilot SET last_inbound_at=MAX(last_inbound_at,?) WHERE code=?',Date.parse(m.sentAt),code);
 if(action==='decline'){await run(env,'UPDATE coupon_feedback_pilot SET declined_at=COALESCE(declined_at,?) WHERE code=?',now,code);return true;}
 if(['worked','later','problem'].includes(action)){
  if(p.feedback&&p.feedback!==action)return true;
  await run(env,'UPDATE coupon_feedback_pilot SET feedback=?,feedback_at=COALESCE(feedback_at,?) WHERE code=?',action,now,code);
  if(action==='worked')await send(env,'feedback-permission:'+code,p.conversation_id,{message:'Glad it worked! ❤️ Would you like to hear about an optional 75¢ contribution toward haircuts for children in India? Your coupon stays free either way.',buttons:[button(code,'Show me','support'),button(code,'No thanks','decline')]});
  if(action==='later')await send(env,'feedback-later:'+code,p.conversation_id,{message:'No rush—thanks for letting us know! Check the coupon’s expiration and participating locations before you go.'});
  if(action==='problem')await send(env,'feedback-problem:'+code,p.conversation_id,{message:'Sorry it didn’t work. Please reply with the salon city and what happened so Kumar can take a look. Please don’t send payment details.'});
  return true;
 }
 if(action==='support'){
  if(p.feedback!=='worked'||!await sent(env,'feedback-permission:'+code))return true;
  const base=env.HAIRCUT_SUPPORT_LINK;if(!/^https:\/\/buy\.stripe\.com\/[A-Za-z0-9]+$/.test(base||''))return true;
  await run(env,'UPDATE coupon_feedback_pilot SET support_opted_in_at=COALESCE(support_opted_in_at,?) WHERE code=?',now,code);
  const link=new URL(base);link.searchParams.set('client_reference_id','haircut_support_v1_'+p.variant+'_'+code);
  const id='feedback-support:'+code;
  await send(env,id,p.conversation_id,{message:SUPPORT_VARIANTS[p.variant].message+'\n\nContribute 75¢ securely: '+link.href+'\n\nOne-time payment. No subscription. Apple Pay or Google Pay may appear if available on your device. Reply STOP to stop messages.'});
  if(await sent(env,id))await run(env,'UPDATE coupon_feedback_pilot SET support_sent_at=COALESCE(support_sent_at,?) WHERE code=?',now,code);
 }
 return true;
}
