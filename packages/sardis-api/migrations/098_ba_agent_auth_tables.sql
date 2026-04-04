-- Migration 098: better-auth agent-auth plugin tables
-- These tables support the @better-auth/agent-auth plugin for AI agent
-- identity, capability grants, and approval flows.
-- Schema derived from the plugin source (v0.x, dist/index.js agentSchema()).
-- All tables use ba_ prefix with snake_case column names to match the
-- project-wide better-auth table mapping convention (see auth.ts).

-- ============================================================================
-- 1. ba_agent_host — host applications that register and manage agents
-- ============================================================================
CREATE TABLE IF NOT EXISTS ba_agent_host (
    id                          TEXT PRIMARY KEY,
    name                        TEXT,                        -- human-readable host name
    user_id                     TEXT REFERENCES ba_user(id) ON DELETE CASCADE,
    default_capabilities        TEXT,                        -- JSON array of default capability strings
    public_key                  TEXT,                        -- host's public key (JWK JSON)
    kid                         TEXT,                        -- key id for JWKS lookup
    jwks_url                    TEXT,                        -- remote JWKS endpoint
    enrollment_token_hash       TEXT,                        -- SHA-256 hash of enrollment token
    enrollment_token_expires_at TIMESTAMPTZ,                 -- enrollment token expiry
    status                      TEXT NOT NULL DEFAULT 'active', -- active | suspended | revoked
    activated_at                TIMESTAMPTZ,                 -- when host was activated
    expires_at                  TIMESTAMPTZ,                 -- optional host expiry
    last_used_at                TIMESTAMPTZ,                 -- last API interaction
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ba_agent_host_user_id ON ba_agent_host(user_id);
CREATE INDEX IF NOT EXISTS idx_ba_agent_host_kid ON ba_agent_host(kid);
CREATE INDEX IF NOT EXISTS idx_ba_agent_host_enrollment_token_hash ON ba_agent_host(enrollment_token_hash);
CREATE INDEX IF NOT EXISTS idx_ba_agent_host_status ON ba_agent_host(status);

-- ============================================================================
-- 2. ba_agent — individual AI agent identities
-- ============================================================================
CREATE TABLE IF NOT EXISTS ba_agent (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,                            -- agent display name
    user_id         TEXT REFERENCES ba_user(id) ON DELETE CASCADE,
    host_id         TEXT NOT NULL REFERENCES ba_agent_host(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'active',           -- active | pending | revoked | expired
    mode            TEXT NOT NULL DEFAULT 'delegated',        -- delegated | autonomous
    public_key      TEXT NOT NULL,                            -- agent's public key (JWK JSON)
    kid             TEXT,                                     -- key id for JWKS lookup
    jwks_url        TEXT,                                     -- remote JWKS endpoint
    last_used_at    TIMESTAMPTZ,                              -- last authenticated action
    activated_at    TIMESTAMPTZ,                              -- when agent became active
    expires_at      TIMESTAMPTZ,                              -- optional agent expiry
    metadata        TEXT,                                     -- JSON blob for arbitrary metadata
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ba_agent_user_id ON ba_agent(user_id);
CREATE INDEX IF NOT EXISTS idx_ba_agent_host_id ON ba_agent(host_id);
CREATE INDEX IF NOT EXISTS idx_ba_agent_status ON ba_agent(status);
CREATE INDEX IF NOT EXISTS idx_ba_agent_kid ON ba_agent(kid);

-- ============================================================================
-- 3. ba_agent_capability_grant — capability grants assigned to agents
-- ============================================================================
CREATE TABLE IF NOT EXISTS ba_agent_capability_grant (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL REFERENCES ba_agent(id) ON DELETE CASCADE,
    capability      TEXT NOT NULL,                            -- capability identifier (e.g. "payments.send")
    denied_by       TEXT REFERENCES ba_user(id) ON DELETE CASCADE,
    granted_by      TEXT REFERENCES ba_user(id) ON DELETE CASCADE,
    expires_at      TIMESTAMPTZ,                              -- optional grant expiry
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          TEXT NOT NULL DEFAULT 'active',           -- active | revoked | expired | denied
    reason          TEXT,                                     -- human-readable reason for grant/deny
    constraints     TEXT                                      -- JSON object with capability constraints
);

CREATE INDEX IF NOT EXISTS idx_ba_agent_capability_grant_agent_id ON ba_agent_capability_grant(agent_id);
CREATE INDEX IF NOT EXISTS idx_ba_agent_capability_grant_capability ON ba_agent_capability_grant(capability);
CREATE INDEX IF NOT EXISTS idx_ba_agent_capability_grant_granted_by ON ba_agent_capability_grant(granted_by);
CREATE INDEX IF NOT EXISTS idx_ba_agent_capability_grant_status ON ba_agent_capability_grant(status);

-- ============================================================================
-- 4. ba_approval_request — CIBA / device-authorization approval flows
-- ============================================================================
CREATE TABLE IF NOT EXISTS ba_approval_request (
    id                              TEXT PRIMARY KEY,
    method                          TEXT NOT NULL,            -- "ciba" | "device_authorization"
    agent_id                        TEXT REFERENCES ba_agent(id) ON DELETE CASCADE,
    host_id                         TEXT REFERENCES ba_agent_host(id) ON DELETE CASCADE,
    user_id                         TEXT REFERENCES ba_user(id) ON DELETE CASCADE,
    capabilities                    TEXT,                     -- JSON array of requested capabilities
    status                          TEXT NOT NULL DEFAULT 'pending', -- pending | approved | denied | expired
    user_code_hash                  TEXT,                     -- hashed user code for device flow
    login_hint                      TEXT,                     -- login hint (email, phone, etc.)
    binding_message                 TEXT,                     -- message shown to user during approval
    client_notification_token       TEXT,                     -- CIBA push notification token
    client_notification_endpoint    TEXT,                     -- CIBA push notification URL
    delivery_mode                   TEXT,                     -- poll | ping | push
    interval                        INTEGER NOT NULL,         -- polling interval in seconds
    last_polled_at                  TIMESTAMPTZ,              -- last poll timestamp
    expires_at                      TIMESTAMPTZ NOT NULL,     -- request expiry
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ba_approval_request_agent_id ON ba_approval_request(agent_id);
CREATE INDEX IF NOT EXISTS idx_ba_approval_request_host_id ON ba_approval_request(host_id);
CREATE INDEX IF NOT EXISTS idx_ba_approval_request_user_id ON ba_approval_request(user_id);
CREATE INDEX IF NOT EXISTS idx_ba_approval_request_status ON ba_approval_request(status);
