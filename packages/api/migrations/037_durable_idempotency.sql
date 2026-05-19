-- Durable idempotency records that survive Redis restarts.
-- Redis remains the primary fast path; DB is write-through + fallback.

CREATE TABLE IF NOT EXISTS idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    response_status INT NOT NULL,
    response_body   JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days')
);

CREATE INDEX IF NOT EXISTS idx_idempotency_expires
    ON idempotency_records (expires_at)
    WHERE expires_at < now();

-- Retention cleanup: run periodically
-- DELETE FROM idempotency_records WHERE expires_at < now();
