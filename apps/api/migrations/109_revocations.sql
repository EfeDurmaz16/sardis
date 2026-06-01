-- Migration: 109_revocations.sql
-- Description: Propagating Revocation — the lead-wedge primitive. ONE revoke
--   atomically propagates across EVERY rail: mark the SpendingMandate(s)
--   revoked (the authority root the orchestrator denies on at execution time),
--   revoke outstanding one-time spend objects, freeze the agent's cards (via
--   CardPort), deny pending ApprovalRequests, block in-flight payments — and
--   return a SIGNED, INDEPENDENTLY-VERIFIABLE RevocationProof listing exactly
--   what was killed and when.
--
--   Fail-closed: a partial propagation is NEVER reported as fully propagated.
--   A downstream kill that cannot be confirmed is recorded blocked_pending /
--   failed; the overall status becomes 'blocked_pending_downstream'. The
--   authority is still denied at execution time (the mandate is revoked), and
--   the proof tells the truth about partial state.
--
--   Sardis owns the revocation DECISION + signed proof (the moat — requires
--   neutrality across all rails, which no single rail-owner has). The per-rail
--   kill is swappable execution (sardis.core.revocation_ports). The proof reuses
--   the HMAC pattern (SARDIS_REVOCATION_HMAC_KEY), mirroring DecisionEvidence /
--   ExecutionReceipt.

CREATE TYPE revocation_target_kind AS ENUM ('agent', 'mandate', 'principal');
CREATE TYPE revocation_status AS ENUM ('propagated', 'blocked_pending_downstream');

CREATE TABLE IF NOT EXISTS revocations (
    -- Primary key: rev_<base36_ts>_<rand>
    id VARCHAR(64) PRIMARY KEY,

    -- The authority being killed
    target_kind revocation_target_kind NOT NULL,
    target_ref VARCHAR(128) NOT NULL,             -- agent_id | mandate_id | principal_id
    scope VARCHAR(256) NOT NULL DEFAULT 'all',    -- "all" | "rails:card,usdc" | ...

    -- Provenance
    requested_by VARCHAR(256) NOT NULL,           -- principal id / "system"
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Outcome
    status revocation_status NOT NULL DEFAULT 'propagated',
    revoked_at TIMESTAMPTZ,                        -- set when propagation finalizes

    -- The full propagation record: ordered list of PropagationTarget dicts
    -- {kind, ref, kill_status, detail, killed_at}. Bound verbatim into the proof.
    targets JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Signed, independently-verifiable RevocationProof: decision_hash binds the
    -- revocation identity + the full target list + outcome + timestamp; the
    -- signature is HMAC-SHA256 over the decision hash (SARDIS_REVOCATION_HMAC_KEY).
    proof JSONB,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_revocations_target ON revocations(target_kind, target_ref);
CREATE INDEX idx_revocations_status ON revocations(status);
CREATE INDEX idx_revocations_requested_at ON revocations(requested_at DESC);

-- Idempotency at the DB layer: at most ONE revocation per (target_kind,
-- target_ref). A re-revoke returns the same row (and the same signed proof)
-- instead of double-propagating. Two concurrent revoke calls cannot both insert.
CREATE UNIQUE INDEX uq_revocations_target
    ON revocations(target_kind, target_ref);

COMMENT ON TABLE revocations IS
    'Propagating Revocation: ONE revoke atomically kills authority across every '
    'rail (mandate, spend objects, cards, approvals, in-flight) and returns a '
    'signed, independently-verifiable RevocationProof. Sardis owns the decision '
    '+ proof (moat); per-rail kill is swappable execution. Fail-closed: partial '
    'propagation -> blocked_pending_downstream, never reported as propagated.';
COMMENT ON COLUMN revocations.targets IS
    'Ordered PropagationTarget list {kind, ref, kill_status (killed|'
    'blocked_pending|failed|already_dead), detail, killed_at}. Bound into the proof.';
COMMENT ON COLUMN revocations.proof IS
    'Signed RevocationProof: HMAC-SHA256 over decision_hash binding the '
    'revocation identity + full target list + outcome + timestamp '
    '(SARDIS_REVOCATION_HMAC_KEY). Independently verifiable from its fields.';
