-- =============================================================================
-- Migration 016: Recurring Payments (Subscriptions)
-- =============================================================================
-- Adds tables for subscription registry, billing events, and notifications.
-- Supports shared-card model with subscription-aware ASA matching.
-- =============================================================================

-- Subscription Registry
CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    owner_id TEXT NOT NULL DEFAULT '',

    -- Merchant info
    merchant TEXT NOT NULL,
    merchant_mcc TEXT,

    -- Billing details
    amount_cents BIGINT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    billing_cycle TEXT NOT NULL DEFAULT 'monthly',
    billing_day INTEGER NOT NULL DEFAULT 1,
    next_billing TIMESTAMPTZ NOT NULL,

    -- Card association (NULL = any card on the wallet)
    card_id TEXT,

    -- Approval settings
    auto_approve BOOLEAN NOT NULL DEFAULT true,
    auto_approve_threshold_cents BIGINT NOT NULL DEFAULT 10000,

    -- Amount tolerance for ASA matching
    amount_tolerance_cents INTEGER NOT NULL DEFAULT 500,

    -- Notifications
    notify_owner BOOLEAN NOT NULL DEFAULT true,
    notification_channel TEXT,

    -- Status and failure tracking
    status TEXT NOT NULL DEFAULT 'active',
    last_charged_at TIMESTAMPTZ,
    failure_count INTEGER NOT NULL DEFAULT 0,
    max_failures INTEGER NOT NULL DEFAULT 3,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_wallet ON subscriptions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_next_billing ON subscriptions(next_billing)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_subscriptions_card ON subscriptions(card_id)
    WHERE card_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_subscriptions_merchant ON subscriptions(merchant);

-- Billing Events (per-cycle execution records)
CREATE TABLE IF NOT EXISTS billing_events (
    id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    wallet_id TEXT NOT NULL,

    scheduled_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    amount_cents BIGINT NOT NULL,

    -- Linked records
    fund_tx_id TEXT,
    approval_id TEXT,
    charge_tx_id TEXT,

    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_events_subscription ON billing_events(subscription_id);
CREATE INDEX IF NOT EXISTS idx_billing_events_wallet ON billing_events(wallet_id);
CREATE INDEX IF NOT EXISTS idx_billing_events_status ON billing_events(status);
CREATE INDEX IF NOT EXISTS idx_billing_events_created ON billing_events(created_at DESC);

-- Subscription Notifications (owner notification queue)
CREATE TABLE IF NOT EXISTS subscription_notifications (
    id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    owner_id TEXT NOT NULL,

    notification_type TEXT NOT NULL,
    channel TEXT,
    payload JSONB DEFAULT '{}',

    sent BOOLEAN NOT NULL DEFAULT false,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sub_notif_pending ON subscription_notifications(sent, created_at)
    WHERE sent = false;
CREATE INDEX IF NOT EXISTS idx_sub_notif_subscription ON subscription_notifications(subscription_id);
