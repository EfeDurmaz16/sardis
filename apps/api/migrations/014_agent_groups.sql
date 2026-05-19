-- Migration 014: Agent Groups (Multi-Agent Governance)
-- Creates tables for agent groups and group membership.

CREATE TABLE IF NOT EXISTS agent_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     TEXT UNIQUE NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    budget_per_tx   NUMERIC(20, 6) NOT NULL DEFAULT 500.00,
    budget_daily    NUMERIC(20, 6) NOT NULL DEFAULT 5000.00,
    budget_monthly  NUMERIC(20, 6) NOT NULL DEFAULT 50000.00,
    budget_total    NUMERIC(20, 6) NOT NULL DEFAULT 500000.00,
    merchant_policy JSONB NOT NULL DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_groups_org_id ON agent_groups(organization_id);
CREATE INDEX IF NOT EXISTS idx_agent_groups_external_id ON agent_groups(external_id);

CREATE TABLE IF NOT EXISTS agent_group_members (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id  UUID NOT NULL REFERENCES agent_groups(id) ON DELETE CASCADE,
    agent_id  TEXT NOT NULL,
    added_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(group_id, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_group_members_group_id ON agent_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_agent_group_members_agent_id ON agent_group_members(agent_id);
