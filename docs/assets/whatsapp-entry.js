// Shared entry point for the homepage and generated salon pages.
(() => {
  const config=fetch('https://greatclips-email.mehulchaudhari.workers.dev/whatsapp/config',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error();return r.json();});
  config.catch(()=>{});
  for(const name of ['getCoupon','gcOpenModal']){
    const original=window[name];if(typeof original!=='function')continue;
    window[name]=async function(...args){
      let c;
      try{c=await config;}catch{alert('Unable to load coupon delivery. Please try again shortly.');return;}
      if(!c.enabled)return original.apply(this,args);
      const url=name==='getCoupon'?args[0]:args[0]?.url;
      if(url)location.href='/whatsapp-coupon.html?coupon='+encodeURIComponent(url);
    };
  }
})();
