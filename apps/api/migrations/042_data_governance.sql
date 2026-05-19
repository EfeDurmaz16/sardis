-- Migration 042: Data governance — PII classification, retention, tenant data export
-- Phase 4.5

-- Data classification registry: track which tables/columns contain PII
CREATE TABLE IF NOT EXISTS data_classification (
    id              SERIAL PRIMARY KEY,
    table_name      TEXT NOT NULL,
    column_name     TEXT NOT NULL,
    classification  TEXT NOT NULL DEFAULT 'internal',  -- public, internal, confidential, restricted
    pii_type        TEXT,                              -- email, phone, name, address, wallet_address, ip, null
    retention_days  INT NOT NULL DEFAULT 365,
    anonymize_on_expiry BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(table_name, column_name)
);

-- Seed known PII columns
INSERT INTO data_classification (table_name, column_name, classification, pii_type, retention_days, anonymize_on_expiry) VALUES
    ('users',           'email',              'restricted',   'email',          730,  TRUE),
    ('users',           'full_name',          'confidential', 'name',           730,  TRUE),
    ('users',           'phone',              'restricted',   'phone',          730,  TRUE),
    ('agents',          'owner_id',           'confidential', NULL,             1095, FALSE),
    ('wallets',         'address',            'confidential', 'wallet_address', 1095, FALSE),
    ('access_audit_log','ip_address',         'restricted',   'ip',            90,   TRUE),
    ('access_audit_log','user_agent',         'internal',     NULL,            90,   TRUE),
    ('idempotency_records','response_body',   'confidential', NULL,            7,    FALSE),
    ('merchant_checkout_sessions','payer_wallet_address', 'confidential', 'wallet_address', 365, TRUE)
ON CONFLICT (table_name, column_name) DO NOTHING;

-- Data retention job log: track purge operations
CREATE TABLE IF NOT EXISTS data_retention_log (
    id              SERIAL PRIMARY KEY,
    table_name      TEXT NOT NULL,
    rows_purged     INT NOT NULL DEFAULT 0,
    rows_anonymized INT NOT NULL DEFAULT 0,
    retention_days  INT NOT NULL,
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_ms     INT,
    error           TEXT
);

-- Tenant data export requests (GDPR right to data portability)
CREATE TABLE IF NOT EXISTS tenant_data_exports (
    id              SERIAL PRIMARY KEY,
    org_id          TEXT NOT NULL,
    requested_by    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    export_format   TEXT NOT NULL DEFAULT 'json',     -- json, csv
    download_url    TEXT,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- Tenant data deletion requests (GDPR right to erasure)
CREATE TABLE IF NOT EXISTS tenant_data_deletions (
    id              SERIAL PRIMARY KEY,
    org_id          TEXT NOT NULL,
    requested_by    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    tables_processed TEXT[] DEFAULT '{}',
    rows_deleted    INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_data_retention_log_table ON data_retention_log(table_name);
CREATE INDEX IF NOT EXISTS idx_tenant_exports_org ON tenant_data_exports(org_id);
CREATE INDEX IF NOT EXISTS idx_tenant_deletions_org ON tenant_data_deletions(org_id);
