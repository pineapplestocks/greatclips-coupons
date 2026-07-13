/**
 * Cloudflare Worker — Stripe payment backend for the $5 coupon paywall on GreatClipsDeal.com
 *
 * Environment variables to set in Cloudflare dashboard (Workers > greatclips-payments > Settings > Variables):
 *   STRIPE_SECRET_KEY — your Stripe secret key (sk_live_... or sk_test_... while testing). Mark as "Encrypt".
 *
 * Routes:
 *   POST /create-payment-intent  -> { client_secret }
 *   POST /refund                 -> { status } (body: { payment_intent_id })
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

const UNLOCK_AMOUNT_CENTS = 75;

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

async function stripeRequest(env, path, params) {
  const body = new URLSearchParams(params);
  const res = await fetch(`https://api.stripe.com/v1/${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error?.message || 'Stripe request failed');
  }
  return data;
}

async function handleCreatePaymentIntent(env) {
  const intent = await stripeRequest(env, 'payment_intents', {
    amount: String(UNLOCK_AMOUNT_CENTS),
    currency: 'usd',
    'automatic_payment_methods[enabled]': 'true',
    description: 'Unlock exclusive $5 Great Clips coupon',
  });
  return jsonResponse({ client_secret: intent.client_secret, id: intent.id });
}

async function handleRefund(env, request) {
  const body = await request.json().catch(() => ({}));
  const paymentIntentId = body.payment_intent_id;
  if (!paymentIntentId || typeof paymentIntentId !== 'string') {
    return jsonResponse({ error: 'payment_intent_id is required' }, 400);
  }

  const refund = await stripeRequest(env, 'refunds', {
    payment_intent: paymentIntentId,
  });
  return jsonResponse({ status: refund.status });
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    try {
      if (request.method === 'POST' && url.pathname === '/create-payment-intent') {
        return await handleCreatePaymentIntent(env);
      }
      if (request.method === 'POST' && url.pathname === '/refund') {
        return await handleRefund(env, request);
      }
    } catch (err) {
      return jsonResponse({ error: err.message || 'Internal error' }, 500);
    }

    return jsonResponse({ error: 'Not found' }, 404);
  },
};
