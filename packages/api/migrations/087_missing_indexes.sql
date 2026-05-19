-- Migration 087: Add missing composite and covering indexes
-- These indexes support common query patterns identified in the codebase
-- that currently cause sequential scans.

-- execution_intents: frequently filtered by agent_id
CREATE INDEX IF NOT EXISTS idx_intents_agent_id
    ON execution_intents(agent_id);

-- mandate_state_transitions: queried by mandate_id ordered by created_at
CREATE INDEX IF NOT EXISTS idx_mandate_transitions_mandate_time
    ON mandate_state_transitions(mandate_id, created_at);

-- execution_receipts: org-scoped pagination queries
CREATE INDEX IF NOT EXISTS idx_receipts_org_created
    ON execution_receipts(org_id, created_at DESC);

-- holds: active holds checked against expiry for cleanup jobs
CREATE INDEX IF NOT EXISTS idx_holds_status_expires
    ON holds(status, expires_at) WHERE status = 'active';

-- on_chain_records: pending records polled by confirmation workers
CREATE INDEX IF NOT EXISTS idx_chain_records_status
    ON on_chain_records(status) WHERE status = 'pending';

-- spending_mandates: looked up by principal_id for policy checks
CREATE INDEX IF NOT EXISTS idx_mandates_principal
    ON spending_mandates(principal_id);

-- reconciliation_queue: pending items processed in FIFO order
CREATE INDEX IF NOT EXISTS idx_recon_queue_pending_created
    ON reconciliation_queue(created_at ASC) WHERE status = 'pending';

-- Track migration
INSERT INTO schema_migrations (version, description)
VALUES ('087_missing_indexes', 'Add missing composite and covering indexes for common query patterns')
ON CONFLICT DO NOTHING;
