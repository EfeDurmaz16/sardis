-- 057: Persistent reconciliation queue
--
-- Replaces InMemoryReconciliationQueue that loses pending entries on restart.
-- Any payment where ledger append fails after chain execution will now
-- persist its reconciliation state across process restarts.

CREATE TABLE IF NOT EXISTS reconciliation_queue (
    id              BIGSERIAL PRIMARY KEY,
    entry_type      TEXT NOT NULL,
    payload_json    JSONB NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    CHECK (status IN ('pending', 'processing', 'resolved', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_recon_queue_status
    ON reconciliation_queue (status) WHERE status = 'pending';
