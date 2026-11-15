import test from 'node:test';
import assert from 'node:assert/strict';
import {supportEligibility,supportVariant,previewSupportPilot,SUPPORT_VARIANTS} from '../cloudflare-worker/support-message-variants.js';
const now=1800000000000;
const eligible={code:'ABCDEFGH',sender_id:'person',conversation_id:'conversation',sent_at:now-12*3600000,feedback:'worked',feedback_at:now-60000,support_opted_in_at:now-60000,last_inbound_at:now-60000};
test('delivery alone never establishes success or fundraising consent',()=>{
 assert.equal(supportEligibility({...eligible,feedback:null},now),'success_not_confirmed_recently');
 assert.equal(supportEligibility({...eligible,support_opted_in_at:null},now),'no_support_opt_in');
 assert.equal(supportEligibility(eligible,now),'eligible');
});
test('respects cohort, service window, STOP, previous sends, and future timestamps',()=>{
 for(const change of [{sent_at:now-73*3600000},{last_inbound_at:now-24*3600000},{feedback_at:now-25*3600000},{opted_out:true},{support_sent_at:now-1000},{feedback:'not_yet'},{feedback:'failed'},{last_inbound_at:now+1000}])assert.notEqual(supportEligibility({...eligible,...change},now),'eligible');
});
test('assignment is stable and one recipient never receives multiple variants',async()=>{
 assert.equal(await supportVariant('person'),await supportVariant('person'));
 const result=await previewSupportPilot([eligible,{...eligible,code:'DIFFERENT',sent_at:now-120000}],now);
 assert.equal(result.selected.length,1);assert.equal(result.excluded.duplicate_recipient,1);
 assert.ok(SUPPORT_VARIANTS[result.selected[0].variant]);assert.equal(result.mode,'preview_only');
});
