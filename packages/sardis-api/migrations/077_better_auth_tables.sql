-- Migration 077: better-auth tables (prefixed with ba_ to avoid conflicts)
-- Provides session-based authentication infrastructure via better-auth library.
-- All tables use ba_ prefix to coexist with existing sardis auth tables.

CREATE TABLE IF NOT EXISTS ba_user (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    image           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Custom fields for Sardis
    org_id          TEXT,
    role            TEXT NOT NULL DEFAULT 'user',
    kyc_status      TEXT NOT NULL DEFAULT 'not_started',
    display_name    TEXT
);

CREATE TABLE IF NOT EXISTS ba_session (
    id              TEXT PRIMARY KEY,
    expires_at      TIMESTAMPTZ NOT NULL,
    token           TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address      TEXT,
    user_agent      TEXT,
    user_id         TEXT NOT NULL REFERENCES ba_user(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ba_account (
    id                          TEXT PRIMARY KEY,
    account_id                  TEXT NOT NULL,
    provider_id                 TEXT NOT NULL,
    user_id                     TEXT NOT NULL REFERENCES ba_user(id) ON DELETE CASCADE,
    access_token                TEXT,
    refresh_token               TEXT,
    id_token                    TEXT,
    access_token_expires_at     TIMESTAMPTZ,
    refresh_token_expires_at    TIMESTAMPTZ,
    scope                       TEXT,
    password                    TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ba_verification (
    id              TEXT PRIMARY KEY,
    identifier      TEXT NOT NULL,
    value           TEXT NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ba_jwks (
    id              TEXT PRIMARY KEY,
    public_key      TEXT NOT NULL,
    private_key     TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ba_passkey (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    public_key      TEXT NOT NULL,
    user_id         TEXT NOT NULL REFERENCES ba_user(id) ON DELETE CASCADE,
    credential_id   TEXT NOT NULL UNIQUE,
    counter         INTEGER NOT NULL DEFAULT 0,
    device_type     TEXT,
    backed_up       BOOLEAN NOT NULL DEFAULT FALSE,
    transports      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes on foreign keys (required for efficient CASCADE deletes and JOINs)
CREATE INDEX IF NOT EXISTS idx_ba_session_user_id ON ba_session(user_id);
CREATE INDEX IF NOT EXISTS idx_ba_account_user_id ON ba_account(user_id);
CREATE INDEX IF NOT EXISTS idx_ba_passkey_user_id ON ba_passkey(user_id);

-- Indexes on commonly queried fields
CREATE INDEX IF NOT EXISTS idx_ba_user_email ON ba_user(email);
CREATE INDEX IF NOT EXISTS idx_ba_user_org_id ON ba_user(org_id) WHERE org_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ba_user_kyc_status ON ba_user(kyc_status) WHERE kyc_status != 'not_started';
CREATE INDEX IF NOT EXISTS idx_ba_session_token ON ba_session(token);
CREATE INDEX IF NOT EXISTS idx_ba_session_expires_at ON ba_session(expires_at);
CREATE INDEX IF NOT EXISTS idx_ba_account_provider_id ON ba_account(provider_id);
CREATE INDEX IF NOT EXISTS idx_ba_account_provider_account ON ba_account(provider_id, account_id);
CREATE INDEX IF NOT EXISTS idx_ba_verification_identifier ON ba_verification(identifier);
CREATE INDEX IF NOT EXISTS idx_ba_verification_expires_at ON ba_verification(expires_at);
CREATE INDEX IF NOT EXISTS idx_ba_passkey_credential_id ON ba_passkey(credential_id);
