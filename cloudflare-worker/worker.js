/**
 * Cloudflare Worker — Brevo transactional email sender for GreatClipsDeal.com
 *
 * Environment variables to set in Cloudflare dashboard (Workers > Settings > Variables):
 *   BREVO_API_KEY  — your Brevo API key (xsmtpsib-...)
 *   SENDER_EMAIL   — a verified sender email in your Brevo account (e.g. coupons@greatclipsdeal.com)
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

const DEFAULT_ADMIN_EMAIL = 'mehulchaudhari@gmail.com';
const DAY_MS = 24 * 60 * 60 * 1000;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function getSafeOfferUrl(value) {
  try {
    const url = new URL(String(value || ''));
    if (url.protocol !== 'https:' || url.hostname !== 'offers.greatclips.com') {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

function formatNumber(value) {
  return new Intl.NumberFormat('en-US').format(Number(value || 0));
}

function formatSigned(value) {
  const number = Number(value || 0);
  const sign = number > 0 ? '+' : '';
  return `${sign}${formatNumber(number)}`;
}

function formatPercent(value) {
  if (!Number.isFinite(value)) {
    return 'N/A';
  }
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

function iso(date) {
  return date.toISOString();
}

function startOfUtcDay(date) {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

function startOfUtcMonth(date) {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1));
}

function addDays(date, days) {
  return new Date(date.getTime() + days * DAY_MS);
}

function addMonths(date, months) {
  return new Date(Date.UTC(
    date.getUTCFullYear(),
    date.getUTCMonth() + months,
    date.getUTCDate(),
    date.getUTCHours(),
    date.getUTCMinutes(),
    date.getUTCSeconds(),
    date.getUTCMilliseconds(),
  ));
}

function formatDate(date) {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Phoenix',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date);
}

function formatDateTime(date) {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Phoenix',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(date);
}

async function queryFirst(env, sql, ...bindings) {
  return env.DB.prepare(sql).bind(...bindings).first();
}

async function queryAll(env, sql, ...bindings) {
  const result = await env.DB.prepare(sql).bind(...bindings).all();
  return result.results || [];
}

async function ensureSubscriberSchema(env) {
  if (!env.DB) return;

  const columns = await queryAll(env, 'PRAGMA table_info(subscribers)');
  const hasZipCode = columns.some((column) => column.name === 'zip_code');
  if (!hasZipCode) {
    await env.DB.prepare('ALTER TABLE subscribers ADD COLUMN zip_code TEXT').run();
  }
  const hasUnsub = columns.some((column) => column.name === 'unsubscribed_at');
  if (!hasUnsub) {
    await env.DB.prepare('ALTER TABLE subscribers ADD COLUMN unsubscribed_at TEXT').run();
  }
  const hasBounced = columns.some((column) => column.name === 'bounced_at');
  if (!hasBounced) {
    await env.DB.prepare('ALTER TABLE subscribers ADD COLUMN bounced_at TEXT').run();
  }

  // Ledger of drip sends: one row per address per campaign, so the random
  // nightly pick can never mail the same person twice.
  await env.DB.prepare(
    `CREATE TABLE IF NOT EXISTS campaign_sends (
       email TEXT NOT NULL,
       campaign TEXT NOT NULL,
       sent_at TEXT NOT NULL,
       PRIMARY KEY (email, campaign)
     )`
  ).run();
}

function normalizeZipCode(value) {
  const zipCode = String(value || '').trim();
  return /^\d{5}$/.test(zipCode) ? zipCode : '';
}

async function sendBrevoEmail(env, { toEmail, toName, subject, htmlContent }) {
  return fetch('https://api.brevo.com/v3/smtp/email', {
    method: 'POST',
    headers: {
      'api-key': env.BREVO_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      sender: {
        name: 'Great Clips Deal',
        email: env.SENDER_EMAIL || 'coupons@greatclipsdeal.com',
      },
      to: [{ email: toEmail, name: toName }],
      subject,
      htmlContent,
    }),
  });
}

function statCard(label, value, subtext) {
  return `
    <td valign="top" style="width:50%;padding:8px;">
      <div style="background:#f8faf6;border:1px solid #dfe8dc;border-radius:14px;padding:16px;">
        <p style="margin:0 0 7px;color:#5c6a66;font-size:12px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;">${escapeHtml(label)}</p>
        <p style="margin:0;color:#052d22;font-size:30px;font-weight:900;line-height:1;">${escapeHtml(value)}</p>
        <p style="margin:8px 0 0;color:#6c7774;font-size:13px;line-height:1.4;">${escapeHtml(subtext)}</p>
      </div>
    </td>`;
}

function tableRows(rows, columns) {
  if (!rows.length) {
    return `<tr><td colspan="${columns.length}" style="padding:14px;color:#6c7774;text-align:center;">No data yet.</td></tr>`;
  }

  return rows.map((row) => `
    <tr>
      ${columns.map((column) => `
        <td style="padding:10px 8px;border-top:1px solid #e6ece5;color:#1c2e29;font-size:13px;line-height:1.35;${column.align === 'right' ? 'text-align:right;' : ''}">
          ${escapeHtml(column.render ? column.render(row) : row[column.key])}
        </td>`).join('')}
    </tr>`).join('');
}

async function buildSubscriberSummary(env, now = new Date()) {
  if (!env.DB) {
    throw new Error('DB binding is not configured');
  }
  await ensureSubscriberSchema(env);

  const todayStart = startOfUtcDay(now);
  const tomorrowStart = addDays(todayStart, 1);
  const yesterdayStart = addDays(todayStart, -1);
  const sevenDaysStart = addDays(now, -7);
  const thirtyDaysStart = addDays(now, -30);
  const currentMonthStart = startOfUtcMonth(now);
  const previousMonthStart = addMonths(currentMonthStart, -1);
  const previousMonthEnd = currentMonthStart;
  const previousMonthSamePoint = addMonths(now, -1);

  const [
    total,
    unique,
    today,
    yesterday,
    last7,
    last30,
    currentMonth,
    previousMonthToDate,
    previousFullMonth,
    latest,
    topStates,
    topZipCodes,
    topLocations,
    topCoupons,
  ] = await Promise.all([
    queryFirst(env, 'SELECT COUNT(*) AS count FROM subscribers'),
    queryFirst(env, 'SELECT COUNT(DISTINCT lower(email)) AS count FROM subscribers'),
    queryFirst(env, 'SELECT COUNT(*) AS count FROM subscribers WHERE subscribed_at >= ? AND subscribed_at < ?', iso(todayStart), iso(tomorrowStart)),
    queryFirst(env, 'SELECT COUNT(*) AS count FROM subscribers WHERE subscribed_at >= ? AND subscribed_at < ?', iso(yesterdayStart), iso(todayStart)),
    queryFirst(env, 'SELECT COUNT(*) AS count FROM subscribers WHERE subscribed_at >= ?', iso(sevenDaysStart)),
    queryFirst(env, 'SELECT COUNT(*) AS count FROM subscribers WHERE subscribed_at >= ?', iso(thirtyDaysStart)),
    queryFirst(env, 'SELECT COUNT(*) AS count FROM subscribers WHERE subscribed_at >= ?', iso(currentMonthStart)),
    queryFirst(env, 'SELECT COUNT(*) AS count FROM subscribers WHERE subscribed_at >= ? AND subscribed_at < ?', iso(previousMonthStart), iso(previousMonthSamePoint)),
    queryFirst(env, 'SELECT COUNT(*) AS count FROM subscribers WHERE subscribed_at >= ? AND subscribed_at < ?', iso(previousMonthStart), iso(previousMonthEnd)),
    queryAll(env, `SELECT email, zip_code, coupon_url, location_name, city, state, subscribed_at
      FROM subscribers ORDER BY subscribed_at DESC LIMIT 8`),
    queryAll(env, `SELECT COALESCE(NULLIF(state, ''), 'Unknown') AS state, COUNT(*) AS count
      FROM subscribers GROUP BY COALESCE(NULLIF(state, ''), 'Unknown')
      ORDER BY count DESC LIMIT 8`),
    queryAll(env, `SELECT COALESCE(NULLIF(zip_code, ''), 'Unknown') AS zip_code, COUNT(*) AS count
      FROM subscribers GROUP BY COALESCE(NULLIF(zip_code, ''), 'Unknown')
      ORDER BY count DESC LIMIT 8`),
    queryAll(env, `SELECT COALESCE(NULLIF(location_name, ''), 'Unknown') AS location_name,
        COALESCE(NULLIF(state, ''), 'Unknown') AS state, COUNT(*) AS count
      FROM subscribers
      GROUP BY COALESCE(NULLIF(location_name, ''), 'Unknown'), COALESCE(NULLIF(state, ''), 'Unknown')
      ORDER BY count DESC LIMIT 8`),
    queryAll(env, `SELECT coupon_url, COUNT(*) AS count
      FROM subscribers GROUP BY coupon_url ORDER BY count DESC LIMIT 8`),
  ]);

  const currentMonthCount = Number(currentMonth?.count || 0);
  const previousMonthToDateCount = Number(previousMonthToDate?.count || 0);
  const monthDelta = currentMonthCount - previousMonthToDateCount;
  const monthDeltaPercent = previousMonthToDateCount
    ? (monthDelta / previousMonthToDateCount) * 100
    : (currentMonthCount ? Infinity : 0);

  return {
    generatedAt: now,
    ranges: {
      currentMonth: `${formatDate(currentMonthStart)} - ${formatDate(now)}`,
      previousMonthToDate: `${formatDate(previousMonthStart)} - ${formatDate(previousMonthSamePoint)}`,
      previousFullMonth: `${formatDate(previousMonthStart)} - ${formatDate(addDays(previousMonthEnd, -1))}`,
    },
    counts: {
      total: Number(total?.count || 0),
      unique: Number(unique?.count || 0),
      today: Number(today?.count || 0),
      yesterday: Number(yesterday?.count || 0),
      last7: Number(last7?.count || 0),
      last30: Number(last30?.count || 0),
      currentMonth: currentMonthCount,
      previousMonthToDate: previousMonthToDateCount,
      previousFullMonth: Number(previousFullMonth?.count || 0),
      monthDelta,
      monthDeltaPercent,
    },
    latest,
    topStates,
    topZipCodes,
    topLocations,
    topCoupons,
  };
}

function buildSummaryEmail(summary) {
  const counts = summary.counts;
  const generatedAt = formatDateTime(summary.generatedAt);

  return `<!doctype html>
<html>
<body style="margin:0;background:#eef2ec;font-family:Arial,Helvetica,sans-serif;color:#12211c;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#eef2ec;padding:26px 14px;">
    <tr><td align="center">
      <table width="720" cellpadding="0" cellspacing="0" role="presentation" style="max-width:720px;width:100%;background:#ffffff;border-radius:22px;overflow:hidden;box-shadow:0 18px 45px rgba(7,30,24,0.12);">
        <tr>
          <td style="background:#052d22;background-image:linear-gradient(135deg,#052d22 0%,#083f2f 100%);padding:30px 34px;">
            <p style="display:inline-block;margin:0 0 14px;background:#d7f36f;color:#071e18;border-radius:999px;padding:8px 12px;font-size:12px;font-weight:900;letter-spacing:0.1em;text-transform:uppercase;">Daily subscribers</p>
            <h1 style="color:#ffffff;margin:0;font-size:32px;line-height:1.12;">GreatClipsDeal subscriber summary</h1>
            <p style="color:#cfe0da;margin:10px 0 0;font-size:14px;">Generated ${escapeHtml(generatedAt)}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:26px;">
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              <tr>
                ${statCard('Total signups', formatNumber(counts.total), `${formatNumber(counts.unique)} unique email addresses`)}
                ${statCard('This month', formatNumber(counts.currentMonth), summary.ranges.currentMonth)}
              </tr>
              <tr>
                ${statCard('Prior month to date', formatNumber(counts.previousMonthToDate), summary.ranges.previousMonthToDate)}
                ${statCard('Change vs prior month', `${formatSigned(counts.monthDelta)} (${formatPercent(counts.monthDeltaPercent)})`, 'Month-to-date comparison')}
              </tr>
              <tr>
                ${statCard('Today', formatNumber(counts.today), 'Since midnight UTC')}
                ${statCard('Yesterday', formatNumber(counts.yesterday), 'Previous UTC day')}
              </tr>
              <tr>
                ${statCard('Last 7 days', formatNumber(counts.last7), 'Rolling 7-day window')}
                ${statCard('Last 30 days', formatNumber(counts.last30), 'Rolling 30-day window')}
              </tr>
              <tr>
                ${statCard('Previous full month', formatNumber(counts.previousFullMonth), summary.ranges.previousFullMonth)}
                ${statCard('Current run status', 'OK', 'D1 query and Brevo email completed')}
              </tr>
            </table>

            <h2 style="font-size:18px;margin:26px 0 10px;color:#052d22;">Top states</h2>
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              ${tableRows(summary.topStates, [
                { key: 'state' },
                { key: 'count', align: 'right', render: (row) => formatNumber(row.count) },
              ])}
            </table>

            <h2 style="font-size:18px;margin:26px 0 10px;color:#052d22;">Top ZIP codes</h2>
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              ${tableRows(summary.topZipCodes, [
                { key: 'zip_code' },
                { key: 'count', align: 'right', render: (row) => formatNumber(row.count) },
              ])}
            </table>

            <h2 style="font-size:18px;margin:26px 0 10px;color:#052d22;">Top locations</h2>
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              ${tableRows(summary.topLocations, [
                { render: (row) => `${row.location_name} (${row.state})` },
                { key: 'count', align: 'right', render: (row) => formatNumber(row.count) },
              ])}
            </table>

            <h2 style="font-size:18px;margin:26px 0 10px;color:#052d22;">Top coupon links</h2>
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              ${tableRows(summary.topCoupons, [
                { key: 'coupon_url' },
                { key: 'count', align: 'right', render: (row) => formatNumber(row.count) },
              ])}
            </table>

            <h2 style="font-size:18px;margin:26px 0 10px;color:#052d22;">Latest signups</h2>
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              ${tableRows(summary.latest, [
                { key: 'email' },
                { render: (row) => `${row.zip_code || 'No ZIP'} - ${row.location_name || 'Unknown'} ${row.state ? `(${row.state})` : ''}` },
                { render: (row) => formatDateTime(new Date(row.subscribed_at)) },
              ])}
            </table>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;
}

async function sendSubscriberSummary(env, source = 'manual') {
  if (!env.BREVO_API_KEY || !env.SENDER_EMAIL) {
    throw new Error('BREVO_API_KEY and SENDER_EMAIL must be configured');
  }

  const summary = await buildSubscriberSummary(env);
  const subject = `GreatClipsDeal subscribers: ${formatNumber(summary.counts.total)} total, ${formatSigned(summary.counts.monthDelta)} MTD`;
  const brevoRes = await sendBrevoEmail(env, {
    toEmail: env.ADMIN_EMAIL || DEFAULT_ADMIN_EMAIL,
    toName: 'Mehul',
    subject,
    htmlContent: buildSummaryEmail(summary),
  });

  if (!brevoRes.ok) {
    const errText = await brevoRes.text();
    throw new Error(`Brevo summary email failed (${brevoRes.status}): ${errText}`);
  }

  return { ok: true, source, sent_to: env.ADMIN_EMAIL || DEFAULT_ADMIN_EMAIL, summary };
}

// ============================================================
// Daily coupon drip
//
// Mails a capped slice of subscribers the live nationwide coupon, newest
// eligible first, so the site earns a steady trickle of return visits instead
// of one blast. Deliberately conservative: it only runs when a national coupon is
// actually live, never mails the same address twice (campaign_sends), skips
// anyone who unsubscribed, and stops at DRIP_DAILY_CAP so it stays inside the
// Brevo free tier.
// ============================================================

const DRIP_CAMPAIGN = 'nationwide-drip';
const DRIP_DAILY_CAP = 100;
const DRIP_MIN_AGE_DAYS = 2;    // skip only people who just received their coupon email

// The first 200-contact send bounced 4.0% hard on the *newest* addresses, and
// the drip deliberately targets older ones. Providers throttle past ~5% and
// Brevo suspends the account - which would take coupon delivery down with it.
// So: pull hard bounces back from Brevo each run and never retry them, and
// stop the drip entirely if the trailing rate crosses the ceiling.
const DRIP_BOUNCE_CEILING = 0.04;
const DRIP_BOUNCE_WINDOW_DAYS = 3;
const DRIP_BOUNCE_MIN_SAMPLE = 50;   // do not judge a rate on a tiny sample
const FEED_URL = 'https://greatclipsdeal.com/data/coupons.json';
const SITE_URL = 'https://greatclipsdeal.com';

async function fetchNationalCoupon() {
  const res = await fetch(FEED_URL, { cf: { cacheTtl: 60 } });
  if (!res.ok) throw new Error('coupon feed ' + res.status);
  const feed = await res.json();
  const national = (feed.coupons || []).filter((c) => c.scope === 'national');
  if (!national.length) return null;
  // cheapest wins, matching scripts/national_offer.py
  national.sort((a, b) => (a.price_value == null ? 1e9 : a.price_value) - (b.price_value == null ? 1e9 : b.price_value));
  return national[0];
}

// Signed so an unsubscribe link cannot be forged or enumerated.
async function unsubToken(env, email) {
  const secret = env.UNSUB_SECRET || env.BREVO_API_KEY || 'gcd-fallback';
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(email.toLowerCase()));
  return [...new Uint8Array(sig)].slice(0, 16).map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function unsubUrl(env, email) {
  const token = await unsubToken(env, email);
  return SITE_URL + '/unsubscribe?e=' + encodeURIComponent(email) + '&t=' + token;
}

// ============================================================
// Deal Dropper partner block
//
// Shared by the coupon-request email and the daily drip. The WhatsApp invite
// comes from the DEAL_DROPPER_URL Worker variable (set in the dashboard, no
// redeploy needed), falling back to the constant below. If neither holds a
// real chat.whatsapp.com invite the whole block is omitted, so a broken link
// can never reach a subscriber.
// ============================================================

const DEAL_DROPPER_URL = 'https://chat.whatsapp.com/Jgifq2XjPAkIgfXMdwM5j5';

// Served from the site so the image comes from the sending domain. Commit the
// file to docs/assets/email/ and let Pages deploy before the Worker ships.
const DEAL_DROPPER_LOGO = SITE_URL + '/assets/email/deal-dropper-logo.png';

// Featured "latest drop" card shown above the deals table. Set to null to hide
// it. The image is hosted under docs/assets/email/ like the logo.
const DEAL_DROPPER_SPOTLIGHT = {
  title: '80 bags of Cheez-It.',
  price: '$16.63',
  emoji: '🤯',
  blurb: 'That’s about 21¢ per bag for lunchboxes, office snacks, or stocking the pantry.',
  note: 'Amazon currently shows 58% off its displayed bundle “was” price.',
  image: SITE_URL + '/assets/email/deal-cheezit.jpg',
  alt: '80-count Cheez-It snack bags',
};

// Refresh these when the group shares better examples. "Usually on Amazon" is
// the comparison price advertised in the source post; only call something a
// price error once that has actually been confirmed. The owner chose to run
// the block without a footnote or Associates disclosure. Optional `image`: a
// 56px-ish square hosted under docs/assets/email/, shown as a row thumbnail.
const DEAL_DROPPER_DEALS = [
  { name: 'Goya Chick Peas',        detail: '8-pack',                  usually: '$11.99', deal: '$6.44' },
  { name: 'BEAR Fruit Snack Rolls', detail: '24-pack',                 usually: '$21.00', deal: '$11.39' },
  { name: 'Hanes Full-Zip Hoodie',  detail: 'select size/color',       usually: '$28.00', deal: '$9.09' },
  { name: 'Vaseline Lotion',        detail: '6 bottles, with coupons', usually: '$47.88', deal: '$17.61' },
];

// Shared <head> styles for subscriber emails: client resets plus the phone
// layout. Gmail, Apple Mail and Outlook.com honour these media queries;
// Outlook desktop ignores them and gets the desktop layout, which still fits.
const EMAIL_STYLE = `<style>
html,body{margin:0!important;padding:0!important;width:100%!important;}
body,table,td,a{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}
table,td{mso-table-lspace:0pt;mso-table-rspace:0pt;}
img{-ms-interpolation-mode:bicubic;outline:none;text-decoration:none;}
a[x-apple-data-detectors]{color:inherit!important;text-decoration:none!important;}
@media screen and (max-width:620px){
  .outer-pad{padding:10px 8px!important;}
  .masthead{padding:16px 18px!important;}
  .masthead-note{display:none!important;}
  .hero-pad{padding-left:20px!important;padding-right:20px!important;}
  .hero-title{font-size:43px!important;line-height:45px!important;letter-spacing:-1.5px!important;}
  .hero-copy{font-size:20px!important;line-height:27px!important;}
  .coupon-card{padding:18px 10px!important;}
  .coupon-label{font-size:12px!important;letter-spacing:2px!important;}
  .coupon-price{font-size:76px!important;line-height:80px!important;}
  .cta{font-size:20px!important;line-height:25px!important;padding:17px 10px!important;}
  .step{padding:6px 2px!important;}
  .step-number{display:block!important;margin:0 auto 5px!important;}
  .step-label{display:block!important;padding-left:0!important;text-align:center!important;font-size:12px!important;line-height:16px!important;}
  .promo-pad{padding-left:18px!important;padding-right:18px!important;}
  .eyebrow{font-size:10px!important;letter-spacing:1.2px!important;}
  .promo-title{font-size:26px!important;line-height:30px!important;}
  .promo-copy{font-size:15px!important;line-height:22px!important;}
  .spot-title{font-size:19px!important;line-height:24px!important;}
  .price-heading{font-size:9px!important;letter-spacing:.5px!important;}
  .product-name{font-size:14px!important;line-height:19px!important;}
  .product-detail{font-size:12px!important;line-height:16px!important;}
  .deal-price{font-size:19px!important;line-height:24px!important;}
}
</style>`;

// Accepts the invite with or without WhatsApp's share-tracking query string
// (?s=cl&p=i...) and returns the canonical https://chat.whatsapp.com/<code>.
function dealDropperUrl(env) {
  const raw = String((env && env.DEAL_DROPPER_URL) || DEAL_DROPPER_URL || '').trim();
  const m = raw.match(/^https:\/\/chat\.whatsapp\.com\/([A-Za-z0-9_-]+)(?:[?#].*)?$/);
  return m ? 'https://chat.whatsapp.com/' + m[1] : '';
}

function dealDropperHtml(env) {
  const url = dealDropperUrl(env);
  if (!url) return '';
  const withThumbs = DEAL_DROPPER_DEALS.some((d) => d.image);
  const rows = DEAL_DROPPER_DEALS.map((d, i) => {
    const line = i ? 'border-top:1px solid #e4ede6;' : '';
    const thumb = !withThumbs ? '' : `
          <td width="72" valign="middle" style="padding:14px 0 14px 16px;${line}">${d.image ? `
            <img src="${escapeHtml(d.image)}" width="56" height="56" alt="" style="display:block;width:56px;height:56px;border:0;border-radius:8px;">` : ''}</td>`;
    return `
        <tr>${thumb}
          <td valign="middle" style="padding:14px 16px;${line}">
            <div class="product-name" style="color:#063c2d;font-size:16px;line-height:21px;font-weight:700;">${escapeHtml(d.name)}</div>
            <div class="product-detail" style="color:#66736e;font-size:14px;line-height:19px;">${escapeHtml(d.detail)}</div></td>
          <td align="right" valign="middle" style="padding:14px 16px;${line}white-space:nowrap;">
            <div style="color:#8a958f;font-size:14px;line-height:18px;text-decoration:line-through;">${escapeHtml(d.usually)}</div>
            <div class="deal-price" style="color:#063c2d;font-size:21px;line-height:26px;font-weight:800;">${escapeHtml(d.deal)}</div></td>
        </tr>`;
  }).join('');
  const sp = DEAL_DROPPER_SPOTLIGHT;
  const spot = !sp ? '' : `
  <tr><td class="promo-pad" style="padding:20px 28px 0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="background:#ffffff;border-radius:14px;">
      <tr><td style="padding:14px 14px 0;">
        <a href="${url}" target="_blank"><img src="${sp.image}" width="556" alt="${escapeHtml(sp.alt)}"
          style="display:block;width:100%;max-width:556px;height:auto;border:0;border-radius:10px;"></a></td></tr>
      <tr><td style="padding:14px 16px 18px;">
        <div class="eyebrow" style="color:#1fa855;font-size:11px;line-height:15px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;">Latest drop</div>
        <div class="spot-title" style="padding-top:6px;color:#063c2d;font-size:22px;line-height:27px;font-weight:900;">${escapeHtml(sp.title)} Just <span style="color:#0f7a52;">${escapeHtml(sp.price)}</span>. ${sp.emoji || ''}</div>
        <div style="padding-top:6px;color:#3d4f47;font-size:15px;line-height:22px;">${escapeHtml(sp.blurb)}</div>
        <div style="padding-top:8px;color:#66736e;font-size:13px;line-height:18px;">${escapeHtml(sp.note)}</div>
      </td></tr>
    </table>
  </td></tr>`;
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#e8f6ea" style="background:#e8f6ea;border-radius:20px;">
  <tr><td class="promo-pad eyebrow" style="padding:28px 28px 0;color:#063c2d;font-size:12px;line-height:16px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;"><span style="color:#1fa855;">Price errors &amp; glitched deals</span><br>Take advantage with our WhatsApp group</td></tr>
  <tr><td class="promo-pad" style="padding:16px 28px 0;">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td valign="middle" style="padding-right:16px;">
        <a href="${url}" target="_blank"><img src="${DEAL_DROPPER_LOGO}" width="72" height="72" alt="Deal Dropper"
          style="display:block;width:72px;height:72px;border:0;border-radius:16px;background:#0b1424;"></a></td>
      <td valign="middle" class="promo-title" style="color:#063c2d;font-size:30px;line-height:34px;font-weight:900;letter-spacing:-0.3px;">Your next deal is one WhatsApp away.</td>
    </tr></table>
  </td></tr>
  <tr><td class="promo-pad promo-copy" style="padding:12px 28px 0;color:#3d4f47;font-size:16px;line-height:24px;">
    Amazon finds for your pantry, family &amp; home. Shopping links and coupon steps included.
  </td></tr>
${spot}
  <tr><td class="promo-pad" style="padding:22px 28px 0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
      <td valign="bottom" class="price-heading" style="color:#063c2d;font-size:11px;line-height:15px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;">Recent deals we shared</td>
      <td align="right" valign="bottom" class="price-heading" style="color:#66736e;font-size:11px;line-height:15px;font-weight:800;letter-spacing:1px;text-transform:uppercase;">Usually on Amazon<br>Deal Price Alerted</td>
    </tr></table>
  </td></tr>
  <tr><td class="promo-pad" style="padding:10px 28px 0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="background:#ffffff;border-radius:14px;">${rows}
    </table>
  </td></tr>
  <tr><td class="promo-pad" style="padding:22px 28px 28px;">
    <div class="promo-copy" style="padding-bottom:12px;text-align:center;color:#063c2d;font-size:16px;line-height:22px;font-weight:700;">Want alerts like this directly in WhatsApp?</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" bgcolor="#1fa855" style="border-radius:12px;">
      <a class="cta" href="${url}" target="_blank" style="display:block;padding:18px 24px;color:#ffffff;font-size:20px;line-height:24px;font-weight:800;text-decoration:none;">
        Join Deal Dropper &nbsp;&rarr;</a>
    </td></tr></table>
  </td></tr>
</table>`;
}

function dripHtml(env, coupon, unsubscribeUrl) {
  const q = '?subscribed=1&utm_source=brevo&utm_medium=email&utm_campaign=nationwide-drip';
  const price = escapeHtml(coupon.price || '$5.00');
  const dealDropper = dealDropperHtml(env);
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">${EMAIL_STYLE}</head>
<body style="margin:0;padding:0;background:#f2f4f5;font-family:Arial,Helvetica,sans-serif;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">Get ${price} off your next haircut at participating Great Clips locations.</div>
<table role="presentation" width="100%" bgcolor="#f2f4f5"><tr><td align="center" style="padding:20px 10px;">
<table role="presentation" width="600" style="width:100%;max-width:600px;background:#ffffff;">
  <tr><td bgcolor="#003e42" style="background:#003e42;padding:24px 30px;color:#ffffff;font-size:23px;font-weight:bold;">
    GreatClipsDeal<span style="color:#5fd3bd;">.com</span>
    <div style="margin-top:5px;color:#8fd8ca;font-size:10px;font-weight:bold;letter-spacing:2px;">INDEPENDENT COUPON TRACKER</div>
  </td></tr>
  <tr><td><a href="${SITE_URL}/${q}" target="_blank"><img src="${SITE_URL}/assets/email/coupon-5off.jpg"
      alt="Haircut coupon: ${price} off at participating Great Clips locations"
      width="600" style="width:100%;max-width:600px;height:auto;display:block;background:#00615c;"></a></td></tr>
  <tr><td align="center" style="padding:28px 40px 0;color:#061631;">
    <div style="color:#008c79;font-size:15px;font-weight:bold;letter-spacing:4px;">NATIONWIDE OFFER</div>
    <div style="font-size:52px;line-height:56px;font-weight:800;padding-top:8px;">${price} OFF</div>
    <div style="font-size:28px;line-height:34px;font-weight:800;">your next haircut</div>
    <div style="padding:16px 0 0;color:#34445c;font-size:16px;line-height:25px;">
      Valid at participating Great Clips locations anywhere in the US.
    </div>
  </td></tr>
  <tr><td align="center" style="padding:26px 40px 0;">
    <table role="presentation"><tr><td bgcolor="#00947e" style="border-radius:40px;">
      <a href="${SITE_URL}/${q}" target="_blank" style="display:block;padding:17px 44px;color:#ffffff;font-size:20px;font-weight:bold;text-decoration:none;">
        Get my ${price} coupon &nbsp; &rarr;</a>
    </td></tr></table>
    <div style="padding-top:13px;color:#47546b;font-size:14px;">
      One click on the site &mdash; you will not be asked for your email again.
    </div>
  </td></tr>
  ${dealDropper ? `<tr><td class="hero-pad" style="padding:30px 40px 0;">${dealDropper}</td></tr>` : ''}
  <tr><td align="center" style="padding:30px 40px 34px;color:#7a8598;font-size:11px;line-height:18px;">
    <div style="border-top:1px solid #d9dfe4;padding-top:20px;">
      You are receiving this because you requested a Great Clips coupon at GreatClipsDeal.com.<br>
      <a href="${unsubscribeUrl}" style="color:#455168;">Unsubscribe</a><br><br>
      Great Clips Deal &middot; 1383 E Dara Pl, Chandler, AZ 85249, United States<br><br>
      GreatClipsDeal is an independent coupon directory and is not affiliated with,
      endorsed by, or sponsored by Great Clips, Inc.
    </div>
  </td></tr>
</table></td></tr></table></body></html>`;
}

// Pull hard bounces back from Brevo and mark them in D1, so a dead address is
// picked once and never again. Brevo blocklists them on its side too, but that
// does not stop this Worker from burning a daily slot on them.
async function syncHardBounces(env, days = 7) {
  const fmt = (d) => d.toISOString().slice(0, 10);
  const startDate = fmt(new Date(Date.now() - days * DAY_MS));
  const endDate = fmt(new Date());
  let marked = 0;

  for (let offset = 0; offset < 1000; offset += 100) {
    const url = 'https://api.brevo.com/v3/smtp/statistics/events'
      + `?limit=100&offset=${offset}&startDate=${startDate}&endDate=${endDate}&event=hardBounces`;
    let body;
    try {
      const res = await fetch(url, {
        headers: { 'api-key': env.BREVO_API_KEY, accept: 'application/json' },
      });
      if (!res.ok) break;
      body = await res.json();
    } catch (err) {
      console.error('bounce sync error', err);
      break;
    }
    const events = body.events || [];
    if (!events.length) break;
    for (const ev of events) {
      const email = String(ev.email || '').trim().toLowerCase();
      if (!email) continue;
      const result = await env.DB.prepare(
        'UPDATE subscribers SET bounced_at = ? WHERE lower(trim(email)) = ? AND bounced_at IS NULL'
      ).bind(ev.date || new Date().toISOString(), email).run();
      marked += (result.meta && result.meta.changes) || 0;
    }
    if (events.length < 100) break;
  }
  return marked;
}

// Hard-bounce rate among drip sends over the trailing window.
async function recentBounceRate(env) {
  const since = new Date(Date.now() - DRIP_BOUNCE_WINDOW_DAYS * DAY_MS).toISOString();
  const row = await queryFirst(env,
    `SELECT COUNT(*) AS sent,
            SUM(CASE WHEN EXISTS (
                  SELECT 1 FROM subscribers s
                   WHERE lower(trim(s.email)) = c.email AND s.bounced_at IS NOT NULL
                ) THEN 1 ELSE 0 END) AS bounced
       FROM campaign_sends c
      WHERE c.campaign = ? AND c.sent_at >= ?`,
    DRIP_CAMPAIGN, since);
  const sent = Number((row && row.sent) || 0);
  const bounced = Number((row && row.bounced) || 0);
  if (sent < DRIP_BOUNCE_MIN_SAMPLE) return { rate: 0, sent, bounced, judged: false };
  return { rate: bounced / sent, sent, bounced, judged: true };
}

async function runDailyDrip(env, trigger) {
  if (!env.DB || !env.BREVO_API_KEY) return { ok: false, reason: 'not configured' };
  await ensureSubscriberSchema(env);

  const coupon = await fetchNationalCoupon();
  if (!coupon) {
    console.log('drip: no live national coupon, sending nothing');
    return { ok: true, sent: 0, reason: 'no national coupon' };
  }

  // Retire addresses Brevo has already hard-bounced, then check whether the
  // trailing rate is healthy enough to keep sending at all.
  const retired = await syncHardBounces(env);
  const health = await recentBounceRate(env);
  if (health.judged && health.rate > DRIP_BOUNCE_CEILING) {
    console.error(
      `drip HALTED: hard-bounce rate ${(health.rate * 100).toFixed(1)}% over last `
      + `${health.sent} sends exceeds ceiling ${(DRIP_BOUNCE_CEILING * 100).toFixed(1)}%`
    );
    return {
      ok: true, sent: 0, halted: true, reason: 'bounce rate above ceiling',
      bounceRate: health.rate, window: health.sent, retired,
    };
  }

  const cutoff = new Date(Date.now() - DRIP_MIN_AGE_DAYS * DAY_MS).toISOString();
  const candidates = await queryAll(env,
    `SELECT lower(trim(s.email)) AS email
       FROM subscribers s
      WHERE s.email LIKE '%_@_%.__%'
        AND s.subscribed_at < ?
        AND s.unsubscribed_at IS NULL
        AND s.bounced_at IS NULL
        AND NOT EXISTS (
              SELECT 1 FROM campaign_sends c
               WHERE c.email = lower(trim(s.email)) AND c.campaign = ?
            )
      GROUP BY lower(trim(s.email))
      ORDER BY MAX(s.subscribed_at) DESC
      LIMIT ?`,
    cutoff, DRIP_CAMPAIGN, DRIP_DAILY_CAP);

  let sent = 0;
  let failed = 0;
  for (const row of candidates) {
    const email = row.email;
    try {
      const res = await sendBrevoEmail(env, {
        toEmail: email,
        subject: 'Your ' + (coupon.price || '$5.00') + ' off Great Clips coupon is live',
        htmlContent: dripHtml(env, coupon, await unsubUrl(env, email)),
      });
      if (!res.ok) {
        // Out of credits or throttled: stop cleanly rather than burn the list.
        const body = await res.text();
        console.error('drip send failed', res.status, body.slice(0, 200));
        failed++;
        if (res.status === 402 || res.status === 429) break;
        continue;
      }
      await env.DB.prepare(
        'INSERT OR IGNORE INTO campaign_sends (email, campaign, sent_at) VALUES (?, ?, ?)'
      ).bind(email, DRIP_CAMPAIGN, new Date().toISOString()).run();
      sent++;
    } catch (err) {
      console.error('drip error', email, err);
      failed++;
    }
  }

  console.log(
    'drip(' + trigger + '): ' + sent + ' sent, ' + failed + ' failed, '
    + candidates.length + ' candidates, ' + retired + ' retired, trailing bounce '
    + (health.judged ? (health.rate * 100).toFixed(1) + '%' : 'n/a')
  );
  return {
    ok: true, sent, failed, candidates: candidates.length,
    coupon: coupon.coupon_code, retired,
    bounceRate: health.judged ? health.rate : null,
  };
}

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    if (url.pathname === '/unsubscribe') {
      const email = (url.searchParams.get('e') || '').trim().toLowerCase();
      const token = url.searchParams.get('t') || '';
      const page = (msg) => new Response(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        + '<div style="font-family:system-ui,sans-serif;max-width:520px;margin:16vh auto;padding:0 24px;text-align:center;">'
        + '<h1 style="font-size:22px;color:#061631;">' + msg + '</h1>'
        + '<p style="color:#5b6676;font-size:15px;">GreatClipsDeal.com</p></div>',
        { headers: { 'Content-Type': 'text/html; charset=utf-8' } });

      if (!email || token !== await unsubToken(env, email)) {
        return page('That unsubscribe link is not valid.');
      }
      try {
        await ensureSubscriberSchema(env);
        await env.DB.prepare(
          'UPDATE subscribers SET unsubscribed_at = ? WHERE lower(trim(email)) = ?'
        ).bind(new Date().toISOString(), email).run();
      } catch (err) {
        console.error('unsubscribe error', err);
        return page('Something went wrong. Please try again.');
      }
      return page('You are unsubscribed. You will not receive these emails again.');
    }

    if (url.pathname === '/admin/run-drip') {
      if (request.method !== 'POST') return jsonResponse({ error: 'Method not allowed' }, 405);
      if (!env.ADMIN_TOKEN || request.headers.get('Authorization') !== `Bearer ${env.ADMIN_TOKEN}`) {
        return jsonResponse({ error: 'Unauthorized' }, 401);
      }
      return jsonResponse(await runDailyDrip(env, 'manual'));
    }

    if (url.pathname === '/admin/send-summary') {
      if (request.method !== 'POST') {
        return jsonResponse({ error: 'Method not allowed' }, 405);
      }
      if (!env.ADMIN_TOKEN || request.headers.get('Authorization') !== `Bearer ${env.ADMIN_TOKEN}`) {
        return jsonResponse({ error: 'Unauthorized' }, 401);
      }
      try {
        const result = await sendSubscriberSummary(env, 'manual');
        return jsonResponse({
          ok: true,
          sent_to: result.sent_to,
          total: result.summary.counts.total,
          current_month: result.summary.counts.currentMonth,
          previous_month_to_date: result.summary.counts.previousMonthToDate,
          month_delta: result.summary.counts.monthDelta,
        });
      } catch (err) {
        console.error('Summary email error:', err);
        return jsonResponse({ error: 'Failed to send summary email', detail: String(err.message || err) }, 500);
      }
    }

    if (request.method !== 'POST') {
      return jsonResponse({ error: 'Method not allowed' }, 405);
    }

    if (!env.BREVO_API_KEY) {
      return jsonResponse({ error: 'BREVO_API_KEY secret not set in Cloudflare Worker environment' }, 500);
    }
    if (!env.SENDER_EMAIL) {
      return jsonResponse({ error: 'SENDER_EMAIL secret not set in Cloudflare Worker environment' }, 500);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return jsonResponse({ error: 'Invalid JSON body' }, 400);
    }

    const { email, coupon_url, price, location_name, city, state } = body;
    const zip_code = normalizeZipCode(body.zip_code);

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return jsonResponse({ error: 'Invalid email address' }, 400);
    }

    if (!coupon_url) {
      return jsonResponse({ error: 'Missing coupon_url' }, 400);
    }

    const safeCouponUrl = getSafeOfferUrl(coupon_url);
    if (!safeCouponUrl) {
      return jsonResponse({ error: 'Invalid coupon_url; expected an offers.greatclips.com link' }, 400);
    }

    const priceStr = escapeHtml(price ? price : 'Great Clips');
    const subjectPrice = price ? String(price).slice(0, 40) : 'Great Clips';
    const subject = `Your ${subjectPrice} Great Clips coupon is ready`;
    // Replaces the old curry leaf partner ad. Empty until DEAL_DROPPER_URL is set.
    const dealDropper = dealDropperHtml(env);

    const unsubscribeUrl = await unsubUrl(env, email);
    const ticketPrice = price ? priceStr : 'Coupon';
    const htmlContent = `<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="format-detection" content="telephone=no,date=no,address=no,email=no,url=no">
  <title>Your ${priceStr} Great Clips coupon is ready</title>
  <!--[if mso]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
${EMAIL_STYLE}
</head>
<body style="margin:0;padding:0;background:#f5f4f0;font-family:Arial,Helvetica,sans-serif;color:#063c2d;">
  <div style="display:none;font-size:1px;line-height:1px;color:#f5f4f0;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">Open your ${priceStr} haircut coupon${dealDropper ? ' &mdash; plus get Amazon deal alerts from our free WhatsApp group.' : ' and show it before your haircut.'}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#f5f4f0" style="background:#f5f4f0;"><tr><td class="outer-pad" align="center" style="padding:24px 12px;">
  <!--[if mso]><table role="presentation" width="640" align="center"><tr><td><![endif]-->
  <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="width:100%;max-width:640px;">

    <!-- Coupon card -->
    <tr><td>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="background:#ffffff;border-radius:18px;">
        <tr><td class="masthead" style="padding:18px 26px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
            <td style="color:#063c2d;font-size:20px;line-height:26px;font-weight:700;letter-spacing:-0.5px;"><span style="font-size:25px;">&#9986;</span>&nbsp; GreatClipsDeal.com</td>
            <td class="masthead-note" align="right" style="color:#66736e;font-size:10px;line-height:26px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;">Your coupon is ready</td>
          </tr></table>
        </td></tr>

        <!-- Hero -->
        <tr><td>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#063c2d" style="background:#063c2d;">
            <tr><td class="hero-pad" style="padding:30px 34px 0;">
              <div class="hero-title" style="color:#ffffff;font-size:57px;line-height:58px;font-weight:800;letter-spacing:-2px;">Fresh cut.<br>Better price.</div>
              <div class="hero-copy" style="padding-top:14px;color:#b8e9bf;font-size:25px;line-height:31px;font-weight:700;">Your Great Clips haircut coupon is ready.</div>
            </td></tr>
            <tr><td class="hero-pad" style="padding:26px 34px 0;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="background:#ffffff;border:2px dashed #93b8a3;border-radius:14px;">
                <tr><td class="coupon-card" align="center" style="padding:22px 20px 20px;">
                  <div class="coupon-label" style="color:#063c2d;font-size:13px;line-height:18px;font-weight:800;letter-spacing:3px;text-transform:uppercase;">Great Clips Haircut</div>
                  <div class="coupon-price" style="padding-top:6px;font-size:96px;line-height:100px;font-weight:900;letter-spacing:-2px;"><a href="${safeCouponUrl}" style="color:#063c2d;text-decoration:none;">${ticketPrice}</a></div>
                  <div style="padding-top:6px;color:#4c5d58;font-size:13px;line-height:18px;">At participating salons. See coupon for details.</div>
                </td></tr>
              </table>
            </td></tr>
            <tr><td class="hero-pad" style="padding:22px 34px 0;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" bgcolor="#c6f542" style="border-radius:12px;">
                <a class="cta" href="${safeCouponUrl}" style="display:block;padding:18px 24px;color:#063c2d;font-size:24px;line-height:28px;font-weight:800;text-decoration:none;">Open My Coupon &nbsp;&rarr;</a>
              </td></tr></table>
            </td></tr>
            <tr><td class="hero-pad" align="center" style="padding:14px 34px 30px;color:#ffffff;font-size:14px;line-height:20px;">Open on your phone &nbsp;&bull;&nbsp; Show before your haircut</td></tr>
          </table>
        </td></tr>

        <!-- 3 steps -->
        <tr><td style="padding:18px 12px 20px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
              <td class="step" width="33%" align="center" style="padding:4px 6px;">
                <table role="presentation" cellpadding="0" cellspacing="0"><tr>
                  <td class="step-number" width="26" height="26" align="center" valign="middle" bgcolor="#063c2d" style="border-radius:13px;color:#ffffff;font-size:13px;line-height:26px;font-weight:800;">1</td>
                  <td class="step-label" style="padding-left:10px;color:#063c2d;font-size:15px;line-height:20px;font-weight:600;">Open coupon</td>
                </tr></table>
              </td>
              <td class="step" width="33%" align="center" style="padding:4px 6px;border-left:1px solid #dfe6e0;border-right:1px solid #dfe6e0;">
                <table role="presentation" cellpadding="0" cellspacing="0"><tr>
                  <td class="step-number" width="26" height="26" align="center" valign="middle" bgcolor="#063c2d" style="border-radius:13px;color:#ffffff;font-size:13px;line-height:26px;font-weight:800;">2</td>
                  <td class="step-label" style="padding-left:10px;color:#063c2d;font-size:15px;line-height:20px;font-weight:600;">Show your stylist</td>
                </tr></table>
              </td>
              <td class="step" width="33%" align="center" style="padding:4px 6px;">
                <table role="presentation" cellpadding="0" cellspacing="0"><tr>
                  <td class="step-number" width="26" height="26" align="center" valign="middle" bgcolor="#063c2d" style="border-radius:13px;color:#ffffff;font-size:13px;line-height:26px;font-weight:800;">3</td>
                  <td class="step-label" style="padding-left:10px;color:#063c2d;font-size:15px;line-height:20px;font-weight:600;">Enjoy your savings</td>
                </tr></table>
              </td>
          </tr></table>
        </td></tr>
      </table>
    </td></tr>

    <!-- Partner block -->
    ${dealDropper ? `<tr><td style="padding-top:16px;">${dealDropper}</td></tr>` : ''}

    <!-- Footer -->
    <tr><td align="center" style="padding:24px 20px 0;color:#66736e;font-size:12px;line-height:20px;">
      You requested a coupon at <a href="https://greatclipsdeal.com" style="color:#063c2d;font-weight:700;text-decoration:none;">GreatClipsDeal.com</a>.<br>
      <a href="${unsubscribeUrl}" style="color:#66736e;">Unsubscribe</a> &nbsp;&middot;&nbsp; &copy; 2026 GreatClipsDeal.com<br>
      Great Clips Deal &middot; 1383 E Dara Pl, Chandler, AZ 85249, United States<br>
      Not affiliated with Great Clips, Inc.
    </td></tr>

  </table>
  <!--[if mso]></td></tr></table><![endif]-->
  </td></tr></table>
</body>
</html>`;

    const brevoRes = await sendBrevoEmail(env, {
      toEmail: email,
      subject,
      htmlContent,
    });

    if (!brevoRes.ok) {
      const errText = await brevoRes.text();
      console.error('Brevo API error:', brevoRes.status, errText);
      return jsonResponse({ error: 'Failed to send email', detail: errText, status: brevoRes.status }, 500);
    }

    // Store subscriber + location in D1
    if (env.DB) {
      try {
        await ensureSubscriberSchema(env);
        await env.DB.prepare(
          `INSERT INTO subscribers (email, zip_code, location_name, city, state, coupon_url, subscribed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)`
        ).bind(
          email,
          zip_code,
          location_name || '',
          city || '',
          state || '',
          safeCouponUrl,
          new Date().toISOString()
        ).run();
      } catch (err) {
        console.error('D1 insert error:', err);
      }
    }

    return jsonResponse({ ok: true });
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(sendSubscriberSummary(env, 'scheduled'));
    ctx.waitUntil(runDailyDrip(env, 'scheduled'));
  },
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
