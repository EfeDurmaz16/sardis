-- Subscription multi-currency and modification tracking
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD';
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS preferred_card_id TEXT;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS striga_standing_order_id TEXT;
