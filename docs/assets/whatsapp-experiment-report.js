(() => {
  const el=id=>document.getElementById(id);let token='',data;
  const pct=n=>(100*n).toFixed(1)+'%';
  const date=n=>new Date(n).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
  function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
  function render(){
    if(!data)return;
    el('login').hidden=true;el('report').hidden=false;
    el('dates').textContent='Enrollment: '+date(data.starts_at)+' – '+date(data.ends_at);
    el('verdict').textContent=data.verdict.text;
    el('review').textContent='Final review: '+date(data.analysis_at)+'. '+(data.active?'Collecting new visitors.':data.archived?'Final aggregate report saved.':'Enrollment closed; conversions may still arrive.');
    const rows=el('mature').checked?data.mature:data.live;
    el('variants').replaceChildren();el('funnel').replaceChildren();
    for(const r of rows){
      const card=node('article',undefined,'variant');card.append(node('span',r.variant,'letter'),node('h2',data.variants[r.variant].name));
      card.append(node('div',r.viewers?pct(r.membership_rate):'—','rate'),node('p','Membership conversion','note'));
      card.append(node('p',r.members+' verified / '+r.viewers+' popup viewers','note'));
      const bar=node('div',undefined,'bar'),fill=node('span');fill.style.width=pct(r.membership_rate);bar.append(fill);card.append(bar);
      card.append(node('p',r.clicks+' clicked · '+r.no_click+' have not clicked','note'));
      const link=node('a','Preview '+r.variant+' (not tracked)','preview');link.href='/whatsapp-preview.html?wa_preview='+r.variant;link.target='_blank';link.rel='noopener noreferrer';card.append(link);el('variants').append(card);
      const row=node('tr');for(const value of [r.variant,r.viewers,r.clicks,r.no_click,r.messages,r.members,r.observed_joins,r.existing_members,r.delivered,r.viewers?pct(r.click_rate):'—',r.viewers?pct(r.membership_rate):'—',r.viewers?r.interval.map(pct).join(' – '):'—'])row.append(node('td',String(value)));el('funnel').append(row);
    }
    el('updated').textContent='Updated '+new Date(data.updated_at).toLocaleString()+'. Refresh to load the latest results.';
  }
  async function load(){
    el('error').textContent='';el('unlock').disabled=true;
    try{const r=await fetch('https://greatclips-email.mehulchaudhari.workers.dev/whatsapp/experiment/report',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:'{}'});const result=await r.json();if(!r.ok||result.error)throw new Error(result.error||'Unable to load results.');data=result;render();}
    catch(e){el('error').textContent=e.message;}finally{el('unlock').disabled=false;}
  }
  el('unlock').onclick=()=>{token=el('access').value.trim();el('access').value='';load();};el('access').addEventListener('keydown',e=>{if(e.key==='Enter')el('unlock').click();});el('refresh').onclick=load;el('mature').onchange=render;
  el('lock').onclick=()=>{token='';data=null;el('report').hidden=true;el('login').hidden=false;el('variants').replaceChildren();el('funnel').replaceChildren();};
  el('download').onclick=()=>{if(!data)return;const keys=['variant','viewers','clicks','no_click','messages','members','observed_joins','existing_members','delivered','click_rate','membership_rate'];const rows=el('mature').checked?data.mature:data.live;const csv=[keys.join(','),...rows.map(r=>keys.map(k=>r[k]).join(','))].join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));const a=document.createElement('a');a.href=url;a.download=data.experiment_id+(el('mature').checked?'-mature':'-live')+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
})();
