-- Bind durable idempotency records to the original request fingerprint.
-- Redis already stores request_hash; this closes the DB fallback gap.

ALTER TABLE idempotency_records
    ADD COLUMN IF NOT EXISTS request_hash TEXT;

UPDATE idempotency_records
SET request_hash = 'legacy-unbound'
WHERE request_hash IS NULL;

ALTER TABLE idempotency_records
    ALTER COLUMN request_hash SET NOT NULL;
