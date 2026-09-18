# WhatsApp coupon requests

Customer flow: select a coupon, consent to joining Deal Dropper, send the prefilled private WhatsApp request, join with the same number, and wait for admin approval. The random request code ties that person's number to the selected offer. Invite clicks never prove membership.

The homepage and salon coupon buttons use `/assets/whatsapp-entry.js`. `/whatsapp-coupon.html` shows request progress; `/whatsapp-admin.html` is the approval queue. Admin access uses the existing worker `ADMIN_TOKEN`, held only in tab memory. This dashboard is noindex, but the API bearer token is what protects it.

The bot runs from `C:\Users\mehul\whatsapp-deals`, using its existing Baileys linked-device session. This is not an official Cloud API integration. `couponGate` in the ignored bot `config.json` configures the worker URL and exact group ID/name. `COUPON_BRIDGE_TOKEN` in its ignored `.env` must match the worker secret `WHATSAPP_BRIDGE_TOKEN`. `couponGate.live` explicitly enables private replies independently of marketing-post dry-run settings.

Keep the computer and bot online. Membership checks run every 45 seconds; new requests are unavailable if the verified-group heartbeat is over three minutes old. Approvals require recent membership, which the bot checks again immediately before sending. A removed/expired/stale offer fails closed. Offers are restricted to the live site's verified feed and exclude the blocked coupons.

An admin checks the number and clicks **Approve & send**. STOP cancels pending requests. No ongoing private marketing is added. Each send acquires a database claim and writes a local receipt before contacting WhatsApp. Ambiguous outcomes and interrupted sends require manual review; never automatically resend them. `sent` means WhatsApp accepted the message, not that the recipient read it.

Request records and local receipts are cleaned up after 90 days. Worker cleanup runs on the existing daily schedule; local cleanup needs the bot online. This does not erase existing WhatsApp chats. The gate controls the site's supported coupon buttons, not copies of publicly available official offers or the public coupon feed.

## Deploy and operate

1. Run `node --test tests/whatsapp.test.mjs` and the bot's `node --test test/coupon-gate.test.js`.
2. Apply `cloudflare-worker/migrations/002_whatsapp_coupon_requests.sql` with Wrangler D1 using `--config wrangler.toml`.
3. Set the bridge secret using `wrangler secret put WHATSAPP_BRIDGE_TOKEN --config wrangler.toml`. Never put tokens in source, URLs, or chat.
4. Deploy the worker with `npx wrangler deploy --config wrangler.toml --keep-vars` and publish the `docs` directory through the existing Pages workflow.
5. Enable `WHATSAPP_COUPONS_ENABLED="true"` in `wrangler.toml`, deploy, and confirm `/whatsapp/config` reports enabled and online. Start/restart only the existing bot instance to avoid competing linked sessions.

To pause new WhatsApp requests and return the main buttons to their previous flow, set the worker flag to `false`, redeploy, and reload the site. Existing request pages remain available for status checking. Do not delete the delivery ledger to retry a send.

Tests use fake numbers, a mocked WhatsApp socket, and an in-memory database. They do not send messages to real people.
