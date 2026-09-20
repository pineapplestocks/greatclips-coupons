(() => {
 if(window.gcZernioOption)return;window.gcZernioOption=true;
 const api='https://greatclips-email.mehulchaudhari.workers.dev/zernio';
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
  section.querySelector('.gc-selected-title').textContent=offer.price?offer.price+' Great Clips offer':'Your Great Clips coupon';
  section.querySelector('.gc-selected-location').textContent=offer.location?offer.location.replace(/,+/g,','):'See the official offer for participating locations.';
  section.querySelector('[role="status"]').textContent='';
 }
 function install(){
  for(const id of ['emailFormView','gcFormView']){
   const host=document.getElementById(id),form=host?.querySelector('form');
   if(!form)continue;
   const existing=host.querySelector('.gc-whatsapp-option');
   if(existing){updateOffer(existing,id);existing.querySelector('button').disabled=!enabled||existing.dataset.busy==='true';continue;}
   const heading=host.querySelector('h3');if(heading)heading.textContent='Get Your Great Clips Coupon on WhatsApp';
   const intro=heading?.nextElementSibling;if(intro?.tagName==='P'){intro.hidden=false;intro.textContent='Join my deals group to get this coupon—and discover more haircut savings and Amazon deals.';}
   const section=document.createElement('div');section.className='gc-whatsapp-option';
   section.style.cssText='margin:0;text-align:center';
   const offer=document.createElement('div');offer.style.cssText='text-align:left;background:#f5f0ff;border:1px solid #e5d9ff;border-radius:14px;padding:15px 16px;margin:0 0 18px';
   const label=document.createElement('p');label.textContent='Your Selected Coupon';label.style.cssText='font-size:11px;letter-spacing:.08em;font-weight:800;color:#7c3aed;margin:0 0 5px';
   const title=document.createElement('p');title.className='gc-selected-title';title.style.cssText='font-size:20px;font-weight:800;color:#0f172a;line-height:1.3;margin:0';
   const location=document.createElement('p');location.className='gc-selected-location';location.style.cssText='font-size:14px;line-height:1.5;color:#64748b;margin:5px 0 0';
   offer.append(label,title,location);
   const button=document.createElement('button');button.disabled=!enabled;button.type='button';button.textContent='Text My Coupon on WhatsApp';
   button.style.cssText='width:100%;padding:15px 12px;border:0;border-radius:12px;background:#08ad59;color:white;font:inherit;font-weight:800;cursor:pointer';
   const note=document.createElement('p');note.textContent='Send your request, join the group, then tap “I’ve joined” to get your coupon.';
   note.style.cssText='font-size:14px;line-height:1.5;color:#64748b;margin:10px 0';
   const reassurance=document.createElement('p');reassurance.textContent='Free to join · Leave anytime';reassurance.style.cssText='font-size:13px;color:#64748b;margin:12px 0 0';
   const status=document.createElement('p');status.setAttribute('role','status');status.style.cssText='font-size:14px;color:#64748b';if(loaded&&!enabled)status.textContent='WhatsApp is temporarily unavailable. Please try again later.';
   button.onclick=async()=>{
    const url=id==='emailFormView'?(typeof pendingCouponUrl==='undefined'?'':pendingCouponUrl):window.gcPending?.url;
    if(!url||!enabled)return;
    section.dataset.busy='true';button.disabled=true;status.textContent='Opening WhatsApp…';
    const chat=window.open('about:blank','_blank');if(chat)chat.opener=null;
    try{
     const r=await fetch(api+'/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({coupon_url:url}),signal:AbortSignal.timeout(15000)});
     const d=await r.json();if(!r.ok)throw new Error(d.error||'WhatsApp is unavailable. Please try again later.');
     if(!/^https:\/\/wa\.me\/\d+\?/.test(d.whatsapp_url))throw new Error('WhatsApp is unavailable. Please try again later.');
     if(chat&&!chat.closed)chat.location.replace(d.whatsapp_url);else window.location.assign(d.whatsapp_url);
     status.textContent='Tap Send in WhatsApp to continue.';
    }catch(error){if(chat&&!chat.closed)chat.close();status.textContent='Unable to open WhatsApp. Please try again.';}
    finally{delete section.dataset.busy;button.disabled=!enabled;}
   };
   section.append(offer,button,note,reassurance,status);form.before(section);updateOffer(section,id);
  }
 }
 install();new MutationObserver(install).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["class"]});
 fetch(api+'/config',{cache:'no-store',signal:AbortSignal.timeout(4000)}).then(r=>r.json()).then(c=>{enabled=c.enabled===true;loaded=true;install();if(!enabled)unavailable();}).catch(()=>{loaded=true;unavailable();});
 function unavailable(){for(const p of document.querySelectorAll('.gc-whatsapp-option [role="status"]'))p.textContent='WhatsApp is temporarily unavailable. Please try again later.';}
})();
