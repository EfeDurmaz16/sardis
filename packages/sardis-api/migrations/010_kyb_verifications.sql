-- =============================================================================
-- Sardis Migration: 010_kyb_verifications
-- =============================================================================
--
-- Adds KYB (Know Your Business) verification tracking for organizations.
-- Required for regulatory compliance when organizations deploy agents
-- that handle transactions above threshold amounts.
--
-- Apply: psql $DATABASE_URL -f migrations/010_kyb_verifications.sql
--
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('010', 'KYB verification tracking for organizations')
ON CONFLICT (version) DO NOTHING;

CREATE TABLE IF NOT EXISTS kyb_verifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          TEXT NOT NULL,
    inquiry_id      TEXT UNIQUE NOT NULL,
    provider        VARCHAR(20) NOT NULL DEFAULT 'persona',
    status          VARCHAR(20) NOT NULL DEFAULT 'not_started',
    verified_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    reason          TEXT,
    business_name   TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kyb_org ON kyb_verifications(org_id);
CREATE INDEX IF NOT EXISTS idx_kyb_status ON kyb_verifications(status);
