-- =============================================================================
-- Sardis Migration: 094_agent_heartbeat
-- =============================================================================
--
-- Adds heartbeat/telemetry columns to agents table for SDK auto-registration
-- and online status tracking.
--
-- Apply: psql $DATABASE_URL -f migrations/094_agent_heartbeat.sql
--
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('094', 'Add heartbeat columns to agents for SDK telemetry')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Agents: heartbeat + telemetry columns
-- -----------------------------------------------------------------------------

ALTER TABLE agents ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS session_id VARCHAR(64);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS sdk_version VARCHAR(32);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS framework VARCHAR(64);

-- Fast lookup for online agents (last_seen_at within org)
CREATE INDEX IF NOT EXISTS idx_agents_last_seen
ON agents (organization_id, last_seen_at DESC)
WHERE is_active = TRUE;
