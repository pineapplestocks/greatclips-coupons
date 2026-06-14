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
    queryAll(env, `SELECT email, coupon_url, location_name, city, state, subscribed_at
      FROM subscribers ORDER BY subscribed_at DESC LIMIT 8`),
    queryAll(env, `SELECT COALESCE(NULLIF(state, ''), 'Unknown') AS state, COUNT(*) AS count
      FROM subscribers GROUP BY COALESCE(NULLIF(state, ''), 'Unknown')
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
                { render: (row) => `${row.location_name || 'Unknown'} ${row.state ? `(${row.state})` : ''}` },
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

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
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
                  <div style="color:#89cf28;font-size:34px;line-height:1;margin-bottom:9px;">[$]</div>
                  <div style="color:#0a3026;font-size:15px;font-weight:900;margin-bottom:5px;">Instant Savings</div>
                  <div style="color:#4c5d58;font-size:13px;line-height:1.45;">Show before your cut to save</div>
                </td>
                <td valign="top" width="33.33%" style="padding:0 12px;text-align:left;">
                  <div style="color:#89cf28;font-size:34px;line-height:1;margin-bottom:9px;">[14]</div>
                  <div style="color:#0a3026;font-size:15px;font-weight:900;margin-bottom:5px;">Valid for 14 Days</div>
                  <div style="color:#4c5d58;font-size:13px;line-height:1.45;">After your first redeem</div>
                </td>
              </tr>
            </table>

            <p style="color:#1c2e29;text-align:center;font-size:17px;line-height:1.6;margin:0 0 20px;">
              Click below to open the coupon on the official Great Clips offer page.
            </p>

            <!-- CTA Button -->
            <div style="text-align:center;margin-bottom:26px;">
              <a href="${safeCouponUrl}"
                 style="display:inline-block;background:#87d11f;background-image:linear-gradient(135deg,#94dc25 0%,#6fbd16 100%);color:#ffffff;font-weight:900;font-size:23px;padding:18px 58px;border-radius:10px;text-decoration:none;letter-spacing:0;box-shadow:0 12px 24px rgba(106,184,20,0.28);">
                Open My Coupon &rarr;
              </a>
            </div>

            <!-- Tips -->
            <div style="background:#f8faf6;border:1px solid #dfe8dc;border-radius:16px;padding:24px 26px;margin-bottom:22px;">
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td valign="top" width="58%" style="padding-right:20px;">
                    <p style="margin:0 0 20px;font-weight:900;color:#0a3026;font-size:19px;text-transform:uppercase;letter-spacing:0.06em;">How to use it</p>
                    <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                      <tr>
                        <td width="38" valign="top" style="padding-bottom:13px;"><div style="background:#8bd124;color:#0a3026;border-radius:999px;width:28px;height:28px;line-height:28px;text-align:center;font-weight:900;">1</div></td>
                        <td style="color:#1c2e29;font-size:15px;line-height:1.65;padding-bottom:13px;">Open the coupon link on your phone.</td>
                      </tr>
                      <tr>
                        <td width="38" valign="top" style="padding-bottom:13px;"><div style="background:#8bd124;color:#0a3026;border-radius:999px;width:28px;height:28px;line-height:28px;text-align:center;font-weight:900;">2</div></td>
                        <td style="color:#1c2e29;font-size:15px;line-height:1.65;padding-bottom:13px;">Show it to your stylist <strong>before your haircut.</strong></td>
                      </tr>
                      <tr>
                        <td width="38" valign="top"><div style="background:#8bd124;color:#0a3026;border-radius:999px;width:28px;height:28px;line-height:28px;text-align:center;font-weight:900;">3</div></td>
                        <td style="color:#1c2e29;font-size:15px;line-height:1.65;">Print it instead if that is easier.</td>
                      </tr>
                    </table>
                  </td>
                  <td valign="bottom" width="42%" style="text-align:center;">
                    <div style="background:#eaf2e8;border-radius:999px;width:180px;height:120px;margin:0 auto 10px;"></div>
                    <div style="background:#ffffff;border:3px solid #1e4a3d;border-radius:8px 8px 0 0;width:190px;margin:-96px auto 0;padding:8px 0;color:#0a3026;font-weight:900;font-size:14px;">Great Clips</div>
                    <div style="border-left:3px solid #1e4a3d;border-right:3px solid #1e4a3d;border-bottom:3px solid #1e4a3d;width:190px;height:70px;margin:0 auto;background:#f7fbf4;">
                      <div style="display:inline-block;width:70px;height:58px;border-right:2px solid #8aa297;margin-top:12px;"></div>
                      <div style="display:inline-block;width:70px;height:58px;margin-top:12px;"></div>
                    </div>
                  </td>
                </tr>
              </table>
            </div>

            <!-- Donation -->
            <div style="background:#061f1a;background-image:linear-gradient(135deg,#061f1a 0%,#082c24 100%);border-radius:18px;padding:28px 34px;margin-bottom:24px;box-shadow:0 14px 28px rgba(7,30,24,0.16);">
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td valign="middle" width="28%" align="center" style="padding-right:20px;">
                    <div style="background:rgba(255,255,255,0.1);border-radius:999px;width:104px;height:104px;line-height:104px;color:#c7f36a;font-size:48px;">♡</div>
                  </td>
                  <td valign="middle" width="72%">
                    <p style="margin:0 0 8px;color:#c7f36a;font-size:16px;font-weight:900;letter-spacing:0.12em;text-transform:uppercase;">Did the coupon work?</p>
                    <p style="margin:0 0 18px;color:#ffffff;font-size:17px;line-height:1.45;">A $0.50 Venmo donation helps keep GreatClipsDeal live and updated.</p>
                    <a href="https://venmo.com/GoldBond123?txn=pay&amp;amount=0.50&amp;note=GreatClipsDeal%20coupon%20worked"
                       style="display:inline-block;background:#2f92f4;background-image:linear-gradient(135deg,#2f92f4 0%,#1f72db 100%);color:#ffffff;font-weight:900;font-size:17px;padding:13px 34px;border-radius:999px;text-decoration:none;">
                      Send $0.50 on Venmo
                    </a>
                    <p style="margin:12px 0 0;color:#aebfbb;font-size:13px;">@GoldBond123</p>
                  </td>
                </tr>
              </table>
            </div>

            <hr style="border:none;border-top:1px solid #dfe8dc;margin:0 0 18px;">

            <p style="color:#89938f;font-size:11px;text-align:center;margin:0;line-height:1.7;">
              You received this because you requested a coupon at
              <a href="https://greatclipsdeal.com" style="color:#17211f;font-weight:700;text-decoration:none;">greatclipsdeal.com</a><br>
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
        await env.DB.prepare(
          `INSERT INTO subscribers (email, location_name, city, state, coupon_url, subscribed_at)
           VALUES (?, ?, ?, ?, ?, ?)`
        ).bind(
          email,
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
  },
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
