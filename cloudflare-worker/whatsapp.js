// Automatically fulfill explicit coupon requests after verified group membership.
import { experimentAction, experimentReport, requestAttribution } from './whatsapp-experiment.js';
const SITE = 'https://greatclipsdeal.com';
const FEED = SITE + '/data/coupons.json';
const DAY = 86400000;
const GROUP = 'Deal Dropper';
const INVITE = 'https://chat.whatsapp.com/Jgifq2XjPAkIgfXMdwM5j5';
const PHONE = '13465138167';
const ORIGINS = new Set([SITE, 'https://www.greatclipsdeal.com']);
const CONSENT = 'whatsapp-group-coupon-v1';
const json = (value, status=200) => new Response(JSON.stringify(value), {
  status, headers: {'Content-Type':'application/json', 'Cache-Control':'no-store'},
});
const fail = (message, status=400) => { throw Object.assign(new Error(message), {status}); };
const one = (env, sql, ...args) => env.DB.prepare(sql).bind(...args).first();
const run = (env, sql, ...args) => env.DB.prepare(sql).bind(...args).run();
const rows = async (env, sql, ...args) => (await env.DB.prepare(sql).bind(...args).all()).results;
const random = () => crypto.randomUUID().replaceAll('-', '');
const shortCode = () => Array.from(crypto.getRandomValues(new Uint8Array(8)), b => 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'[b & 31]).join('');
async function reference(env, r) {
  if(r.request_code)return r.request_code;
  for(let attempt=0;attempt<5;attempt++) {
    try {
      await run(env,'UPDATE whatsapp_requests SET request_code=? WHERE id=? AND request_code IS NULL',shortCode(),r.id);
      return (await one(env,'SELECT request_code FROM whatsapp_requests WHERE id=?',r.id)).request_code;
    } catch(error) { if(!String(error.message).includes('UNIQUE'))throw error; }
  }
  fail('Unable to prepare your coupon reference. Try again.',503);
}

async function equal(a, b) {
  if (!a || !b) return false;
  const bytes = new TextEncoder();
  const [x,y] = await Promise.all([a,b].map(v => crypto.subtle.digest('SHA-256',bytes.encode(v))));
  return new Uint8Array(x).reduce((diff,v,i) => diff | (v ^ new Uint8Array(y)[i]),0) === 0;
}
async function authorize(request, token) {
  if (!await equal(request.headers.get('Authorization'), token && `Bearer ${token}`)) fail('Unauthorized',401);
}
export function offerExpiration(value) {
  if (!value) return null;
  const s=String(value).trim();
  const us=/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s);
  const iso=us ? `${us[3]}-${us[1].padStart(2,'0')}-${us[2].padStart(2,'0')}` : s;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return NaN;
  return Date.parse(iso+'T00:00:00Z');
}
export async function currentOffer(url) {
  let parsed;
  try { parsed=new URL(url); } catch { fail('Choose a current coupon.'); }
  if (parsed.origin!=='https://offers.greatclips.com' || parsed.username || parsed.password ||
      ['yMEcKko','6bWu89Y'].includes(parsed.pathname.slice(1))) fail('Choose a current coupon.');
  const response=await fetch(FEED,{headers:{'Cache-Control':'no-cache'},signal:AbortSignal.timeout(10000)});
  if (!response.ok) fail('Coupon listings are temporarily unavailable.',503);
  const feed=await response.json();
  const offer=feed.coupons?.find(c=>c.url===url);
  if (!offer) fail('This coupon is no longer listed. Choose another coupon.',409);
  const expiry=offerExpiration(offer.expiration);
  // Do not deliver on the expiration date: the offer's timezone is unknown.
  if (expiry!==null && (!Number.isFinite(expiry) || expiry<=Date.now())) fail('This coupon has expired or expires today.',409);
  const checked=Date.parse(offer.last_verified+'T00:00:00Z');
  if (!Number.isFinite(checked) || Date.now()-checked>2*DAY) fail('This coupon needs a fresh availability check.',409);
  const location=[offer.address,offer.city?.replace(/,+$/,''),offer.state==='AREA' ? '' : offer.state].filter(Boolean).join(', ') || offer.area_name || offer.location_name;
  return {url:offer.url,label:`Great Clips coupon — ${location || 'participating locations'}`,expiration:offer.expiration || 'See official offer'};
}
async function body(request) {
  const raw=await request.text();
  if (raw.length>8192) fail('Request too large.',413);
  try { return JSON.parse(raw); } catch { fail('Invalid JSON.'); }
}
const active = r => r && Date.now()-r.created_at < 7*DAY;
const publicStatus = r => ({id:r.id,status:!active(r)&&!['sent','cancelled','rejected'].includes(r.status)?'expired':r.status,label:r.coupon_label,member_verified:!!r.member_verified});

async function route(request,env) {
  const url=new URL(request.url),path=url.pathname;
  if (path==='/whatsapp/config' && request.method==='GET') {
    const enabled=env.WHATSAPP_COUPONS_ENABLED==='true';
    let online=false;
    if(enabled && env.DB) {
      const r=await one(env,'SELECT heartbeat FROM whatsapp_runtime WHERE id=1');
      online=!!r && Date.now()-r.heartbeat<180000;
    }
    return json({enabled,online,group_name:GROUP,business_phone:PHONE,consent_version:CONSENT});
  }
  if (!env.DB) fail('Request storage unavailable.',503);
  if (request.method!=='POST') fail('Method not allowed.',405);
  if(path==='/whatsapp/experiment/report') {
    await authorize(request,env.ADMIN_TOKEN);
    return json(await experimentReport(env));
  }
  if(path==='/whatsapp/experiment') {
    if(!ORIGINS.has(request.headers.get('Origin')))fail('Use the website.',403);
    return json(await experimentAction(request,env,await body(request)));
  }
  if (path==='/whatsapp/admin') {
    await authorize(request,env.ADMIN_TOKEN);
    const b=await body(request);
    if(b.action==='list') {
      return json({requests:await rows(env,`SELECT id,coupon_label,created_at,wa_id,display_name,status,member_verified,
        member_checked_at,approved_at,sent_at,error FROM whatsapp_requests WHERE created_at>? ORDER BY created_at DESC LIMIT 100`,Date.now()-30*DAY)});
    }
    const r=await one(env,'SELECT * FROM whatsapp_requests WHERE id=?',String(b.id||''));
    if(!active(r)) fail('Request missing or older than seven days.',404);
    if(b.action==='reject') {
      await run(env,"UPDATE whatsapp_requests SET status='rejected' WHERE id=? AND status IN ('awaiting_message','awaiting_join','ready','awaiting_approval','approved')",r.id);
    } else fail('Unknown action.');
    return json({ok:true});
  }
  if(path==='/whatsapp/bridge') {
    await authorize(request,env.WHATSAPP_BRIDGE_TOKEN);
    const b=await body(request);
    if(b.action==='heartbeat') {
      await run(env,'INSERT INTO whatsapp_runtime(id,heartbeat) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET heartbeat=excluded.heartbeat',Date.now());
      // Keep identifiable request records for at most 90 days.
      await run(env,'DELETE FROM whatsapp_requests WHERE created_at<?',Date.now()-90*DAY);
      return json({ok:true});
    }
    if(env.WHATSAPP_COUPONS_ENABLED!=='true') fail('Coupon delivery is paused.',503);
    if(b.action==='pending') return json({requests:await rows(env,`SELECT id,wa_id,sender_jid,status FROM whatsapp_requests
      WHERE created_at>? AND status IN ('awaiting_join','ready','awaiting_approval','approved') ORDER BY created_at LIMIT 100`,Date.now()-7*DAY)});
    if(b.action==='stop') {
      if(!/^\d{7,15}$/.test(b.wa_id||'')) fail('Invalid number.');
      await run(env,"UPDATE whatsapp_requests SET status='cancelled' WHERE wa_id=? AND status IN ('awaiting_join','ready','awaiting_approval','approved')",b.wa_id);
      return json({ok:true});
    }
    const r=b.action==='claim'
      ? await one(env,'SELECT * FROM whatsapp_requests WHERE id=? OR request_code=?',String(b.id||'').toLowerCase(),String(b.id||'').toUpperCase())
      : await one(env,'SELECT * FROM whatsapp_requests WHERE id=?',String(b.id||''));
    if(!active(r)) fail('Request missing or older than seven days.',404);
    if(b.action==='claim') {
      if(!/^\d{7,15}$/.test(b.wa_id||'') || !/^[0-9:]+@(s\.whatsapp\.net|lid)$/.test(b.sender_jid||'')) fail('Verified sender required.');
      if(r.wa_id && r.wa_id!==b.wa_id) fail('This request is already linked to another number.',409);
      if(r.status==='awaiting_message') {
        const existing=await one(env,"SELECT id FROM whatsapp_requests WHERE wa_id=? AND coupon_url=? AND status IN ('awaiting_join','ready','awaiting_approval','approved','sending','sent','uncertain') LIMIT 1",b.wa_id,r.coupon_url);
        if(existing && existing.id!==r.id) fail('This number already requested this coupon.',409);
        const changed=await run(env,"UPDATE whatsapp_requests SET wa_id=?,sender_jid=?,display_name=?,claimed_at=?,status='awaiting_join' WHERE id=? AND wa_id IS NULL AND status='awaiting_message'",b.wa_id,b.sender_jid,String(b.display_name||'').slice(0,80),Date.now(),r.id);
        if(!changed.meta.changes) fail('Request already claimed; retry.',409);
      } else if(!['awaiting_join','ready','awaiting_approval','approved'].includes(r.status)) fail('Request already finished.',409);
      return json({ok:true,id:r.id,invite:INVITE,label:r.coupon_label,group_name:GROUP});
    }
    if(b.action==='membership') {
      if(typeof b.member!=='boolean') fail('Membership result required.');
      await run(env,`UPDATE whatsapp_requests SET member_verified=?,member_checked_at=?,
        membership_initial=COALESCE(membership_initial,?),
        member_confirmed_at=CASE WHEN ?=1 THEN COALESCE(member_confirmed_at,?) ELSE member_confirmed_at END,
        status=CASE WHEN ?=1 THEN 'ready' ELSE 'awaiting_join' END
        WHERE id=? AND wa_id IS NOT NULL AND status IN ('awaiting_join','ready','awaiting_approval','approved')`,b.member?1:0,Date.now(),b.member?1:0,b.member?1:0,Date.now(),b.member?1:0,r.id);
      const updated=await one(env,'SELECT status FROM whatsapp_requests WHERE id=?',r.id);
      return json({ok:true,status:updated.status});
    }
    if(b.action==='start-send') {
      if(r.status!=='ready' || !r.member_verified || Date.now()-r.member_checked_at>120000) fail('A fresh verified group membership check is required.',409);
      let offer;
      try { offer=await currentOffer(r.coupon_url); } catch(e) {
        if(e.status===409) await run(env,"UPDATE whatsapp_requests SET status='unavailable',error=? WHERE id=? AND status='ready'",e.message,r.id);
        throw e;
      }
      const changed=await run(env,"UPDATE whatsapp_requests SET status='sending' WHERE id=? AND status='ready'",r.id);
      if(!changed.meta.changes) fail('A send was already started.',409);
      return json({id:r.id,wa_id:r.wa_id,sender_jid:r.sender_jid,
        text:`Your requested ${offer.label} is ready.\n\n${offer.url}\n\nExpiration: ${offer.expiration}. Check the official offer for price, participating salons and restrictions before visiting.\n\nYou requested this coupon from GreatClipsDeal.com after joining ${GROUP}. Independent coupon resource; not affiliated with Great Clips.`});
    }
    if(b.action==='result') {
      if(!['sent','uncertain'].includes(b.result)) fail('Invalid delivery result.');
      await run(env,"UPDATE whatsapp_requests SET status=?,sent_at=?,message_id=?,error=? WHERE id=? AND status='sending'",b.result,b.result==='sent'?Date.now():null,String(b.message_id||'').slice(0,160),b.result==='uncertain'?'Delivery outcome needs manual review; do not retry automatically.':null,r.id);
      return json({ok:true});
    }
    fail('Unknown bridge action.');
  }
  if(path==='/whatsapp/status') {
    const b=await body(request);
    const r=await one(env,'SELECT * FROM whatsapp_requests WHERE id=?',String(b.id||''));
    if(!r || !await equal(request.headers.get('Authorization'),`Bearer ${r.status_token}`)) fail('Request not found.',404);
    return json({...publicStatus(r),request_code:await reference(env,r)});
  }
  if(path==='/whatsapp/requests') {
    if(!ORIGINS.has(request.headers.get('Origin'))) fail('Use the coupon request page.',403);
    if(env.WHATSAPP_COUPONS_ENABLED!=='true' || !env.WHATSAPP_BRIDGE_TOKEN) fail('WhatsApp requests are not enabled yet.',503);
    const runtime=await one(env,'SELECT heartbeat FROM whatsapp_runtime WHERE id=1');
    if(!runtime || Date.now()-runtime.heartbeat>180000) fail('WhatsApp delivery is temporarily offline. Please try again later.',503);
    const b=await body(request);
    if(b.consent!==true || b.consent_version!==CONSENT) fail('Please agree to the group and private coupon delivery.');
    const ip=request.headers.get('CF-Connecting-IP');
    if(!ip) fail('Unable to verify the request source.',403);
    const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.WHATSAPP_BRIDGE_TOKEN),{name:'HMAC',hash:'SHA-256'},false,['sign']);
    const digest=await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(ip));
    const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
    const count=await one(env,'SELECT COUNT(*) AS n FROM whatsapp_requests WHERE ip_hash=? AND created_at>?',hash,Date.now()-3600000);
    if(count.n>=5) fail('Too many requests. Please try again in an hour.',429);
    const offer=await currentOffer(String(b.coupon_url||''));
    let attribution=null;
    try{attribution=await requestAttribution(env,b);}catch(error){console.error('Experiment attribution unavailable:',error.name);}
    const id=random(),token=random();
    await run(env,'INSERT INTO whatsapp_requests(id,status_token,coupon_url,coupon_label,created_at,ip_hash,consent_version,experiment_id,experiment_visitor) VALUES(?,?,?,?,?,?,?,?,?)',id,token,offer.url,offer.label,Date.now(),hash,CONSENT,attribution?.experiment_id||null,attribution?.visitor_id||null);
    const code=await reference(env,{id});
    const message=`Send me my Great Clips coupon! (GC-${code})`;
    return json({id,token,request_code:code,label:offer.label,whatsapp_url:`https://wa.me/${PHONE}?text=${encodeURIComponent(message)}`,group_invite:INVITE},201);
  }
  return json({error:'Not found'},404);
}

export async function handleWhatsApp(request,env) {
  const origin=request.headers.get('Origin');
  const sameOrigin=origin===new URL(request.url).origin;
  if(origin && !ORIGINS.has(origin) && !sameOrigin) return json({error:'Origin not allowed'},403);
  let response;
  if(request.method==='OPTIONS') response=new Response(null,{status:204});
  else try {response=await route(request,env);} catch(error) {
    if(!error.status) console.error('WhatsApp request error:',error.name);
    response=json({error:error.status?error.message:'Unable to process the request right now.'},error.status||503);
  }
  if(ORIGINS.has(origin) || sameOrigin) response.headers.set('Access-Control-Allow-Origin',origin);
  response.headers.set('Access-Control-Allow-Methods','GET, POST, OPTIONS');
  response.headers.set('Access-Control-Allow-Headers','Content-Type, Authorization');
  response.headers.set('Vary','Origin');
  return response;
}
