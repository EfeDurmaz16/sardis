-- Migration 048: Settlement tracking

CREATE TABLE IF NOT EXISTS settlement_records (
    id                     BIGSERIAL PRIMARY KEY,
    settlement_id          TEXT          NOT NULL UNIQUE,
    intent_id              TEXT          NOT NULL,
    receipt_id             TEXT,
    mode                   TEXT          NOT NULL,
    status                 TEXT          NOT NULL DEFAULT 'initiated',
    amount                 NUMERIC(20,6) NOT NULL,
    currency               TEXT          NOT NULL,
    fee                    NUMERIC(20,6) NOT NULL DEFAULT 0,
    network_reference      TEXT,
    credential_id          TEXT REFERENCES delegated_credentials(credential_id),
    authorization_status   TEXT,
    capture_status         TEXT,
    dispute_status         TEXT,
    reversal_reference     TEXT,
    liability_party        TEXT,
    initiated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    confirmed_at           TIMESTAMPTZ,
    settled_at             TIMESTAMPTZ,
    failed_at              TIMESTAMPTZ,
    expected_settlement_at TIMESTAMPTZ,
    retry_count            INTEGER       NOT NULL DEFAULT 0,
    last_error             TEXT,
    metadata               JSONB         NOT NULL DEFAULT '{}',
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stl_intent ON settlement_records(intent_id);
CREATE INDEX IF NOT EXISTS idx_stl_status ON settlement_records(status, mode);
CREATE INDEX IF NOT EXISTS idx_stl_pending ON settlement_records(expected_settlement_at)
    WHERE status IN ('initiated', 'pending_confirmation');
CREATE INDEX IF NOT EXISTS idx_stl_disputes ON settlement_records(dispute_status)
    WHERE dispute_status IS NOT NULL;
