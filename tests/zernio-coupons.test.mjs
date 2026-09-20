import test from 'node:test';import assert from 'node:assert/strict';import {DatabaseSync} from 'node:sqlite';import{readFileSync}from'node:fs';import{createHmac}from'node:crypto';
import{handleZernio,drainZernio}from'../cloudflare-worker/zernio-coupons.js';
function fixture(){
 const db=new DatabaseSync(':memory:');db.exec(readFileSync(new URL('../cloudflare-worker/migrations/006_zernio_self_confirmation.sql',import.meta.url),'utf8'));
 const env={ZERNIO_COUPONS_ENABLED:'true',ZERNIO_API_KEY:'fake',ZERNIO_WEBHOOK_SECRET:'secret',ZERNIO_ACCOUNT_ID:'account',ZERNIO_PHONE:'15555550123',ZERNIO_GROUP_INVITE:'https://chat.whatsapp.com/example',DB:{prepare(sql){return{bind(...args){const s=db.prepare(sql);return{first:async()=>s.get(...args),all:async()=>({results:s.all(...args)}),run:async()=>({meta:{changes:s.run(...args).changes}})}}}}}};
 const pending=[];const ctx={waitUntil(p){pending.push(p)}};
 const call=async(path,data,signature=true)=>{const raw=JSON.stringify(data);return handleZernio(new Request('https://test/zernio/'+path,{method:'POST',headers:{Origin:'https://greatclipsdeal.com','CF-Connecting-IP':'192.0.2.1','X-Zernio-Signature':signature?createHmac('sha256','secret').update(raw).digest('hex'):'bad'},body:raw}),env,ctx)};
 const event=(text,id='m1',conversation='c1',interactiveId)=>({id,event:'message.received',timestamp:new Date().toISOString(),account:{accountId:'account'},conversation:{id:conversation},message:{id,platformMessageId:id,conversationId:conversation,platform:'whatsapp',direction:'incoming',text,sender:{id:conversation+'-sender'},sentAt:new Date().toISOString()},metadata:{interactiveId}});
 return {db,env,call,event,flush:async()=>{while(pending.length)await pending.shift()}};
}
test('official webhook: request -> invitation -> self-confirmation -> selected coupon, deduplicated and bound to requester',async()=>{
 const f=fixture(),original=globalThis.fetch,sends=[];
 globalThis.fetch=async(url,options)=>{if(String(url).includes('/data/coupons.json'))return Response.json({coupons:[{url:'https://offers.greatclips.com/valid',last_verified:new Date().toISOString().slice(0,10)}]});sends.push({body:JSON.parse(options.body),key:options.headers['Idempotency-Key']});return Response.json({data:{messageId:'out'+sends.length}})};
 try{
  let r=await f.call('requests',{coupon_url:'https://offers.greatclips.com/valid'});assert.equal(r.status,200);const d=await r.json(),code=decodeURIComponent(d.whatsapp_url).match(/GC-([A-Z2-9]{8})/)[1];
  assert.equal((await f.call('webhook',f.event('GC-'+code),false)).status,401);
  await f.call('webhook',f.event('GC-'+code));await f.flush();assert.equal(sends.length,1);assert.ok(sends[0].body.message.includes(f.env.ZERNIO_GROUP_INVITE));assert.equal(sends[0].body.buttons[0].payload,'gc_joined:'+code);
  await f.call('webhook',f.event('GC-'+code));await f.flush();assert.equal(sends.length,1);
  await f.call('webhook',f.event('','m2','attacker','gc_joined:'+code));await f.flush();assert.equal(sends.length,1);
  await f.call('webhook',f.event('','m3','c1','gc_joined:'+code));await f.flush();assert.equal(sends.length,2);assert.ok(sends[1].body.message.includes('/valid'));
  const row=f.db.prepare('SELECT * FROM zernio_coupon_requests').get();assert.ok(row.self_confirmed_at);assert.ok(row.sent_at);assert.equal(row.member_verified,undefined);
  await f.call('webhook',f.event('','m4','c1','gc_joined:'+code));await f.flush();assert.equal(sends.length,2);
 }finally{globalThis.fetch=original}
});
test('STOP, stale events, foreign account, outgoing echoes and disabled service cannot release coupons',async()=>{
 const f=fixture(),original=globalThis.fetch;let sends=0;
 globalThis.fetch=async()=>{sends++;return Response.json({data:{messageId:'fake'}})};
 f.db.prepare('INSERT INTO zernio_coupon_requests(code,coupon_url,label,created_at,ip_hash) VALUES(?,?,?,?,?)').run('ABCDEFGH','https://offers.greatclips.com/test','test',Date.now(),'hash');
 try{
  for(const change of [e=>e.account.accountId='other',e=>e.message.direction='outgoing',e=>e.metadata.standby=true,e=>e.message.sentAt='2020-01-01T00:00:00Z']){const e=f.event('GC-ABCDEFGH');change(e);await f.call('webhook',e);await f.flush()}
  assert.equal(sends,0);await f.call('webhook',f.event('STOP','stop'));await f.flush();await f.call('webhook',f.event('GC-ABCDEFGH','request'));await f.flush();assert.equal(sends,0);
  f.env.ZERNIO_COUPONS_ENABLED='false';assert.equal((await f.call('requests',{})).status,503);assert.equal((await f.call('webhook',f.event('GC-ABCDEFGH','disabled'))).status,503);
 }finally{globalThis.fetch=original}
});
test('network failures retry with the same immutable idempotency key',async()=>{
 const f=fixture(),original=globalThis.fetch,keys=[];
 f.db.prepare('INSERT INTO zernio_coupon_requests(code,coupon_url,label,created_at,ip_hash) VALUES(?,?,?,?,?)').run('ABCDEFGH','https://offers.greatclips.com/test','test',Date.now(),'hash');
 globalThis.fetch=async(url,opts)=>{keys.push(opts.headers['Idempotency-Key']);if(keys.length===1)throw new Error('network');return Response.json({data:{messageId:'fake'}})};
 try{await f.call('webhook',f.event('GC-ABCDEFGH'));await f.flush();assert.equal(keys.length,1);f.db.exec('UPDATE zernio_events SET lease_until=0');await drainZernio(f.env);assert.equal(keys.length,2);assert.equal(keys[0],keys[1]);assert.equal(f.db.prepare('SELECT state FROM zernio_events').get().state,'done');}finally{globalThis.fetch=original}
});
