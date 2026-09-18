// Fixed 28-day A/B/C test, followed by a seven-day conversion window.
export const EXPERIMENT='wa-popup-v1';
const DAY=86400000;
export const VARIANTS={
  A:{name:'Kumar’s personal introduction',host:true,title:'Get your Great Clips Coupon!',copy:'Message me and join my group. Your coupon arrives automatically! Stick around for haircut deals, Amazon price glitches and big coupon stacks.',button:'Text My Coupon on WhatsApp'},
  B:{name:'Short and coupon-first',host:false,title:'Get your Great Clips Coupon!',copy:'Message me, join Deal Dropper, and get your coupon automatically. Three quick steps. One less full-price haircut.',button:'Text My Coupon on WhatsApp'},
  C:{name:'Coupon plus ongoing deals',host:true,title:'Your Great Clips coupon. More deals to follow.',copy:'Join my group for your coupon, then stick around for haircut savings, Amazon finds and big coupon stacks. Message me to get started.',button:'Get My Coupon & More Deals'},
};
const one=(env,sql,...args)=>env.DB.prepare(sql).bind(...args).first();
const run=(env,sql,...args)=>env.DB.prepare(sql).bind(...args).run();
const rows=async(env,sql,...args)=>(await env.DB.prepare(sql).bind(...args).all()).results;
const invalid=message=>{throw Object.assign(new Error(message),{status:400});};
const validVisitor=id=>typeof id==='string'&&/^[a-f0-9]{32}$/.test(id);
async function setup(env){return one(env,'SELECT * FROM whatsapp_experiments WHERE id=?',EXPERIMENT);}
function active(env,e){return !!e&&env.WHATSAPP_EXPERIMENT_ENABLED==='true'&&Date.now()>=e.starts_at&&Date.now()<e.ends_at;}
export async function variantFor(visitor){
  const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(EXPERIMENT+':'+visitor));
  return ['A','B','C'][Math.floor(new DataView(hash).getUint32(0)/4294967296*3)];
}
async function ipHash(request,env){
  const ip=request.headers.get('CF-Connecting-IP');if(!ip)invalid('Unable to identify request source.');
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.WHATSAPP_BRIDGE_TOKEN),{name:'HMAC',hash:'SHA-256'},false,['sign']);
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
    if(!['view','click','dismiss'].includes(b.event))invalid('Invalid experiment event.');
    const now=Date.now();
    if(b.event==='view')await run(env,'UPDATE whatsapp_exposures SET exposed_at=COALESCE(exposed_at,?) WHERE experiment_id=? AND visitor_id=?',now,EXPERIMENT,b.visitor_id);
    if(b.event==='click')await run(env,'UPDATE whatsapp_exposures SET exposed_at=COALESCE(exposed_at,?),clicked_at=COALESCE(clicked_at,?) WHERE experiment_id=? AND visitor_id=?',now,now,EXPERIMENT,b.visitor_id);
    if(b.event==='dismiss')await run(env,'UPDATE whatsapp_exposures SET dismissed_at=COALESCE(dismissed_at,?) WHERE experiment_id=? AND visitor_id=? AND exposed_at IS NOT NULL AND clicked_at IS NULL',now,EXPERIMENT,b.visitor_id);
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
export function interval(success,total){
  if(!total)return [0,1];const z=1.96,p=success/total,d=1+z*z/total;
  const center=(p+z*z/(2*total))/d,half=z*Math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d;
  return [Math.max(0,center-half),Math.min(1,center+half)];
}
async function cohort(env,mature){
  const exists=field=>`EXISTS(SELECT 1 FROM whatsapp_requests r WHERE r.experiment_id=e.experiment_id AND r.experiment_visitor=e.visitor_id AND r.created_at>=e.exposed_at AND r.created_at<=e.exposed_at+${7*DAY} AND ${field})`;
  const found=await rows(env,`SELECT e.variant,COUNT(*) AS viewers,
    SUM(CASE WHEN e.clicked_at IS NOT NULL AND e.clicked_at<=e.exposed_at+${7*DAY} THEN 1 ELSE 0 END) AS clicks,
    SUM(CASE WHEN e.dismissed_at IS NOT NULL THEN 1 ELSE 0 END) AS dismissals,
    SUM(${exists(`r.claimed_at<=e.exposed_at+${7*DAY}`)}) AS messages,
    SUM(${exists(`r.member_confirmed_at<=e.exposed_at+${7*DAY}`)}) AS members,
    SUM(${exists(`r.membership_initial=0 AND r.member_confirmed_at<=e.exposed_at+${7*DAY}`)}) AS observed_joins,
    SUM(${exists(`r.membership_initial=1 AND r.member_confirmed_at<=e.exposed_at+${7*DAY}`)}) AS existing_members,
    SUM(${exists(`r.status='sent' AND r.sent_at<=e.exposed_at+${7*DAY}`)}) AS delivered
    FROM whatsapp_exposures e WHERE e.experiment_id=? AND e.exposed_at IS NOT NULL AND e.exposed_at<=? GROUP BY e.variant`,EXPERIMENT,Date.now()-(mature?7*DAY:0));
  return Object.keys(VARIANTS).map(variant=>{
    const r=found.find(x=>x.variant===variant)||{variant,viewers:0,clicks:0,dismissals:0,messages:0,members:0,observed_joins:0,existing_members:0,delivered:0};
    return {...r,no_click:Math.max(0,r.viewers-r.clicks),membership_rate:r.viewers?r.members/r.viewers:0,click_rate:r.viewers?r.clicks/r.viewers:0,interval:interval(r.members,r.viewers)};
  });
}
export function verdict(mature,e,now=Date.now()){
  if(now<e.ends_at+7*DAY)return {state:'running',text:'No winner yet. Wait for the 28-day test and seven-day conversion window.'};
  if(mature.some(r=>r.viewers<500||r.members<20||r.viewers-r.members<20))return {state:'insufficient',text:'Not enough data for a reliable winner. At least 500 viewers and 20 outcomes of each kind per variant are required.'};
  const total=mature.reduce((n,r)=>n+r.viewers,0),expected=total/3;
  if(mature.reduce((n,r)=>n+(r.viewers-expected)**2/expected,0)>13.82)return {state:'imbalance',text:'Traffic is unexpectedly uneven. Check experiment delivery before choosing a winner.'};
  const sorted=[...mature].sort((a,b)=>b.membership_rate-a.membership_rate),best=sorted[0];
  const beats=sorted.slice(1).every(r=>{const pool=(best.members+r.members)/(best.viewers+r.viewers);const se=Math.sqrt(pool*(1-pool)*(1/best.viewers+1/r.viewers));return se>0&&(best.membership_rate-r.membership_rate)/se>=2.40;});
  return beats?{state:'winner',variant:best.variant,text:`Variant ${best.variant} has the strongest supported membership conversion rate.`}:{state:'inconclusive',text:'No clear winner. The observed differences could be random variation.'};
}
export async function experimentReport(env){
  const saved=await one(env,'SELECT report_json FROM whatsapp_experiment_results WHERE experiment_id=?',EXPERIMENT);
  if(saved)return {...JSON.parse(saved.report_json),archived:true};
  const e=await setup(env);if(!e)return {error:'Experiment not configured'};
  const [live,mature]=await Promise.all([cohort(env,false),cohort(env,true)]);
  return {experiment_id:EXPERIMENT,starts_at:e.starts_at,ends_at:e.ends_at,analysis_at:e.ends_at+7*DAY,active:active(env,e),variants:VARIANTS,live,mature,verdict:verdict(mature,e),updated_at:Date.now(),archived:false};
}
export async function maintainExperiment(env){
  if(!env.DB)return;const e=await setup(env);
  if(e&&Date.now()>=e.ends_at+7*DAY){const report=await experimentReport(env);if(!report.archived)await run(env,'INSERT OR IGNORE INTO whatsapp_experiment_results VALUES(?,?,?)',EXPERIMENT,Date.now(),JSON.stringify(report));}
  await run(env,'DELETE FROM whatsapp_exposures WHERE assigned_at<?',Date.now()-90*DAY);
}
