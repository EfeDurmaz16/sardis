-- Migration 097: ba_apikey table for better-auth api-key plugin
-- This table is shared between the Next.js dashboard (via better-auth plugin)
-- and the FastAPI sardis-api (via direct SQL queries).
-- Schema mirrors the better-auth @better-auth/api-key plugin expectations
-- with snake_case field mappings from auth.ts configuration.

CREATE TABLE IF NOT EXISTS ba_apikey (
    id                      TEXT PRIMARY KEY,
    key                     TEXT NOT NULL,               -- hashed API key (SHA-256)
    name                    TEXT,                        -- human-readable key name
    prefix                  TEXT,                        -- starting characters for display (first 12 chars)
    user_id                 TEXT NOT NULL REFERENCES ba_user(id) ON DELETE CASCADE,
    config_id               TEXT NOT NULL DEFAULT 'test',-- "test" or "live" (maps to key mode)
    reference_id            TEXT,                        -- optional external reference
    refill_interval         INTEGER,                     -- rate limit refill interval (ms)
    refill_amount           INTEGER,                     -- rate limit refill amount
    last_refill_at          TIMESTAMPTZ,                 -- last rate limit refill
    rate_limit_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    rate_limit_time_window  INTEGER,                     -- rate limit window (ms)
    rate_limit_max          INTEGER DEFAULT 100,         -- max requests per window
    request_count           INTEGER NOT NULL DEFAULT 0,  -- current request count
    last_request            TIMESTAMPTZ,                 -- last request timestamp
    expires_at              TIMESTAMPTZ,                 -- key expiration
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    permissions             JSONB,                       -- resource-action permissions
    metadata                JSONB,                       -- arbitrary metadata (mode, labels, etc.)
    enabled                 BOOLEAN NOT NULL DEFAULT TRUE -- active/revoked flag
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_ba_apikey_user_id ON ba_apikey(user_id);
CREATE INDEX IF NOT EXISTS idx_ba_apikey_prefix ON ba_apikey(prefix);
CREATE INDEX IF NOT EXISTS idx_ba_apikey_key ON ba_apikey(key);
CREATE INDEX IF NOT EXISTS idx_ba_apikey_config_id ON ba_apikey(config_id);
CREATE INDEX IF NOT EXISTS idx_ba_apikey_enabled ON ba_apikey(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_ba_apikey_expires_at ON ba_apikey(expires_at) WHERE expires_at IS NOT NULL;
