-- Migration 028: Add Circle Programmable Wallet fields
-- Adds circle_wallet_id to wallets table for Circle MPC integration
-- and kya_attestation_uid for EAS KYA attestation tracking.

ALTER TABLE wallets ADD COLUMN IF NOT EXISTS circle_wallet_id TEXT;
ALTER TABLE wallets ADD COLUMN IF NOT EXISTS kya_attestation_uid TEXT;

CREATE INDEX IF NOT EXISTS idx_wallets_circle_id ON wallets(circle_wallet_id)
    WHERE circle_wallet_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_wallets_kya_uid ON wallets(kya_attestation_uid)
    WHERE kya_attestation_uid IS NOT NULL;

-- Rollback:
-- ALTER TABLE wallets DROP COLUMN IF EXISTS circle_wallet_id;
-- ALTER TABLE wallets DROP COLUMN IF EXISTS kya_attestation_uid;
-- DROP INDEX IF EXISTS idx_wallets_circle_id;
-- DROP INDEX IF EXISTS idx_wallets_kya_uid;
