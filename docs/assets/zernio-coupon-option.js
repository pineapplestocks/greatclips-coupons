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
 const style=document.createElement("style");style.textContent="#emailFormView > form,#emailFormView > button,#emailFormView > p,#gcFormView > form,#gcFormView > button,#gcFormView > p{display:none!important}";document.head.append(style);
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
  if(offer.price){const price=document.createElement('span');price.textContent=String(offer.price).replace(/(\d)\.\s+(\d)/g,'$1.$2');price.style.cssText='white-space:nowrap;letter-spacing:0;font-family:Arial,sans-serif';title.append(price,document.createTextNode(' Great Clips offer'));}else title.textContent='Your Great Clips coupon';
  section.querySelector('.gc-selected-location').textContent=offer.location?offer.location.replace(/,+/g,','):'See the official offer for participating locations.';
  section.querySelector('[role="status"]').textContent='';
 }
 function install(){
  for(const id of ['emailFormView','gcFormView']){
   const host=document.getElementById(id),form=host?.querySelector('form');
   if(!form)continue;
   const existing=host.querySelector('.gc-whatsapp-option');
   if(existing){updateOffer(existing,id);existing.querySelector('button').disabled=!enabled||!assignmentReady||existing.dataset.busy==='true';applyVariation(host);continue;}
   const heading=host.querySelector('h3');if(heading)heading.textContent='Get Your Great Clips Coupon on WhatsApp';
   const intro=heading?.nextElementSibling;if(intro?.tagName==='P'){intro.hidden=false;intro.textContent='Join my deals group to get this coupon—and discover more haircut savings and Amazon deals.';}
   const section=document.createElement('div');section.className='gc-whatsapp-option';
   section.style.cssText='margin:0;text-align:center';
   const offer=document.createElement('div');offer.style.cssText='text-align:left;background:#f5f0ff;border:1px solid #e5d9ff;border-radius:14px;padding:15px 16px;margin:0 0 18px';
   const label=document.createElement('p');label.textContent='Your Selected Coupon';label.style.cssText='font-size:11px;letter-spacing:.08em;font-weight:800;color:#7c3aed;margin:0 0 5px';
   const title=document.createElement('p');title.className='gc-selected-title';title.style.cssText='font-size:20px;font-weight:800;color:#0f172a;line-height:1.3;margin:0';
   const location=document.createElement('p');location.className='gc-selected-location';location.style.cssText='font-size:14px;line-height:1.5;color:#64748b;margin:5px 0 0';
   offer.append(label,title,location);
   const button=document.createElement('button');button.disabled=!enabled||!assignmentReady;button.type='button';button.textContent='Text My Coupon on WhatsApp';
   button.style.cssText='width:100%;padding:15px 12px;border:0;border-radius:12px;background:#08ad59;color:white;font:inherit;font-weight:800;cursor:pointer';
   const note=document.createElement('p');note.textContent='1: Join Group\n2: Receive Text with Coupon';
   note.style.cssText='font-size:16px;font-weight:700;line-height:1.8;white-space:pre-line;color:#334155;margin:0 0 16px';
   const reassurance=document.createElement('p');reassurance.textContent='After joining, tap “I’ve joined” in WhatsApp to receive your coupon.';reassurance.style.cssText='font-size:13px;color:#64748b;margin:12px 0 0';
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
