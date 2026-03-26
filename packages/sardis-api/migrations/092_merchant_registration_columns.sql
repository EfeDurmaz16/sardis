-- =============================================================================
-- Sardis Migration: 092_merchant_registration_columns
-- =============================================================================
--
-- Add columns needed by merchant self-registration:
--   client_id         – deterministic public identifier for checkout embed SDK
--   client_secret_hash – SHA-256 hash of the merchant client secret
--   website           – merchant website URL
--   registered_by     – user/principal who registered the merchant
--
-- Apply: psql $DATABASE_URL -f migrations/092_merchant_registration_columns.sql
--
-- =============================================================================

ALTER TABLE merchants ADD COLUMN IF NOT EXISTS client_id VARCHAR(64);
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS client_secret_hash VARCHAR(128);
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS website TEXT;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS registered_by VARCHAR(128);

-- Unique constraint on client_id (one credential pair per merchant)
CREATE UNIQUE INDEX IF NOT EXISTS idx_merchants_client_id ON merchants(client_id)
    WHERE client_id IS NOT NULL;
