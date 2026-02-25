-- =============================================================================
-- Sardis Database Initialization Script
-- =============================================================================
-- This script sets up the initial database schema for Sardis.
-- Run automatically by docker-compose or manually with:
-- psql -U sardis -d sardis -f init-db.sql

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- Agents & Wallets
-- =============================================================================

CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    owner_id VARCHAR(255) NOT NULL,
    policy_id UUID,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id UUID REFERENCES agents(id),
    address VARCHAR(255) NOT NULL,
    chain VARCHAR(50) NOT NULL,
    turnkey_wallet_id VARCHAR(255),
    turnkey_address VARCHAR(255),
    policy_id UUID,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_wallets_agent_id ON wallets(agent_id);
CREATE INDEX idx_wallets_address ON wallets(address);
CREATE INDEX idx_wallets_chain ON wallets(chain);

-- =============================================================================
-- Policies
-- =============================================================================

CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    rules JSONB NOT NULL DEFAULT '[]',
    -- Limits
    daily_limit_usd DECIMAL(18, 2),
    monthly_limit_usd DECIMAL(18, 2),
    single_tx_limit_usd DECIMAL(18, 2),
    -- Restrictions
    allowed_merchants JSONB DEFAULT '[]',
    blocked_merchants JSONB DEFAULT '[]',
    allowed_categories JSONB DEFAULT '[]',
    blocked_categories JSONB DEFAULT '[]',
    -- Approval requirements
    approval_threshold_usd DECIMAL(18, 2),
    require_approval_for_new_merchants BOOLEAN DEFAULT FALSE,
    -- Meta
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Link policies to agents and wallets
ALTER TABLE agents ADD CONSTRAINT fk_agents_policy FOREIGN KEY (policy_id) REFERENCES policies(id);
ALTER TABLE wallets ADD CONSTRAINT fk_wallets_policy FOREIGN KEY (policy_id) REFERENCES policies(id);

-- =============================================================================
-- Transactions
-- =============================================================================

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    wallet_id UUID REFERENCES wallets(id),
    -- Transaction details
    type VARCHAR(50) NOT NULL, -- 'payment', 'hold', 'capture', 'refund', 'deposit', 'withdrawal'
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Amounts
    amount DECIMAL(38, 18) NOT NULL,
    token VARCHAR(50) NOT NULL,
    chain VARCHAR(50) NOT NULL,
    -- Parties
    from_address VARCHAR(255),
    to_address VARCHAR(255),
    merchant_name VARCHAR(255),
    merchant_category VARCHAR(100),
    -- Blockchain
    tx_hash VARCHAR(255),
    block_number BIGINT,
    -- Hold reference (for captures)
    hold_id UUID,
    -- Metadata
    memo TEXT,
    metadata JSONB DEFAULT '{}',
    -- Policy evaluation
    policy_result JSONB,
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_transactions_wallet_id ON transactions(wallet_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
CREATE INDEX idx_transactions_tx_hash ON transactions(tx_hash);

-- =============================================================================
-- Holds (Pre-authorizations)
-- =============================================================================

CREATE TABLE IF NOT EXISTS holds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    wallet_id UUID REFERENCES wallets(id),
    -- Hold details
    amount DECIMAL(38, 18) NOT NULL,
    captured_amount DECIMAL(38, 18) DEFAULT 0,
    token VARCHAR(50) NOT NULL,
    -- Merchant
    merchant_name VARCHAR(255) NOT NULL,
    merchant_category VARCHAR(100),
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- 'active', 'captured', 'voided', 'expired'
    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    -- Metadata
    description TEXT,
    metadata JSONB DEFAULT '{}',
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    captured_at TIMESTAMP WITH TIME ZONE,
    voided_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_holds_wallet_id ON holds(wallet_id);
CREATE INDEX idx_holds_status ON holds(status);
CREATE INDEX idx_holds_expires_at ON holds(expires_at);

-- =============================================================================
-- Virtual Cards
-- =============================================================================

CREATE TABLE IF NOT EXISTS cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    wallet_id UUID REFERENCES wallets(id),
    -- Card details (from Lithic)
    lithic_card_id VARCHAR(255),
    last_four VARCHAR(4),
    card_type VARCHAR(50) DEFAULT 'virtual',
    -- Limits
    spending_limit_usd DECIMAL(18, 2),
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- 'active', 'frozen', 'cancelled'
    -- Metadata
    nickname VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cards_wallet_id ON cards(wallet_id);
CREATE INDEX idx_cards_status ON cards(status);

-- =============================================================================
-- Approvals
-- =============================================================================

CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    wallet_id UUID REFERENCES wallets(id),
    transaction_id UUID REFERENCES transactions(id),
    -- Approval details
    amount DECIMAL(38, 18) NOT NULL,
    reason TEXT NOT NULL,
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'expired'
    -- Approver
    approved_by VARCHAR(255),
    rejection_reason TEXT,
    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_approvals_wallet_id ON approvals(wallet_id);
CREATE INDEX idx_approvals_status ON approvals(status);

-- =============================================================================
-- Audit Log
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- What happened
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    -- Who did it
    actor_type VARCHAR(50) NOT NULL, -- 'agent', 'user', 'system'
    actor_id VARCHAR(255) NOT NULL,
    -- Details
    details JSONB DEFAULT '{}',
    -- For tamper-evidence
    previous_hash VARCHAR(64),
    hash VARCHAR(64),
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_actor ON audit_log(actor_type, actor_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- =============================================================================
-- API Keys
-- =============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    key_prefix VARCHAR(10) NOT NULL, -- First 10 chars for identification
    name VARCHAR(255) NOT NULL,
    owner_id VARCHAR(255) NOT NULL,
    -- Permissions
    scopes JSONB DEFAULT '["read", "write"]',
    -- Rate limits
    rate_limit_per_minute INT DEFAULT 60,
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_owner_id ON api_keys(owner_id);

-- =============================================================================
-- Compliance Records
-- =============================================================================

CREATE TABLE IF NOT EXISTS compliance_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Subject
    subject_type VARCHAR(50) NOT NULL, -- 'agent', 'wallet', 'address', 'transaction'
    subject_id VARCHAR(255) NOT NULL,
    -- Check details
    check_type VARCHAR(100) NOT NULL, -- 'kyc', 'aml', 'sanctions', 'pep'
    provider VARCHAR(100) NOT NULL, -- 'persona', 'elliptic', 'complyadvantage'
    -- Result
    status VARCHAR(50) NOT NULL, -- 'passed', 'failed', 'pending', 'review'
    risk_level VARCHAR(50),
    details JSONB DEFAULT '{}',
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_compliance_checks_subject ON compliance_checks(subject_type, subject_id);
CREATE INDEX idx_compliance_checks_status ON compliance_checks(status);

-- Persistent KYA state (manifest, trust and attestation snapshots)
CREATE TABLE IF NOT EXISTS kya_agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    owner_id VARCHAR(255),
    manifest JSONB NOT NULL DEFAULT '{}',
    kya_level VARCHAR(32) NOT NULL DEFAULT 'none',
    kya_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    trust_score JSONB,
    code_attestation JSONB,
    liveness JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_kya_agents_level ON kya_agents(kya_level);
CREATE INDEX idx_kya_agents_status ON kya_agents(kya_status);

-- =============================================================================
-- Functions
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON wallets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_policies_updated_at BEFORE UPDATE ON policies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_holds_updated_at BEFORE UPDATE ON holds FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_cards_updated_at BEFORE UPDATE ON cards FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_approvals_updated_at BEFORE UPDATE ON approvals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Default Data
-- =============================================================================

-- Create a default policy
INSERT INTO policies (external_id, name, description, rules, daily_limit_usd, monthly_limit_usd, single_tx_limit_usd)
VALUES (
    'pol_default',
    'Default Policy',
    'Standard spending policy for new agents',
    '[
        {"type": "daily_limit", "limit_usd": 1000},
        {"type": "monthly_limit", "limit_usd": 10000},
        {"type": "single_tx_limit", "limit_usd": 500},
        {"type": "blocked_category", "categories": ["gambling", "adult"]}
    ]'::jsonb,
    1000,
    10000,
    500
) ON CONFLICT (external_id) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sardis;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sardis;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Sardis database initialized successfully!';
END $$;
