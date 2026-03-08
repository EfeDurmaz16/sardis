-- Migration 046: Delegated credentials and consent tables
-- Consent table first (credentials reference it)

CREATE TABLE IF NOT EXISTS delegation_consents (
    id                       BIGSERIAL PRIMARY KEY,
    consent_id               TEXT          NOT NULL UNIQUE,
    org_id                   TEXT          NOT NULL,
    user_id                  TEXT,
    agent_id                 TEXT          NOT NULL,
    credential_id            TEXT,
    consent_type             TEXT          NOT NULL,
    granted_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    expires_at               TIMESTAMPTZ,
    approved_scopes_snapshot JSONB         NOT NULL DEFAULT '{}',
    revocable                BOOLEAN       NOT NULL DEFAULT TRUE,
    revoked_at               TIMESTAMPTZ,
    revoke_reason            TEXT,
    source_surface           TEXT          NOT NULL,
    user_auth_context        JSONB         NOT NULL DEFAULT '{}',
    metadata                 JSONB         NOT NULL DEFAULT '{}',
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_consent_agent ON delegation_consents(agent_id);
CREATE INDEX IF NOT EXISTS idx_consent_org ON delegation_consents(org_id);

-- Credentials table (references consent)
CREATE TABLE IF NOT EXISTS delegated_credentials (
    id               BIGSERIAL PRIMARY KEY,
    credential_id    TEXT          NOT NULL UNIQUE,
    org_id           TEXT          NOT NULL,
    agent_id         TEXT          NOT NULL,
    network          TEXT          NOT NULL,
    status           TEXT          NOT NULL DEFAULT 'provisioning',
    credential_class TEXT          NOT NULL DEFAULT 'opaque_delegated_token',
    token_reference  TEXT          NOT NULL,
    token_encrypted  BYTEA         NOT NULL,
    scope_json       JSONB         NOT NULL DEFAULT '{}',
    provider_metadata JSONB        NOT NULL DEFAULT '{}',
    consent_id       TEXT          NOT NULL REFERENCES delegation_consents(consent_id),
    last_used_at     TIMESTAMPTZ,
    expires_at       TIMESTAMPTZ,
    revoked_at       TIMESTAMPTZ,
    revoke_reason    TEXT,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dcred_agent ON delegated_credentials(agent_id, status);
CREATE INDEX IF NOT EXISTS idx_dcred_org ON delegated_credentials(org_id, status);
CREATE INDEX IF NOT EXISTS idx_dcred_network ON delegated_credentials(network, status);
CREATE INDEX IF NOT EXISTS idx_dcred_expires ON delegated_credentials(expires_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_consent_cred ON delegation_consents(credential_id);
