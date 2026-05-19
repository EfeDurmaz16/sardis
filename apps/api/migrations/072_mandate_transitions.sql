-- Mandate state transition audit log.
-- Every lifecycle change (activate, suspend, revoke, expire) is recorded
-- for compliance and forensic analysis.

CREATE TABLE IF NOT EXISTS mandate_state_transitions (
    id TEXT PRIMARY KEY DEFAULT 'mst_' || substr(md5(random()::text), 1, 16),
    mandate_id TEXT NOT NULL REFERENCES spending_mandates(id) ON DELETE CASCADE,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    changed_by TEXT NOT NULL,                  -- user_id or system identifier
    reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mandate_transitions_mandate
    ON mandate_state_transitions(mandate_id);
CREATE INDEX IF NOT EXISTS idx_mandate_transitions_time
    ON mandate_state_transitions(created_at);
