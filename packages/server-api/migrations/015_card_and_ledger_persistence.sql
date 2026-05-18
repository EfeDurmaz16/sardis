-- =============================================================================
-- Migration 015: Card & Ledger Persistence
-- =============================================================================
-- Adds tables for persistent card services and full-precision ledger engine.
-- No data migration needed (starting fresh).
-- =============================================================================

-- Card Conversions (auto USDC<->USD conversion records)
CREATE TABLE IF NOT EXISTS card_conversions (
    id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    direction TEXT NOT NULL,  -- 'usdc_to_usd' or 'usd_to_usdc'
    amount_cents BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_card_conversions_wallet ON card_conversions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_card_conversions_status ON card_conversions(status);

-- Card-to-Wallet Mappings (for auto-conversion routing)
CREATE TABLE IF NOT EXISTS card_wallet_mappings (
    card_id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_card_wallet_mappings_wallet ON card_wallet_mappings(wallet_id);

-- Offramp Transactions (USDC -> USD off-ramp records)
CREATE TABLE IF NOT EXISTS offramp_transactions (
    id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    amount_cents BIGINT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_tx_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_offramp_tx_wallet ON offramp_transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_offramp_tx_status ON offramp_transactions(status);
CREATE INDEX IF NOT EXISTS idx_offramp_tx_created ON offramp_transactions(created_at DESC);

-- Processed Webhook Events (deduplication)
CREATE TABLE IF NOT EXISTS processed_webhook_events (
    event_id TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ledger Entries v2 (full-precision append-only ledger for LedgerEngine)
CREATE TABLE IF NOT EXISTS ledger_entries_v2 (
    entry_id TEXT PRIMARY KEY,
    tx_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    amount NUMERIC(38,18) NOT NULL,
    fee NUMERIC(38,18) DEFAULT 0,
    running_balance NUMERIC(38,18) DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'USDC',
    chain TEXT,
    chain_tx_hash TEXT,
    block_number BIGINT,
    audit_anchor TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    confirmed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ledger_v2_account ON ledger_entries_v2(account_id);
CREATE INDEX IF NOT EXISTS idx_ledger_v2_tx ON ledger_entries_v2(tx_id);
CREATE INDEX IF NOT EXISTS idx_ledger_v2_created ON ledger_entries_v2(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_v2_status ON ledger_entries_v2(status);
