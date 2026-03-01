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

    const { email, coupon_url, price } = body;

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return jsonResponse({ error: 'Invalid email address' }, 400);
    }

    if (!coupon_url) {
      return jsonResponse({ error: 'Missing coupon_url' }, 400);
    }

    const priceStr = price ? price : 'Great Clips';
    const subject = `Your ${priceStr} Great Clips Coupon ✂️`;

    const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Your Great Clips Coupon</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#7c3aed,#db2777);border-radius:16px 16px 0 0;padding:32px;text-align:center;">
            <p style="margin:0;font-size:32px;">✂️</p>
            <h1 style="color:white;margin:8px 0 4px;font-size:26px;">Great Clips Deal</h1>
            <p style="color:rgba(255,255,255,0.8);margin:0;font-size:15px;">Your coupon is ready to use!</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:white;padding:32px;border-radius:0 0 16px 16px;box-shadow:0 4px 12px rgba(0,0,0,0.08);">

            <!-- Price badge -->
            <div style="text-align:center;margin-bottom:28px;">
              <div style="display:inline-block;background:#fffbeb;border:2px dashed #f59e0b;border-radius:14px;padding:18px 40px;">
                <span style="font-size:52px;font-weight:900;color:#d97706;line-height:1;">${priceStr}</span>
                <p style="margin:6px 0 0;color:#92400e;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Great Clips Haircut</p>
              </div>
            </div>

            <p style="color:#374151;text-align:center;font-size:15px;line-height:1.6;margin:0 0 24px;">
              Click the button below to open your coupon on the Great Clips website.<br>
              <strong>Valid for 14 days after you first redeem it.</strong>
            </p>

            <!-- CTA Button -->
            <div style="text-align:center;margin-bottom:28px;">
              <a href="${coupon_url}"
                 style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#db2777);color:white;font-weight:700;font-size:18px;padding:16px 48px;border-radius:12px;text-decoration:none;letter-spacing:0.02em;">
                Claim My Coupon &rarr;
              </a>
            </div>

            <!-- Tips -->
            <div style="background:#f9fafb;border-radius:10px;padding:16px 20px;margin-bottom:24px;">
              <p style="margin:0 0 8px;font-weight:700;color:#374151;font-size:13px;text-transform:uppercase;letter-spacing:0.05em;">💡 How to use</p>
              <ul style="margin:0;padding-left:18px;color:#6b7280;font-size:13px;line-height:1.8;">
                <li>Open the coupon link above on your phone</li>
                <li>Show it to your stylist <strong>before</strong> your haircut</li>
                <li>Or print it and bring it in</li>
              </ul>
            </div>

            <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 20px;">

            <p style="color:#9ca3af;font-size:11px;text-align:center;margin:0;line-height:1.6;">
              You received this because you requested a coupon at
              <a href="https://greatclipsdeal.com" style="color:#7c3aed;text-decoration:none;">greatclipsdeal.com</a><br>
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

    return jsonResponse({ ok: true });
  },
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
