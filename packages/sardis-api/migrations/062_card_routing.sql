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
