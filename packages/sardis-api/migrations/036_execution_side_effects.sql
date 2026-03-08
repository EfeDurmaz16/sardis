-- Side-effect queue for durable post-payment operations (ledger, webhooks, spend recording).
-- Uses FOR UPDATE SKIP LOCKED for concurrent worker consumption.

CREATE TABLE IF NOT EXISTS execution_side_effects (
    id              BIGSERIAL PRIMARY KEY,
    tx_id           TEXT NOT NULL,              -- Idempotency / correlation key
    effect_type     TEXT NOT NULL,              -- 'ledger_append', 'webhook', 'spend_record', 'alert'
    payload         JSONB NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    attempt_count   INT NOT NULL DEFAULT 0,
    max_attempts    INT NOT NULL DEFAULT 5,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    next_retry_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_side_effects_pending
    ON execution_side_effects (next_retry_at)
    WHERE status IN ('pending', 'failed') AND attempt_count < max_attempts;

CREATE INDEX IF NOT EXISTS idx_side_effects_tx_id
    ON execution_side_effects (tx_id);

-- Auto-purge completed side effects older than 7 days (run via cron or pg_cron)
-- DELETE FROM execution_side_effects WHERE status = 'completed' AND processed_at < now() - interval '7 days';
