-- Migration 040: Policy version history for audit trail and rollback
-- Every policy change creates an immutable version record.

CREATE TABLE IF NOT EXISTS policy_versions (
    id                TEXT PRIMARY KEY,
    agent_id          TEXT NOT NULL,
    version           INTEGER NOT NULL,
    policy_json       JSONB NOT NULL,
    policy_text       TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by        TEXT,
    parent_version_id TEXT REFERENCES policy_versions(id),
    hash              TEXT NOT NULL,
    UNIQUE(agent_id, version)
);

CREATE INDEX IF NOT EXISTS idx_policy_versions_agent ON policy_versions(agent_id, version DESC);
