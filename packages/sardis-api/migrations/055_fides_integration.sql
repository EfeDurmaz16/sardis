-- Migration 055: FIDES Trust Graph Integration
-- Adds DID mapping, trust score snapshots, and agent FIDES fields

CREATE TABLE IF NOT EXISTS did_mappings (
    agent_id TEXT NOT NULL,
    fides_did TEXT NOT NULL UNIQUE,
    public_key_hex TEXT,
    verified_at TIMESTAMPTZ,
    verification_signature TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (agent_id, fides_did)
);
CREATE INDEX IF NOT EXISTS idx_did_fides ON did_mappings(fides_did);

DO $$ BEGIN
    ALTER TABLE agents ADD COLUMN IF NOT EXISTS fides_did TEXT;
    ALTER TABLE agents ADD COLUMN IF NOT EXISTS agit_repo_hash TEXT;
EXCEPTION WHEN undefined_table THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS trust_score_snapshots (
    agent_id TEXT NOT NULL,
    overall DOUBLE PRECISION NOT NULL,
    tier TEXT NOT NULL,
    signals JSONB NOT NULL,
    fides_did TEXT,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (agent_id, calculated_at)
);
CREATE INDEX IF NOT EXISTS idx_trust_score_agent ON trust_score_snapshots(agent_id);
