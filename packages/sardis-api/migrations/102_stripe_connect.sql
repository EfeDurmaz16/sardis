-- =============================================================================
-- Sardis Migration: 102_stripe_connect
-- =============================================================================
--
-- Add Stripe Connect Express account columns to merchants table.
-- Enables merchants to link their Stripe account for fiat settlement
-- via Sardis Connect (zero-crypto merchant experience).
--
-- Apply: psql $DATABASE_URL -f migrations/102_stripe_connect.sql
--
-- =============================================================================

-- Stripe Connect account fields
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS stripe_account_id VARCHAR(64);
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS stripe_onboarding_state VARCHAR(32)
    DEFAULT 'not_started'
    CHECK (stripe_onboarding_state IN (
        'not_started', 'pending', 'complete', 'restricted', 'rejected'
    ));
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS stripe_charges_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS stripe_payouts_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS stripe_details_submitted BOOLEAN DEFAULT FALSE;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS stripe_disabled_reason TEXT;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS stripe_current_deadline TIMESTAMPTZ;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS stripe_last_synced_at TIMESTAMPTZ;

-- Expand settlement_preference to include stripe_connect
ALTER TABLE merchants DROP CONSTRAINT IF EXISTS merchants_settlement_preference_check;
ALTER TABLE merchants ADD CONSTRAINT merchants_settlement_preference_check
    CHECK (settlement_preference IN ('usdc', 'fiat', 'stripe_connect', 'internal', 'tempo', 'cpn'));

-- Unique index on stripe_account_id (one Stripe account per merchant)
CREATE UNIQUE INDEX IF NOT EXISTS idx_merchants_stripe_account_id
    ON merchants(stripe_account_id)
    WHERE stripe_account_id IS NOT NULL;

-- Stripe Connect payout tracking table
CREATE TABLE IF NOT EXISTS stripe_connect_payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id),
    session_id VARCHAR(64),
    stripe_transfer_id VARCHAR(64) NOT NULL,
    stripe_payout_id VARCHAR(64),
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'usd',
    status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'failed', 'canceled')),
    failure_code TEXT,
    failure_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stripe_connect_payouts_merchant
    ON stripe_connect_payouts(merchant_id);
CREATE INDEX IF NOT EXISTS idx_stripe_connect_payouts_status
    ON stripe_connect_payouts(status) WHERE status = 'pending';
CREATE UNIQUE INDEX IF NOT EXISTS idx_stripe_connect_payouts_transfer
    ON stripe_connect_payouts(stripe_transfer_id);
