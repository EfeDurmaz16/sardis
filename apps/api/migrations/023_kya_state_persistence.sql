-- =============================================================================
-- Sardis Migration: 023_kya_state_persistence
-- =============================================================================
--
-- Persists KYA state (manifest, level, status, trust score, attestations)
-- so KYA enforcement survives process restarts.
--
-- Apply: psql $DATABASE_URL -f migrations/023_kya_state_persistence.sql
--
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('023', 'Add persistent KYA state store')
ON CONFLICT (version) DO NOTHING;

CREATE TABLE IF NOT EXISTS kya_agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    owner_id VARCHAR(255),
    manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
    kya_level VARCHAR(32) NOT NULL DEFAULT 'none',
    kya_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    trust_score JSONB,
    code_attestation JSONB,
    liveness JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kya_agents_level ON kya_agents(kya_level);
CREATE INDEX IF NOT EXISTS idx_kya_agents_status ON kya_agents(kya_status);
CREATE INDEX IF NOT EXISTS idx_kya_agents_updated_at ON kya_agents(updated_at DESC);

COMMENT ON TABLE kya_agents IS
    'Persistent KYA state for agent manifests, trust levels, attestations, and liveness snapshots';
