CREATE TABLE whatsapp_experiments (
  id TEXT PRIMARY KEY, starts_at INTEGER NOT NULL, ends_at INTEGER NOT NULL
);
INSERT INTO whatsapp_experiments VALUES('wa-popup-v1',CAST(strftime('%s','now') AS INTEGER)*1000,CAST(strftime('%s','now') AS INTEGER)*1000+2419200000);
CREATE TABLE whatsapp_exposures (
  experiment_id TEXT NOT NULL, visitor_id TEXT NOT NULL, variant TEXT NOT NULL CHECK(variant IN ('A','B','C')),
  assigned_at INTEGER NOT NULL, ip_hash TEXT NOT NULL, exposed_at INTEGER, clicked_at INTEGER, dismissed_at INTEGER,
  PRIMARY KEY(experiment_id,visitor_id)
);
CREATE INDEX idx_wa_exposure_ip ON whatsapp_exposures(ip_hash,assigned_at);
ALTER TABLE whatsapp_requests ADD COLUMN experiment_id TEXT;
ALTER TABLE whatsapp_requests ADD COLUMN experiment_visitor TEXT;
ALTER TABLE whatsapp_requests ADD COLUMN claimed_at INTEGER;
ALTER TABLE whatsapp_requests ADD COLUMN membership_initial INTEGER;
ALTER TABLE whatsapp_requests ADD COLUMN member_confirmed_at INTEGER;
CREATE INDEX idx_wa_experiment_requests ON whatsapp_requests(experiment_id,experiment_visitor,created_at);
CREATE TABLE whatsapp_experiment_results (experiment_id TEXT PRIMARY KEY, saved_at INTEGER NOT NULL, report_json TEXT NOT NULL);
