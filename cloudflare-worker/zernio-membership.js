import { currentOffer } from './whatsapp.js';
const DAY=86400000;
const one=(e,s,...a)=>e.DB.prepare(s).bind(...a).first();
const run=(e,s,...a)=>e.DB.prepare(s).bind(...a).run();
const fail=(message,status=400)=>{throw Object.assign(new Error(message),{status});};
export function senderPhone(sender){
 for(const value of [sender?.phoneNumber,sender?.id])if(/^\+?\d{8,15}$/.test(value||''))return String(value).replace(/^\+/,'');
 return null;
}
export async function queueMembership(env,r,message){
 await run(env,`INSERT INTO zernio_membership_checks(code,sender_phone,requested_at,last_inbound_at)
 VALUES(?,?,?,?) ON CONFLICT(code) DO UPDATE SET
 sender_phone=COALESCE(excluded.sender_phone,sender_phone),last_inbound_at=MAX(last_inbound_at,excluded.last_inbound_at)`,
 r.code,senderPhone(message.sender),Date.now(),Date.parse(message.sentAt));
}
export async function membershipAction(env,b,send){
 if(env.ZERNIO_COUPONS_ENABLED!=='true'||!env.ZERNIO_GROUP_ID||!env.ZERNIO_GROUP_NAME)fail('Zernio membership verification is unavailable.',503);
 const now=Date.now();
 if(b.action==='pending'){
  const rows=(await env.DB.prepare(`SELECT r.code,r.sender_id,q.sender_phone FROM zernio_membership_checks q
   JOIN zernio_coupon_requests r ON r.code=q.code
   WHERE q.state='pending' AND q.lease_until<?
   AND q.last_inbound_at>? AND r.created_at>? AND r.self_confirmed_at IS NOT NULL
   AND r.sent_at IS NULL AND r.cancelled_at IS NULL
   AND NOT EXISTS(SELECT 1 FROM zernio_optouts o WHERE o.conversation_id=r.conversation_id)
   ORDER BY q.requested_at LIMIT 10`).bind(now,now-23*3600000,now-7*DAY).all()).results||[];
  const requests=[];
  for(const row of rows){
   if(!/^\d{8,15}$/.test(row.sender_phone||''))continue;
   const lease=crypto.randomUUID();
   const claimed=await run(env,`UPDATE zernio_membership_checks SET lease_until=?,lease_token=?
    WHERE code=? AND state='pending' AND lease_until<?`,now+60000,lease,row.code,now);
   if(claimed.meta.changes)requests.push({...row,lease_token:lease});
  }
  return {enabled:true,group_id:env.ZERNIO_GROUP_ID,group_name:env.ZERNIO_GROUP_NAME,requests};
 }
 if(b.action!=='check')fail('Unknown membership action.');
 if(b.group_id!==env.ZERNIO_GROUP_ID||typeof b.member!=='boolean')fail('Invalid membership verification.',403);
 const r=await one(env,`SELECT r.*,q.last_inbound_at,q.lease_until,q.lease_token,q.state AS membership_state
  FROM zernio_coupon_requests r JOIN zernio_membership_checks q ON q.code=r.code WHERE r.code=?`,String(b.code||''));
 if(!r||r.cancelled_at||r.sent_at||r.membership_state!=='pending')return {status:'inactive'};
 if(r.sender_id!==b.sender_id||!b.lease_token||r.lease_token!==b.lease_token||r.lease_until<=now)fail('Membership check expired; check again.',409);
 if(!r.self_confirmed_at||now-r.created_at>7*DAY||now-r.last_inbound_at>23*3600000)return {status:'expired'};
 if(await one(env,'SELECT conversation_id FROM zernio_optouts WHERE conversation_id=?',r.conversation_id))return {status:'cancelled'};
 await run(env,'UPDATE zernio_membership_checks SET checked_at=?,member=?,verified_at=? WHERE code=?',now,b.member?1:0,b.member?now:null,r.code);
 if(!b.member){
  await send(env,'join-reminder:'+r.code,r.conversation_id,{message:'Please join our '+env.ZERNIO_GROUP_NAME+' group first:\n'+env.ZERNIO_GROUP_INVITE+'\n\nWe share great offers that can help you save money. Joining supports us and helps the group grow. Once we verify you are in the group, we will send your selected coupon. Reply STOP to cancel.',buttons:[{type:'postback',title:'I’ve joined',payload:'gc_joined:'+r.code}]});
  await run(env,'UPDATE zernio_membership_checks SET lease_until=0,lease_token=NULL WHERE code=?',r.code);
  return {status:'awaiting_join'};
 }
 let offer;
 try{offer=await currentOffer(r.coupon_url);}catch(error){
  if(error.status&&error.status<500){
   await send(env,'expired:'+r.code,r.conversation_id,{message:'That coupon is no longer available. Pick another current offer at https://greatclipsdeal.com'});
   await run(env,"UPDATE zernio_membership_checks SET state='expired',lease_until=0,lease_token=NULL WHERE code=?",r.code);
   return {status:'expired'};
  }throw error;
 }
 await send(env,'coupon:'+r.code,r.conversation_id,{message:'Here’s your Great Clips coupon! ✂️\n'+offer.url+'\nCheck the offer’s location and terms before your haircut. Reply STOP to stop coupon replies.'});
 if(await one(env,'SELECT id FROM zernio_outbox WHERE id=? AND sent_at IS NOT NULL','coupon:'+r.code)){
  await run(env,'UPDATE zernio_coupon_requests SET sent_at=COALESCE(sent_at,?) WHERE code=?',Date.now(),r.code);
  await run(env,"UPDATE zernio_membership_checks SET state='sent',lease_until=0,lease_token=NULL WHERE code=?",r.code);
  return {status:'sent'};
 }
 return {status:'cancelled'};
}
