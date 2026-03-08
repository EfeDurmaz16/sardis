-- Migration 051: Outcome tracking for trust-by-evidence
-- Links payment decisions to real-world outcomes for learning loops.

CREATE TABLE IF NOT EXISTS payment_outcomes (
    outcome_id          TEXT PRIMARY KEY,
    receipt_id          TEXT REFERENCES execution_receipts(receipt_id),
    intent_id           TEXT NOT NULL,
    decision            TEXT NOT NULL,       -- 'approved', 'denied', 'flagged'
    decision_reason     TEXT,
    outcome_type        TEXT,                -- 'completed', 'disputed', 'refunded', 'fraud_confirmed', 'false_positive'
    outcome_data        JSONB,
    decided_at          TIMESTAMPTZ NOT NULL,
    resolved_at         TIMESTAMPTZ,
    agent_id            TEXT NOT NULL,
    org_id              TEXT NOT NULL,
    merchant_id         TEXT,
    amount              NUMERIC(20,6),
    currency            TEXT,
    anomaly_score       REAL,
    confidence_score    REAL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outcomes_agent ON payment_outcomes(agent_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_merchant ON payment_outcomes(merchant_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_decision ON payment_outcomes(decision);
CREATE INDEX IF NOT EXISTS idx_outcomes_type ON payment_outcomes(outcome_type);
CREATE INDEX IF NOT EXISTS idx_outcomes_org ON payment_outcomes(org_id);

-- Compounding agent risk profile
CREATE TABLE IF NOT EXISTS agent_risk_profiles (
    agent_id                TEXT PRIMARY KEY,
    org_id                  TEXT NOT NULL,
    total_decisions         INT DEFAULT 0,
    total_approved          INT DEFAULT 0,
    total_denied            INT DEFAULT 0,
    total_flagged           INT DEFAULT 0,
    false_positive_count    INT DEFAULT 0,
    true_positive_count     INT DEFAULT 0,
    false_negative_count    INT DEFAULT 0,
    avg_anomaly_score       REAL DEFAULT 0,
    avg_confidence_score    REAL DEFAULT 0,
    last_updated            TIMESTAMPTZ DEFAULT NOW()
);

-- Merchant risk profile (compounding from outcomes)
CREATE TABLE IF NOT EXISTS merchant_risk_profiles (
    merchant_id             TEXT PRIMARY KEY,
    total_transactions      INT DEFAULT 0,
    dispute_count           INT DEFAULT 0,
    refund_count            INT DEFAULT 0,
    fraud_count             INT DEFAULT 0,
    dispute_rate            REAL DEFAULT 0,
    risk_tier               TEXT DEFAULT 'unknown',
    first_seen              TIMESTAMPTZ DEFAULT NOW(),
    last_transaction        TIMESTAMPTZ,
    last_updated            TIMESTAMPTZ DEFAULT NOW()
);
