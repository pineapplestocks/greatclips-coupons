DROP INDEX IF EXISTS idx_wa_active_coupon;
CREATE UNIQUE INDEX idx_wa_active_coupon ON whatsapp_requests(wa_id,coupon_url)
  WHERE wa_id IS NOT NULL AND status IN ('awaiting_join','ready','awaiting_approval','approved','sending','sent','uncertain');
