-- Migration 085: Add missing settlements and escrows tables
-- a2a_settlement.py and a2a_escrow.py INSERT into these tables but they were never created.

-- ============================================================================
-- Settlements table (used by a2a_settlement.py SettlementEngine)
-- ============================================================================
CREATE TABLE IF NOT EXISTS settlements (
    id TEXT PRIMARY KEY,
    escrow_id TEXT NOT NULL,
    settlement_type TEXT NOT NULL CHECK (settlement_type IN ('on_chain', 'off_chain')),
    tx_hash TEXT,
    amount NUMERIC(38,18) NOT NULL,
    token TEXT NOT NULL,
    chain TEXT NOT NULL,
    payer_agent_id TEXT NOT NULL,
    payee_agent_id TEXT NOT NULL,
    settled_at TIMESTAMPTZ NOT NULL,
    ledger_entries TEXT[] DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_settlements_escrow ON settlements(escrow_id);
CREATE INDEX IF NOT EXISTS idx_settlements_payer ON settlements(payer_agent_id);
CREATE INDEX IF NOT EXISTS idx_settlements_payee ON settlements(payee_agent_id);
CREATE INDEX IF NOT EXISTS idx_settlements_settled ON settlements(settled_at DESC);
CREATE INDEX IF NOT EXISTS idx_settlements_type ON settlements(settlement_type);

-- ============================================================================
-- Escrows table (used by a2a_escrow.py EscrowManager)
-- ============================================================================
CREATE TABLE IF NOT EXISTS escrows (
    id TEXT PRIMARY KEY,
    payer_agent_id TEXT NOT NULL,
    payee_agent_id TEXT NOT NULL,
    amount NUMERIC(38,18) NOT NULL,
    token TEXT NOT NULL,
    chain TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'created'
        CHECK (state IN ('created', 'funded', 'delivered', 'released', 'refunded', 'disputed', 'expired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    funded_at TIMESTAMPTZ,
    funding_tx_hash TEXT,
    delivery_proof TEXT,
    delivered_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    release_tx_hash TEXT,
    refunded_at TIMESTAMPTZ,
    refund_tx_hash TEXT,
    refund_reason TEXT,
    disputed_at TIMESTAMPTZ,
    dispute_reason TEXT,
    dispute_resolution TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_escrows_payer ON escrows(payer_agent_id);
CREATE INDEX IF NOT EXISTS idx_escrows_payee ON escrows(payee_agent_id);
CREATE INDEX IF NOT EXISTS idx_escrows_state ON escrows(state);
CREATE INDEX IF NOT EXISTS idx_escrows_expires ON escrows(expires_at) WHERE state IN ('created', 'funded');
CREATE INDEX IF NOT EXISTS idx_escrows_created ON escrows(created_at DESC);

-- Track migration
INSERT INTO schema_migrations (version, description)
VALUES ('085_a2a_tables', 'Add missing settlements and escrows tables for a2a engine')
ON CONFLICT DO NOTHING;
