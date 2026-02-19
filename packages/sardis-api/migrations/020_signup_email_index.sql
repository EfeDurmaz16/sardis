-- Migration 020: Add expression index for email lookup in organizations.settings JSONB
-- Used by the public signup endpoint for duplicate email detection.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_settings_email
    ON organizations ((settings->>'email'))
    WHERE settings->>'email' IS NOT NULL;
