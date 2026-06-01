-- Base cards table (TEXT card_id, per the sardis.cards.models.Card domain
-- model: card_xxx ids, currency + replacement_for fields). Created here so the
-- ALTER statements below resolve on a fresh database; IF NOT EXISTS keeps it a
-- no-op on any DB where the table already exists. Distinct from virtual_cards
-- (UUID-keyed provider mirror in migration 003).
CREATE TABLE IF NOT EXISTS cards (
    card_id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'lithic',
    provider_card_id TEXT,
    card_number_last4 TEXT,
    card_type TEXT DEFAULT 'multi_use',
    status TEXT DEFAULT 'pending',
    locked_merchant_id TEXT,
    funding_source TEXT DEFAULT 'stablecoin',
    funded_amount NUMERIC(38,18) DEFAULT 0,
    limit_per_tx NUMERIC(38,18),
    limit_daily NUMERIC(38,18),
    limit_monthly NUMERIC(38,18),
    spent_today NUMERIC(38,18) DEFAULT 0,
    spent_this_month NUMERIC(38,18) DEFAULT 0,
    total_spent NUMERIC(38,18) DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cards_wallet ON cards(wallet_id);
CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(status);

-- Card routing preferences and replacement tracking
CREATE TABLE IF NOT EXISTS card_merchant_preferences (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    wallet_id TEXT NOT NULL,
    merchant_pattern TEXT NOT NULL,
    preferred_card_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_card_merchant_prefs_wallet ON card_merchant_preferences(wallet_id);

CREATE TABLE IF NOT EXISTS card_replacements (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    old_card_id TEXT NOT NULL,
    new_card_id TEXT NOT NULL,
    reason TEXT DEFAULT 'expired',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_card_replacements_old ON card_replacements(old_card_id);
CREATE INDEX IF NOT EXISTS idx_card_replacements_new ON card_replacements(new_card_id);

-- Add currency and replacement_for to cards table
ALTER TABLE cards ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD';
ALTER TABLE cards ADD COLUMN IF NOT EXISTS replacement_for TEXT;
