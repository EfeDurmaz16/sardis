-- Striga vIBAN tracking for SEPA payments
CREATE TABLE IF NOT EXISTS striga_vibans (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    wallet_id TEXT NOT NULL,
    viban TEXT NOT NULL UNIQUE,
    bic TEXT DEFAULT '',
    currency TEXT DEFAULT 'EUR',
    status TEXT DEFAULT 'active',
    striga_user_id TEXT NOT NULL,
    bank_name TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_striga_vibans_wallet ON striga_vibans(wallet_id);
CREATE INDEX IF NOT EXISTS idx_striga_vibans_user ON striga_vibans(striga_user_id);
