-- =============================================================================
-- Migration 017: ERC-4337 wallet metadata fields
-- =============================================================================
-- Adds wallet-level execution metadata for v2 smart wallets.
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('017', 'Add ERC-4337 wallet metadata fields')
ON CONFLICT (version) DO NOTHING;

ALTER TABLE wallets
ADD COLUMN IF NOT EXISTS account_type VARCHAR(32) NOT NULL DEFAULT 'mpc_v1',
ADD COLUMN IF NOT EXISTS smart_account_address VARCHAR(66),
ADD COLUMN IF NOT EXISTS entrypoint_address VARCHAR(66),
ADD COLUMN IF NOT EXISTS paymaster_enabled BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS bundler_profile VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_wallets_account_type ON wallets(account_type);
CREATE INDEX IF NOT EXISTS idx_wallets_smart_account ON wallets(smart_account_address)
    WHERE smart_account_address IS NOT NULL;
