-- =============================================================================
-- Sardis Migration: 003_ledger_compliance_tables
-- =============================================================================
--
-- Adds tables used by sardis-ledger and sardis-compliance that were
-- previously created at runtime via CREATE TABLE IF NOT EXISTS in Python code.
--
-- Apply: psql $DATABASE_URL -f migrations/003_ledger_compliance_tables.sql
--
-- =============================================================================

-- Guard: record migration
INSERT INTO schema_migrations (version, description)
VALUES ('003', 'Add ledger receipts, compliance audit trail, and supporting tables')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Ledger: Receipts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS receipts (
    tx_id VARCHAR(128) PRIMARY KEY,
    tx_hash VARCHAR(128),
    chain VARCHAR(32),
    block_number BIGINT,
    status VARCHAR(32),
    audit_anchor TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_receipts_created ON receipts(created_at);
CREATE INDEX IF NOT EXISTS idx_receipts_tx_hash ON receipts(tx_hash);

-- -----------------------------------------------------------------------------
-- Ledger: Metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ledger_meta (
    key VARCHAR(128) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Ledger: Balance Snapshots
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS balance_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(128) NOT NULL,
    currency VARCHAR(16) NOT NULL,
    balance NUMERIC(20,6) NOT NULL,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entry_count BIGINT DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_snapshots_account ON balance_snapshots(account_id, currency);
CREATE INDEX IF NOT EXISTS idx_snapshots_time ON balance_snapshots(snapshot_at);

-- -----------------------------------------------------------------------------
-- Ledger: Pending Reconciliation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pending_reconciliation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mandate_id VARCHAR(128) NOT NULL,
    expected_amount NUMERIC(20,6),
    actual_amount NUMERIC(20,6),
    discrepancy_type VARCHAR(64),
    priority INTEGER DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_reconciliation_resolved ON pending_reconciliation(resolved);
CREATE INDEX IF NOT EXISTS idx_reconciliation_mandate ON pending_reconciliation(mandate_id);
CREATE INDEX IF NOT EXISTS idx_reconciliation_priority ON pending_reconciliation(priority, created_at);

-- -----------------------------------------------------------------------------
-- Ledger: Audit Logs (ledger-specific)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    action VARCHAR(64) NOT NULL,
    actor VARCHAR(128),
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

-- -----------------------------------------------------------------------------
-- Ledger: Row Locks (for advisory locking)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS row_locks (
    lock_key VARCHAR(128) PRIMARY KEY,
    locked_by VARCHAR(128),
    locked_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Compliance: Audit Trail
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compliance_audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mandate_id VARCHAR(128) NOT NULL,
    subject VARCHAR(128) NOT NULL,
    decision VARCHAR(32) NOT NULL,
    reason TEXT,
    rule_id VARCHAR(64),
    risk_score NUMERIC(5,2),
    metadata JSONB DEFAULT '{}',
    evaluated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_mandate_id ON compliance_audit_trail(mandate_id);
CREATE INDEX IF NOT EXISTS idx_audit_subject ON compliance_audit_trail(subject);
CREATE INDEX IF NOT EXISTS idx_audit_evaluated_at ON compliance_audit_trail(evaluated_at);

-- -----------------------------------------------------------------------------
-- Protocol: Mandate Chains (sardis-protocol storage)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mandate_chains (
    chain_id VARCHAR(128) PRIMARY KEY,
    mandate_id VARCHAR(128) NOT NULL,
    chain_data JSONB NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Virtual Cards
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS virtual_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES wallets(id),
    provider VARCHAR(32) NOT NULL DEFAULT 'lithic',
    provider_card_id VARCHAR(128),
    card_number_last4 VARCHAR(4),
    status VARCHAR(32) DEFAULT 'active',
    spending_limit NUMERIC(20,6),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_virtual_cards_wallet ON virtual_cards(wallet_id);
CREATE INDEX IF NOT EXISTS idx_virtual_cards_provider ON virtual_cards(provider, provider_card_id);
CREATE INDEX IF NOT EXISTS idx_virtual_cards_status ON virtual_cards(status);

-- -----------------------------------------------------------------------------
-- Card Transactions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS card_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID REFERENCES virtual_cards(id),
    provider_tx_id VARCHAR(128),
    amount NUMERIC(20,6) NOT NULL,
    currency VARCHAR(16) DEFAULT 'USD',
    merchant_name VARCHAR(255),
    merchant_category VARCHAR(64),
    status VARCHAR(32) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_card_tx_card ON card_transactions(card_id);
CREATE INDEX IF NOT EXISTS idx_card_tx_status ON card_transactions(status);
CREATE INDEX IF NOT EXISTS idx_card_tx_created ON card_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_card_tx_provider ON card_transactions(provider_tx_id);

-- -----------------------------------------------------------------------------
-- KYC Verifications
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kyc_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    inquiry_id VARCHAR(128),
    status VARCHAR(32) DEFAULT 'pending',
    provider VARCHAR(32) DEFAULT 'persona',
    risk_level VARCHAR(32),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_kyc_agent ON kyc_verifications(agent_id);
CREATE INDEX IF NOT EXISTS idx_kyc_inquiry ON kyc_verifications(inquiry_id);

-- -----------------------------------------------------------------------------
-- Invoices
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    invoice_number VARCHAR(64) UNIQUE,
    amount NUMERIC(20,6) NOT NULL,
    currency VARCHAR(16) DEFAULT 'USD',
    status VARCHAR(32) DEFAULT 'draft',
    due_date TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_invoices_org ON invoices(organization_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);

-- -----------------------------------------------------------------------------
-- Checkouts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS checkouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    amount NUMERIC(20,6) NOT NULL,
    currency VARCHAR(16) DEFAULT 'USD',
    status VARCHAR(32) DEFAULT 'pending',
    payment_method VARCHAR(32),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_checkouts_org ON checkouts(organization_id);
CREATE INDEX IF NOT EXISTS idx_checkouts_status ON checkouts(status);

-- -----------------------------------------------------------------------------
-- Marketplace tables
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marketplace_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_agent_id UUID REFERENCES agents(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(64),
    price NUMERIC(20,6),
    currency VARCHAR(16) DEFAULT 'USD',
    status VARCHAR(32) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_services_provider ON marketplace_services(provider_agent_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_services_category ON marketplace_services(category);
CREATE INDEX IF NOT EXISTS idx_marketplace_services_status ON marketplace_services(status);

CREATE TABLE IF NOT EXISTS marketplace_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES marketplace_services(id),
    provider_agent_id UUID REFERENCES agents(id),
    consumer_agent_id UUID REFERENCES agents(id),
    amount NUMERIC(20,6),
    currency VARCHAR(16) DEFAULT 'USD',
    status VARCHAR(32) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_offers_service ON marketplace_offers(service_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_offers_provider ON marketplace_offers(provider_agent_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_offers_consumer ON marketplace_offers(consumer_agent_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_offers_status ON marketplace_offers(status);

CREATE TABLE IF NOT EXISTS marketplace_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES marketplace_services(id),
    offer_id UUID REFERENCES marketplace_offers(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_reviews_service ON marketplace_reviews(service_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_reviews_offer ON marketplace_reviews(offer_id);
