import test from 'node:test';
import assert from 'node:assert/strict';
import {setup,url} from './whatsapp-fixture.mjs';
import {EXPERIMENT,variantFor,verdict,interval,maintainExperiment} from '../cloudflare-worker/whatsapp-experiment.js';

test('stable assignment, previews excluded, client cannot choose tracked variant',async()=>{
  const {db,call}=setup(),visitor='1'.repeat(32);
  const first=await call('experiment',{action:'assign',visitor_id:visitor,variant:'X'});
  assert.equal(first.data.variant,await variantFor(visitor));assert.equal(first.data.tracked,true);
  assert.equal((await call('experiment',{action:'assign',visitor_id:visitor})).data.variant,first.data.variant);
  assert.equal((await call('experiment',{action:'preview',variant:'C'})).data.tracked,false);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM whatsapp_exposures').get().n,1);
  assert.equal((await call('experiment',{action:'assign',visitor_id:'bad'})).status,400);
  assert.equal((await call('experiment',{action:'event',visitor_id:visitor,event:'member'})).status,400);
  assert.equal((await call('experiment/report',{})).status,401);
  db.close();
});
test('view-to-delivery funnel deduplicates and distinguishes observed joins from existing members',async t=>{
  t.mock.method(globalThis,'fetch',async()=>Response.json({coupons:[{url,last_verified:new Date().toISOString().slice(0,10)}]}));
  const {db,call,bridge}=setup();await bridge({action:'heartbeat'});
  for(const [visitor,wa,initial] of [['1'.repeat(32),'15555550123',false],['2'.repeat(32),'15555550124',true]]){
    await call('experiment',{action:'assign',visitor_id:visitor});
    for(const event of ['view','view','click','click','dismiss'])assert.equal((await call('experiment',{action:'event',event,visitor_id:visitor})).status,200);
    const request=await call('requests',{coupon_url:url,consent:true,consent_version:'whatsapp-group-coupon-v1',experiment_id:EXPERIMENT,experiment_visitor:visitor});
    assert.equal(request.status,201);const id=request.data.id;
    await bridge({action:'claim',id,wa_id:wa,sender_jid:wa+'@s.whatsapp.net'});
    await bridge({action:'membership',id,member:initial});
    await bridge({action:'membership',id,member:true});
    await bridge({action:'membership',id,member:true});
    await bridge({action:'start-send',id});await bridge({action:'result',id,result:'sent'});
  }
  const report=(await call('experiment/report',{},'admin-test')).data;
  const sum=key=>report.live.reduce((n,r)=>n+r[key],0);
  for(const key of ['viewers','clicks','messages','members','delivered'])assert.equal(sum(key),2,key);
  assert.equal(sum('observed_joins'),1);assert.equal(sum('existing_members'),1);assert.equal(sum('no_click'),0);assert.equal(sum('dismissals'),0);
  assert.equal(report.mature.reduce((n,r)=>n+r.viewers,0),0);
  const later=Date.now()+8*86400000;t.mock.method(Date,'now',()=>later);
  const mature=(await call('experiment/report',{},'admin-test')).data;
  assert.equal(mature.mature.reduce((n,r)=>n+r.members,0),2);
  assert.equal(mature.verdict.state,'running');db.close();
});
test('non-clickers counted, enrollment ends, unsupported attribution ignored, aggregate archived',async()=>{
  const {db,env,call}=setup(),visitor='3'.repeat(32);
  await call('experiment',{action:'assign',visitor_id:visitor});
  await call('experiment',{action:'event',event:'view',visitor_id:visitor});
  await call('experiment',{action:'event',event:'dismiss',visitor_id:visitor});
  let report=(await call('experiment/report',{},'admin-test')).data;
  assert.equal(report.live.reduce((n,r)=>n+r.no_click,0),1);
  assert.equal(report.live.reduce((n,r)=>n+r.dismissals,0),1);
  db.prepare('UPDATE whatsapp_experiments SET ends_at=?').run(Date.now()-8*86400000);
  assert.equal((await call('experiment',{action:'assign',visitor_id:'4'.repeat(32)})).data.tracked,false);
  await maintainExperiment(env);
  report=(await call('experiment/report',{},'admin-test')).data;
  assert.equal(report.archived,true);assert.equal(report.verdict.state,'insufficient');
  assert.equal(JSON.stringify(report).includes(visitor),false,'aggregate does not expose visitor identifiers');db.close();
});
test('winner requires a mature, adequate, balanced sample and corrected pairwise evidence',()=>{
  const e={ends_at:0},now=40*86400000;
  const counts=(values,n=1000)=>values.map((members,i)=>({variant:['A','B','C'][i],members,viewers:n,membership_rate:members/n}));
  assert.equal(verdict(counts([100,200,100]),e,now).variant,'B');
  assert.equal(verdict(counts([100,110,105]),e,now).state,'inconclusive');
  assert.equal(verdict(counts([50,150,50],499),e,now).state,'insufficient');
  assert.equal(verdict(counts([100,200,100]),{ends_at:now},now).state,'running');
  const bad=counts([100,200,100]);bad[1].viewers=3000;assert.equal(verdict(bad,e,now).state,'imbalance');
  const [lo,hi]=interval(50,100);assert.ok(lo<.5&&hi>.5&&lo>0&&hi<1);
});
