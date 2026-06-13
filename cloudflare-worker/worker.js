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

    const priceStr = price ? price : 'Great Clips';
    const subject = `Your ${priceStr} Great Clips coupon is ready`;

    const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Your Great Clips Coupon</title>
</head>
<body style="margin:0;padding:0;background:#f6f3ee;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f3ee;padding:28px 14px;">
    <tr><td align="center">
      <table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:#17211f;border-radius:24px 24px 0 0;padding:30px 28px 26px;text-align:left;">
            <p style="display:inline-block;margin:0 0 16px;background:#d8f36a;color:#17211f;border-radius:999px;padding:7px 12px;font-size:12px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;">Coupon ready</p>
            <h1 style="color:#ffffff;margin:0 0 8px;font-size:31px;line-height:1.12;font-weight:900;">Your Great Clips deal is ready.</h1>
            <p style="color:#c9d6d1;margin:0;font-size:15px;line-height:1.55;">Open your coupon, show it before your cut, and save at participating salons.</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:#ffffff;padding:30px 28px;border-radius:0 0 24px 24px;box-shadow:0 18px 45px rgba(23,33,31,0.12);">

            <!-- Price badge -->
            <div style="text-align:center;margin-bottom:26px;">
              <div style="display:inline-block;background:#fff8e7;border:1px solid #f1d28a;border-radius:22px;padding:22px 42px;box-shadow:inset 0 0 0 2px #fff2c7;">
                <p style="margin:0 0 6px;color:#85620a;font-size:12px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;">Great Clips haircut</p>
                <span style="font-size:58px;font-weight:900;color:#bf6200;line-height:0.98;">${priceStr}</span>
              </div>
            </div>

            <p style="color:#263330;text-align:center;font-size:16px;line-height:1.65;margin:0 0 24px;">
              Click below to open the coupon on the official Great Clips offer page.<br>
              <strong style="color:#17211f;">Valid for 14 days after you first redeem it.</strong>
            </p>

            <!-- CTA Button -->
            <div style="text-align:center;margin-bottom:26px;">
              <a href="${coupon_url}"
                 style="display:inline-block;background:#17211f;color:#ffffff;font-weight:800;font-size:17px;padding:16px 34px;border-radius:999px;text-decoration:none;letter-spacing:0.01em;box-shadow:0 10px 24px rgba(23,33,31,0.22);">
                Open My Coupon &rarr;
              </a>
            </div>

            <!-- Tips -->
            <div style="background:#f7f8f4;border:1px solid #e5eadc;border-radius:18px;padding:18px 20px;margin-bottom:18px;">
              <p style="margin:0 0 12px;font-weight:900;color:#17211f;font-size:13px;text-transform:uppercase;letter-spacing:0.08em;">How to use it</p>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="28" valign="top" style="color:#7a8f1f;font-weight:900;font-size:15px;line-height:1.8;">1</td>
                  <td style="color:#465653;font-size:14px;line-height:1.8;">Open the coupon link on your phone.</td>
                </tr>
                <tr>
                  <td width="28" valign="top" style="color:#7a8f1f;font-weight:900;font-size:15px;line-height:1.8;">2</td>
                  <td style="color:#465653;font-size:14px;line-height:1.8;">Show it to your stylist before your haircut.</td>
                </tr>
                <tr>
                  <td width="28" valign="top" style="color:#7a8f1f;font-weight:900;font-size:15px;line-height:1.8;">3</td>
                  <td style="color:#465653;font-size:14px;line-height:1.8;">Print it instead if that is easier.</td>
                </tr>
              </table>
            </div>

            <!-- Donation -->
            <div style="background:#17211f;border-radius:18px;padding:20px;margin-bottom:22px;text-align:center;">
              <p style="margin:0 0 6px;color:#d8f36a;font-size:13px;font-weight:900;letter-spacing:0.08em;text-transform:uppercase;">Did the coupon work?</p>
              <p style="margin:0 0 15px;color:#ffffff;font-size:15px;line-height:1.6;">A $0.50 Venmo donation helps keep GreatClipsDeal live and updated.</p>
              <a href="https://venmo.com/GoldBond123?txn=pay&amp;amount=0.50&amp;note=GreatClipsDeal%20coupon%20worked"
                 style="display:inline-block;background:#3d95ce;color:#ffffff;font-weight:800;font-size:15px;padding:12px 22px;border-radius:999px;text-decoration:none;">
                Send $0.50 on Venmo
              </a>
              <p style="margin:10px 0 0;color:#adc0ba;font-size:12px;">@GoldBond123</p>
            </div>

            <hr style="border:none;border-top:1px solid #e4e8e2;margin:0 0 18px;">

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
          coupon_url,
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
