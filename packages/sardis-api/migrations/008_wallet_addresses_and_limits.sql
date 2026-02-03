-- =============================================================================
-- Sardis Migration: 008_wallet_addresses_and_limits
-- =============================================================================
--
-- Adds production-grade wallet fields:
-- - multi-chain addresses JSONB
-- - mpc_provider, currency
-- - limit_per_tx, limit_total
--
-- Apply: psql $DATABASE_URL -f migrations/008_wallet_addresses_and_limits.sql
--
-- =============================================================================

-- Guard: record migration
INSERT INTO schema_migrations (version, description)
VALUES ('008', 'Add wallets.addresses JSONB + limits + mpc_provider/currency')
ON CONFLICT (version) DO NOTHING;

ALTER TABLE wallets
ADD COLUMN IF NOT EXISTS mpc_provider VARCHAR(32) NOT NULL DEFAULT 'turnkey',
ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'USDC',
ADD COLUMN IF NOT EXISTS limit_per_tx NUMERIC(20,6) NOT NULL DEFAULT 100,
ADD COLUMN IF NOT EXISTS limit_total NUMERIC(20,6) NOT NULL DEFAULT 1000,
ADD COLUMN IF NOT EXISTS addresses JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_wallets_addresses_gin
ON wallets USING GIN (addresses);

COMMENT ON COLUMN wallets.addresses IS
    'Multi-chain addresses mapping (e.g., {\"base\":\"0x..\",\"ethereum\":\"0x..\"}).';

