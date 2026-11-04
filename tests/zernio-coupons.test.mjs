import test from 'node:test';import assert from 'node:assert/strict';import {DatabaseSync} from 'node:sqlite';import{readFileSync}from'node:fs';import{createHmac}from'node:crypto';
import{handleZernio,drainZernio}from'../cloudflare-worker/zernio-coupons.js';
function fixture(){
 const db=new DatabaseSync(':memory:');db.exec(readFileSync(new URL('../cloudflare-worker/migrations/006_zernio_self_confirmation.sql',import.meta.url),'utf8'));
 db.exec("ALTER TABLE zernio_coupon_requests ADD COLUMN experiment_id TEXT; ALTER TABLE zernio_coupon_requests ADD COLUMN experiment_visitor TEXT; ALTER TABLE zernio_coupon_requests ADD COLUMN claimed_at INTEGER;");
 db.exec(readFileSync(new URL('../cloudflare-worker/migrations/008_zernio_emoji_references.sql',import.meta.url),'utf8'));
 db.exec(readFileSync(new URL('../cloudflare-worker/migrations/009_zernio_verified_membership.sql',import.meta.url),'utf8'));
 const env={WHATSAPP_BRIDGE_TOKEN:'bridge-test',ZERNIO_GROUP_ID:'group@g.us',ZERNIO_GROUP_NAME:'Deal Dropper',ZERNIO_COUPONS_ENABLED:'true',ZERNIO_API_KEY:'fake',ZERNIO_WEBHOOK_SECRET:'secret',ZERNIO_ACCOUNT_ID:'account',ZERNIO_PHONE:'15555550123',ZERNIO_GROUP_INVITE:'https://chat.whatsapp.com/example',DB:{prepare(sql){return{bind(...args){const s=db.prepare(sql);return{first:async()=>s.get(...args),all:async()=>({results:s.all(...args)}),run:async()=>({meta:{changes:s.run(...args).changes}})}}}}}};
 const pending=[];const ctx={waitUntil(p){pending.push(p)}};
 const call=async(path,data,signature=true)=>{const raw=JSON.stringify(data);return handleZernio(new Request('https://test/zernio/'+path,{method:'POST',headers:{Origin:'https://greatclipsdeal.com','CF-Connecting-IP':'192.0.2.1','X-Zernio-Signature':signature?createHmac('sha256','secret').update(raw).digest('hex'):'bad'},body:raw}),env,ctx)};
 const event=(text,id='m1',conversation='c1',interactiveId)=>({id,event:'message.received',timestamp:new Date().toISOString(),account:{accountId:'account'},conversation:{id:conversation},message:{id,platformMessageId:id,conversationId:conversation,platform:'whatsapp',direction:'incoming',text,sender:{id:conversation+'-sender',phoneNumber:'15555550123'},sentAt:new Date().toISOString()},metadata:{interactiveId}});
 const membership=async(body,token='bridge-test')=>handleZernio(new Request('https://test/zernio/membership',{method:'POST',headers:{Authorization:'Bearer '+token},body:JSON.stringify(body)}),env,ctx);
 const verify=async(code,member=true)=>{const b=await (await membership({action:'pending'})).json();const r=b.requests.find(r=>r.code===code);assert.ok(r,'membership request queued');return membership({...r,action:'check',member,group_id:'group@g.us'});};
 return {db,env,call,event,membership,verify,flush:async()=>{while(pending.length)await pending.shift()}};
}
test('official webhook: request -> invitation -> self-confirmation -> selected coupon, deduplicated and bound to requester',async()=>{
 const f=fixture(),original=globalThis.fetch,sends=[];
 globalThis.fetch=async(url,options)=>{if(String(url).includes('/data/coupons.json'))return Response.json({coupons:[{url:'https://offers.greatclips.com/valid',last_verified:new Date().toISOString().slice(0,10)}]});sends.push({body:JSON.parse(options.body),key:options.headers['Idempotency-Key']});return Response.json({data:{messageId:'out'+sends.length}})};
 try{
  let r=await f.call('requests',{coupon_url:'https://offers.greatclips.com/valid'});assert.equal(r.status,200);const d=await r.json(),code=f.db.prepare('SELECT code FROM zernio_coupon_requests').get().code;
  assert.equal((await f.call('webhook',f.event('GC-'+code),false)).status,401);
  await f.call('webhook',f.event(new URL(d.whatsapp_url).searchParams.get('text')));await f.flush();assert.equal(sends.length,1);assert.ok(sends[0].body.message.includes(f.env.ZERNIO_GROUP_INVITE));assert.equal(sends[0].body.buttons[0].payload,'gc_joined:'+code);
  await f.call('webhook',f.event(new URL(d.whatsapp_url).searchParams.get('text')));await f.flush();assert.equal(sends.length,1);
  await f.call('webhook',f.event('','m2','attacker','gc_joined:'+code));await f.flush();assert.equal(sends.length,1);
  await f.call('webhook',f.event('','m3','c1','gc_joined:'+code));await f.flush();assert.equal(sends.length,1,'button alone cannot release a coupon');await f.verify(code);assert.equal(sends.length,2);assert.ok(sends[1].body.message.includes('/valid'));
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

test('nonmembers receive one reminder; only the authenticated group check can release a coupon',async()=>{
 const f=fixture(),original=globalThis.fetch,sends=[];
 globalThis.fetch=async(url,options)=>{
  if(String(url).includes('/data/coupons.json'))return Response.json({coupons:[{url:'https://offers.greatclips.com/valid',last_verified:new Date().toISOString().slice(0,10)}]});
  sends.push(JSON.parse(options.body));return Response.json({data:{messageId:'out'+sends.length}});
 };
 try{
  await f.call('requests',{coupon_url:'https://offers.greatclips.com/valid'});
  const code=f.db.prepare('SELECT code FROM zernio_coupon_requests').get().code;
  await f.call('webhook',f.event('GC-'+code));await f.flush();
  await f.call('webhook',f.event('','joined','c1','gc_joined:'+code));await f.flush();
  assert.equal(sends.length,1);
  await f.call('webhook',f.event("I've joined",'typed-join'));await f.flush();
  assert.equal(sends.length,1,'typed confirmation also needs real membership');
  assert.equal((await f.membership({action:'pending'},'wrong')).status,401);
  await f.verify(code,false);assert.equal(sends.length,2);assert.match(sends[1].message,/Please join/);
  assert.equal(f.db.prepare('SELECT sent_at FROM zernio_coupon_requests').get().sent_at,null);
  f.db.exec('UPDATE zernio_membership_checks SET checked_at=0');
  await f.verify(code,false);assert.equal(sends.length,2,'polling cannot send repeated reminders');
  f.db.exec('UPDATE zernio_membership_checks SET checked_at=0');
  await f.verify(code,true);assert.equal(sends.length,3);assert.match(sends[2].message,/offers.greatclips.com/);
  assert.ok(f.db.prepare('SELECT verified_at FROM zernio_membership_checks').get().verified_at);
 }finally{globalThis.fetch=original}
});

test('wrong groups, stale leases, sender substitutions and opt-outs cannot authorize a coupon',async()=>{
 const f=fixture(),original=globalThis.fetch;let sends=0;
 globalThis.fetch=async()=>{sends++;return Response.json({data:{messageId:'fake'}})};
 f.db.prepare('INSERT INTO zernio_coupon_requests(code,coupon_url,label,created_at,ip_hash,conversation_id,sender_id,self_confirmed_at) VALUES(?,?,?,?,?,?,?,?)')
  .run('ABCDEFGH','https://offers.greatclips.com/test','test',Date.now(),'hash','c1','sender',Date.now());
 f.db.prepare('INSERT INTO zernio_membership_checks(code,sender_phone,requested_at,last_inbound_at) VALUES(?,?,?,?)')
  .run('ABCDEFGH','15555550123',Date.now(),Date.now());
 try{
  const batch=await(await f.membership({action:'pending'})).json(),request=batch.requests[0];
  assert.equal((await(await f.membership({action:'pending'})).json()).requests.length,0,'leased checks cannot overlap');
  assert.equal((await f.membership({...request,action:'check',member:true,group_id:'other@g.us'})).status,403);
  assert.equal((await f.membership({...request,action:'check',member:true,group_id:'group@g.us',sender_id:'attacker'})).status,409);
  f.db.exec('UPDATE zernio_membership_checks SET lease_until=0');
  assert.equal((await f.membership({...request,action:'check',member:true,group_id:'group@g.us'})).status,409);
  f.db.prepare('INSERT INTO zernio_optouts VALUES(?,?)').run('c1',Date.now());
  assert.equal((await(await f.membership({action:'pending'})).json()).requests.length,0);
  assert.equal(sends,0);
 }finally{globalThis.fetch=original}
});

test('emoji routing keeps requests distinct, preserves legacy links and safely handles missing emoji',async()=>{
 const f=fixture(),original=globalThis.fetch,sends=[];
 globalThis.fetch=async(url,options)=>{if(String(url).includes('/data/coupons.json'))return Response.json({coupons:['one','two'].map(n=>({url:'https://offers.greatclips.com/'+n,last_verified:new Date().toISOString().slice(0,10)}))});sends.push(JSON.parse(options.body));return Response.json({data:{messageId:'out'+sends.length}})};
 try{
  const messages=[];
  for(const n of ['one','two']){const r=await f.call('requests',{coupon_url:'https://offers.greatclips.com/'+n});assert.equal(r.status,200);messages.push(new URL((await r.json()).whatsapp_url).searchParams.get('text'))}
  assert.ok(messages.every(m=>/GC-[A-Z2-9]{8}$/.test(m)));assert.notEqual(messages[0],messages[1]);
  const refs=f.db.prepare('SELECT * FROM zernio_emoji_references').all();assert.equal(refs.length,2);
  const {readPair,EMOJIS}=await import('../cloudflare-worker/zernio-emoji.js');assert.ok(EMOJIS.length>300);
  const pair=refs[0].pair;assert.equal(Array.from(pair).length,2);assert.equal(readPair(Array.from(pair).join(' \uFE0F')+'\uFE0F'),pair);
  await f.call('webhook',f.event('Hi! Please send me my Great Clips coupon '+pair,'emoji1'));await f.flush();assert.equal(sends.length,1);
  const first=f.db.prepare('SELECT * FROM zernio_coupon_requests WHERE coupon_url LIKE ?').get('%/one');assert.equal(first.conversation_id,'c1');
  await f.call('webhook',f.event('','confirm1','c1','gc_joined:'+first.code));await f.flush();await f.verify(first.code);assert.ok(sends[1].message.includes('/one'));
  const second=f.db.prepare('SELECT * FROM zernio_coupon_requests WHERE coupon_url LIKE ?').get('%/two');
  await f.call('webhook',f.event('GC-'+second.code,'legacy','c2'));await f.flush();assert.equal(sends.length,3);
  await f.call('webhook',f.event('Hi! Please send me my Great Clips coupon','missing','c3'));await f.flush();assert.match(sends.at(-1).message,/GC code/);
  assert.equal(f.db.prepare('SELECT COUNT(*) n FROM zernio_coupon_requests WHERE sent_at IS NOT NULL').get().n,1);
  // Deleted requests leave permanent reference reservations, so old messages cannot route to a later offer.
  f.db.prepare('DELETE FROM zernio_coupon_requests WHERE code=?').run(first.code);
  assert.equal(f.db.prepare('SELECT code FROM zernio_emoji_references WHERE pair=?').get(pair).code,first.code);
 }finally{globalThis.fetch=original}
});
