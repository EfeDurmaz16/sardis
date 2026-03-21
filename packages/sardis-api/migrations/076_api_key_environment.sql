-- Migration 076: Add environment column to api_keys for dual test/live routing.
-- sk_test_* keys route to Base Sepolia (testnet), sk_live_* keys route to Tempo (mainnet).

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS environment VARCHAR(10) DEFAULT 'test';
CREATE INDEX IF NOT EXISTS idx_api_keys_environment ON api_keys(environment);
