// Fixed 28-day A/B/C test, followed by a seven-day conversion window.
export const EXPERIMENT='zernio-popup-v1';
import { interval, verdict as assess } from './whatsapp-experiment.js';
const DAY=86400000;
export const VARIANTS={
 A:{name:'Savings and more deals',title:'Get Your Great Clips Coupon on WhatsApp',copy:'Join my deals group to get this coupon—and discover more haircut savings and Amazon deals.',button:'Text My Coupon on WhatsApp'},
 B:{name:'Short and coupon-first',title:'Your Great Clips Coupon Is Next',copy:'Your selected offer is below. Message us, join the group, and confirm to receive your coupon.',button:'Text My Coupon on WhatsApp'},
 C:{name:'A personal invite from Kumar',title:'Hi, I’m Kumar. Let’s Save You Some Money.',copy:'Join my deals group for this Great Clips coupon. Stick around for the Amazon finds and coupon stacks I share.',button:'Text My Coupon on WhatsApp'},
};
const one=(env,sql,...args)=>env.DB.prepare(sql).bind(...args).first();
const run=(env,sql,...args)=>env.DB.prepare(sql).bind(...args).run();
const rows=async(env,sql,...args)=>(await env.DB.prepare(sql).bind(...args).all()).results;
const invalid=message=>{throw Object.assign(new Error(message),{status:400});};
const validVisitor=id=>typeof id==='string'&&/^[a-f0-9]{32}$/.test(id);
async function setup(env){return one(env,'SELECT * FROM whatsapp_experiments WHERE id=?',EXPERIMENT);}
function active(env,e){return !!e&&env.ZERNIO_EXPERIMENT_ENABLED==='true'&&Date.now()>=e.starts_at&&Date.now()<e.ends_at;}
export async function variantFor(visitor){
  const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(EXPERIMENT+':'+visitor));
  return ['A','B','C'][Math.floor(new DataView(hash).getUint32(0)/4294967296*3)];
}
async function ipHash(request,env){
  const ip=request.headers.get('CF-Connecting-IP');if(!ip)invalid('Unable to identify request source.');
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.ZERNIO_WEBHOOK_SECRET),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const hash=await crypto.subtle.sign('HMAC',key,new TextEncoder().encode('experiment:'+ip));
  return Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');
}
export async function experimentAction(request,env,b){
  if(b.action==='preview'){
    if(!VARIANTS[b.variant])invalid('Unknown variation.');
    return {experiment_id:EXPERIMENT,variant:b.variant,copy:VARIANTS[b.variant],tracked:false,preview:true};
  }
  const e=await setup(env);
  if(!active(env,e))return {experiment_id:EXPERIMENT,variant:'A',copy:VARIANTS.A,tracked:false};
  if(!validVisitor(b.visitor_id))invalid('Invalid visitor identifier.');
  if(b.action==='assign'){
    let entry=await one(env,'SELECT variant FROM whatsapp_exposures WHERE experiment_id=? AND visitor_id=?',EXPERIMENT,b.visitor_id);
    if(!entry){
      const hash=await ipHash(request,env);
      const count=await one(env,'SELECT COUNT(*) AS n FROM whatsapp_exposures WHERE ip_hash=? AND assigned_at>?',hash,Date.now()-DAY);
      if(count.n>=100)return {experiment_id:EXPERIMENT,variant:'A',copy:VARIANTS.A,tracked:false};
      await run(env,'INSERT OR IGNORE INTO whatsapp_exposures(experiment_id,visitor_id,variant,assigned_at,ip_hash) VALUES(?,?,?,?,?)',EXPERIMENT,b.visitor_id,await variantFor(b.visitor_id),Date.now(),hash);
      entry=await one(env,'SELECT variant FROM whatsapp_exposures WHERE experiment_id=? AND visitor_id=?',EXPERIMENT,b.visitor_id);
    }
    return {experiment_id:EXPERIMENT,variant:entry.variant,copy:VARIANTS[entry.variant],tracked:true};
  }
  if(b.action==='event'){
    if(!['view','click','dismiss','exit'].includes(b.event))invalid('Invalid experiment event.');
    const now=Date.now();
    if(b.event==='view')await run(env,'UPDATE whatsapp_exposures SET exposed_at=COALESCE(exposed_at,?) WHERE experiment_id=? AND visitor_id=?',now,EXPERIMENT,b.visitor_id);
    if(b.event==='click')await run(env,'UPDATE whatsapp_exposures SET exposed_at=COALESCE(exposed_at,?),clicked_at=COALESCE(clicked_at,?) WHERE experiment_id=? AND visitor_id=?',now,now,EXPERIMENT,b.visitor_id);
    if(b.event==='dismiss')await run(env,'UPDATE whatsapp_exposures SET dismissed_at=COALESCE(dismissed_at,?) WHERE experiment_id=? AND visitor_id=? AND exposed_at IS NOT NULL AND clicked_at IS NULL',now,EXPERIMENT,b.visitor_id);
    if(b.event==='exit')await run(env,'UPDATE whatsapp_exposures SET exited_at=COALESCE(exited_at,?) WHERE experiment_id=? AND visitor_id=? AND exposed_at IS NOT NULL AND clicked_at IS NULL',now,EXPERIMENT,b.visitor_id);
    return {ok:true};
  }
  invalid('Unknown experiment action.');
}
export async function requestAttribution(env,b){
  if(b.experiment_id!==EXPERIMENT||!validVisitor(b.experiment_visitor))return null;
  const e=await setup(env);if(!active(env,e))return null;
  const r=await one(env,'SELECT * FROM whatsapp_exposures WHERE experiment_id=? AND visitor_id=?',EXPERIMENT,b.experiment_visitor);
  if(!r||r.exposed_at&&Date.now()-r.exposed_at>7*DAY)return null;
  await run(env,'UPDATE whatsapp_exposures SET exposed_at=COALESCE(exposed_at,?),clicked_at=COALESCE(clicked_at,?) WHERE experiment_id=? AND visitor_id=?',Date.now(),Date.now(),EXPERIMENT,b.experiment_visitor);
  return {experiment_id:EXPERIMENT,visitor_id:b.experiment_visitor};
}
async function cohort(env,mature){
 const window=7*DAY;
 const exists=condition=>`EXISTS(SELECT 1 FROM zernio_coupon_requests r WHERE r.experiment_id=e.experiment_id AND r.experiment_visitor=e.visitor_id AND r.created_at>=e.exposed_at AND r.created_at<=e.exposed_at+${window} AND ${condition})`;
 const found=await rows(env,`SELECT e.variant,COUNT(*) viewers,
 SUM(CASE WHEN e.clicked_at<=e.exposed_at+${window} THEN 1 ELSE 0 END) clicks,
 SUM(CASE WHEN e.dismissed_at<=e.exposed_at+${window} THEN 1 ELSE 0 END) dismissals,
 SUM(CASE WHEN e.exited_at<=e.exposed_at+${window} THEN 1 ELSE 0 END) exits,
 SUM(${exists('1=1')}) requests,
 SUM(${exists(`r.claimed_at<=e.exposed_at+${window}`)}) messages,
 SUM(${exists(`r.self_confirmed_at<=e.exposed_at+${window}`)}) confirmed,
 SUM(${exists(`r.sent_at<=e.exposed_at+${window}`)}) sent
 FROM whatsapp_exposures e WHERE e.experiment_id=? AND e.exposed_at IS NOT NULL AND e.exposed_at<=? GROUP BY e.variant`,EXPERIMENT,Date.now()-(mature?window:0));
 return ['A','B','C'].map(variant=>{
  const r=found.find(x=>x.variant===variant)||{variant,viewers:0,clicks:0,dismissals:0,exits:0,requests:0,messages:0,confirmed:0,sent:0};
  return {...r,no_click:Math.max(0,r.viewers-r.clicks),click_rate:r.viewers?r.clicks/r.viewers:0,conversion_rate:r.viewers?r.sent/r.viewers:0,interval:interval(r.sent,r.viewers)};
 });
}
export async function experimentReport(env){
 const saved=await one(env,'SELECT report_json FROM whatsapp_experiment_results WHERE experiment_id=?',EXPERIMENT);if(saved)return {...JSON.parse(saved.report_json),archived:true};
 const e=await setup(env);if(!e)throw new Error('Experiment not configured');
 const [live,mature]=await Promise.all([cohort(env,false),cohort(env,true)]);
 const verdict=assess(mature.map(r=>({...r,members:r.sent,membership_rate:r.conversion_rate})),e);
 verdict.text=verdict.text.replace('membership conversion','coupon-send conversion');
 return {experiment_id:EXPERIMENT,starts_at:e.starts_at,ends_at:e.ends_at,analysis_at:e.ends_at+7*DAY,active:active(env,e),variants:VARIANTS,live,mature,verdict,updated_at:Date.now(),archived:false};
}
export async function maintainExperiment(env){
 if(!env.DB)return;const e=await setup(env);
 if(e&&Date.now()>=e.ends_at+7*DAY){const report=await experimentReport(env);if(!report.archived)await run(env,'INSERT OR IGNORE INTO whatsapp_experiment_results VALUES(?,?,?)',EXPERIMENT,Date.now(),JSON.stringify(report));}
}
