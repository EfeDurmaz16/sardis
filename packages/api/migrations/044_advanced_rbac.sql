-- Migration 044: Advanced RBAC — custom roles and resource-level permissions
-- Phase 4.3

-- Custom roles: org-defined roles with explicit permissions
CREATE TABLE IF NOT EXISTS custom_roles (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    permissions     TEXT[] NOT NULL DEFAULT '{}',
    inherits_from   TEXT,  -- built-in role to inherit from (org_admin, team_admin, etc.)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, name)
);

-- Resource-level permissions: grant specific permissions on specific resources
CREATE TABLE IF NOT EXISTS resource_permissions (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    permission      TEXT NOT NULL,
    resource_type   TEXT NOT NULL,  -- agent, wallet, group, policy
    resource_id     TEXT NOT NULL,
    granted_by      TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, permission, resource_type, resource_id)
);

CREATE INDEX IF NOT EXISTS idx_custom_roles_org ON custom_roles(org_id);
CREATE INDEX IF NOT EXISTS idx_resource_perms_user ON resource_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_resource_perms_resource ON resource_permissions(resource_type, resource_id);
