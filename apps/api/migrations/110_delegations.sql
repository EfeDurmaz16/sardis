-- Migration: 110_delegations.sql
-- Description: Attenuated Delegation Graph — object-capability for money. An
--   agent (or principal) delegates a SCOPED, BOUNDED, REVOCABLE slice of its
--   own authority to a sub-agent, forming an attenuating capability chain:
--   human -> $500 mandate -> Agent A delegates $50 -> sub-agent B delegates
--   $20 -> tool C. Every hop attenuates — a delegate can NEVER exceed its
--   delegator (cap <= parent remaining, expiry <= parent, scope subset of
--   parent).
--
--   A delegation is a DERIVED authority: a scoped, signed child of its parent
--   (a SpendingMandate at the root, or another delegation deeper down). At
--   execution time the WHOLE chain up to the root mandate is re-checked link by
--   link (each non-revoked + within cap/scope + non-expired); any break -> DENY
--   (fail-closed). Revoking a parent (via the Revocation engine) propagates to
--   the entire delegation subtree (all descendants -> revoked).
--
--   Sardis owns the delegation DECISION + signed evidence (the moat). The proof
--   reuses the HMAC pattern (SARDIS_DELEGATION_HMAC_KEY), mirroring
--   DecisionEvidence / RevocationProof / ExecutionReceipt.

CREATE TYPE delegator_kind AS ENUM ('mandate', 'delegation');
CREATE TYPE delegation_status AS ENUM ('active', 'revoked', 'expired', 'exhausted');

CREATE TABLE IF NOT EXISTS delegations (
    -- Primary key: dlg_<base36_ts>_<rand>
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL DEFAULT '',

    -- The parent this authority is DRAWN FROM (the delegator in the chain).
    delegator_kind delegator_kind NOT NULL,        -- 'mandate' (root) | 'delegation'
    delegator_ref VARCHAR(128) NOT NULL,           -- parent mandate id | parent delegation id
    delegator_principal VARCHAR(256) NOT NULL,     -- who is delegating (agent/principal)

    -- The sub-agent receiving the attenuated slice.
    delegatee VARCHAR(256) NOT NULL,

    -- The SpendingMandate at the root of this chain (denormalized for fast
    -- subtree resolution + execution-time re-check).
    root_mandate_id VARCHAR(128) NOT NULL,

    -- Attenuated grant — each dimension MUST narrow the delegator.
    amount_cap NUMERIC(38, 18),                    -- token units; <= parent remaining (NULL = uncapped only if parent uncapped)
    currency VARCHAR(16) NOT NULL DEFAULT 'USDC',
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,      -- {counterparties, categories, mcc, rails} — subset of parent
    expires_at TIMESTAMPTZ,                         -- <= parent expiry
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Position in the attenuating chain (root mandate = depth 0; first delegation = 1).
    depth INTEGER NOT NULL DEFAULT 1,

    -- Spend tracking: a delegate spend decrements this hop AND every ancestor.
    spent_total NUMERIC(38, 18) NOT NULL DEFAULT 0,

    -- Lifecycle
    status delegation_status NOT NULL DEFAULT 'active',
    revoked_at TIMESTAMPTZ,
    revoked_by VARCHAR(256),
    revocation_reason TEXT,

    -- Signed, independently-verifiable DelegationEvidence: decision_hash binds
    -- the delegation identity + delegator chain + attenuated grant (cap, scope
    -- hash, expiry, depth); signature is HMAC-SHA256 over the decision hash
    -- (SARDIS_DELEGATION_HMAC_KEY).
    evidence JSONB,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Subtree resolution: find the direct children drawn from a parent (the
-- Revocation engine walks this recursively to kill a delegation subtree).
CREATE INDEX idx_delegations_delegator ON delegations(delegator_kind, delegator_ref);
-- Chain entry point: the active delegation a sub-agent currently holds.
CREATE INDEX idx_delegations_delegatee ON delegations(delegatee) WHERE status = 'active';
-- Root-keyed sweep + reporting.
CREATE INDEX idx_delegations_root ON delegations(root_mandate_id);
CREATE INDEX idx_delegations_status ON delegations(status);
CREATE INDEX idx_delegations_org ON delegations(org_id);

COMMENT ON TABLE delegations IS
    'Attenuated Delegation Graph: object-capability for money. A delegation is a '
    'scoped, bounded, revocable, derived child of its parent (a SpendingMandate '
    'root or another delegation). A delegate can NEVER exceed its delegator '
    '(cap/expiry/scope all narrow). Execution re-checks the whole chain to the '
    'root mandate; any broken link denies fail-closed. Revoking a parent kills '
    'the entire subtree. Sardis owns the decision + signed evidence (moat).';
COMMENT ON COLUMN delegations.scope IS
    'Attenuated authority surface {counterparties, categories, mcc, rails}. Each '
    'dimension is a subset of the delegator scope — narrowing only, never widening.';
COMMENT ON COLUMN delegations.evidence IS
    'Signed DelegationEvidence: HMAC-SHA256 over decision_hash binding the '
    'delegation identity + delegator chain + attenuated grant '
    '(SARDIS_DELEGATION_HMAC_KEY). Independently verifiable from its fields.';
