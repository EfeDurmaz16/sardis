-- =============================================================================
-- Sardis Migration: 012_travel_rule
-- =============================================================================
--
-- Travel Rule (FATF Recommendation 16) transfer records.
--
-- Stores originator/beneficiary information for transfers above threshold
-- ($3,000 USD / $1,000 EUR equivalent).
--
-- Apply: psql $DATABASE_URL -f migrations/012_travel_rule.sql
--
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('012', 'Travel Rule transfer records')
ON CONFLICT (version) DO NOTHING;

CREATE TABLE IF NOT EXISTS travel_rule_transfers (
    transfer_id         TEXT PRIMARY KEY,
    tx_id               TEXT,
    amount              NUMERIC(20, 6) NOT NULL,
    currency            VARCHAR(10) NOT NULL DEFAULT 'USDC',
    chain               VARCHAR(20),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    originator_data     JSONB DEFAULT '{}',
    beneficiary_data    JSONB DEFAULT '{}',
    protocol            VARCHAR(20) NOT NULL DEFAULT 'manual',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_travel_rule_status ON travel_rule_transfers(status);
CREATE INDEX IF NOT EXISTS idx_travel_rule_tx ON travel_rule_transfers(tx_id);
CREATE INDEX IF NOT EXISTS idx_travel_rule_created ON travel_rule_transfers(created_at);
