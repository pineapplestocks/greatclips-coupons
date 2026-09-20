// Single-code-point emoji avoid skin-tone and joined-sequence parsing differences.
export const EMOJIS=Array.from(new Set(Array.from('🍎🍏🍐🍊🍋🍌🍉🍇🍓🍈🍒🥭🍍🥥🥝🍅🥑🥦🥬🥒🌶🌽🥕🧄🧅🥔🍠🥐🥯🍞🥖🥨🧀🥚🍳🥞🧇🥓🥩🍗🍖🌭🍔🍟🍕🥪🥙🌮🌯🥗🥘🍝🍜🍲🍛🍣🍱🥟🍤🍙🍚🍘🍥🥠🍢🍡🍧🍨🍦🥧🧁🍰🎂🍮🍭🍬🍫🍿🍩🍪🍯🥛🍼🍵🥤🧃🧊🥄🍴🥣🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐸🐵🐔🐧🐦🐤🦆🦉🦋🐌🐞🐢🐙🦑🦀🐠🐟🐬🐳🐋🦈🐊🐘🦒🦓🦍🐪🐫🦙🐑🐐🦌🐕🐩🐈🐓🦃🦚🦜🦢🐇🦝🦔🐿🌵🎄🌲🌳🌴🌱🌿🍀🎍🎋🍃🍂🍁🍄🐚🌾💐🌷🌹🌺🌸🌼🌻🌞🌝🌛🌜🌚🌕🌖🌗🌘🌑🌒🌓🌔🌙🌎🌍🌏🪐💫🌟✨💥🔥🌈🌊🎈🎉🎊🎁🎀🎨🎭🎪🎫🎟🎮🎲🧩🧸🪁🎯🎳🏀🏈🏉🎾🏐🎱🏓🏸🥅🏒🏑🏏🥊🎣🤿🎽🎿🛷🏆🥇🥈🥉🏅🎖🎤🎧🎼🎹🥁🎷🎺🎸🎻🪕🚗🚕🚙🚌🚎🏎🚓🚑🚒🚐🚚🚛🚜🛵🚲🛴🚂🚆🚊🚉🚀🛸🚁🛶🚤🛳🚢🗼🏰🏯🏠🏡🏢🏬🏫🏛⛲🎡🎢🎠🌋🏔🗻🏕🏖🏜🏝🌅🌄🌇🌆🌃🌌🌉🎆🎇💎💡🔦🔑🗝🔔📚📖📕📗📘📙📓📝📌📎📐📏🔍🔎🔒🔓🧲🧰🔧🔨🪛🧱🧵🧶👒🎩🧢👑🎓👜👛🎒👟👞👢🧤🧣🧦👕👖👗')));
export function randomPair(){const values=crypto.getRandomValues(new Uint32Array(2));return values.map(v=>v%EMOJIS.length).reduce((s,i)=>s+EMOJIS[i],'');}
export function readPair(text){
 const normalized=text.replace(/[\uFE0E\uFE0F\s]/gu,'');const chars=Array.from(normalized),pair=chars.slice(-2);
 return pair.length===2&&pair.every(c=>EMOJIS.includes(c))?pair.join(''):null;
}
export async function reservePair(env,code){
 for(let attempt=0;attempt<32;attempt++){const pair=randomPair();const result=await env.DB.prepare('INSERT OR IGNORE INTO zernio_emoji_references(pair,code) VALUES(?,?)').bind(pair,code).run();if(result.meta.changes)return pair;}
 throw Object.assign(new Error('Please try requesting your coupon again shortly.'),{status:503});
}
