-- Subscription Mandates: recurring payment authorization with dunning.
--
-- Subscriptions auto-generate payment objects on a schedule.
-- Supports billing cycles, grace periods, trials, and usage metering.

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id TEXT PRIMARY KEY,              -- sub_xxx
    org_id TEXT NOT NULL,
    mandate_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL,
    agent_id TEXT,

    -- Billing
    billing_cycle TEXT DEFAULT 'monthly'
        CHECK (billing_cycle IN ('daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'annual')),
    charge_amount NUMERIC(20,6) NOT NULL,
    currency TEXT DEFAULT 'USDC',
    description TEXT,

    -- Grace & dunning
    grace_period_days INTEGER DEFAULT 3,
    dunning_rules JSONB DEFAULT '{"max_retries": 4, "retry_schedule_days": [1,3,5,7], "cancel_after_exhausted": true}',

    -- Trial
    trial_days INTEGER DEFAULT 0,
    trial_end TIMESTAMPTZ,

    -- Schedule
    current_period_start TIMESTAMPTZ DEFAULT now(),
    current_period_end TIMESTAMPTZ,
    anchor_day INTEGER,

    -- Lifecycle
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'past_due', 'dunning', 'paused', 'cancelled', 'expired', 'trial')),
    charges_count INTEGER DEFAULT 0,
    total_charged NUMERIC(20,6) DEFAULT 0,
    last_charge_at TIMESTAMPTZ,
    next_charge_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subs_org ON subscriptions(org_id);
CREATE INDEX IF NOT EXISTS idx_subs_mandate ON subscriptions(mandate_id);
CREATE INDEX IF NOT EXISTS idx_subs_merchant ON subscriptions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_subs_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subs_next_charge ON subscriptions(next_charge_at)
    WHERE status IN ('active', 'trial');

-- Charge intents: individual charge attempts within a subscription
CREATE TABLE IF NOT EXISTS charge_intents (
    charge_id TEXT PRIMARY KEY,                    -- chg_xxx
    subscription_id TEXT NOT NULL REFERENCES subscriptions(subscription_id),
    payment_object_id TEXT,
    amount NUMERIC(20,6) NOT NULL,
    currency TEXT DEFAULT 'USDC',
    billing_period_start TIMESTAMPTZ,
    billing_period_end TIMESTAMPTZ,
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'succeeded', 'failed', 'cancelled')),
    attempt_number INTEGER DEFAULT 1,
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_charges_sub ON charge_intents(subscription_id);
CREATE INDEX IF NOT EXISTS idx_charges_status ON charge_intents(status);

-- Usage meters: metered billing with countersignature
CREATE TABLE IF NOT EXISTS usage_meters (
    meter_id TEXT PRIMARY KEY,                     -- meter_xxx
    subscription_id TEXT NOT NULL REFERENCES subscriptions(subscription_id),
    metric_name TEXT NOT NULL,
    unit_price NUMERIC(20,8) NOT NULL,
    currency TEXT DEFAULT 'USDC',
    current_usage NUMERIC(20,6) DEFAULT 0,
    billing_period_usage NUMERIC(20,6) DEFAULT 0,
    included_units NUMERIC(20,6) DEFAULT 0,
    max_units NUMERIC(20,6),
    requires_countersignature BOOLEAN DEFAULT true,
    last_countersigned_at TIMESTAMPTZ,
    last_countersigned_usage NUMERIC(20,6) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_meters_sub ON usage_meters(subscription_id);
