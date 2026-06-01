-- Durable idempotency records that survive Redis restarts.
-- Redis remains the primary fast path; DB is write-through + fallback.

CREATE TABLE IF NOT EXISTS idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    response_status INT NOT NULL,
    response_body   JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days')
);

-- Plain b-tree index on expires_at to accelerate the retention sweep
-- (DELETE ... WHERE expires_at < now()). A partial predicate using now()
-- is rejected by Postgres because now() is STABLE, not IMMUTABLE.
CREATE INDEX IF NOT EXISTS idx_idempotency_expires
    ON idempotency_records (expires_at);

-- Retention cleanup: run periodically
-- DELETE FROM idempotency_records WHERE expires_at < now();
