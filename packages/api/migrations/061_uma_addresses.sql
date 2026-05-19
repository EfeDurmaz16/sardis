-- UMA address registry for A2A payments
CREATE TABLE IF NOT EXISTS uma_addresses (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    wallet_id TEXT NOT NULL,
    uma_address TEXT NOT NULL UNIQUE,
    provider TEXT DEFAULT 'lightspark_grid',
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_uma_addresses_address ON uma_addresses(uma_address);
CREATE INDEX IF NOT EXISTS idx_uma_addresses_wallet ON uma_addresses(wallet_id);
