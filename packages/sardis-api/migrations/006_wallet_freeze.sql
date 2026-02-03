-- =============================================================================
-- Sardis Migration: 006_wallet_freeze
-- =============================================================================
--
-- Adds wallet freeze capability with DB persistence.
-- Frozen wallets are blocked from making any transactions.
--
-- Apply: psql $DATABASE_URL -f migrations/006_wallet_freeze.sql
--
-- =============================================================================

-- Guard: record migration
INSERT INTO schema_migrations (version, description)
VALUES ('006', 'Add wallet freeze columns for compliance blocking')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Add Freeze Columns to Wallets Table
-- -----------------------------------------------------------------------------

ALTER TABLE wallets
ADD COLUMN IF NOT EXISTS is_frozen BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS frozen_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS frozen_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS freeze_reason TEXT;

-- -----------------------------------------------------------------------------
-- Index for Finding Frozen Wallets
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_wallets_is_frozen
ON wallets(is_frozen)
WHERE is_frozen = TRUE;

-- Index for freeze audit queries (when + who)
CREATE INDEX IF NOT EXISTS idx_wallets_frozen_at
ON wallets(frozen_at DESC)
WHERE frozen_at IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Column Comments (Documentation)
-- -----------------------------------------------------------------------------

COMMENT ON COLUMN wallets.is_frozen IS
    'Whether wallet is frozen (blocks all transactions). Set via freeze/unfreeze endpoints.';

COMMENT ON COLUMN wallets.frozen_at IS
    'Timestamp when wallet was frozen. NULL if wallet is not frozen or has been unfrozen.';

COMMENT ON COLUMN wallets.frozen_by IS
    'Admin email, system identifier, or compliance rule that froze the wallet.';

COMMENT ON COLUMN wallets.freeze_reason IS
    'Human-readable reason for freezing: compliance violation, suspicious activity, manual freeze, etc.';

-- -----------------------------------------------------------------------------
-- Usage Examples (for documentation)
-- -----------------------------------------------------------------------------

-- Freeze a wallet:
-- UPDATE wallets
-- SET is_frozen = TRUE,
--     frozen_at = NOW(),
--     frozen_by = 'admin@sardis.sh',
--     freeze_reason = 'Suspicious transaction pattern detected'
-- WHERE external_id = 'wallet_abc123';

-- Unfreeze a wallet:
-- UPDATE wallets
-- SET is_frozen = FALSE,
--     frozen_at = NULL,
--     frozen_by = NULL,
--     freeze_reason = NULL
-- WHERE external_id = 'wallet_abc123';

-- Find all frozen wallets:
-- SELECT external_id, agent_id, frozen_at, frozen_by, freeze_reason
-- FROM wallets
-- WHERE is_frozen = TRUE
-- ORDER BY frozen_at DESC;

-- Find wallets frozen by compliance rules:
-- SELECT external_id, freeze_reason, frozen_at
-- FROM wallets
-- WHERE is_frozen = TRUE
--   AND frozen_by LIKE 'compliance:%';
