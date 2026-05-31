-- Migration: 108_recourse_holds.sql
-- Description: Programmable Recourse — durable, signed, time-boxed recourse
--   holds. A payment that carries a policy-defined recourse window opens a
--   RecourseHold after successful execution instead of immediate finality. The
--   hold settles down a single fail-closed path: held -> released (window
--   expired) | refunded (within window, <= held) | disputed -> resolved
--   (refund|release). Every transition carries signed DecisionEvidence
--   (HMAC + decision/policy/mandate hashes), reusing the approval evidence
--   shape. Sardis owns the decision/policy/evidence (moat); the escrow contract
--   / reverse-transfer referenced here is swappable execution.

CREATE TYPE recourse_hold_status AS ENUM ('held', 'released', 'refunded', 'disputed', 'resolved');
CREATE TYPE recourse_resolution AS ENUM ('release', 'refund');

CREATE TABLE IF NOT EXISTS recourse_holds (
    -- Primary key: rch_<base36_ts>_<rand>
    id VARCHAR(64) PRIMARY KEY,

    -- Linkage
    payment_ref VARCHAR(128) NOT NULL,           -- payment_object_id / mandate_id backed
    mandate_id VARCHAR(128),                      -- the payment mandate_id
    agent_id VARCHAR(64),                         -- acting agent

    -- Money: Decimal + exact integer minor-units (never float)
    amount DECIMAL(38, 18) NOT NULL DEFAULT 0,
    amount_minor BIGINT NOT NULL,
    currency VARCHAR(16) NOT NULL,

    -- Parties
    payer VARCHAR(256) NOT NULL,                  -- refundTo (gets money back on refund)
    recipient VARCHAR(256) NOT NULL,             -- to (gets money on release)

    -- Window
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,

    -- State machine
    status recourse_hold_status NOT NULL DEFAULT 'held',
    resolution recourse_resolution,              -- set on terminal (release|refund)
    refunded_minor BIGINT NOT NULL DEFAULT 0,    -- cumulative minor-units refunded (<= amount_minor)
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(256),

    -- Bound snapshot hashes (captured when the hold opened; pin the evidence)
    policy_hash VARCHAR(128) NOT NULL DEFAULT '',
    mandate_hash VARCHAR(128) NOT NULL DEFAULT '',

    -- Swappable-execution references (escrow contract / reverse-transfer)
    escrow_contract VARCHAR(128),
    escrow_payment_id VARCHAR(128),              -- RefundProtocol paymentID
    open_tx_hash VARCHAR(128),
    settle_tx_hash VARCHAR(128),

    -- Signed evidence for the latest transition (HMAC over decision/policy/mandate hashes)
    evidence JSONB,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Fail-closed invariant at the DB layer: a refund can never exceed the held amount.
    CONSTRAINT recourse_refund_within_held CHECK (refunded_minor >= 0 AND refunded_minor <= amount_minor)
);

CREATE INDEX idx_recourse_holds_status ON recourse_holds(status);
CREATE INDEX idx_recourse_holds_payment_ref ON recourse_holds(payment_ref);
CREATE INDEX idx_recourse_holds_mandate_id ON recourse_holds(mandate_id);
CREATE INDEX idx_recourse_holds_agent_id ON recourse_holds(agent_id);
CREATE INDEX idx_recourse_holds_open_expiry
    ON recourse_holds(expires_at) WHERE status = 'held';

-- A payment_ref may have at most ONE non-terminal (held/disputed) recourse hold
-- at a time. Terminal rows are unconstrained so a residual claim could re-open.
CREATE UNIQUE INDEX uq_recourse_holds_open_payment_ref
    ON recourse_holds(payment_ref) WHERE status IN ('held', 'disputed');

COMMENT ON TABLE recourse_holds IS
    'Programmable Recourse: durable, signed, time-boxed holds. held -> released '
    '(window expired) | refunded (within window) | disputed -> resolved. Sardis '
    'owns the decision/policy/evidence; escrow contract is swappable execution.';
COMMENT ON COLUMN recourse_holds.evidence IS
    'Signed DecisionEvidence for the latest transition: HMAC-SHA256 over '
    'decision + hold/policy/mandate hashes (SARDIS_RECOURSE_HMAC_KEY).';
COMMENT ON COLUMN recourse_holds.refunded_minor IS
    'Cumulative minor-units returned to payer; CHECK-constrained <= amount_minor.';
