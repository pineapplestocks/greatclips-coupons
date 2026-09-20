CREATE TABLE IF NOT EXISTS zernio_coupon_requests (
 code TEXT PRIMARY KEY, coupon_url TEXT NOT NULL, label TEXT NOT NULL, created_at INTEGER NOT NULL,
 ip_hash TEXT NOT NULL, conversation_id TEXT, sender_id TEXT, self_confirmed_at INTEGER,
 sent_at INTEGER, cancelled_at INTEGER
);
CREATE INDEX IF NOT EXISTS zernio_request_ip ON zernio_coupon_requests(ip_hash,created_at);
CREATE TABLE IF NOT EXISTS zernio_events (
 id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at INTEGER NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending', lease_until INTEGER NOT NULL DEFAULT 0,
 attempts INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS zernio_outbox (
 id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, payload TEXT NOT NULL,
 created_at INTEGER NOT NULL, sent_at INTEGER, message_id TEXT
);
CREATE TABLE IF NOT EXISTS zernio_optouts (conversation_id TEXT PRIMARY KEY, stopped_at INTEGER NOT NULL);

CREATE INDEX IF NOT EXISTS zernio_events_ready ON zernio_events(state,lease_until,created_at);
