"""Attenuated Delegation Graph + Portable Proof-of-Authority API.

This surface exposes the two object-capability-for-money primitives the product
and third parties consume:

PRIMITIVE 1 — Attenuated Delegation Graph
-----------------------------------------
An agent (or principal) delegates a SCOPED, BOUNDED, REVOCABLE slice of its own
authority to a sub-agent, forming an attenuating capability chain — a delegate
can NEVER exceed its delegator.  The routes:

* ``POST /api/v2/delegations``            — mint a new attenuated delegation.
  Sardis owns the DECISION (the moat): the engine REJECTS the mint fail-closed
  unless the requested grant is a strict narrowing of the delegator's *current*
  authority (cap ``<=`` parent remaining, expiry ``<=`` parent, scope ``⊆``
  parent, depth under the ceiling).  Returns the durable delegation + its signed
  :class:`~sardis.core.delegation.DelegationEvidence`.
* ``GET  /api/v2/delegations/{id}``       — fetch one delegation hop + evidence.
* ``GET  /api/v2/delegations``            — list this org's delegations
  (optionally filter by ``delegatee``).
* ``GET  /api/v2/delegations/agent/{agent}/chain`` — resolve the FULL attenuated
  chain (root mandate first, leaf delegation last) for an acting sub-agent.
* ``POST /api/v2/delegations/{id}/revoke`` — revoke a delegation; PROPAGATES to
  the entire delegation subtree via the SAME RevocationEngine the orchestrator
  denies at execution time.  Returns the signed proof-of-revocation.
* ``POST /api/v2/delegations/verify``      — independently verify a
  ``DelegationEvidence`` from its own fields (HMAC; Sardis-internal tamper check).

PRIMITIVE 2 — Portable Proof-of-Authority
-----------------------------------------
A signed, self-contained credential proving an action WAS authorized.  Emitted
on every authorized execution (bound into the orchestrator's PaymentResult), it
binds policy_hash + mandate_hash + delegation_chain + decision + inputs and is
verifiable OFFLINE by a merchant/auditor/regulator with a *published* Ed25519
public key — no trust in, and no call to, Sardis.  The routes:

* ``POST /api/v2/authority/proofs/verify`` — PUBLIC (no auth): verify a Proof-of-
  Authority (JSON or compact JWS) against the published public key.  This is the
  third-party offline check.
* ``GET  /api/v2/authority/proofs/jwk``    — PUBLIC: the published Ed25519
  verification key (JWK + base64url) anyone uses to verify proofs offline.

Hard rules honored:

* **Sardis owns the authority decision.**  Attenuation is enforced by the engine
  at mint time; the chain is re-checked at execution time by the orchestrator.
* **Fail-closed.**  No delegation engine configured ⇒ the mutating/list/get
  routes return ``503`` rather than silently doing nothing.  Money is
  :class:`~decimal.Decimal` token units; minor units on the proof.
* **Auth + org-scope.**  The actor is the authenticated
  :class:`~server.authz.Principal`; the owning ``organization_id`` is stamped on
  every minted delegation so a caller from another org gets a ``404`` (not 403).
  The two proof-verification routes are PUBLIC by design — a portable proof is
  meant to be checked by anyone.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sardis.core.delegation import (
    Delegation,
    DelegationEvidence,
    DelegationScope,
    DelegatorKind,
)
from sardis.core.delegation_engine import DelegationError
from sardis.core.revocation import RevocationTargetKind

from server.authz import Principal, require_principal

logger = logging.getLogger(__name__)

# Org-scoped routes (delegation CRUD). The public proof-verification routes live
# on a separate unauthenticated router (`public_router`) below.
router = APIRouter(dependencies=[Depends(require_principal)])
public_router = APIRouter()

# Metadata key under which the owning org is stamped on a delegation minted via
# this API surface, so reads/list are org-scoped (mirrors the revocation surface).
_ORG_KEY = "organization_id"


# ── Engine resolution (fail-closed) ────────────────────────────────────


def _resolve_delegation_engine(request: Request) -> Any:
    """Resolve the shared DelegationEngine wired in dependencies.py.

    Fail-closed: if the engine is not configured (dev/in-memory has no
    delegations table), the surface refuses (503) rather than pretend a
    delegation was minted/resolved.  The orchestrator's execution-time chain
    re-check is a separate backstop."""
    engine = getattr(request.app.state, "delegation_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="delegation engine unavailable; attenuated delegation requires Postgres",
        )
    return engine


def _resolve_revocation_engine(request: Request) -> Any:
    engine = getattr(request.app.state, "revocation_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="revocation engine unavailable; cannot propagate delegation revoke",
        )
    return engine


async def _require_delegation_in_org(
    engine: Any, delegation_id: str, principal: Principal
) -> Delegation:
    """Fetch a delegation and enforce org ownership — fail-closed (404 cross-org)."""
    dlg = await engine._store.get(delegation_id)
    if dlg is None:
        raise HTTPException(status_code=404, detail=f"delegation {delegation_id} not found")
    owner = (dlg.metadata or {}).get(_ORG_KEY) or dlg.org_id
    if owner != principal.organization_id:
        raise HTTPException(status_code=404, detail=f"delegation {delegation_id} not found")
    return dlg


def _parse_amount(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail=f"invalid amount_cap {value!r}: {exc}"
        ) from exc


def _parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"invalid expires_at {value!r}: ISO-8601 required"
        ) from exc


# ── Models ──────────────────────────────────────────────────────────────


class ScopeModel(BaseModel):
    """The attenuated authority surface a delegation grants (subset constraints)."""

    counterparties: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    mcc: list[str] = Field(default_factory=list)
    rails: list[str] = Field(default_factory=list)

    def to_scope(self) -> DelegationScope:
        return DelegationScope(
            counterparties=list(self.counterparties),
            categories=list(self.categories),
            mcc=list(self.mcc),
            rails=list(self.rails),
        )


class CreateDelegationRequest(BaseModel):
    """Mint an attenuated delegation: delegator → delegatee, narrowing every dim.

    ``delegator_kind`` is ``mandate`` (delegate from a root SpendingMandate,
    depth 0) or ``delegation`` (delegate from a deeper hop).  ``delegator_ref`` is
    that parent's id.  The engine REJECTS the mint fail-closed if the grant is
    not a strict narrowing of the delegator's CURRENT authority.
    """

    delegator_kind: DelegatorKind = Field(
        default=DelegatorKind.MANDATE,
        description="mandate (root) | delegation (deeper hop) — what the slice is drawn FROM.",
    )
    delegator_ref: str = Field(
        ..., description="The parent mandate id (kind=mandate) or delegation id (kind=delegation)."
    )
    delegator_principal: str = Field(
        ..., description="Who is delegating (the agent/principal id doing the granting)."
    )
    delegatee: str = Field(..., description="The sub-agent receiving the scoped authority.")
    amount_cap: str | None = Field(
        default=None,
        description="Cap in token (major) units; MUST be <= delegator remaining. None inherits if delegator uncapped.",
    )
    currency: str | None = Field(default=None, description="Must match the delegator's currency.")
    scope: ScopeModel = Field(default_factory=ScopeModel)
    expires_at: str | None = Field(
        default=None, description="ISO-8601; MUST be <= delegator expiry. Omitted inherits parent expiry."
    )


class EvidenceModel(BaseModel):
    """The signed, independently-verifiable DelegationEvidence (HMAC)."""

    delegation_id: str
    delegator_kind: str
    delegator_ref: str
    delegator_principal: str
    delegatee: str
    root_mandate_id: str
    depth: int
    amount_cap: str | None = None
    currency: str
    expires_at: str | None = None
    scope_hash: str
    created_at: str
    decision_hash: str
    signature: str

    @staticmethod
    def from_evidence(ev: DelegationEvidence) -> EvidenceModel:
        return EvidenceModel(**ev.to_dict())


class DelegationModel(BaseModel):
    """A derived, attenuated, revocable slice of spending authority + its evidence."""

    id: str
    org_id: str
    delegator_kind: str
    delegator_ref: str
    delegator_principal: str
    delegatee: str
    root_mandate_id: str
    amount_cap: str | None = None
    currency: str
    scope: dict[str, Any]
    expires_at: str | None = None
    depth: int
    spent_total: str
    remaining: str | None = None
    status: str
    revoked_at: str | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None
    evidence: EvidenceModel | None = None
    created_at: str | None = None

    @staticmethod
    def from_delegation(dlg: Delegation) -> DelegationModel:
        d = dlg.to_dict()
        remaining = dlg.remaining
        return DelegationModel(
            id=d["id"],
            org_id=d["org_id"],
            delegator_kind=d["delegator_kind"],
            delegator_ref=d["delegator_ref"],
            delegator_principal=d["delegator_principal"],
            delegatee=d["delegatee"],
            root_mandate_id=d["root_mandate_id"],
            amount_cap=d["amount_cap"],
            currency=d["currency"],
            scope=d["scope"],
            expires_at=d["expires_at"],
            depth=d["depth"],
            spent_total=d["spent_total"],
            remaining=str(remaining) if remaining is not None else None,
            status=d["status"],
            revoked_at=d["revoked_at"],
            revoked_by=d["revoked_by"],
            revocation_reason=d["revocation_reason"],
            evidence=(
                EvidenceModel.from_evidence(dlg.evidence) if dlg.evidence else None
            ),
            created_at=d["created_at"],
        )


class ChainLinkModel(BaseModel):
    """One link in a resolved attenuated chain, root mandate first."""

    kind: str  # mandate | delegation
    ref: str
    depth: int
    amount_cap: str | None = None
    currency: str = ""
    scope_hash: str = ""
    status: str = ""


class ChainModel(BaseModel):
    """The full resolved chain for an acting delegatee (root mandate → leaf)."""

    delegatee: str
    depth: int  # number of delegation hops (chain length minus the root mandate)
    links: list[ChainLinkModel]


class VerifyEvidenceRequest(BaseModel):
    """A DelegationEvidence to verify INDEPENDENTLY from its own fields (HMAC)."""

    delegation_id: str
    delegator_kind: str
    delegator_ref: str
    delegator_principal: str
    delegatee: str
    root_mandate_id: str
    depth: int
    amount_cap: str | None = None
    currency: str = "USDC"
    expires_at: str | None = None
    scope_hash: str
    created_at: str
    decision_hash: str
    signature: str


class VerifyEvidenceResponse(BaseModel):
    valid: bool
    hash_matches: bool
    signature_matches: bool
    delegation_id: str
    detail: str


# ── Delegation endpoints (org-scoped) ───────────────────────────────────


@router.post("", response_model=DelegationModel, status_code=status.HTTP_201_CREATED)
async def create_delegation(
    body: CreateDelegationRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Mint an attenuated delegation — fail-closed if it does not narrow.

    Sardis owns the DECISION: the engine rejects (409) any grant whose cap,
    expiry, scope or depth would exceed/widen the delegator's CURRENT authority.
    On success returns the durable delegation + its signed DelegationEvidence,
    stamped with this org for tenant-scoped reads.
    """
    engine = _resolve_delegation_engine(request)
    try:
        dlg = await engine.delegate(
            delegator_ref=body.delegator_ref,
            delegator_kind=body.delegator_kind,
            delegatee=body.delegatee,
            delegator_principal=body.delegator_principal,
            amount_cap=_parse_amount(body.amount_cap),
            scope=body.scope.to_scope(),
            expires_at=_parse_expiry(body.expires_at),
            currency=body.currency,
            org_id=principal.organization_id,
            metadata={_ORG_KEY: principal.organization_id},
        )
    except DelegationError as exc:
        # Attenuation violated / delegator not found-or-active — DENY, no row.
        logger.info(
            "delegation mint denied (%s): %s violations=%s",
            exc.error_code, exc, exc.violations,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": str(exc),
                "error_code": exc.error_code,
                "violations": exc.violations,
            },
        ) from exc
    logger.info(
        "delegation minted %s by org=%s delegatee=%s depth=%d",
        dlg.id, principal.organization_id, dlg.delegatee, dlg.depth,
    )
    return DelegationModel.from_delegation(dlg)


@router.get("", response_model=list[DelegationModel])
async def list_delegations(
    request: Request,
    delegatee: str | None = Query(default=None, description="Filter to this sub-agent."),
    principal: Principal = Depends(require_principal),
):
    """List this org's delegations (optionally for one delegatee)."""
    engine = _resolve_delegation_engine(request)
    rows = await engine._store.list_for_org(
        organization_id=principal.organization_id, delegatee=delegatee
    )
    return [DelegationModel.from_delegation(d) for d in rows]


@router.get("/{delegation_id}", response_model=DelegationModel)
async def get_delegation(
    delegation_id: str,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Fetch one delegation hop + its signed evidence (org-scoped, 404 cross-org)."""
    engine = _resolve_delegation_engine(request)
    dlg = await _require_delegation_in_org(engine, delegation_id, principal)
    return DelegationModel.from_delegation(dlg)


@router.get("/agent/{agent_id}/chain", response_model=ChainModel)
async def get_agent_chain(
    agent_id: str,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Resolve the FULL attenuated chain for an acting sub-agent (root → leaf).

    Returns the ordered chain the orchestrator re-checks at execution time:
    root SpendingMandate first, then each delegation hop down to the leaf the
    agent holds.  An empty ``links`` means the agent holds no active delegation
    (it is not acting under delegated authority).
    """
    engine = _resolve_delegation_engine(request)
    chain = await engine.resolve_chain(agent_id)
    # Org-scope: the leaf delegation (if any) must belong to this org.
    if chain:
        leaf = chain[-1]
        if isinstance(leaf, Delegation):
            owner = (leaf.metadata or {}).get(_ORG_KEY) or leaf.org_id
            if owner != principal.organization_id:
                raise HTTPException(status_code=404, detail="no delegation chain for agent")
    links = [_link_model(link) for link in chain]
    return ChainModel(
        delegatee=agent_id,
        depth=max(0, len(links) - 1),
        links=links,
    )


def _link_model(link: Any) -> ChainLinkModel:
    """Reduce a chain link (root mandate or delegation hop) to its bound facts."""
    if isinstance(link, Delegation):
        return ChainLinkModel(
            kind="delegation",
            ref=link.id,
            depth=link.depth,
            amount_cap=str(link.amount_cap) if link.amount_cap is not None else None,
            currency=link.currency,
            scope_hash=link.scope.scope_hash(),
            status=link.status.value,
        )
    # SpendingMandate root (depth 0).
    cap = getattr(link, "amount_total", None)
    status_val = getattr(getattr(link, "status", None), "value", "")
    return ChainLinkModel(
        kind="mandate",
        ref=getattr(link, "id", ""),
        depth=0,
        amount_cap=str(cap) if cap is not None else None,
        currency=getattr(link, "currency", ""),
        scope_hash="",
        status=status_val,
    )


@router.post("/{delegation_id}/revoke")
async def revoke_delegation(
    delegation_id: str,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Revoke a delegation — PROPAGATES to the entire delegation subtree.

    Hands the kill to the SHARED RevocationEngine (the same instance the
    orchestrator denies revoked authority from): every descendant delegation is
    flipped to ``revoked`` and the execution-time chain re-check denies any
    payment under the subtree fail-closed.  Returns the signed proof-of-
    revocation.  Org-scoped: a delegation from another tenant 404s before any
    kill.
    """
    deleg_engine = _resolve_delegation_engine(request)
    # Org boundary FIRST: confirm the delegation belongs to this tenant (404 else).
    await _require_delegation_in_org(deleg_engine, delegation_id, principal)

    rev_engine = _resolve_revocation_engine(request)
    try:
        rev = await rev_engine.revoke(
            target_kind=RevocationTargetKind.DELEGATION,
            target_ref=delegation_id,
            requested_by=principal.user_id,
            reason="delegation revoked via API",
            scope="all",
            metadata={_ORG_KEY: principal.organization_id},
        )
    except Exception as exc:  # noqa: BLE001 - engine failure must not 200 silently
        logger.error("delegation revoke failed for %s: %s", delegation_id, exc)
        raise HTTPException(
            status_code=500, detail="delegation revocation propagation failed"
        ) from exc

    d = rev.to_dict()
    logger.info(
        "delegation %s revoked by %s (subtree propagated, outcome=%s)",
        delegation_id, principal.user_id, d.get("status"),
    )
    return {
        "delegation_id": delegation_id,
        "revocation": d,
        "proof": rev.proof.to_dict() if rev.proof is not None else None,
    }


@router.post("/verify", response_model=VerifyEvidenceResponse)
async def verify_delegation_evidence(body: VerifyEvidenceRequest):
    """Independently verify a DelegationEvidence from its own fields (HMAC).

    Recomputes the decision hash from the bound attenuated grant and checks the
    HMAC.  A tampered/widened grant breaks ``hash_matches``; a wrong/forged key
    breaks ``signature_matches``; ``valid`` requires both.  (This is the
    Sardis-internal tamper check; the PORTABLE, third-party offline credential is
    the Proof-of-Authority, verified at ``/api/v2/authority/proofs/verify``.)
    """
    ev = DelegationEvidence.from_dict(body.model_dump())
    hash_ok = ev.decision_hash == ev.compute_decision_hash()
    try:
        sig_ok = ev.signature == ev.compute_signature()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"cannot verify evidence: signing key unavailable ({exc})",
        ) from exc
    valid = hash_ok and sig_ok
    if valid:
        detail = "evidence is authentic: decision hash and signature both verify"
    elif not hash_ok:
        detail = "decision hash mismatch — attenuated grant or identity fields tampered"
    else:
        detail = "signature mismatch — wrong signing key or forged signature"
    return VerifyEvidenceResponse(
        valid=valid,
        hash_matches=hash_ok,
        signature_matches=sig_ok,
        delegation_id=ev.delegation_id,
        detail=detail,
    )


# ── Portable Proof-of-Authority endpoints (PUBLIC — offline verification) ─


class VerifyAuthorityProofRequest(BaseModel):
    """A Proof-of-Authority to verify offline.

    Supply EITHER ``proof`` (the structured JSON form, as emitted on a
    PaymentResult) OR ``jws`` (the compact ``<payload>.<signature>`` envelope).
    ``public_key`` is OPTIONAL: when omitted the server's published key is used
    (so a caller can sanity-check), but the WHOLE POINT is that a third party
    supplies their own copy of the published key and never trusts Sardis.
    """

    proof: dict[str, Any] | None = None
    jws: str | None = None
    public_key: str | None = Field(
        default=None,
        description="base64url/hex Ed25519 public key. Omitted = use the server's published key.",
    )


class VerifyAuthorityProofResponse(BaseModel):
    valid: bool
    proof_id: str
    action_id: str
    agent: str
    amount_minor: int
    currency: str
    counterparty: str
    decision: str
    delegation_depth: int
    detail: str


@public_router.post("/verify", response_model=VerifyAuthorityProofResponse)
async def verify_authority_proof(body: VerifyAuthorityProofRequest):
    """Offline-verify a portable Proof-of-Authority with a published key.

    PUBLIC by design: a merchant/auditor/regulator verifies that an agent was
    authorized for an exact action — under this policy + mandate + (attenuated)
    delegation chain — WITHOUT trusting or calling Sardis.  Verification
    recomputes the canonical claim from the bound fields (tampered/widened/
    truncated delegation hop ⇒ invalid) and checks the Ed25519 signature.
    """
    from sardis.core.authority_proof import AuthorityProof, public_key_bytes

    if not body.proof and not body.jws:
        raise HTTPException(status_code=422, detail="supply either 'proof' or 'jws'")
    try:
        proof = (
            AuthorityProof.from_jws(body.jws)
            if body.jws
            else AuthorityProof.from_dict(body.proof or {})
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"malformed proof: {exc}") from exc

    if body.public_key:
        pub: Any = body.public_key
    else:
        # Fall back to the server's published key (fail-closed in prod if unset).
        try:
            pub = public_key_bytes()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"no public key to verify against: {exc}",
            ) from exc

    valid = proof.verify(pub)
    return VerifyAuthorityProofResponse(
        valid=valid,
        proof_id=proof.proof_id,
        action_id=proof.action_id,
        agent=proof.agent,
        amount_minor=int(proof.amount_minor),
        currency=proof.currency,
        counterparty=proof.counterparty,
        decision=proof.decision,
        delegation_depth=max(0, len(proof.delegation_chain) - 1),
        detail=(
            "proof verifies: the action was authorized under the bound policy, "
            "mandate and delegation chain"
            if valid
            else "proof does NOT verify: tampered field/chain, wrong key, or non-ALLOWED decision"
        ),
    )


@public_router.get("/jwk")
async def authority_proof_jwk():
    """The PUBLISHED Ed25519 verification key for offline proof verification.

    Anyone can fetch this (or pin it from `.well-known`/docs) and verify a
    Proof-of-Authority without any Sardis access.  Possessing the public key
    grants verification, never forgery.
    """
    from sardis.core.authority_proof import public_jwk, public_key_b64url

    try:
        jwk = public_jwk()
        b64 = public_key_b64url()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail=f"authority-proof key unavailable: {exc}"
        ) from exc
    return {"jwk": jwk, "public_key_b64url": b64, "alg": "EdDSA", "crv": "Ed25519"}
