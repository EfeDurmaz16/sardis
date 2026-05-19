-- =============================================================================
-- Sardis Migration: 106_agent_registry
-- =============================================================================
--
-- Public agent identity registry. Agents register their identity,
-- capabilities, and spending authority. Merchants verify before transacting.
--
-- Apply: psql $DATABASE_URL -f migrations/106_agent_registry.sql
--
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    principal_id VARCHAR(128),
    org_id VARCHAR(128),
    capabilities TEXT[] DEFAULT '{}',
    max_authority TEXT,
    supported_protocols TEXT[] DEFAULT '{sardis,x402,mpp}',
    website TEXT,
    contact_email VARCHAR(255),
    trust_score NUMERIC(4, 2),
    verified BOOLEAN DEFAULT FALSE,
    kya_status VARCHAR(32) DEFAULT 'unverified'
        CHECK (kya_status IN ('unverified', 'pending', 'verified', 'rejected')),
    total_transactions INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_registry_capabilities
    ON agent_registry USING GIN(capabilities);
CREATE INDEX IF NOT EXISTS idx_agent_registry_verified
    ON agent_registry(verified) WHERE verified = TRUE;
CREATE INDEX IF NOT EXISTS idx_agent_registry_org
    ON agent_registry(org_id);
