-- =============================================================================
-- Sardis Migration: 030_merchant_checkout
-- =============================================================================
--
-- Merchant checkout tables for "Pay with Sardis" stablecoin payment network.
--
-- Apply: psql $DATABASE_URL -f migrations/030_merchant_checkout.sql
--
-- =============================================================================

-- Guard: skip if already applied
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'merchants') THEN
        RAISE NOTICE 'Migration 030 already applied, skipping.';
        RETURN;
    END IF;

-- -----------------------------------------------------------------------------
-- Merchants
-- -----------------------------------------------------------------------------
CREATE TABLE merchants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    org_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    logo_url TEXT,
    webhook_url TEXT,
    webhook_secret VARCHAR(128),
    settlement_preference VARCHAR(10) NOT NULL DEFAULT 'usdc'
        CHECK (settlement_preference IN ('usdc', 'fiat')),
    settlement_wallet_id VARCHAR(64),
    bank_account JSONB DEFAULT '{}',
    mcc_code VARCHAR(4),
    category VARCHAR(100),
    platform_fee_bps INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_merchants_org ON merchants(org_id);
CREATE INDEX idx_merchants_active ON merchants(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_merchants_external ON merchants(external_id);

-- -----------------------------------------------------------------------------
-- Merchant API Keys
-- -----------------------------------------------------------------------------
CREATE TABLE merchant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id) NOT NULL,
    key_prefix VARCHAR(12) NOT NULL,
    key_hash VARCHAR(128) NOT NULL,
    label VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX idx_merchant_api_keys_merchant ON merchant_api_keys(merchant_id);
CREATE INDEX idx_merchant_api_keys_prefix ON merchant_api_keys(key_prefix);

-- -----------------------------------------------------------------------------
-- Merchant Checkout Sessions
-- -----------------------------------------------------------------------------
CREATE TABLE merchant_checkout_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(64) UNIQUE NOT NULL,
    merchant_id UUID REFERENCES merchants(id) NOT NULL,
    payer_wallet_id VARCHAR(64),
    amount NUMERIC(20,6) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USDC',
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'funded', 'paid', 'settled', 'expired', 'failed')),
    payment_method VARCHAR(20)
        CHECK (payment_method IS NULL OR payment_method IN ('wallet', 'fund_and_pay')),
    tx_hash VARCHAR(128),
    settlement_tx_hash VARCHAR(128),
    settlement_status VARCHAR(20) DEFAULT NULL
        CHECK (settlement_status IS NULL OR settlement_status IN ('pending', 'processing', 'completed', 'failed')),
    offramp_id VARCHAR(128),
    success_url TEXT,
    cancel_url TEXT,
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mcs_merchant ON merchant_checkout_sessions(merchant_id);
CREATE INDEX idx_mcs_status ON merchant_checkout_sessions(status);
CREATE INDEX idx_mcs_session_id ON merchant_checkout_sessions(session_id);
CREATE INDEX idx_mcs_settlement ON merchant_checkout_sessions(settlement_status)
    WHERE settlement_status IS NOT NULL;
CREATE INDEX idx_mcs_expires ON merchant_checkout_sessions(expires_at)
    WHERE status = 'pending';

-- -----------------------------------------------------------------------------
-- Merchant Settlements
-- -----------------------------------------------------------------------------
CREATE TABLE merchant_settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settlement_id VARCHAR(64) UNIQUE NOT NULL,
    merchant_id UUID REFERENCES merchants(id) NOT NULL,
    total_amount NUMERIC(20,6) NOT NULL,
    session_count INTEGER NOT NULL DEFAULT 1,
    settlement_method VARCHAR(20) NOT NULL DEFAULT 'bridge'
        CHECK (settlement_method IN ('bridge', 'coinbase', 'usdc')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    offramp_id VARCHAR(128),
    bank_account JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_ms_merchant ON merchant_settlements(merchant_id);
CREATE INDEX idx_ms_status ON merchant_settlements(status);

END $$;
