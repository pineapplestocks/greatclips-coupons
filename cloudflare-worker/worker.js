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

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
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

    const brevoRes = await fetch('https://api.brevo.com/v3/smtp/email', {
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
        to: [{ email }],
        subject,
        htmlContent,
      }),
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
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
