CREATE TABLE IF NOT EXISTS whatsapp_requests (
  id TEXT PRIMARY KEY,
  status_token TEXT NOT NULL,
  coupon_url TEXT NOT NULL,
  coupon_label TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  ip_hash TEXT NOT NULL,
  consent_version TEXT NOT NULL,
  wa_id TEXT,
  sender_jid TEXT,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'awaiting_message',
  member_verified INTEGER NOT NULL DEFAULT 0,
  member_checked_at INTEGER,
  approved_at INTEGER,
  sent_at INTEGER,
  message_id TEXT,
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_wa_status ON whatsapp_requests(status, created_at);
CREATE INDEX IF NOT EXISTS idx_wa_ip ON whatsapp_requests(ip_hash, created_at);
CREATE INDEX IF NOT EXISTS idx_wa_number ON whatsapp_requests(wa_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_wa_active_coupon ON whatsapp_requests(wa_id,coupon_url)
  WHERE wa_id IS NOT NULL AND status IN ('awaiting_join','awaiting_approval','approved','sending','sent','uncertain');
CREATE TABLE IF NOT EXISTS whatsapp_runtime (id INTEGER PRIMARY KEY CHECK(id=1), heartbeat INTEGER NOT NULL);
