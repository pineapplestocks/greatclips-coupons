# Official WhatsApp coupon self-confirmation

The existing email modal offers WhatsApp when /zernio/config is enabled. Website selection creates a short GC reference with a current-feed validated offer. The customer sends it privately to the connected Deal Dropper account. A signed Zernio message.received webhook binds the request to that sender and conversation, sends the existing group invite and an “I’ve joined” reply button. The button is bound to that coupon. On tap, the worker checks current coupon availability again and replies privately. self_confirmed_at is never treated as verified membership. No ongoing private marketing, group inspection or group posting is enabled.

Email and its skip option remain available. Legacy Baileys flags, experiment and Windows task remain disabled. The one-minute Cloudflare cron only drains the Zernio queue; existing daily email schedules are preserved. Requests, event receipts and outbox records expire after 90 days. STOP/cancel/unsubscribe suppress future coupon replies in the conversation; opt-out records persist until an explicit owner-mediated resubscription. No automatic resubscription occurs.

## Operations

Apply migration 006 after the existing migrations. Store ZERNIO_API_KEY and ZERNIO_WEBHOOK_SECRET as Worker secrets; matching private values are in ignored .env. Account ID, phone and group invite are in wrangler.toml. Enable ZERNIO_COUPONS_ENABLED only after account health and the signed webhook test pass. Deploy with npx wrangler deploy --config wrangler.toml --keep-vars. Publish docs through Pages.

Register a webhook named GreatClips coupon self-confirmation at /zernio/webhook, subscribing only to message.received with the configured secret. Signature is lowercase hex HMAC-SHA256 over the raw body. Incoming platform message IDs are deduplicated. Only the configured WhatsApp account, incoming messages and the matching sender/conversation are accepted; standby, echoes and stale events are ignored. Durable event rows are saved before acknowledgment. Background and cron workers lease each event for two minutes, with at most five attempts; Zernio sends use stable idempotency keys and immutable payloads. Replies older than the 23-hour window are skipped; no template or unsolicited-message fallback is attempted. Sending status means API accepted, not delivery or read confirmation. Never manually retry ambiguous sends with a new idempotency key.

Test: node --test tests/zernio-coupons.test.mjs tests/whatsapp.test.mjs tests/whatsapp-experiment.test.mjs. Tests mock outbound messages. For a live acceptance check, the owner selects a listed coupon, sends the prepared message, taps the confirmation and verifies the selected offer arrives once. Do not fabricate signed production inbound messages as a test.

Pause: set ZERNIO_COUPONS_ENABLED=false and redeploy. Email stays available and queue processing stops. No automatic activation of the legacy WhatsApp bot.

Sources: https://docs.zernio.com/webhooks ; https://docs.zernio.com/webhooks/inbox ; https://docs.zernio.com/messages/send-inbox-message .
