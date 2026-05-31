-- Migration: 107_approval_requests.sql
-- Description: Durable, signed human-in-the-loop approval requests for the
--   orchestrator's requires_approval gate. Distinct from the legacy `approvals`
--   table (UI-facing): this table is the ENGINE's durable record that gates
--   re-execution through the single fail-closed payment path. Every decision
--   carries signed evidence (HMAC + decision/policy/mandate hashes).

CREATE TYPE approval_request_status AS ENUM ('pending', 'approved', 'denied', 'expired');

CREATE TABLE IF NOT EXISTS approval_requests (
    -- Primary key: apreq_<base36_ts>_<rand>
    id VARCHAR(64) PRIMARY KEY,

    -- Context: who/what/how-much/where
    agent_id VARCHAR(64),                       -- requesting agent
    mandate_id VARCHAR(128),                    -- the payment mandate_id gated
    spending_mandate_id VARCHAR(64),            -- governing SpendingMandate, if any
    amount DECIMAL(38, 18) NOT NULL DEFAULT 0,  -- Decimal money, exact
    currency VARCHAR(16) NOT NULL,
    counterparty VARCHAR(256),                  -- merchant id / destination address
    reason TEXT NOT NULL,

    -- State machine
    status approval_request_status NOT NULL DEFAULT 'pending',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    decided_by VARCHAR(256),                    -- principal id / email / 'system'
    decided_at TIMESTAMPTZ,

    -- Bound snapshot hashes (captured at request time; re-execution checks drift)
    policy_hash VARCHAR(128) NOT NULL DEFAULT '',
    mandate_hash VARCHAR(128) NOT NULL DEFAULT '',

    -- High-value approvals require OTP step-up of the approver
    requires_step_up BOOLEAN NOT NULL DEFAULT FALSE,

    -- Idempotent re-execution accounting: approved unlocks exactly ONE settle
    reexecuted BOOLEAN NOT NULL DEFAULT FALSE,

    -- Signed decision evidence (HMAC-SHA256 over decision/policy/mandate hashes)
    evidence JSONB,

    -- Extensible metadata (deny reason, delivery handles, etc.)
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_approval_requests_status ON approval_requests(status);
CREATE INDEX idx_approval_requests_agent_id ON approval_requests(agent_id);
CREATE INDEX idx_approval_requests_mandate_id ON approval_requests(mandate_id);
CREATE INDEX idx_approval_requests_pending_expiry
    ON approval_requests(expires_at) WHERE status = 'pending';

-- A payment mandate may only have ONE non-terminal (pending) approval gate at a
-- time. Terminal rows are unconstrained so re-requests after deny/expire work.
CREATE UNIQUE INDEX uq_approval_requests_pending_mandate
    ON approval_requests(mandate_id) WHERE status = 'pending' AND mandate_id IS NOT NULL;

COMMENT ON TABLE approval_requests IS
    'Durable, signed human-in-the-loop approval gate for the orchestrator. '
    'Approved unlocks exactly one idempotent re-execution through the '
    'fail-closed payment path; denied/expired block money permanently.';
COMMENT ON COLUMN approval_requests.evidence IS
    'Signed DecisionEvidence: HMAC-SHA256 over decision + request/policy/mandate hashes.';
COMMENT ON COLUMN approval_requests.reexecuted IS
    'TRUE once the approved payment has been (idempotently) re-executed. '
    'Guards against double-settlement on repeated approve callbacks.';
