CREATE TABLE IF NOT EXISTS coupon_day_passes (
 token_hash TEXT PRIMARY KEY,
 checkout_id TEXT UNIQUE,
 checkout_url TEXT,
 created_at INTEGER NOT NULL,
 paid_at INTEGER,
 expires_at INTEGER,
 payment_intent TEXT,
 status TEXT NOT NULL DEFAULT 'pending'
);
