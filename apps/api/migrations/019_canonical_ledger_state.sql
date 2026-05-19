-- =============================================================================
-- Migration 019: Canonical Ledger State + Reconciliation Ops
-- =============================================================================
-- Normalizes fiat/stablecoin event rails into one canonical state machine.
-- Adds operator-focused reconciliation break detection and manual review queues.
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('019', 'Add canonical ledger event/state tables with break detection and manual review queue')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Canonical payment journeys (one row per logical payment flow)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS canonical_ledger_journeys (
    journey_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    rail TEXT NOT NULL,                -- fiat_ach, fiat_card, stablecoin_tx, stablecoin_userop
    provider TEXT NOT NULL,            -- lithic, onchain, etc.
    external_reference TEXT NOT NULL,  -- payment_token, tx_hash, user_op_hash, provider_tx_id...
    direction TEXT,                    -- debit/credit/payout/funding
    currency TEXT NOT NULL DEFAULT 'USD',
    canonical_state TEXT NOT NULL DEFAULT 'created',
    expected_amount_minor BIGINT NOT NULL DEFAULT 0,
    settled_amount_minor BIGINT NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_return_code TEXT,
    break_status TEXT NOT NULL DEFAULT 'ok', -- ok, drift_open, review_open, resolved
    first_event_at TIMESTAMPTZ,
    last_event_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_canonical_journey_org_rail_ref UNIQUE (organization_id, rail, external_reference)
);

CREATE INDEX IF NOT EXISTS idx_canonical_journeys_org_state
    ON canonical_ledger_journeys(organization_id, canonical_state, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_canonical_journeys_break_status
    ON canonical_ledger_journeys(organization_id, break_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_canonical_journeys_provider_ref
    ON canonical_ledger_journeys(provider, external_reference);

-- -----------------------------------------------------------------------------
-- Canonical events (append-only normalized history)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS canonical_ledger_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journey_id TEXT NOT NULL REFERENCES canonical_ledger_journeys(journey_id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_event_id TEXT,
    provider_event_type TEXT NOT NULL,
    canonical_event_type TEXT NOT NULL,
    canonical_state TEXT,
    event_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    amount_minor BIGINT,
    currency TEXT,
    return_code TEXT,
    out_of_order BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_canonical_events_journey_ts
    ON canonical_ledger_events(journey_id, event_ts DESC);
CREATE INDEX IF NOT EXISTS idx_canonical_events_org_ts
    ON canonical_ledger_events(organization_id, event_ts DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_canonical_events_provider_event
    ON canonical_ledger_events(provider, provider_event_id)
    WHERE provider_event_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Reconciliation breaks (drift / mismatch incidents)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reconciliation_breaks (
    break_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL,
    journey_id TEXT NOT NULL REFERENCES canonical_ledger_journeys(journey_id) ON DELETE CASCADE,
    break_type TEXT NOT NULL,       -- expected_settled_mismatch, retry_exhausted, provider_return_high_risk
    severity TEXT NOT NULL,         -- low, medium, high, critical
    expected_amount_minor BIGINT,
    settled_amount_minor BIGINT,
    delta_minor BIGINT,
    status TEXT NOT NULL DEFAULT 'open', -- open, acknowledged, resolved
    notes TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_recon_breaks_org_status
    ON reconciliation_breaks(organization_id, status, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_recon_breaks_journey
    ON reconciliation_breaks(journey_id, detected_at DESC);

-- -----------------------------------------------------------------------------
-- Manual review queue (operator workflow)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS manual_review_queue (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL,
    journey_id TEXT REFERENCES canonical_ledger_journeys(journey_id) ON DELETE SET NULL,
    reason_code TEXT NOT NULL,      -- R29, drift_mismatch, retry_exhausted, etc.
    priority TEXT NOT NULL DEFAULT 'medium', -- low, medium, high, critical
    status TEXT NOT NULL DEFAULT 'queued',   -- queued, in_review, resolved, dismissed
    assigned_to TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_manual_review_org_status
    ON manual_review_queue(organization_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_manual_review_reason
    ON manual_review_queue(reason_code, status, created_at DESC);
