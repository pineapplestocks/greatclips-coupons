CREATE TABLE IF NOT EXISTS zernio_membership_checks (
 code TEXT PRIMARY KEY,
 sender_phone TEXT,
 requested_at INTEGER NOT NULL,
 last_inbound_at INTEGER NOT NULL,
 checked_at INTEGER,
 member INTEGER NOT NULL DEFAULT 0,
 verified_at INTEGER,
 state TEXT NOT NULL DEFAULT 'pending',
 lease_until INTEGER NOT NULL DEFAULT 0,
 lease_token TEXT
);
CREATE INDEX IF NOT EXISTS zernio_membership_pending
 ON zernio_membership_checks(state,lease_until,last_inbound_at);
