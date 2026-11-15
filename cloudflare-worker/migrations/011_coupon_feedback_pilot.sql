CREATE TABLE IF NOT EXISTS coupon_feedback_pilot (
 code TEXT PRIMARY KEY,
 conversation_id TEXT NOT NULL UNIQUE,
 sender_id TEXT NOT NULL UNIQUE,
 variant TEXT NOT NULL CHECK(variant IN ('A','B','C')),
 created_at INTEGER NOT NULL,
 last_inbound_at INTEGER NOT NULL,
 checkin_sent_at INTEGER,
 feedback TEXT,
 feedback_at INTEGER,
 support_opted_in_at INTEGER,
 support_sent_at INTEGER,
 declined_at INTEGER
);
