-- Facility Gate append-only event store + projection records.
--
-- Ported from the retired Alembic revision 030 (apps/api/alembic) so the SQL
-- migration chain remains the single source of truth after Alembic retirement.
-- Backs facility_gate_repository.py / facility_gate_authority.py. Payload
-- columns are JSONB because the repository inserts with ::jsonb casts.
--
-- Idempotent: IF NOT EXISTS on every object so re-applying (or applying after
-- the Alembic 030 tables already exist on the live DB) is a no-op.

-- Append-only event log -------------------------------------------------------
CREATE TABLE IF NOT EXISTS facility_events (
    event_id            VARCHAR(64) PRIMARY KEY,
    organization_id     VARCHAR(128) NOT NULL,
    aggregate_id        VARCHAR(128) NOT NULL,
    event_type          VARCHAR(96) NOT NULL,
    idempotency_key     VARCHAR(160),
    actor_id            VARCHAR(128),
    payload             JSONB NOT NULL,
    previous_event_hash VARCHAR(64),
    event_hash          VARCHAR(64) NOT NULL,
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_facility_events_idempotency UNIQUE (organization_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_facility_events_org_aggregate
    ON facility_events (organization_id, aggregate_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_facility_events_type
    ON facility_events (event_type);

-- Request-state projection ----------------------------------------------------
CREATE TABLE IF NOT EXISTS facility_request_states (
    request_id          VARCHAR(128) PRIMARY KEY,
    organization_id     VARCHAR(128) NOT NULL,
    facility_id         VARCHAR(128) NOT NULL,
    agent_id            VARCHAR(128) NOT NULL,
    mandate_id          VARCHAR(128) NOT NULL,
    status              VARCHAR(64) NOT NULL,
    latest_decision_id  VARCHAR(128),
    latest_verdict      VARCHAR(64),
    merchant            VARCHAR(255) NOT NULL,
    amount_minor        BIGINT NOT NULL,
    currency            VARCHAR(12) NOT NULL,
    payload             JSONB NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_facility_request_states_org
    ON facility_request_states (organization_id, updated_at);

-- Facility records ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facility_records (
    facility_id              VARCHAR(128) PRIMARY KEY,
    organization_id          VARCHAR(128) NOT NULL,
    sponsor_id               VARCHAR(128) NOT NULL,
    provider                 VARCHAR(96) NOT NULL,
    facility_type            VARCHAR(64) NOT NULL,
    status                   VARCHAR(64) NOT NULL,
    version                  INTEGER NOT NULL,
    limit_payload            JSONB NOT NULL,
    allowed_categories       JSONB NOT NULL,
    allowed_merchants        JSONB NOT NULL,
    blocked_merchants        JSONB NOT NULL,
    approval_threshold_minor BIGINT NOT NULL,
    metadata                 JSONB NOT NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_facility_records_org_sponsor
    ON facility_records (organization_id, sponsor_id);
CREATE INDEX IF NOT EXISTS idx_facility_records_status
    ON facility_records (status);

-- Policy snapshot records -----------------------------------------------------
CREATE TABLE IF NOT EXISTS facility_policy_records (
    policy_record_id    VARCHAR(128) PRIMARY KEY,
    organization_id     VARCHAR(128) NOT NULL,
    facility_id         VARCHAR(128) NOT NULL,
    policy_version      VARCHAR(128) NOT NULL,
    snapshot            JSONB NOT NULL,
    snapshot_hash       VARCHAR(64) NOT NULL,
    created_by          VARCHAR(128),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_facility_policy_records_version
        UNIQUE (organization_id, facility_id, policy_version)
);
CREATE INDEX IF NOT EXISTS idx_facility_policy_records_latest
    ON facility_policy_records (organization_id, facility_id, created_at);

-- Mandate snapshot records ----------------------------------------------------
CREATE TABLE IF NOT EXISTS facility_mandate_records (
    mandate_record_id   VARCHAR(128) PRIMARY KEY,
    organization_id     VARCHAR(128) NOT NULL,
    mandate_id          VARCHAR(128) NOT NULL,
    agent_id            VARCHAR(128) NOT NULL DEFAULT '',
    version             INTEGER NOT NULL,
    snapshot            JSONB NOT NULL,
    snapshot_hash       VARCHAR(64) NOT NULL,
    created_by          VARCHAR(128),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_facility_mandate_records_version
        UNIQUE (organization_id, mandate_id, agent_id, version)
);
CREATE INDEX IF NOT EXISTS idx_facility_mandate_records_lookup
    ON facility_mandate_records (organization_id, mandate_id, agent_id, updated_at);
