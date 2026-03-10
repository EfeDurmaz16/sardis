-- Linked bank accounts for Grid fiat rails
CREATE TABLE IF NOT EXISTS linked_bank_accounts (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    wallet_id TEXT NOT NULL,
    plaid_access_token_encrypted TEXT,
    institution_name TEXT DEFAULT '',
    account_mask TEXT DEFAULT '',
    routing_number TEXT DEFAULT '',
    account_type TEXT DEFAULT 'checking',
    rail_preference TEXT DEFAULT 'ach', -- ach, rtp, fednow, wire
    provider TEXT DEFAULT 'lightspark_grid',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_linked_bank_accounts_wallet ON linked_bank_accounts(wallet_id);
