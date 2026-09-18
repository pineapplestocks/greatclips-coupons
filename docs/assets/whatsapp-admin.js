(() => {
  const el=id=>document.getElementById(id);let token='';
  async function api(body){const r=await fetch('https://greatclips-email.mehulchaudhari.workers.dev/whatsapp/admin',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw new Error(d.error);return d;}
  function node(tag,text,cls){const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;}
  async function load(){
    el('error').textContent='';
    try{
      const data=await api({action:'list'});el('login').hidden=true;el('controls').hidden=false;el('requests').hidden=false;el('requests').replaceChildren();
      if(!data.requests.length)el('requests').append(node('p','No coupon requests yet.'));
      for(const r of data.requests){
        const card=node('article',null,'request');card.append(node('span',r.status.replaceAll('_',' '),'badge'),node('h2',r.coupon_label));
        card.append(node('p',(r.display_name||'Waiting for WhatsApp message')+(r.wa_id?' · +'+r.wa_id:'')));
        card.append(node('p','GC-'+r.id+' · '+new Date(r.created_at).toLocaleString(),'meta'));
        card.append(node('p',r.member_verified?'Member confirmed: '+new Date(r.member_checked_at).toLocaleString():'Membership not confirmed','note'));
        if(r.error)card.append(node('p',r.error,'error'));
        const actions=node('div',null,'actions');
        if(r.status==='awaiting_approval'){
          const label=node('label',null,'consent'),check=node('input');check.type='checkbox';label.append(check,node('span','I checked this number in Deal Dropper and approve sending this selected coupon.'));card.append(label);
          const approve=node('button','Approve & send','primary');approve.disabled=true;check.onchange=()=>approve.disabled=!check.checked;
          approve.onclick=async()=>{approve.disabled=true;try{await api({action:'approve',id:r.id,confirmed:check.checked});await load();}catch(e){el('error').textContent=e.message;approve.disabled=false;}};actions.append(approve);
        }
        if(['awaiting_message','awaiting_join','awaiting_approval','approved'].includes(r.status)){
          const reject=node('button','Reject','secondary');reject.onclick=async()=>{reject.disabled=true;try{await api({action:'reject',id:r.id});await load();}catch(e){el('error').textContent=e.message;reject.disabled=false;}};actions.append(reject);
        }
        if(r.status==='sending'||r.status==='uncertain')card.append(node('p','Do not send again until you check the WhatsApp chat and delivery record.','note'));
        card.append(actions);el('requests').append(card);
      }
    }catch(e){el('error').textContent=e.message;}
  }
  el('unlock').onclick=()=>{token=el('token').value.trim();el('token').value='';load();};el('refresh').onclick=load;
  el('logout').onclick=()=>{token='';el('requests').replaceChildren();el('requests').hidden=true;el('controls').hidden=true;el('login').hidden=false;};
})();
