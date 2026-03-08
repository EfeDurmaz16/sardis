-- Migration 041: Policy decision evidence log
-- Every evaluate() call produces a signed evidence bundle for SOC 2 audit.

CREATE TABLE IF NOT EXISTS policy_decisions (
    id                TEXT PRIMARY KEY,
    agent_id          TEXT NOT NULL,
    mandate_id        TEXT,
    policy_version_id TEXT REFERENCES policy_versions(id),
    verdict           TEXT NOT NULL,
    steps_json        JSONB NOT NULL,
    evidence_hash     TEXT NOT NULL,
    group_hierarchy   TEXT[],
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_policy_decisions_agent ON policy_decisions(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_policy_decisions_mandate ON policy_decisions(mandate_id);
