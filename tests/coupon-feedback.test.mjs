import test from 'node:test';import assert from 'node:assert/strict';import{DatabaseSync}from'node:sqlite';import{readFileSync}from'node:fs';
import{feedbackPilot,feedbackReply}from'../cloudflare-worker/coupon-feedback.js';
function setup(){
 const db=new DatabaseSync(':memory:');
 for(const name of ['006_zernio_self_confirmation','009_zernio_verified_membership','011_coupon_feedback_pilot'])db.exec(readFileSync(new URL('../cloudflare-worker/migrations/'+name+'.sql',import.meta.url),'utf8'));
 const env={COUPON_FEEDBACK_ENABLED:'true',HAIRCUT_SUPPORT_LINK:'https://buy.stripe.com/example',DB:{prepare(sql){return{bind(...args){const s=db.prepare(sql);return{first:async()=>s.get(...args),all:async()=>({results:s.all(...args)}),run:async()=>({meta:{changes:s.run(...args).changes}})}}}}}};
 const sends=[];const send=async(e,id,c,body)=>{if(db.prepare('SELECT id FROM zernio_outbox WHERE id=?').get(id))return;sends.push(body);db.prepare('INSERT INTO zernio_outbox(id,conversation_id,payload,created_at,sent_at) VALUES(?,?,?,?,?)').run(id,c,JSON.stringify(body),Date.now(),Date.now());};
 const seed=(code,c,age=3600000)=>{db.prepare('INSERT INTO zernio_coupon_requests(code,coupon_url,label,created_at,ip_hash,conversation_id,sender_id,sent_at) VALUES(?,?,?,?,?,?,?,?)').run(code,'https://offers.greatclips.com/example','coupon',Date.now()-age,'ip',c,c+'-sender',Date.now()-age);db.prepare('INSERT INTO zernio_membership_checks(code,sender_phone,requested_at,last_inbound_at) VALUES(?,?,?,?)').run(code,'15555550123',Date.now()-age,Date.now()-age);};
 const event=(action,c='c1',code='ABCDEFGH')=>({conversation:{id:c},message:{sender:{id:c+'-sender'},sentAt:new Date().toISOString()},metadata:{interactiveId:`gc_feedback:${code}:${action}`}});
 return{db,env,sends,send,seed,event};
}
test('pilot respects reply window and STOP, deduplicates and never assumes success',async()=>{
 const f=setup();f.seed('ABCDEFGH','c1');f.seed('BCDEFGHJ','c1');f.seed('CDEFGHJK','old',25*3600000);f.seed('DEFGHJKL','stop');f.db.prepare('INSERT INTO zernio_optouts VALUES(?,?)').run('stop',Date.now());
 assert.equal((await feedbackPilot(f.env,{action:'preview'},f.send)).eligible_recipients,1);
 assert.equal(f.sends.length,0);
 assert.equal((await feedbackPilot(f.env,{action:'send'},f.send)).checkins_accepted,1);
 await feedbackPilot(f.env,{action:'send'},f.send);assert.equal(f.sends.length,1);
 assert.equal(f.db.prepare('SELECT feedback FROM coupon_feedback_pilot').get().feedback,null);f.db.close();
});
test('only confirmed success plus explicit support request sends one assigned variant',async()=>{
 const f=setup();f.seed('ABCDEFGH','c1');await feedbackPilot(f.env,{action:'send'},f.send);
 await feedbackReply(f.env,f.event('support'),f.send);assert.equal(f.sends.length,1);
 await feedbackReply(f.env,f.event('worked','stranger'),f.send);assert.equal(f.sends.length,1);
 await feedbackReply(f.env,f.event('worked'),f.send);assert.equal(f.sends.length,2);assert.ok(!f.sends[1].message.includes('buy.stripe.com'));
 await feedbackReply(f.env,f.event('support'),f.send);assert.equal(f.sends.length,3);assert.match(f.sends[2].message,/client_reference_id=haircut_support_v1_[ABC]_ABCDEFGH/);
 await feedbackReply(f.env,f.event('support'),f.send);assert.equal(f.sends.length,3);
 assert.ok(f.db.prepare('SELECT support_sent_at FROM coupon_feedback_pilot').get().support_sent_at);f.db.close();
});
test('not-yet, problems, declines, opt-outs and stale replies cannot solicit contributions',async()=>{
 for(const action of ['later','problem','decline']){
  const f=setup();f.seed('ABCDEFGH','c1');await feedbackPilot(f.env,{action:'send'},f.send);await feedbackReply(f.env,f.event(action),f.send);await feedbackReply(f.env,f.event('support'),f.send);assert.ok(f.sends.every(b=>!b.message.includes('buy.stripe.com')));f.db.close();
 }
 const f=setup();f.seed('ABCDEFGH','c1');await feedbackPilot(f.env,{action:'send'},f.send);
 const stale=f.event('worked');stale.message.sentAt=new Date(Date.now()-25*3600000).toISOString();await feedbackReply(f.env,stale,f.send);
 f.db.prepare('INSERT INTO zernio_optouts VALUES(?,?)').run('c1',Date.now());await feedbackReply(f.env,f.event('worked'),f.send);assert.equal(f.sends.length,1);f.db.close();
});
