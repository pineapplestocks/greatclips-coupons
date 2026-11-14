# Browser day passes

Separate Worker: `greatclips-payments`, configured by `wrangler-payments.toml`.
Do not deploy the email Worker as part of this feature.

Apply `migrations/010_coupon_day_pass.sql` to the existing D1 database. Install
`STRIPE_SECRET_KEY` using encrypted Worker secrets. Never put it in source,
client JavaScript, logs, or command arguments. Set `DAY_PASS_ENABLED` to `true`
only after the live account is connected and checkout has been checked.

The $0.75 price is fixed on the server. Checkout is a one-time card payment;
there is no subscription. A random 256-bit browser token is stored locally;
only its SHA-256 hash is stored in D1 and Stripe's client reference. Retry
uses the same Checkout Session and idempotency key. A new token is generated
only after the previous checkout/pass is confirmed expired or revoked.

There is no webhook fulfillment dependency: each status check and redemption
retrieves the stored Checkout Session directly from Stripe, verifies the
browser reference, product marker, paid status, amount, currency, and charge,
and checks refund/dispute status. The 24-hour expiry is based on the charge
creation timestamp, never the return URL or browser clock. Visitors can
return without the success redirect and still recover their paid access.
Stripe outages fail closed, while the independent free WhatsApp path remains.

The pass bypasses group prompts; it does not make publicly listed coupon URLs
secret. Current coupons are validated against the live feed before checkout
and on each redemption. The homepage and city generators preserve the hooks.

Validation: `node --test tests/day-pass.test.mjs`.
Browser DOM checks (requires `jsdom`): `node --test tests/day-pass-browser.test.mjs`.
To pause new use, deploy with `DAY_PASS_ENABLED=false`. This also temporarily
pauses paid redemption, so restore service promptly for active customers.
