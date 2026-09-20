(() => {
 if(window.gcZernioOption)return;window.gcZernioOption=true;
 const api='https://greatclips-email.mehulchaudhari.workers.dev/zernio';
 let enabled=false;
 function install(){
  if(!enabled)return;
  for(const id of ['emailFormView','gcFormView']){
   const host=document.getElementById(id),form=host?.querySelector('form');
   if(!form||host.querySelector('.gc-whatsapp-option'))continue;
   const heading=host.querySelector('h3');if(heading)heading.textContent='Get your Great Clips Coupon!';
   const intro=heading?.nextElementSibling;if(intro?.tagName==='P')intro.textContent='Choose WhatsApp or email.';
   const section=document.createElement('div');section.className='gc-whatsapp-option';
   section.style.cssText='margin:0 0 18px;text-align:center';
   const button=document.createElement('button');button.type='button';button.textContent='Text My Coupon on WhatsApp';
   button.style.cssText='width:100%;padding:15px 12px;border:0;border-radius:12px;background:#08ad59;color:white;font:inherit;font-weight:800;cursor:pointer';
   const note=document.createElement('p');note.textContent='Message me, join my deals group, then tap “I’ve joined” in WhatsApp to get your coupon.';
   note.style.cssText='font-size:14px;line-height:1.5;color:#64748b;margin:10px 0';
   const status=document.createElement('p');status.setAttribute('role','status');status.style.cssText='font-size:14px;color:#64748b';
   const divider=document.createElement('p');divider.textContent='Or get it by email';divider.style.cssText='font-size:13px;color:#64748b;margin:15px 0 0';
   button.onclick=async()=>{
    const url=id==='emailFormView'?(typeof pendingCouponUrl==='undefined'?'':pendingCouponUrl):window.gcPending?.url;
    if(!url)return;
    button.disabled=true;status.textContent='Opening WhatsApp…';
    const chat=window.open('about:blank','_blank');if(chat)chat.opener=null;
    try{
     const r=await fetch(api+'/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({coupon_url:url}),signal:AbortSignal.timeout(15000)});
     const d=await r.json();if(!r.ok)throw new Error(d.error||'Please use email below.');
     if(!/^https:\/\/wa\.me\/\d+\?/.test(d.whatsapp_url))throw new Error('Please use email below.');
     if(chat&&!chat.closed)chat.location.replace(d.whatsapp_url);else window.location.assign(d.whatsapp_url);
     status.textContent='Tap Send in WhatsApp, then follow the group invitation.';
    }catch(error){if(chat&&!chat.closed)chat.close();status.textContent=error.message;}
    finally{button.disabled=false;}
   };
   section.append(button,note,status,divider);form.before(section);
  }
 }
 fetch(api+'/config',{cache:'no-store',signal:AbortSignal.timeout(4000)}).then(r=>r.json()).then(c=>{enabled=c.enabled===true;if(enabled){install();new MutationObserver(install).observe(document.body,{childList:true,subtree:true});}}).catch(()=>{});
})();
