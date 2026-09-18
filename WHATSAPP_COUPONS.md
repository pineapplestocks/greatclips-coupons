# Automatic WhatsApp coupon delivery

The customer selects a coupon and sees one popup on the same page. Clicking its WhatsApp button requests a private invitation and coupon; there is no consent checkbox or separate landing page. WhatsApp opens with a prefilled request, which they send before joining with the same number. A random request code matches that number to the selected offer. The bot checks actual group membership and sends the coupon automatically, usually within about a minute while online. There is no approval queue or manual release step. Invite clicks alone never prove membership.

The homepage and salon buttons use `/assets/whatsapp-entry.js`. The popup handles progress and can show the group invite after the private request is linked. `/whatsapp-coupon.html` remains available for existing request links, but main coupon buttons no longer navigate there. The bot runs from `C:\Users\mehul\whatsapp-deals` using its existing unofficial Baileys linked-device session. Keep the computer and bot online. New requests fail closed after three minutes without a verified-group heartbeat.

Bot configuration lives in its ignored `config.json` under `couponGate`; `live` explicitly enables private fulfillment. `COUPON_BRIDGE_TOKEN` in its ignored `.env` must match worker secret `WHATSAPP_BRIDGE_TOKEN`. Never put tokens in source or URLs. The authenticated admin API supports diagnostic listing and cancellation only; it cannot approve or release a coupon.

Membership checks run every 45 seconds and again immediately before sending. The worker rechecks the selected offer against the current verified public feed. Removed, expired or stale coupons are not sent. STOP cancels pending requests and does not affect unrelated group membership. No ongoing private marketing is added.

A database claim and local receipt precede each send. Ambiguous/interrupted sends are held for troubleshooting rather than blindly retried. `sent` means WhatsApp accepted the message, not that the recipient read it. Request records and local receipts are cleaned after 90 days; local cleanup requires the bot online. This does not erase WhatsApp chats. The gate controls supported site buttons, not copies of public official offers or the public feed.

## Deployment

- Tests: `node --test tests/whatsapp.test.mjs`, plus `node --test test/coupon-gate.test.js` in the bot folder. These use fake numbers and mocked sends.
- Apply migrations 002 and 003 in order using Wrangler D1 and `--config wrangler.toml`.
- Set `WHATSAPP_BRIDGE_TOKEN` with `wrangler secret put` and the matching bot secret locally.
- Deploy with `npx wrangler deploy --config wrangler.toml --keep-vars`. Publish `docs` through the existing Pages workflow.
- Restart only the existing bot instance. Confirm `/whatsapp/config` returns enabled and online.
- Windows task `WhatsApp Deals Automatic Delivery` starts the supervised bot at Mehul's sign-in. Its local script is `C:\Users\mehul\whatsapp-deals\scripts\run-supervised.ps1`; it restarts an exited bot after 30 seconds. The computer must stay awake and online. Do not run a second `npm start` alongside it. Logs are in the bot's `data/supervised.stdout.log` and `data/supervised.stderr.log`.
- Pause by setting `WHATSAPP_COUPONS_ENABLED="false"` in `wrangler.toml` and redeploying. The popup then shows delivery as unavailable.
