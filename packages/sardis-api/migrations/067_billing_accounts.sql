CREATE TABLE IF NOT EXISTS billing_accounts (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL UNIQUE,
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT,
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'starter', 'growth', 'enterprise')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'past_due', 'canceled', 'trialing')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    api_calls_this_period BIGINT DEFAULT 0,
    tx_volume_this_period_cents BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_billing_org ON billing_accounts(org_id);
CREATE INDEX IF NOT EXISTS idx_billing_stripe ON billing_accounts(stripe_customer_id);
