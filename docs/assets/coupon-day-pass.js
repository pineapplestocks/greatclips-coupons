(() => {
 'use strict';
 if(window.GCDayPass)return;
 const API='https://greatclips-payments.mehulchaudhari.workers.dev', KEY='gcd-browser-pass-v1', SELECTED='gcd-pass-coupon';
 let available=false,pass={active:false},busy=false;
 function token(create=false){
  let value=localStorage.getItem(KEY);
  if(!/^[a-f0-9]{64}$/.test(value||'')){
   if(!create)return '';
   value=Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
   localStorage.setItem(KEY,value);
   if(localStorage.getItem(KEY)!==value)throw new Error('Allow browser storage before buying a pass.');
  }
  return value;
 }
 async function request(path,body={}){
  const r=await fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token()},body:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
  const d=await r.json();if(!r.ok)throw Object.assign(new Error(d.error||'Please try again.'),{data:d});return d;
 }
 const expiry=()=>new Date(pass.expires_at).toLocaleString([],{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
 function selected(id){return id==='emailFormView'?(typeof pendingCouponUrl==='undefined'?'':pendingCouponUrl):window.gcPending?.url;}
 function message(text){for(const el of document.querySelectorAll('[data-pass-status]'))if(el.textContent!==text)el.textContent=text;}
 function render(){
  for(const id of ['emailFormView','gcFormView']){
   const host=document.getElementById(id);if(!host||!available||host.querySelector('.gc-day-pass'))continue;
   const panel=document.createElement('div');panel.className='gc-day-pass';
   panel.innerHTML='<h4>Skip the group steps for a day</h4><p><strong>$0.75 once</strong> · Unlimited coupon requests for 24 hours in this browser. No subscription.</p><button type="button">Unlock 24 hours — $0.75</button><p class="gc-pass-small">Website access only, not a haircut. Offer and salon restrictions apply. Keep this browser’s site data to retain your pass.</p><p data-pass-status role="status" aria-live="polite"></p><div class="gc-pass-divider">Or get your coupon free through WhatsApp</div>';
   panel.querySelector('button').onclick=()=>checkout(selected(id));
   const wa=host.querySelector('.gc-whatsapp-option');if(wa)wa.before(panel);else host.append(panel);
  }
  for(const button of document.querySelectorAll('.gc-day-pass button')){
   const label=pass.active?'Open my coupon':'Unlock 24 hours — $0.75';if(button.textContent!==label)button.textContent=label;
   if(button.disabled!==busy)button.disabled=busy;
  }
  let banner=document.getElementById('gc-pass-banner');
  if(pass.active&&!banner){banner=document.createElement('div');banner.id='gc-pass-banner';banner.setAttribute('role','status');document.body.prepend(banner);}
  if(banner){banner.hidden=!pass.active;const text='Day pass active · Unlimited coupon requests until '+expiry();if(pass.active&&banner.textContent!==text)banner.textContent=text;}
 }
 async function refresh(){
  if(!token()){pass={active:false,status:'none'};return pass;}
  pass=await request('/status');render();return pass;
 }
 async function redeem(url){
  const d=await request('/redeem',{coupon_url:url});
  const target=new URL(d.url);if(target.origin!=='https://offers.greatclips.com')throw new Error('Unable to open this coupon.');
  location.assign(target.href);
 }
 async function checkout(url){
  if(busy)return;busy=true;render();message('Checking your browser pass…');
  try{
   // Keep an existing paid/pending token until Stripe has confirmed its state.
   token(true);await refresh();
   if(pass.active){if(url)await redeem(url);else location.assign('/');return;}
   if(['expired','revoked'].includes(pass.status)){localStorage.removeItem(KEY);token(true);}
   if(url)localStorage.setItem(SELECTED,url);
   const d=await request('/create-checkout',url?{coupon_url:url}:{});
   if(d.active){pass=d;render();if(url)await redeem(url);return;}
   if(!/^https:\/\/checkout\.stripe\.com\//.test(d.checkout_url||''))throw new Error('Secure checkout is unavailable.');
   location.assign(d.checkout_url);
  }catch(e){message(e.name==='TimeoutError'?'This is taking longer than expected. Retry to check the same payment; do not pay again.':e.message||'Unable to connect. Please try again.');}
  finally{busy=false;render();}
 }
 window.GCDayPass={
  // An active display state never grants access: every request is verified server-side.
  open(url){if(!pass.active||!url)return false;redeem(url).catch(async e=>{message(e.message);try{await refresh();}catch{}alert(e.message+' You can reopen the coupon to try again.');});return true;},
  checkout,refresh,
 };
 const style=document.createElement('style');style.textContent='.gc-day-pass{padding:18px;margin:18px 0;border:1px solid #c4b5fd;border-radius:14px;background:#faf8ff;text-align:left;color:#172033}.gc-day-pass h4{font-size:19px;margin:0 0 8px}.gc-day-pass p{font-size:15px;line-height:1.5;margin:8px 0}.gc-day-pass button,#pass-action{width:100%;border:0;border-radius:10px;padding:14px;background:#6d28d9;color:white;font:inherit;font-weight:750;cursor:pointer}.gc-day-pass button:disabled,#pass-action:disabled{opacity:.6;cursor:wait}.gc-day-pass .gc-pass-small{font-size:12px;color:#596579}.gc-pass-divider{border-top:1px solid #ddd6fe;margin-top:14px;padding-top:14px;font-size:13px;text-align:center}#gc-pass-banner{padding:12px 18px;background:#ede9fe;color:#4c1d95;text-align:center;font:600 14px/1.5 system-ui}';document.head.append(style);
 const observer=new MutationObserver(render);
 const observe=()=>observer.observe(document.body,{childList:true,subtree:true});observe();
 addEventListener('pagehide',()=>observer.disconnect());
 async function start(){
  const returnPage=document.getElementById('pass-action');
  try{
   const r=await fetch(API+'/config',{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!r.ok)throw new Error('Pass service is unavailable.');
   available=(await r.json()).enabled===true;render();
   if(!available){message('Day passes are not available yet. You can still get coupons free through WhatsApp.');return;}
   await refresh();
   if(returnPage){
    returnPage.hidden=false;
    if(pass.active){message('Your pass is active until '+expiry()+'. Unlimited coupon requests are unlocked in this browser.');returnPage.textContent='Open my coupon';returnPage.onclick=()=>{const url=localStorage.getItem(SELECTED);if(url)redeem(url).catch(e=>message(e.message));else location.assign('/');};}
    else {message(new URLSearchParams(location.search).get('payment')==='cancelled'?'Checkout was cancelled. No pass has been activated.':'No completed payment verified yet. If you just paid, check again in a moment.');returnPage.textContent='Check payment again';returnPage.onclick=start;}
   }
  }catch(e){message(e.message||'Unable to check your pass. Please retry.');if(returnPage){returnPage.hidden=false;returnPage.textContent='Retry verification';returnPage.onclick=start;}}
 }
 addEventListener('pageshow',()=>{observe();if(available)refresh().catch(()=>{});});
 addEventListener('storage',e=>{if(e.key===KEY&&available)refresh().catch(()=>{});});
 start();
})();
