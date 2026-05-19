-- =============================================================================
-- Sardis Migration: 095_agent_events
-- =============================================================================
--
-- Creates the agent_events table for SDK event batching (tool calls, payments,
-- errors, etc.) flushed from client SDKs.
--
-- Apply: psql $DATABASE_URL -f migrations/095_agent_events.sql
--
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('095', 'Create agent_events table for SDK event batching')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Agent Events: batched telemetry from SDKs
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_events (
    id            BIGSERIAL PRIMARY KEY,
    org_id        TEXT NOT NULL,
    agent_id      TEXT NOT NULL,
    session_id    VARCHAR(64),
    event_type    VARCHAR(64) NOT NULL,
    event_data    JSONB NOT NULL DEFAULT '{}',
    sdk_timestamp TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Query events for a specific agent (dashboard feed)
CREATE INDEX IF NOT EXISTS idx_agent_events_agent
ON agent_events (agent_id, created_at DESC);

-- Query events by type within an org (analytics)
CREATE INDEX IF NOT EXISTS idx_agent_events_org_type
ON agent_events (org_id, event_type, created_at DESC);

-- Query events by session (session detail view)
CREATE INDEX IF NOT EXISTS idx_agent_events_session
ON agent_events (session_id, created_at DESC);
