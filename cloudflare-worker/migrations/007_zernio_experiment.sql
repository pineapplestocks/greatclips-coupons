INSERT INTO whatsapp_experiments(id,starts_at,ends_at) VALUES('zernio-popup-v1',CAST(strftime('%s','now') AS INTEGER)*1000,CAST(strftime('%s','now') AS INTEGER)*1000+2419200000);
ALTER TABLE whatsapp_exposures ADD COLUMN exited_at INTEGER;
ALTER TABLE zernio_coupon_requests ADD COLUMN experiment_id TEXT;
ALTER TABLE zernio_coupon_requests ADD COLUMN experiment_visitor TEXT;
ALTER TABLE zernio_coupon_requests ADD COLUMN claimed_at INTEGER;
CREATE INDEX zernio_experiment_requests ON zernio_coupon_requests(experiment_id,experiment_visitor,created_at);
