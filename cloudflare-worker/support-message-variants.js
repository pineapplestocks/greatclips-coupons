// Frozen wording for the first voluntary-contribution A/B/C pilot.
// These contributions are separate from paid browser passes and site funding.
export const SUPPORT_EXPERIMENT='haircut-support-v1';
const purpose='We plan to put 100% of your contribution after payment-processing fees toward haircuts for children in India. This is optional.';
export const SUPPORT_VARIANTS=Object.freeze({
 A:{name:'Savings first',message:'Glad your coupon worked! ❤️ If it saved you $5 or more, would you pass along just 75¢? '+purpose},
 B:{name:'Simple thank-you',message:'Happy we could help you save! ✂️ Would you contribute 75¢ toward a haircut for a child in India? '+purpose},
 C:{name:'Pay it forward',message:'Your coupon worked—now you can help someone else get a haircut. ❤️ Want to pay it forward with 75¢? '+purpose},
});
export async function supportVariant(sender){
 const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(SUPPORT_EXPERIMENT+':'+sender));
 return ['A','B','C'][new DataView(bytes).getUint32(0)%3];
}
export function supportEligibility(record,now=Date.now()){
 // Receipt of a coupon, group membership, and a successful delivery are not
 // evidence of salon acceptance or permission for contribution requests.
 if(record.opted_out)return 'opted_out';
 if(record.support_sent_at)return 'already_contacted';
 if(!record.sender_id||!record.conversation_id)return 'missing_recipient';
 if(!record.sent_at||record.sent_at>now||record.sent_at<now-72*3600000)return 'outside_delivery_cohort';
 if(record.feedback!=='worked'||!record.feedback_at||record.feedback_at<record.sent_at||record.feedback_at>now||record.feedback_at<now-24*3600000)return 'success_not_confirmed_recently';
 if(!record.support_opted_in_at||record.support_opted_in_at>now)return 'no_support_opt_in';
 if(!record.last_inbound_at||record.last_inbound_at>now||record.last_inbound_at<now-23*3600000)return 'outside_reply_window';
 return 'eligible';
}
export async function previewSupportPilot(records,now=Date.now()){
 const excluded={},selected=[],seen=new Set();
 // Latest delivery first, at most one message per sender across conversations.
 for(const row of [...records].sort((a,b)=>b.sent_at-a.sent_at)){
  const reason=supportEligibility(row,now);
  if(reason!=='eligible'){excluded[reason]=(excluded[reason]||0)+1;continue;}
  if(seen.has(row.sender_id)){excluded.duplicate_recipient=(excluded.duplicate_recipient||0)+1;continue;}
  seen.add(row.sender_id);const variant=await supportVariant(row.sender_id);
  selected.push({code:row.code,variant,message:SUPPORT_VARIANTS[variant].message});
 }
 return {experiment:SUPPORT_EXPERIMENT,mode:'preview_only',selected,excluded};
}
