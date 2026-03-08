-- Migration 047: Merchant execution capabilities

CREATE TABLE IF NOT EXISTS merchant_capabilities (
    id                            BIGSERIAL PRIMARY KEY,
    merchant_id                   TEXT NOT NULL UNIQUE,
    domain                        TEXT,
    accepts_native_crypto         BOOLEAN NOT NULL DEFAULT FALSE,
    accepts_card                  BOOLEAN NOT NULL DEFAULT TRUE,
    supports_delegated_card       BOOLEAN NOT NULL DEFAULT FALSE,
    supported_networks            TEXT[] NOT NULL DEFAULT '{}',
    supports_trusted_agent        BOOLEAN NOT NULL DEFAULT FALSE,
    supports_tokenized_delegation BOOLEAN NOT NULL DEFAULT FALSE,
    settlement_preference         TEXT NOT NULL DEFAULT 'any',
    first_seen                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    capability_source             TEXT NOT NULL DEFAULT 'manual',
    verification_status           TEXT NOT NULL DEFAULT 'unverified',
    confidence                    NUMERIC(3,2) NOT NULL DEFAULT 0.5,
    risk_category                 TEXT,
    metadata                      JSONB NOT NULL DEFAULT '{}',
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_merchant_cap_domain ON merchant_capabilities(domain);
