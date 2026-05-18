-- =============================================================================
-- Sardis Migration: 007_agent_spending_policy
-- =============================================================================
--
-- Adds JSONB spending policy storage to agents for production deployments.
--
-- Apply: psql $DATABASE_URL -f migrations/007_agent_spending_policy.sql
--
-- =============================================================================

-- Guard: record migration
INSERT INTO schema_migrations (version, description)
VALUES ('007', 'Add agents.spending_policy JSONB for persistent policy definitions')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Agents: persist policy definition + metadata
-- -----------------------------------------------------------------------------

ALTER TABLE agents
ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}',
ADD COLUMN IF NOT EXISTS spending_policy JSONB;

CREATE INDEX IF NOT EXISTS idx_agents_spending_policy
ON agents ((spending_policy IS NOT NULL));

COMMENT ON COLUMN agents.spending_policy IS
    'Serialized SpendingPolicy (JSON) used for card/webhook/on-chain enforcement. NULL means default policy.';

