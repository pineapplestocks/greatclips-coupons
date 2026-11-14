import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
const script=readFileSync(new URL('../docs/assets/coupon-day-pass.js',import.meta.url),'utf8');
async function setup({active=false,stored=true,enabled=true,blocked=false}={}){
 const dom=new JSDOM('<body><div id="emailFormView"><form></form><div class="gc-whatsapp-option">Free WhatsApp</div></div><p data-pass-status></p><button id="pass-action" hidden></button>',{url:'https://greatclipsdeal.com/day-pass.html?payment=complete',runScripts:'outside-only'});
 const w=dom.window,calls=[];w.AbortSignal=AbortSignal;
 if(stored)w.localStorage.setItem('gcd-browser-pass-v1','a'.repeat(64));
 if(blocked)Object.defineProperty(w,'localStorage',{get(){throw new Error('Storage blocked');}});
 w.fetch=async(url,options)=>{calls.push({url,options});return Response.json(url.endsWith('/config')?{enabled}:url.endsWith('/status')?{active,status:active?'active':'pending',expires_at:Date.now()+86400000}:{});};
 w.eval(script);await new Promise(r=>setTimeout(r,30));const close=dom.window.close.bind(dom.window);dom.window.close=()=>{w.dispatchEvent(new w.Event('pagehide'));close();};return {dom,w,calls};
}
test('success URL alone cannot activate a pass, checkout is explicit and free option stays visible',async()=>{
 const {dom,w,calls}=await setup({stored:false});
 assert.equal(w.document.querySelector('#gc-pass-banner'),null);
 assert.equal(w.GCDayPass.open('https://offers.greatclips.com/test'),false);
 assert.ok(w.document.querySelector('.gc-day-pass button').textContent.includes('$0.75'));
 assert.ok(w.document.querySelector('.gc-whatsapp-option'));
 assert.equal(calls.filter(c=>c.url.endsWith('/create-checkout')).length,0);dom.window.close();
});
test('verified pass is shown without another checkout and expiry comes from server',async()=>{
 const {dom,w,calls}=await setup({active:true});
 assert.match(w.document.querySelector('#gc-pass-banner').textContent,/Day pass active/);
 assert.equal(w.document.querySelector('.gc-day-pass button').textContent,'Open my coupon');
 assert.equal(w.document.querySelector('#pass-action').textContent,'Open my coupon');
 assert.equal(calls.filter(c=>c.url.endsWith('/create-checkout')).length,0);dom.window.close();
});
test('disabled configuration hides purchase controls and blocked storage cannot initiate checkout',async()=>{
 const disabled=await setup({enabled:false});assert.equal(disabled.w.document.querySelector('.gc-day-pass'),null);disabled.dom.window.close();
 const blocked=await setup({blocked:true});await blocked.w.GCDayPass.checkout('https://offers.greatclips.com/test');
 assert.equal(blocked.calls.some(c=>c.url.endsWith('/create-checkout')),false);assert.match(blocked.w.document.querySelector('[data-pass-status]').textContent,/Storage blocked/);blocked.dom.window.close();
});
