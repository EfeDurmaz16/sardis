-- Execution intents table for unified payment tracking.
-- All payment flows (A2A, AP2, checkout) create an intent record.

CREATE TABLE IF NOT EXISTS execution_intents (
    intent_id       TEXT PRIMARY KEY,
    source          TEXT NOT NULL,            -- 'a2a', 'ap2', 'checkout', 'mandate', 'card'
    status          TEXT NOT NULL DEFAULT 'created',
    org_id          TEXT NOT NULL,
    agent_id        TEXT,
    idempotency_key TEXT,

    -- Payment details
    amount          NUMERIC(28,8) NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USDC',
    chain           TEXT NOT NULL DEFAULT 'base',

    -- Parties
    sender_wallet_id    TEXT,
    recipient_wallet_id TEXT,

    -- Results
    tx_hash         TEXT,
    ledger_entry_id TEXT,
    receipt_id      TEXT,
    error           TEXT,

    -- Pipeline snapshots (JSONB for audit)
    policy_result       JSONB,
    compliance_result   JSONB,
    metadata            JSONB DEFAULT '{}',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intents_org_id ON execution_intents (org_id);
CREATE INDEX IF NOT EXISTS idx_intents_status ON execution_intents (status) WHERE status NOT IN ('completed', 'failed');
CREATE INDEX IF NOT EXISTS idx_intents_idempotency ON execution_intents (idempotency_key) WHERE idempotency_key IS NOT NULL;
