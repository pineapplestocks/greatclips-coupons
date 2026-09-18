// A single popup shared by the homepage and salon pages.
(() => {
  if(window.gcWhatsAppPopup)return;
  window.gcWhatsAppPopup=true;
  const api='https://greatclips-email.mehulchaudhari.workers.dev/whatsapp';
  const css=document.createElement('link');css.rel='stylesheet';css.href='/assets/whatsapp-popup.css?v=4';document.head.append(css);
  const waIcon='<svg class="wa-brand-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none"><path d="M20.4 3.6a11 11 0 0 0-17.3 13L1.5 22.5l6-1.6A11 11 0 0 0 20.4 3.6Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M8.4 6.5c-.3-.6-.6-.6-.9-.6h-.7c-.3 0-.6.1-.8.4-.3.3-1 1-1 2.4s1.1 2.8 1.2 3c.2.2 2.1 3.3 5.2 4.5 2.6 1 3.1.8 3.7.8.6-.1 1.8-.8 2.1-1.5.3-.7.3-1.3.2-1.4-.1-.2-.3-.3-.7-.5l-2.1-1c-.3-.1-.6-.2-.8.2l-.9 1.1c-.2.2-.4.3-.7.1-1.1-.5-2-1-2.9-2-.8-.8-1.2-1.5-1.3-1.8-.2-.3 0-.5.1-.7l.5-.6.3-.5c.1-.2.1-.4 0-.6l-.9-2.3Z" fill="currentColor"/></svg>';
  function buttonLabel(node,text){node.innerHTML=waIcon;const label=document.createElement('span');label.textContent=text;node.append(label);const arrow=document.createElement('span');arrow.className='wa-arrow';arrow.setAttribute('aria-hidden','true');arrow.textContent='→';node.append(arrow);}
  let dialog,coupon,config,record,pending=false,poll,opener;
  const el=id=>document.getElementById('wa-'+id);
  const terminal=['sent','uncertain','cancelled','rejected','unavailable','expired'];
  const saved=url=>{try{return JSON.parse(sessionStorage.getItem('wa-coupon:'+url)||'null');}catch{return null;}};
  function build(){
    if(dialog)return;
    dialog=document.createElement('dialog');dialog.id='waCouponDialog';dialog.setAttribute('aria-labelledby','wa-title');dialog.setAttribute('tabindex','-1');
    dialog.innerHTML=`<button id="wa-close" class="wa-close" aria-label="Close coupon popup">×</button>
      <div class="wa-icon" aria-hidden="true">✂</div>
      <h2 id="wa-title">Get your <span style="white-space:nowrap">Great Clips</span> Coupon!</h2>
      <p class="wa-copy" id="wa-description">Message us, join our deals group, and get your coupon.</p>
      <button id="wa-start" class="wa-primary">Text My Coupon on WhatsApp</button>
      <a id="wa-open" class="wa-primary" target="_blank" rel="noopener noreferrer" hidden>Open WhatsApp ↗</a>
      <p id="wa-status" class="wa-status" role="status" aria-live="polite"></p>
      <button id="wa-retry" class="wa-retry" hidden>Try again</button>`;
    document.body.append(dialog);
    buttonLabel(el('start'),'Text My Coupon on WhatsApp');
    el('close').onclick=()=>dialog.close();
    dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
    dialog.addEventListener('close',()=>{clearInterval(poll);opener?.focus();});
    el('start').onclick=begin;el('retry').onclick=load;
  }
  function resume(){
    const chat=new URL(record.whatsapp_url);chat.searchParams.set('text','Send me this coupon\nGC-'+record.id);record.whatsapp_url=chat.href;
    el('start').hidden=true;el('open').hidden=false;el('open').href=record.whatsapp_url;
    buttonLabel(el('open'),'Text My Coupon on WhatsApp');
    el('status').textContent='Send the prepared message. The bot will reply with your group invite.';
    clearInterval(poll);poll=setInterval(status,5000);status();
  }
  async function status(){
    const current=record;if(!current||!dialog.open)return;
    try{
      const r=await fetch(api+'/status',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+current.token},body:JSON.stringify({id:current.id})});
      if(!r.ok)return;const d=await r.json();if(record!==current)return;
      const copy={awaiting_message:'Send the prepared message in WhatsApp to receive the group invite.',awaiting_join:'Your request is linked. Join the group with the same number to receive your coupon.',ready:'Membership confirmed. Your coupon is being sent automatically.',sending:'Sending your coupon. Check your private WhatsApp chat.',sent:'Coupon sent! Check your private WhatsApp chat.',uncertain:'Your delivery needs checking. Please reply in your WhatsApp chat for help.',cancelled:'This request was cancelled.',rejected:'This request was closed.',unavailable:'This coupon is no longer available. Please choose another offer.',expired:'This request expired. Close this popup and choose a current coupon.'};
      el('status').textContent=copy[d.status]||'Checking your request...';
      if(d.status==='awaiting_join'){el('open').href=current.group_invite;buttonLabel(el('open'),'Join WhatsApp group');}
      el('open').hidden=!['awaiting_message','awaiting_join'].includes(d.status);
      if(terminal.includes(d.status)){clearInterval(poll);if(['cancelled','rejected','expired','unavailable'].includes(d.status)){try{sessionStorage.removeItem('wa-coupon:'+coupon);}catch{}}}
    }catch{/* The bot continues privately even if the page cannot refresh. */}
  }
  async function load(){
    const selected=coupon;el('retry').hidden=true;el('start').disabled=true;el('status').textContent='Connecting to WhatsApp delivery…';
    try{
      const r=await fetch(api+'/config',{cache:'no-store'});if(!r.ok)throw new Error('Unable to connect. Please try again.');
      const c=await r.json();if(coupon!==selected)return;config=c;
      if(!c.enabled||!c.online)throw new Error('Delivery is temporarily offline. Please try again shortly.');
      el('status').textContent='';el('start').disabled=false;
    }catch(e){if(coupon!==selected)return;el('status').textContent=e.message;el('retry').hidden=false;}
  }
  async function begin(){
    if(pending||!config?.online)return;
    pending=true;el('start').disabled=true;el('status').textContent='Preparing your WhatsApp message…';
    const selected=coupon;
    // Open during the click so mobile popup blockers cannot swallow the chat.
    const chat=window.open('about:blank','_blank');if(chat)chat.opener=null;
    try{
      const r=await fetch(api+'/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({coupon_url:selected,consent:true,consent_version:config.consent_version})});
      const d=await r.json();if(!r.ok)throw new Error(d.error||'Unable to create your request.');
      try{sessionStorage.setItem('wa-coupon:'+selected,JSON.stringify(d));}catch{}
      if(coupon===selected){record=d;resume();}
      if(chat&&!chat.closed)chat.location.replace(d.whatsapp_url);else window.location.assign(d.whatsapp_url);
    }catch(e){if(chat&&!chat.closed)chat.close();if(coupon===selected){el('status').textContent=e.message;el('start').disabled=false;}}
    finally{pending=false;}
  }
  function open(url){
    if(pending)return;
    build();opener=document.activeElement;coupon=url;config=null;record=saved(url);clearInterval(poll);
    el('start').hidden=false;el('open').hidden=true;el('retry').hidden=true;dialog.showModal();
    if(record)resume();else load();
    dialog.focus({preventScroll:true});
  }
  for(const name of ['getCoupon','gcOpenModal']){
    if(typeof window[name]!=='function')continue;
    window[name]=function(...args){const url=name==='getCoupon'?args[0]:args[0]?.url;if(url)open(url);};
  }
})();
