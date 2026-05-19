-- =============================================================================
-- Sardis Migration: 104_merchant_website_lookup
-- =============================================================================
--
-- Add website column to merchants (if not exists from registration flow)
-- and index for domain-based merchant lookup by unified payment client.
--
-- Apply: psql $DATABASE_URL -f migrations/104_merchant_website_lookup.sql
--
-- =============================================================================

ALTER TABLE merchants ADD COLUMN IF NOT EXISTS website TEXT;

-- Index for fast domain lookup (used by unified payment client discovery)
CREATE INDEX IF NOT EXISTS idx_merchants_website ON merchants(website)
    WHERE website IS NOT NULL;
