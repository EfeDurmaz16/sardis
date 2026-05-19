-- Migration 043: SSO configuration — SAML/OIDC per organization
-- Phase 4.2

CREATE TABLE IF NOT EXISTS sso_configurations (
    id              TEXT PRIMARY KEY DEFAULT 'sso_' || replace(gen_random_uuid()::text, '-', ''),
    org_id          TEXT NOT NULL,
    provider_type   TEXT NOT NULL CHECK (provider_type IN ('saml', 'oidc')),
    display_name    TEXT NOT NULL DEFAULT 'SSO',
    enabled         BOOLEAN NOT NULL DEFAULT FALSE,

    -- OIDC fields
    oidc_issuer_url     TEXT,
    oidc_client_id      TEXT,
    oidc_client_secret  TEXT,  -- encrypted at rest
    oidc_scopes         TEXT[] DEFAULT '{openid,profile,email}',

    -- SAML fields
    saml_entity_id      TEXT,
    saml_sso_url        TEXT,
    saml_certificate    TEXT,  -- IdP X.509 certificate (PEM)
    saml_name_id_format TEXT DEFAULT 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',

    -- Behavior
    auto_provision_users    BOOLEAN NOT NULL DEFAULT TRUE,
    default_role            TEXT NOT NULL DEFAULT 'member',
    enforce_sso_only        BOOLEAN NOT NULL DEFAULT FALSE,  -- block password login when true
    allowed_email_domains   TEXT[] DEFAULT '{}',

    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, provider_type)
);

-- SSO session linkage
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_provider_id TEXT REFERENCES sso_configurations(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_subject_id TEXT;

CREATE INDEX IF NOT EXISTS idx_sso_config_org ON sso_configurations(org_id);
CREATE INDEX IF NOT EXISTS idx_users_sso ON users(sso_provider_id) WHERE sso_provider_id IS NOT NULL;
