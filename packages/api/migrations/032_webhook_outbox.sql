-- 032: Webhook outbox table for guaranteed delivery
-- Implements the transactional outbox pattern: webhook events are written
-- to this table within the same DB transaction as the business operation,
-- then delivered by a background worker.

CREATE TABLE IF NOT EXISTS webhook_outbox (
    outbox_id    TEXT PRIMARY KEY,
    event_id     TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    payload      JSONB NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending, sending, delivered, failed
    attempts     INTEGER NOT NULL DEFAULT 0,
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for the flush query: pending events ordered by creation time
CREATE INDEX IF NOT EXISTS idx_webhook_outbox_pending
    ON webhook_outbox (created_at ASC)
    WHERE status IN ('pending', 'sending');

-- Index for cleanup of old delivered events
CREATE INDEX IF NOT EXISTS idx_webhook_outbox_delivered
    ON webhook_outbox (updated_at)
    WHERE status = 'delivered';

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_webhook_outbox_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_webhook_outbox_updated_at ON webhook_outbox;
CREATE TRIGGER trg_webhook_outbox_updated_at
    BEFORE UPDATE ON webhook_outbox
    FOR EACH ROW
    EXECUTE FUNCTION update_webhook_outbox_updated_at();
