-- =============================================================================
-- Migration 027: Subscription Execution Fields
-- =============================================================================
-- Adds chain execution and autofund metadata to recurring subscriptions so the
-- scheduler can execute deterministic on-chain recurring payments.
-- =============================================================================

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS destination_address TEXT,
    ADD COLUMN IF NOT EXISTS token TEXT NOT NULL DEFAULT 'USDC',
    ADD COLUMN IF NOT EXISTS chain TEXT NOT NULL DEFAULT 'base_sepolia',
    ADD COLUMN IF NOT EXISTS memo TEXT,
    ADD COLUMN IF NOT EXISTS autofund_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS autofund_amount_cents BIGINT,
    ADD COLUMN IF NOT EXISTS last_autofund_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_subscriptions_chain_status
    ON subscriptions(chain, status, next_billing)
    WHERE status = 'active';

