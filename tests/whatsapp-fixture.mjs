import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { handleWhatsApp } from '../cloudflare-worker/whatsapp.js';
export const url='https://offers.greatclips.com/test123';
export function setup() {
  const db=new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../cloudflare-worker/migrations/002_whatsapp_coupon_requests.sql',import.meta.url),'utf8'));
  db.exec(readFileSync(new URL('../cloudflare-worker/migrations/003_whatsapp_automatic_delivery.sql',import.meta.url),'utf8'));
  db.exec(readFileSync(new URL('../cloudflare-worker/migrations/004_whatsapp_short_references.sql',import.meta.url),'utf8'));
  db.exec(readFileSync(new URL('../cloudflare-worker/migrations/005_whatsapp_experiment.sql',import.meta.url),'utf8'));
  const env={ADMIN_TOKEN:'admin-test',WHATSAPP_BRIDGE_TOKEN:'bridge-test',WHATSAPP_COUPONS_ENABLED:'true',WHATSAPP_EXPERIMENT_ENABLED:'true',DB:{
    prepare(sql) { return { bind(...args) {
      const s=db.prepare(sql);
      return {first:async()=>s.get(...args),all:async()=>({results:s.all(...args)}),run:async()=>({meta:{changes:Number(s.run(...args).changes)}})};
    } }; }
  }};
  const call=async(path,data,token,origin='https://greatclipsdeal.com')=>{
    const response=await handleWhatsApp(new Request('https://worker.test/whatsapp/'+path,{method:'POST',headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.1','Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(data)}),env);
    return {status:response.status,data:await response.json()};
  };
  const bridge=b=>call('bridge',b,'bridge-test');
  const admin=b=>call('admin',b,'admin-test');
  const create=()=>call('requests',{coupon_url:url,consent:true,consent_version:'whatsapp-group-coupon-v1'});
  return {db,env,call,bridge,admin,create};
}
