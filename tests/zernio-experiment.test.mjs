import{setup}from'./whatsapp-fixture.mjs';
import{experimentAction,experimentReport,maintainExperiment}from'../cloudflare-worker/zernio-experiment.js';
import test from 'node:test';import assert from 'node:assert/strict';import {DatabaseSync} from 'node:sqlite';import{readFileSync}from'node:fs';import{createHmac}from'node:crypto';
import{handleZernio,drainZernio}from'../cloudflare-worker/zernio-coupons.js';
function fixture(){
 const {db,env:baseEnv}=setup();db.exec(readFileSync(new URL('../cloudflare-worker/migrations/006_zernio_self_confirmation.sql',import.meta.url),'utf8'));
 db.exec(readFileSync(new URL('../cloudflare-worker/migrations/007_zernio_experiment.sql',import.meta.url),'utf8'));
 db.exec(readFileSync(new URL('../cloudflare-worker/migrations/008_zernio_emoji_references.sql',import.meta.url),'utf8'));
 const env={ADMIN_TOKEN:'test-admin',ZERNIO_EXPERIMENT_ENABLED:'true',ZERNIO_COUPONS_ENABLED:'true',ZERNIO_API_KEY:'fake',ZERNIO_WEBHOOK_SECRET:'secret',ZERNIO_ACCOUNT_ID:'account',ZERNIO_PHONE:'15555550123',ZERNIO_GROUP_INVITE:'https://chat.whatsapp.com/example',DB:{prepare(sql){return{bind(...args){const s=db.prepare(sql);return{first:async()=>s.get(...args),all:async()=>({results:s.all(...args)}),run:async()=>({meta:{changes:s.run(...args).changes}})}}}}}};
 const pending=[];const ctx={waitUntil(p){pending.push(p)}};
 const call=async(path,data,signature=true)=>{const raw=JSON.stringify(data);return handleZernio(new Request('https://test/zernio/'+path,{method:'POST',headers:{Origin:'https://greatclipsdeal.com','CF-Connecting-IP':'192.0.2.1','X-Zernio-Signature':signature?createHmac('sha256','secret').update(raw).digest('hex'):'bad'},body:raw}),env,ctx)};
 const event=(text,id='m1',conversation='c1',interactiveId)=>({id,event:'message.received',timestamp:new Date().toISOString(),account:{accountId:'account'},conversation:{id:conversation},message:{id,platformMessageId:id,conversationId:conversation,platform:'whatsapp',direction:'incoming',text,sender:{id:conversation+'-sender'},sentAt:new Date().toISOString()},metadata:{interactiveId}});
 return {db,env,call,event,flush:async()=>{while(pending.length)await pending.shift()}};
}

test('real-traffic experiment: stable allocation, excluded preview, deduplicated complete funnel, private report and archive',async()=>{
 const f=fixture(),id='a'.repeat(32),req=new Request('https://test',{headers:{'CF-Connecting-IP':'192.0.2.1'}});
 const action=b=>experimentAction(req,f.env,{visitor_id:id,...b});
 const a=await action({action:'assign'});assert.equal(a.tracked,true);assert.equal((await action({action:'assign'})).variant,a.variant);
 await action({action:'preview',variant:'C'});assert.equal(f.db.prepare('SELECT COUNT(*) n FROM whatsapp_exposures').get().n,1);
 assert.equal((await f.call('experiment/report',{})).status,401);
 await action({action:'event',event:'view'});await action({action:'event',event:'view'});
 await action({action:'event',event:'dismiss'});await action({action:'event',event:'exit'});
 let report=await experimentReport(f.env);assert.equal(report.live.find(r=>r.variant===a.variant).no_click,1);
 const original=globalThis.fetch,now=Date.now;let sends=0;
 globalThis.fetch=async url=>{if(String(url).includes('/data/coupons.json'))return Response.json({coupons:[{url:'https://offers.greatclips.com/valid',last_verified:new Date().toISOString().slice(0,10)}]});sends++;return Response.json({data:{messageId:'out'+sends}})};
 try{
  const r=await f.call('requests',{coupon_url:'https://offers.greatclips.com/valid',experiment_id:'zernio-popup-v1',experiment_visitor:id});assert.equal(r.status,200);
  const message=new URL((await r.json()).whatsapp_url).searchParams.get('text');const code=f.db.prepare('SELECT code FROM zernio_coupon_requests').get().code;
  await f.call('webhook',f.event(message));await f.flush();
  await f.call('webhook',f.event('','m2','c1','gc_joined:'+code));await f.flush();
  await f.call('webhook',f.event('','m2','c1','gc_joined:'+code));await f.flush();assert.equal(sends,2);
  report=await experimentReport(f.env);const row=report.live.find(r=>r.variant===a.variant);
  for(const key of ['viewers','clicks','requests','messages','confirmed','sent','dismissals','exits'])assert.equal(row[key],1,key);
  assert.equal(row.no_click,0);assert.equal(row.member_verified,undefined);assert.equal(report.mature.reduce((n,r)=>n+r.viewers,0),0);
  const time=now();Date.now=()=>time+8*86400000;assert.equal((await experimentReport(f.env)).mature.find(r=>r.variant===a.variant).sent,1);
  Date.now=()=>time+36*86400000;await maintainExperiment(f.env);assert.equal((await experimentReport(f.env)).archived,true);assert.equal((await action({action:'assign'})).tracked,false);
 }finally{globalThis.fetch=original;Date.now=now}
});
