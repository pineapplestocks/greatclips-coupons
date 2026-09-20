(() => {
 if(window.gcZernioOption)return;window.gcZernioOption=true;
 const api='https://greatclips-email.mehulchaudhari.workers.dev/zernio';
 const experimentId='zernio-popup-v1';
 const preview=new URLSearchParams(location.search).get('zernio_preview');
 const isPreview=['A','B','C'].includes(preview);
 let assignmentReady=false,cohort={variant:'A',tracked:false},wasVisible=false,didClick=false,sawPopup=false;
 const emitted=new Set();
 async function assign(){
  try{
   let visitor;
   if(!isPreview){
    if(navigator.doNotTrack==='1'||navigator.globalPrivacyControl)return;
    const key='gc-zernio-experiment-v1';let saved;try{saved=JSON.parse(localStorage.getItem(key)||'null')}catch{}
    if(!saved||!/^[a-f0-9]{32}$/.test(saved.id)||Date.now()-saved.created>90*86400000){saved={id:crypto.randomUUID().replaceAll('-',''),created:Date.now()};localStorage.setItem(key,JSON.stringify(saved));}
    visitor=saved.id;
   }
   const r=await fetch(api+'/experiment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(isPreview?{action:'preview',variant:preview}:{action:'assign',visitor_id:visitor}),signal:AbortSignal.timeout(1800)});
   if(r.ok)cohort={...await r.json(),visitor_id:visitor};
  }catch{}finally{assignmentReady=true;install();}
 }
 function track(event){
  if(!cohort.tracked||isPreview||emitted.has(event))return;emitted.add(event);
  fetch(api+'/experiment',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'event',event,visitor_id:cohort.visitor_id})}).catch(()=>{});
  if(typeof window.gtag==='function')window.gtag('event','coupon_popup_'+event,{experiment_id:experimentId,variant:cohort.variant,page_type:location.pathname.startsWith('/salons/')?'location':'homepage'});
 }
 function trackVisibility(){
  const visible=['emailModal','gcEmailModal'].some(id=>{const m=document.getElementById(id);return m&&!m.classList.contains('hidden')&&m.getBoundingClientRect().height>0});
  if(assignmentReady&&enabled&&visible){track('view');sawPopup=true;}
  if(wasVisible&&!visible&&!didClick)track('dismiss');wasVisible=visible;
 }
 addEventListener('pagehide',()=>{if(sawPopup&&!didClick)track('exit')});
 function applyVariation(host){
  if(!cohort.copy)return;
  const h=host.querySelector('h3'),intro=h?.nextElementSibling;
  if(h&&h.textContent!==cohort.copy.title)h.textContent=cohort.copy.title;
  if(intro?.tagName==='P'&&intro.textContent!==cohort.copy.copy)intro.textContent=cohort.copy.copy;
  host.dataset.variant=cohort.variant;
 }
 let enabled=false,loaded=false;
 const style=document.createElement("style");style.textContent="#emailFormView > form,#emailFormView > button,#emailFormView > p,#gcFormView > form,#gcFormView > button,#gcFormView > p{display:none!important}";style.textContent+=`
.gc-coupon-panel{width:100%;max-width:480px!important;padding:30px!important;border-radius:22px!important;background:#fff;box-sizing:border-box;max-height:90dvh;overflow-y:auto;position:relative}
.gc-coupon-form>div:first-child{text-align:center;margin-bottom:22px}
.gc-coupon-form>div:first-child>div{display:inline-flex;align-items:center;justify-content:center;width:72px;height:72px;margin-bottom:16px;border-radius:50%;background:linear-gradient(135deg,#994cff,#864bfa)}
.gc-coupon-form>div:first-child>div span{font-size:36px}
.gc-coupon-form h3{font-size:28px!important;font-weight:800!important;line-height:1.18!important;letter-spacing:-.8px;margin:0!important;color:#080f2b}
.gc-coupon-form h3+p{font-size:17px!important;line-height:1.55!important;color:#555e81!important;margin:14px 0 0!important}
.gc-coupon-form #gcModalSalon{display:none}
.gc-coupon-panel>button{position:absolute;right:16px;top:12px;font-size:30px;line-height:1;color:#8996ad;background:none;border:0;cursor:pointer}
.gc-whatsapp-option .gc-steps{display:grid;gap:12px;list-style:none;padding:0;margin:0 0 20px;text-align:left}
.gc-steps li{display:flex;align-items:center;gap:14px;font-size:17px;font-weight:650;line-height:1.4;color:#0f172a}
.gc-steps .gc-step-number{display:grid;place-items:center;flex:0 0 36px;height:36px;border-radius:50%;color:white;font-size:18px;background:linear-gradient(135deg,#9c4cff,#854cff)}
.gc-whatsapp-option .gc-chat-cta{display:flex;align-items:center;justify-content:center;gap:12px;min-height:62px;width:100%;padding:14px 12px;border:0;border-radius:14px;background:linear-gradient(115deg,#04aa60,#00b85c);color:#fff;font:inherit;font-size:20px;font-weight:800;cursor:pointer;box-shadow:0 4px 12px #08ad5915}
.gc-chat-cta:hover{filter:brightness(.96)}.gc-chat-cta:focus-visible{outline:3px solid #8b5cf6;outline-offset:4px}.gc-chat-cta:disabled{opacity:.65;cursor:wait}
.gc-chat-cta svg{flex:none;width:30px;height:30px}.gc-chat-cta svg:last-child{width:20px;height:20px}
.gc-whatsapp-option [role=status]:empty{display:none}
@media(max-width:420px){.gc-coupon-panel{padding:25px 20px!important}.gc-coupon-form h3{font-size:25px!important}.gc-coupon-form h3+p{font-size:16px!important}.gc-steps li{font-size:15px;gap:11px}.gc-whatsapp-option .gc-chat-cta{font-size:17px;gap:9px}}
`;document.head.append(style);
 function selectedOffer(id){
  if(id==='emailFormView'){
   const place=typeof pendingLocation==='undefined'?{}:pendingLocation;
   return {price:typeof pendingCouponPrice==='undefined'?'':pendingCouponPrice,location:[place.location_name,place.city,place.state==='AREA'?'':place.state].filter(Boolean).join(', ')};
  }
  const c=window.gcPending||{},salon=window.gcPendingSalon||{},page=window.__GC_PAGE__||{};
  return {price:c.price||'',location:salon.street?[salon.street,page.cityLabel].filter(Boolean).join(', '):[c.area_name||c.location_name,c.city,c.state==='AREA'?'':c.state].filter(Boolean).join(', ')||page.cityLabel||''};
 }
 function updateOffer(section,id){
  const offer=selectedOffer(id),key=JSON.stringify(offer);if(section.dataset.offer===key)return;section.dataset.offer=key;
  const title=section.querySelector('.gc-selected-title');title.replaceChildren();
  if(offer.price){const price=document.createElement('span');price.textContent=String(offer.price).replace(/(\d)\.\s+(\d)/g,'$1.$2');price.style.cssText='white-space:nowrap;letter-spacing:0;font-family:Arial,sans-serif';title.append(price,document.createTextNode(' Great Clips Offer'));}else title.textContent='Your Great Clips coupon';
  section.querySelector('.gc-selected-location').textContent=offer.location?offer.location.replace(/,+/g,','):'See the official offer for participating locations.';
  section.querySelector('[role="status"]').textContent='';
 }
 function install(){
  for(const id of ['emailFormView','gcFormView']){
   const host=document.getElementById(id),form=host?.querySelector('form');
   if(!form)continue;
   if(!host.classList.contains('gc-coupon-form'))host.classList.add('gc-coupon-form');
   if(!host.parentElement.classList.contains('gc-coupon-panel'))host.parentElement.classList.add('gc-coupon-panel');
   const existing=host.querySelector('.gc-whatsapp-option');
   if(existing){updateOffer(existing,id);existing.querySelector('button').disabled=!enabled||!assignmentReady||existing.dataset.busy==='true';applyVariation(host);continue;}
   const heading=host.querySelector('h3');if(heading)heading.textContent='Get Your Great Clips Coupon on WhatsApp';
   const intro=heading?.nextElementSibling;if(intro?.tagName==='P'){intro.hidden=false;intro.textContent='Join my deals group to get this coupon—and discover more haircut savings and Amazon deals.';}
   const section=document.createElement('div');section.className='gc-whatsapp-option';
   section.style.cssText='margin:0;text-align:center';
   const offer=document.createElement('div');offer.style.cssText='text-align:left;background:linear-gradient(120deg,#f3ecff,#f5f0fd);border:1px solid #e0d2ff;border-radius:14px;padding:17px 18px;margin:0 0 20px';
   const label=document.createElement('p');label.textContent='Your Selected Coupon';label.style.cssText='text-transform:uppercase;font-size:11px;letter-spacing:.04em;font-weight:800;color:#7c3aed;margin:0 0 5px';
   const title=document.createElement('p');title.className='gc-selected-title';title.style.cssText='font-size:23px;font-weight:800;color:#0f172a;line-height:1.3;margin:0';
   const location=document.createElement('p');location.className='gc-selected-location';location.style.cssText='font-size:14px;line-height:1.5;color:#64748b;margin:5px 0 0';
   offer.append(label,title,location);
   const button=document.createElement('button');button.disabled=!enabled||!assignmentReady;button.type='button';button.className='gc-chat-cta';
   button.innerHTML='<svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor"><path d="M20.52 3.48A11.87 11.87 0 0 0 12.05 0C5.47 0 .12 5.35.12 11.93c0 2.1.55 4.15 1.59 5.96L0 24l6.27-1.64a11.9 11.9 0 0 0 5.78 1.47h.01C18.63 23.83 24 18.48 24 11.9c0-3.18-1.24-6.17-3.48-8.42ZM12.06 21.8a9.9 9.9 0 0 1-5.05-1.38l-.36-.22-3.72.98.99-3.63-.24-.37a9.88 9.88 0 0 1-1.52-5.25c0-5.46 4.45-9.91 9.91-9.91a9.85 9.85 0 0 1 7.01 2.91 9.85 9.85 0 0 1 2.9 7.01c0 5.46-4.45 9.86-9.92 9.86Zm5.43-7.4c-.3-.15-1.76-.87-2.03-.96-.27-.1-.47-.15-.67.15-.2.3-.77.96-.94 1.16-.17.2-.35.22-.64.07-.3-.15-1.26-.46-2.4-1.48-.89-.8-1.49-1.78-1.66-2.08-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.03-.52-.07-.15-.67-1.61-.92-2.21-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.07 2.87 1.22 3.07.15.2 2.1 3.21 5.09 4.5.71.3 1.27.49 1.71.63.72.23 1.37.2 1.88.12.57-.08 1.76-.72 2.01-1.41.25-.69.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35Z"/></svg><span>Join &amp; Get My Coupon</span><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m9 5 7 7-7 7"/></svg>';
   const note=document.createElement('ol');note.className='gc-steps';
   for(const [i,text] of ['Join our WhatsApp group','Tap “I’ve joined” to get your coupon'].entries()){const li=document.createElement('li'),number=document.createElement('span'),copy=document.createElement('span');number.className='gc-step-number';number.textContent=String(i+1);number.setAttribute('aria-hidden','true');copy.textContent=text;li.append(number,copy);note.append(li);}
   const reassurance=document.createElement('p');reassurance.textContent='Opens WhatsApp · Leave anytime';reassurance.style.cssText='font-size:13px;color:#74839c;margin:22px 0 0';
   const status=document.createElement('p');status.setAttribute('role','status');status.style.cssText='font-size:14px;color:#64748b';if(loaded&&!enabled)status.textContent='WhatsApp is temporarily unavailable. Please try again later.';
   button.onclick=async()=>{
    const url=id==='emailFormView'?(typeof pendingCouponUrl==='undefined'?'':pendingCouponUrl):window.gcPending?.url;
    if(!url||!enabled||!assignmentReady)return;
    if(isPreview){status.textContent='Preview only. No message is sent.';return;}
    didClick=true;track('click');
    section.dataset.busy='true';button.disabled=true;status.textContent='Opening WhatsApp…';
    const chat=window.open('about:blank','_blank');if(chat)chat.opener=null;
    try{
     const r=await fetch(api+'/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({coupon_url:url,...(cohort.tracked?{experiment_id:experimentId,experiment_visitor:cohort.visitor_id}:{})}),signal:AbortSignal.timeout(15000)});
     const d=await r.json();if(!r.ok)throw new Error(d.error||'WhatsApp is unavailable. Please try again later.');
     if(!/^https:\/\/wa\.me\/\d+\?/.test(d.whatsapp_url))throw new Error('WhatsApp is unavailable. Please try again later.');
     if(chat&&!chat.closed)chat.location.replace(d.whatsapp_url);else window.location.assign(d.whatsapp_url);
     status.textContent='Tap Send in WhatsApp to continue.';
    }catch(error){if(chat&&!chat.closed)chat.close();status.textContent='Unable to open WhatsApp. Please try again.';}
    finally{delete section.dataset.busy;button.disabled=!enabled;}
   };
   section.append(offer,note,button,reassurance,status);form.before(section);updateOffer(section,id);applyVariation(host);
  }
  trackVisibility();
 }
 install();new MutationObserver(install).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["class"]});
 assign();
 if(isPreview){enabled=true;loaded=true;install();return;}
 fetch(api+'/config',{cache:'no-store',signal:AbortSignal.timeout(4000)}).then(r=>r.json()).then(c=>{enabled=c.enabled===true;loaded=true;install();if(!enabled)unavailable();}).catch(()=>{loaded=true;unavailable();});
 function unavailable(){for(const p of document.querySelectorAll('.gc-whatsapp-option [role="status"]'))p.textContent='WhatsApp is temporarily unavailable. Please try again later.';}
})();
