# Automatic WhatsApp coupon delivery

The customer selects a coupon, consents to joining Deal Dropper, sends a prefilled private WhatsApp request, and joins with the same number. A random request code matches that number to the selected offer. The bot checks actual group membership and sends the coupon automatically, usually within about a minute while online. There is no approval queue or manual release step. Invite clicks alone never prove membership.

The homepage and salon buttons use `/assets/whatsapp-entry.js`. `/whatsapp-coupon.html` shows progress. The bot runs from `C:\Users\mehul\whatsapp-deals` using its existing unofficial Baileys linked-device session. Keep the computer and bot online. New requests fail closed after three minutes without a verified-group heartbeat.

Bot configuration lives in its ignored `config.json` under `couponGate`; `live` explicitly enables private fulfillment. `COUPON_BRIDGE_TOKEN` in its ignored `.env` must match worker secret `WHATSAPP_BRIDGE_TOKEN`. Never put tokens in source or URLs. The authenticated admin API supports diagnostic listing and cancellation only; it cannot approve or release a coupon.

Membership checks run every 45 seconds and again immediately before sending. The worker rechecks the selected offer against the current verified public feed. Removed, expired or stale coupons are not sent. STOP cancels pending requests and does not affect unrelated group membership. No ongoing private marketing is added.

A database claim and local receipt precede each send. Ambiguous/interrupted sends are held for troubleshooting rather than blindly retried. `sent` means WhatsApp accepted the message, not that the recipient read it. Request records and local receipts are cleaned after 90 days; local cleanup requires the bot online. This does not erase WhatsApp chats. The gate controls supported site buttons, not copies of public official offers or the public feed.

## Deployment

- Tests: `node --test tests/whatsapp.test.mjs`, plus `node --test test/coupon-gate.test.js` in the bot folder. These use fake numbers and mocked sends.
- Apply migrations 002 and 003 in order using Wrangler D1 and `--config wrangler.toml`.
- Set `WHATSAPP_BRIDGE_TOKEN` with `wrangler secret put` and the matching bot secret locally.
- Deploy with `npx wrangler deploy --config wrangler.toml --keep-vars`. Publish `docs` through the existing Pages workflow.
- Restart only the existing bot instance. Confirm `/whatsapp/config` returns enabled and online.
- Pause by setting `WHATSAPP_COUPONS_ENABLED="false"` in `wrangler.toml` and redeploying. Reloaded main buttons then use their previous flow.
