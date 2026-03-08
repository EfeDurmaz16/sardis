-- Migration 050: Execution receipts persistence
-- Stores HMAC-signed execution receipts for audit and verification.

CREATE TABLE IF NOT EXISTS execution_receipts (
    receipt_id              TEXT PRIMARY KEY,
    timestamp_              DOUBLE PRECISION NOT NULL,
    intent_hash             TEXT NOT NULL,
    policy_snapshot_hash    TEXT NOT NULL,
    compliance_result_hash  TEXT NOT NULL,
    tx_hash                 TEXT NOT NULL,
    chain                   TEXT NOT NULL,
    ledger_entry_id         TEXT,
    ledger_tx_id            TEXT,
    org_id                  TEXT NOT NULL,
    agent_id                TEXT NOT NULL,
    amount                  TEXT NOT NULL,
    currency                TEXT NOT NULL,
    signature               TEXT NOT NULL,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_receipts_tx_hash ON execution_receipts(tx_hash);
CREATE INDEX IF NOT EXISTS idx_receipts_agent_id ON execution_receipts(agent_id);
CREATE INDEX IF NOT EXISTS idx_receipts_org_id ON execution_receipts(org_id);
CREATE INDEX IF NOT EXISTS idx_receipts_created_at ON execution_receipts(created_at);
