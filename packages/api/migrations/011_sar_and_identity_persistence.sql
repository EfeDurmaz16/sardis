-- =============================================================================
-- Sardis Migration: 011_sar_and_identity_persistence
-- =============================================================================
--
-- Persists SAR (Suspicious Activity Reports) and IdentityRegistry to PostgreSQL.
--
-- REGULATORY: SAR data must be retained for 5 years per FinCEN requirements.
-- SECURITY: IdentityRegistry loss breaks TAP/AP2 audit trail.
--
-- Apply: psql $DATABASE_URL -f migrations/011_sar_and_identity_persistence.sql
--
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('011', 'SAR storage and identity registry persistence')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- SAR (Suspicious Activity Reports) — FinCEN 5-year retention
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS suspicious_activity_reports (
    sar_id              TEXT PRIMARY KEY,
    internal_reference  TEXT UNIQUE NOT NULL,
    activity_type       VARCHAR(30) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft',
    priority            VARCHAR(10) NOT NULL DEFAULT 'medium',
    subject_id          TEXT NOT NULL,
    subject_type        VARCHAR(20) NOT NULL DEFAULT 'wallet',
    wallet_address      TEXT,
    activity_description TEXT NOT NULL,
    detection_date      TIMESTAMPTZ NOT NULL,
    filing_deadline     TIMESTAMPTZ,
    filed_date          TIMESTAMPTZ,
    report_data         JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sar_status ON suspicious_activity_reports(status);
CREATE INDEX IF NOT EXISTS idx_sar_priority ON suspicious_activity_reports(priority);
CREATE INDEX IF NOT EXISTS idx_sar_subject ON suspicious_activity_reports(subject_id);
CREATE INDEX IF NOT EXISTS idx_sar_detection ON suspicious_activity_reports(detection_date);

-- -----------------------------------------------------------------------------
-- Identity Registry — TAP/AP2 identity attestation persistence
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS identity_records (
    id              BIGSERIAL PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    public_key      TEXT NOT NULL,
    algorithm       VARCHAR(20) NOT NULL DEFAULT 'ed25519',
    domain          TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_identity_agent_version UNIQUE (agent_id, version)
);

CREATE INDEX IF NOT EXISTS idx_identity_agent ON identity_records(agent_id);
CREATE INDEX IF NOT EXISTS idx_identity_active ON identity_records(agent_id) WHERE revoked_at IS NULL;
