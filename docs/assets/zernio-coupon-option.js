(() => {
 if(window.gcZernioOption)return;window.gcZernioOption=true;
 const api='https://greatclips-email.mehulchaudhari.workers.dev/zernio';
 let enabled=false,loaded=false;
 const style=document.createElement("style");style.textContent="#emailFormView > form,#emailFormView > button,#emailFormView > p,#gcFormView > form,#gcFormView > button,#gcFormView > p{display:none!important}";document.head.append(style);
 function install(){
  for(const id of ['emailFormView','gcFormView']){
   const host=document.getElementById(id),form=host?.querySelector('form');
   if(!form)continue;
   const existing=host.querySelector('.gc-whatsapp-option');
   if(existing){existing.querySelector('button').disabled=!enabled||existing.dataset.busy==='true';continue;}
   const heading=host.querySelector('h3');if(heading)heading.textContent='Get Your Great Clips Coupon on WhatsApp';
   const intro=heading?.nextElementSibling;if(intro?.tagName==='P'){intro.hidden=false;intro.textContent='Save on your next haircut. Join my deals group for your Great Clips coupon, plus Amazon finds and big coupon stacks.';}
   const section=document.createElement('div');section.className='gc-whatsapp-option';
   section.style.cssText='margin:0;text-align:center';
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
   section.append(button,note,reassurance,status);form.before(section);
  }
 }
 install();new MutationObserver(install).observe(document.body,{childList:true,subtree:true});
 fetch(api+'/config',{cache:'no-store',signal:AbortSignal.timeout(4000)}).then(r=>r.json()).then(c=>{enabled=c.enabled===true;loaded=true;install();if(!enabled)unavailable();}).catch(()=>{loaded=true;unavailable();});
 function unavailable(){for(const p of document.querySelectorAll('.gc-whatsapp-option [role="status"]'))p.textContent='WhatsApp is temporarily unavailable. Please try again later.';}
})();
