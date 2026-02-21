-- Migration 022: Multi-tenant organization support
-- Adds organizations, teams, and org_members tables for multi-tenancy

-- Table 1: organizations
-- Top-level organizational entity with billing and plan information
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL DEFAULT 'free',  -- free, pro, enterprise
    billing_email TEXT,
    stripe_customer_id TEXT,
    subscription_status TEXT,  -- active, canceled, past_due, etc.
    settings JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table 2: teams
-- Teams within organizations with optional hierarchy and budget limits
CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    parent_team_id TEXT REFERENCES teams(id) ON DELETE SET NULL,
    budget_limit NUMERIC(38,18),  -- Optional spending cap for this team
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table 3: org_members
-- User memberships in organizations with roles and team assignments
CREATE TABLE IF NOT EXISTS org_members (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,  -- External user ID (from auth system)
    role TEXT NOT NULL DEFAULT 'viewer',  -- org_admin, team_admin, policy_admin, agent_operator, viewer
    teams TEXT[] DEFAULT '{}',  -- Array of team IDs this member belongs to
    invited_by TEXT,  -- User ID who invited this member
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    joined_at TIMESTAMPTZ,
    invite_accepted BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(org_id, user_id)  -- One membership per user per org
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_plan ON organizations(plan);
CREATE INDEX IF NOT EXISTS idx_organizations_created ON organizations(created_at);

CREATE INDEX IF NOT EXISTS idx_teams_org_id ON teams(org_id);
CREATE INDEX IF NOT EXISTS idx_teams_parent_team_id ON teams(parent_team_id);
CREATE INDEX IF NOT EXISTS idx_teams_org_name ON teams(org_id, name);

CREATE INDEX IF NOT EXISTS idx_org_members_org_id ON org_members(org_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user_id ON org_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_role ON org_members(role);
CREATE INDEX IF NOT EXISTS idx_org_members_org_user ON org_members(org_id, user_id);

-- Optional: Add org_id and team_id to existing agents table
-- This migration assumes the agents table exists from previous migrations
-- If your schema differs, adjust accordingly

-- Add org_id column to agents table (nullable for backward compatibility)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agents' AND column_name = 'org_id'
    ) THEN
        ALTER TABLE agents ADD COLUMN org_id TEXT REFERENCES organizations(id) ON DELETE CASCADE;
        CREATE INDEX idx_agents_org_id ON agents(org_id);
    END IF;
END $$;

-- Add team_id column to agents table (nullable, agents can exist without teams)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agents' AND column_name = 'team_id'
    ) THEN
        ALTER TABLE agents ADD COLUMN team_id TEXT REFERENCES teams(id) ON DELETE SET NULL;
        CREATE INDEX idx_agents_team_id ON agents(team_id);
    END IF;
END $$;

-- Add org context to wallets table (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'wallets') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'wallets' AND column_name = 'org_id'
        ) THEN
            ALTER TABLE wallets ADD COLUMN org_id TEXT REFERENCES organizations(id) ON DELETE CASCADE;
            CREATE INDEX idx_wallets_org_id ON wallets(org_id);
        END IF;
    END IF;
END $$;

-- Add org context to api_keys table (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'api_keys') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'api_keys' AND column_name = 'org_id'
        ) THEN
            ALTER TABLE api_keys ADD COLUMN org_id TEXT REFERENCES organizations(id) ON DELETE CASCADE;
            CREATE INDEX idx_api_keys_org_id ON api_keys(org_id);
        END IF;
    END IF;
END $$;

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to auto-update updated_at
DROP TRIGGER IF EXISTS organizations_updated_at ON organizations;
CREATE TRIGGER organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS teams_updated_at ON teams;
CREATE TRIGGER teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE organizations IS 'Top-level organizational entities with billing and plan information';
COMMENT ON TABLE teams IS 'Teams within organizations with optional hierarchy and budget limits';
COMMENT ON TABLE org_members IS 'User memberships in organizations with role-based access control';

COMMENT ON COLUMN organizations.slug IS 'URL-safe unique identifier for the organization';
COMMENT ON COLUMN organizations.plan IS 'Billing plan tier: free, pro, enterprise';
COMMENT ON COLUMN teams.parent_team_id IS 'Parent team for hierarchical team structures';
COMMENT ON COLUMN teams.budget_limit IS 'Optional spending cap for this team (aggregated across agents)';
COMMENT ON COLUMN org_members.role IS 'RBAC role: org_admin, team_admin, policy_admin, agent_operator, viewer';
COMMENT ON COLUMN org_members.teams IS 'Array of team IDs this member belongs to';
