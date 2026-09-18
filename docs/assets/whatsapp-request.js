(() => {
  const api='https://greatclips-email.mehulchaudhari.workers.dev/whatsapp';
  const el=id=>document.getElementById(id);
  const coupon=new URLSearchParams(location.search).get('coupon');
  let config,record,timer;
  const terminal=['sent','uncertain','rejected','cancelled','unavailable','expired'];
  el('consent').onchange=()=>{el('begin').disabled=!(config?.enabled&&config?.online&&el('consent').checked);};
  const messages={expired:'This request is older than seven days. Choose a current coupon and start again.',awaiting_message:'Send the prefilled request in WhatsApp so we can match your number to your selected coupon.',awaiting_join:'Your request is linked. Join Deal Dropper with the same WhatsApp number. Membership checks run about once a minute.',ready:'Your group membership is confirmed. Your coupon will be sent automatically.',sending:'Your coupon is being sent. Please check your WhatsApp chat.',sent:'Your coupon was sent to your WhatsApp chat. Check the official terms before visiting.',uncertain:'We are checking the delivery result. Please do not submit another request.',rejected:'This request was closed. You can reply in your WhatsApp chat for help.',cancelled:'Your request was cancelled.',unavailable:'This coupon is no longer available. Return to the website to choose a current offer.'};
  async function status(){
    if(!record)return;
    try{
      const r=await fetch(api+'/status',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+record.token},body:JSON.stringify({id:record.id})});
      const data=await r.json();if(!r.ok)throw new Error(data.error);
      el('status').textContent=messages[data.status]||'Checking your request...';
      const stage=data.status==='awaiting_message'?0:data.status==='awaiting_join'?1:2;
      ['message','join','delivery'].forEach((name,i)=>{el('step-'+name).className=i<stage||data.status==='sent'?'done':i===stage?'active':'';});
      el('message').hidden=stage>0;
      el('join').hidden=stage!==1;
      el('another').hidden=!terminal.includes(data.status);
      if(terminal.includes(data.status)){clearInterval(timer);el('message').hidden=true;el('join').hidden=true;}
      el('connection').textContent=data.status==='sent'?'Coupon sent':'Request saved';
      el('connection').className='connection online';
    }catch(e){el('status').textContent='Unable to refresh the status right now. Your request is saved; check WhatsApp or refresh this page.';}
  }
  function show(){el('start').hidden=true;el('progress').hidden=false;el('selected').textContent='Your coupon is on its way.';el('offer-name').textContent=record.label;el('message').href=record.whatsapp_url;el('join').href=record.group_invite;el('reference').textContent='Request GC-'+record.id;clearInterval(timer);timer=setInterval(status,15000);status();}
  el('begin').onclick=async()=>{
    if(!el('consent').checked)return;
    el('begin').disabled=true;el('error').textContent='';
    try{
      const r=await fetch(api+'/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({coupon_url:coupon,consent:true,consent_version:config.consent_version})});
      const data=await r.json();if(!r.ok)throw new Error(data.error);
      record=data;try{sessionStorage.setItem('wa-coupon:'+coupon,JSON.stringify(record));}catch{}
      show();
      // A real link is used after the network request so mobile popup blocking cannot lose the request.
      el('message').focus();
    }catch(e){el('error').textContent=e.message;el('begin').disabled=false;}
  };
  try{record=JSON.parse(sessionStorage.getItem('wa-coupon:'+coupon)||'null');}catch{}
  if(record){show();return;}
  async function availability(){
    el('retry').hidden=true;el('error').textContent='';el('begin').disabled=true;
    el('connection').textContent='Checking availability';
    try{
      const r=await fetch(api+'/config',{cache:'no-store'});if(!r.ok)throw new Error('Unable to check delivery. Please try again.');
      config=await r.json();
      if(!coupon)throw new Error('Choose a coupon on the website first.');
      if(!config.enabled||!config.online)throw new Error('WhatsApp delivery is temporarily offline. Please check again shortly.');
      el('connection').textContent='Delivery online';el('connection').className='connection online';
      el('begin').disabled=!el('consent').checked;
    }catch(e){el('error').textContent=e.message;el('connection').textContent='Delivery unavailable';el('connection').className='connection offline';el('retry').hidden=false;config=null;}
  }
  el('retry').onclick=availability;
  availability();
  fetch('/data/coupons.json').then(r=>r.json()).then(feed=>{
    const offer=feed.coupons?.find(c=>c.url===coupon);if(!offer)return;
    const place=[offer.address,offer.city?.replace(/,+$/,''),offer.state==='AREA'?'':offer.state].filter(Boolean).join(', ')||offer.area_name||offer.location_name;
    el('offer-name').textContent='Great Clips coupon'+(place?' · '+place:'');
  }).catch(()=>{});
})();
