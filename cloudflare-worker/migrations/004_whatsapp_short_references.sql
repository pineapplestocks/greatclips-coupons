ALTER TABLE whatsapp_requests ADD COLUMN request_code TEXT;
CREATE UNIQUE INDEX idx_wa_request_code ON whatsapp_requests(request_code);
