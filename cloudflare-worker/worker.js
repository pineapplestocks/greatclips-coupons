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
// Mails a capped, random slice of older subscribers the live nationwide
// coupon, so the site earns a steady trickle of return visits instead of one
// blast. Deliberately conservative: it only runs when a national coupon is
// actually live, never mails the same address twice (campaign_sends), skips
// anyone who unsubscribed, and stops at DRIP_DAILY_CAP so it stays inside the
// Brevo free tier.
// ============================================================

const DRIP_CAMPAIGN = 'nationwide-drip';
const DRIP_DAILY_CAP = 100;
const DRIP_MIN_AGE_DAYS = 10;   // leave recent signups alone; they just got one
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

function dripHtml(coupon, unsubscribeUrl) {
  const q = '?subscribed=1&utm_source=brevo&utm_medium=email&utm_campaign=nationwide-drip';
  const price = escapeHtml(coupon.price || '$5.00');
  return `<!doctype html><html><body style="margin:0;padding:0;background:#f2f4f5;font-family:Arial,Helvetica,sans-serif;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">Get ${price} off your next haircut at participating Great Clips locations.</div>
<table role="presentation" width="100%" bgcolor="#f2f4f5"><tr><td align="center" style="padding:20px 10px;">
<table role="presentation" width="600" style="width:600px;max-width:600px;background:#ffffff;">
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

async function runDailyDrip(env, trigger) {
  if (!env.DB || !env.BREVO_API_KEY) return { ok: false, reason: 'not configured' };
  await ensureSubscriberSchema(env);

  const coupon = await fetchNationalCoupon();
  if (!coupon) {
    console.log('drip: no live national coupon, sending nothing');
    return { ok: true, sent: 0, reason: 'no national coupon' };
  }

  const cutoff = new Date(Date.now() - DRIP_MIN_AGE_DAYS * DAY_MS).toISOString();
  const candidates = await queryAll(env,
    `SELECT lower(trim(s.email)) AS email
       FROM subscribers s
      WHERE s.email LIKE '%_@_%.__%'
        AND s.subscribed_at < ?
        AND s.unsubscribed_at IS NULL
        AND NOT EXISTS (
              SELECT 1 FROM campaign_sends c
               WHERE c.email = lower(trim(s.email)) AND c.campaign = ?
            )
      GROUP BY lower(trim(s.email))
      ORDER BY RANDOM()
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
        htmlContent: dripHtml(coupon, await unsubUrl(env, email)),
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

  console.log('drip(' + trigger + '): ' + sent + ' sent, ' + failed + ' failed, ' + candidates.length + ' candidates');
  return { ok: true, sent, failed, candidates: candidates.length, coupon: coupon.coupon_code };
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

    const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Your Great Clips Coupon</title>
</head>
<body style="margin:0;padding:0;background:#eef2ec;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#eef2ec;padding:0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0" role="presentation" style="max-width:680px;width:100%;background:#ffffff;border-radius:0 0 30px 30px;overflow:hidden;">

        <!-- Header -->
        <tr>
          <td style="background:#052d22;background-image:linear-gradient(135deg,#052d22 0%,#083f2f 55%,#031d17 100%);padding:34px 44px 96px;text-align:left;">
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              <tr>
                <td valign="top" style="width:66%;padding-right:18px;">
                  <div style="display:inline-block;background:#d7f36f;color:#071e18;border-radius:999px;padding:10px 15px;font-size:12px;font-weight:900;letter-spacing:0.12em;text-transform:uppercase;box-shadow:0 8px 18px rgba(0,0,0,0.14);">Coupon ready <span style="display:inline-block;margin-left:8px;background:#ffffff;color:#83c91e;border-radius:999px;width:22px;height:22px;line-height:22px;text-align:center;">✓</span></div>
                  <h1 style="color:#ffffff;margin:26px 0 14px;font-size:45px;line-height:1.06;font-weight:900;letter-spacing:0;">Your Great Clips deal is <span style="color:#a6df3e;">ready.</span></h1>
                  <p style="color:#edf5f1;margin:0;font-size:18px;line-height:1.55;">Open your coupon, show it before your cut, and save at participating salons.</p>
                </td>
                <td valign="top" align="right" style="width:34%;padding-top:22px;">
                  <div style="color:#ffffff;font-size:42px;line-height:0.95;font-weight:400;letter-spacing:0;">Great<br>Clips</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:#ffffff;padding:0 44px 34px;">

            <!-- Price badge -->
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin-top:-54px;margin-bottom:30px;">
              <tr>
                <td align="center">
                  <table width="520" cellpadding="0" cellspacing="0" role="presentation" style="max-width:520px;width:100%;background:#ffffff;border:1px solid #dfe8dc;border-radius:18px;box-shadow:0 18px 35px rgba(7,30,24,0.14);">
                    <tr>
                      <td align="center" style="padding:28px 20px 30px;">
                        <div style="color:#0a3026;font-size:16px;font-weight:900;letter-spacing:0.24em;text-transform:uppercase;margin-bottom:13px;">Great Clips Haircut</div>
                        <div style="color:#052d22;font-size:76px;line-height:0.95;font-weight:900;letter-spacing:0;">${priceStr}</div>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <!-- Value props -->
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin-bottom:34px;">
              <tr>
                <td valign="top" width="33.33%" style="padding:0 12px;text-align:left;">
                  <div style="color:#89cf28;font-size:34px;line-height:1;margin-bottom:9px;">[+]</div>
                  <div style="color:#0a3026;font-size:15px;font-weight:900;margin-bottom:5px;">Official Offer</div>
                  <div style="color:#4c5d58;font-size:13px;line-height:1.45;">100% authentic Great Clips coupon</div>
                </td>
                <td valign="top" width="33.33%" style="padding:0 12px;border-left:1px solid #d7dfd8;border-right:1px solid #d7dfd8;text-align:left;">
                  <div style="color:#89cf28;font-size:34px;line-height:1;margin-bottom:9px;">[&#10003;]</div>
                  <div style="color:#0a3026;font-size:15px;font-weight:900;margin-bottom:5px;">Ready to Use</div>
                  <div style="color:#4c5d58;font-size:13px;line-height:1.45;">Open it on your phone at the salon</div>
                </td>
                <td valign="top" width="33.33%" style="padding:0 12px;text-align:left;">
                  <div style="color:#89cf28;font-size:34px;line-height:1;margin-bottom:9px;">[&#9679;]</div>
                  <div style="color:#0a3026;font-size:15px;font-weight:900;margin-bottom:5px;">Location Specific</div>
                  <div style="color:#4c5d58;font-size:13px;line-height:1.45;">Check the offer page for full terms</div>
                </td>
              </tr>
            </table>

            <p style="color:#1c2e29;text-align:center;font-size:17px;line-height:1.6;margin:0 0 20px;">
              Open your coupon now and have it ready before you arrive.
            </p>

            <!-- CTA Button -->
            <div style="text-align:center;margin-bottom:26px;">
              <a href="${safeCouponUrl}"
                 style="display:inline-block;background:#87d11f;background-image:linear-gradient(135deg,#94dc25 0%,#6fbd16 100%);color:#ffffff;font-weight:900;font-size:23px;padding:18px 58px;border-radius:10px;text-decoration:none;letter-spacing:0;box-shadow:0 12px 24px rgba(106,184,20,0.28);">
                Open My Coupon &rarr;
              </a>
            </div>

            <!-- Redemption steps -->
            <div style="background:#f8faf6;border:1px solid #dfe8dc;border-radius:16px;padding:22px 26px;margin-bottom:22px;">
              <p style="margin:0 0 14px;font-weight:900;color:#0a3026;font-size:17px;text-transform:uppercase;letter-spacing:0.06em;">Use your coupon in 3 steps</p>
              <p style="margin:0;color:#1c2e29;font-size:15px;line-height:1.7;"><strong style="color:#6ead17;">1.</strong> Open the offer on your phone &nbsp;&nbsp; <strong style="color:#6ead17;">2.</strong> Show it before your haircut &nbsp;&nbsp; <strong style="color:#6ead17;">3.</strong> Save at the participating salon</p>
            </div>

            <!-- Partner offer -->
            <div style="background:#061f1a;background-image:linear-gradient(135deg,#061f1a 0%,#0a3529 100%);border-radius:18px;padding:28px 34px;margin-bottom:24px;box-shadow:0 14px 28px rgba(7,30,24,0.16);">
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td valign="middle" width="31%" align="center" style="padding-right:22px;">
                    <a href="https://curryleafplant.com/products/healthy-curry-leaf-plants-6-inches" style="text-decoration:none;">
                      <img src="https://curryleafplant.com/cdn/shop/products/Curry-Tree-Leaves.webp?v=1696697979&amp;width=360" width="150" alt="Healthy Curry Leaf Plant from Kumar's Garden" style="display:block;width:150px;max-width:100%;height:auto;border:0;border-radius:14px;">
                    </a>
                  </td>
                  <td valign="middle" width="69%">
                    <p style="margin:0 0 7px;color:#c7f36a;font-size:13px;font-weight:900;letter-spacing:0.1em;text-transform:uppercase;">Partner deal &bull; Save $10</p>
                    <p style="margin:0 0 8px;color:#ffffff;font-size:23px;line-height:1.2;font-weight:900;">Grow fresh curry leaves at home</p>
                    <p style="margin:0 0 18px;color:#d6e2de;font-size:15px;line-height:1.5;">Get $10 off a healthy 6-inch Curry Leaf Plant from our partner, Kumar's Garden.</p>
                    <a href="https://curryleafplant.com/products/healthy-curry-leaf-plants-6-inches"
                       style="display:inline-block;background:#d7f36f;color:#071e18;font-weight:900;font-size:16px;padding:13px 25px;border-radius:9px;text-decoration:none;">
                      Shop Curry Leaf Plants &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </div>

            <hr style="border:none;border-top:1px solid #dfe8dc;margin:0 0 18px;">

            <p style="color:#89938f;font-size:11px;text-align:center;margin:0;line-height:1.7;">
              You received this because you requested a coupon at
              <a href="https://greatclipsdeal.com" style="color:#17211f;font-weight:700;text-decoration:none;">greatclipsdeal.com</a><br>
              Partner offer provided by Kumar's Garden.<br>
              &copy; 2026 GreatClipsDeal.com &mdash; Not affiliated with Great Clips, Inc.
            </p>

          </td>
        </tr>

      </table>
    </td></tr>
  </table>
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
