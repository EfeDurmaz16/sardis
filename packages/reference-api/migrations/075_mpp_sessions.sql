-- Migration 075: MPP (Machine Payments Protocol) session tracking
-- Supports session-based streaming payments via MPP

CREATE TABLE IF NOT EXISTS mpp_sessions (
    session_id      VARCHAR(64) PRIMARY KEY,
    org_id          VARCHAR(64) NOT NULL,
    mandate_id      VARCHAR(64),
    wallet_id       VARCHAR(64),
    agent_id        VARCHAR(64),

    -- Payment configuration
    method          VARCHAR(32) NOT NULL DEFAULT 'tempo',
    chain           VARCHAR(32) NOT NULL DEFAULT 'tempo',
    currency        VARCHAR(10) NOT NULL DEFAULT 'USDC',

    -- Spending limits
    spending_limit  NUMERIC(20, 6) NOT NULL,
    remaining       NUMERIC(20, 6) NOT NULL,
    total_spent     NUMERIC(20, 6) NOT NULL DEFAULT 0,
    payment_count   INTEGER NOT NULL DEFAULT 0,

    -- Lifecycle
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,

    -- Metadata
    metadata        JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT mpp_sessions_status_check
        CHECK (status IN ('active', 'closed', 'expired', 'exhausted')),
    CONSTRAINT mpp_sessions_spending_limit_positive
        CHECK (spending_limit > 0)
);

CREATE TABLE IF NOT EXISTS mpp_payments (
    payment_id      VARCHAR(64) PRIMARY KEY,
    session_id      VARCHAR(64) NOT NULL REFERENCES mpp_sessions(session_id),
    amount          NUMERIC(20, 6) NOT NULL,
    currency        VARCHAR(10) NOT NULL DEFAULT 'USDC',
    merchant        VARCHAR(256) NOT NULL,
    merchant_url    TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    tx_hash         VARCHAR(128),
    chain           VARCHAR(32) NOT NULL DEFAULT 'tempo',
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT mpp_payments_status_check
        CHECK (status IN ('pending', 'completed', 'failed')),
    CONSTRAINT mpp_payments_amount_positive
        CHECK (amount > 0)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_mpp_sessions_org_id ON mpp_sessions(org_id);
CREATE INDEX IF NOT EXISTS idx_mpp_sessions_mandate_id ON mpp_sessions(mandate_id);
CREATE INDEX IF NOT EXISTS idx_mpp_sessions_status ON mpp_sessions(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_mpp_payments_session_id ON mpp_payments(session_id);
CREATE INDEX IF NOT EXISTS idx_mpp_payments_status ON mpp_payments(status) WHERE status = 'pending';
