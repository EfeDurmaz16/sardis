-- =============================================================================
-- Sardis Migration: 103_checkout_mandate_bridge
-- =============================================================================
--
-- Bridge spending mandates to the checkout flow. Adds mandate_id to checkout
-- sessions so agents can pay using pre-authorized spending mandates.
--
-- Apply: psql $DATABASE_URL -f migrations/103_checkout_mandate_bridge.sql
--
-- =============================================================================

-- Add mandate reference to checkout sessions
ALTER TABLE merchant_checkout_sessions
    ADD COLUMN IF NOT EXISTS mandate_id TEXT;

-- Index for looking up sessions by mandate
CREATE INDEX IF NOT EXISTS idx_checkout_sessions_mandate
    ON merchant_checkout_sessions(mandate_id)
    WHERE mandate_id IS NOT NULL;
