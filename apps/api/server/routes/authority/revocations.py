"""Propagating-Revocation API — the lead-wedge kill switch surface.

One revoke must ATOMICALLY propagate across EVERY rail — freeze the agent's
cards, revoke its outstanding spend objects / one-time passes, deny its pending
approvals + in-flight payments, mark the mandate revoked — and return a SIGNED,
INDEPENDENTLY-VERIFIABLE proof-of-revocation listing exactly what was killed and
when.  No single rail-owner can build this: it requires neutrality across all
rails.  Sardis owns the revocation DECISION and its signed proof (the moat);
the per-rail kill is swappable execution wired in
:func:`server.dependencies.build_revocation_engine`.

This module exposes the three routes the product/UI consumes:

* ``POST /api/v2/revocations`` — revoke an agent / mandate / principal.  Returns
  the propagation SUMMARY (N cards frozen, M spend objects killed, K pending
  approvals + in-flight blocked, mandates revoked) plus the signed
  :class:`~sardis.core.revocation.RevocationProof`.
* ``GET  /api/v2/revocations``        — list this org's recent revocations.
* ``GET  /api/v2/revocations/{id}``   — fetch one revocation + its proof.
* ``POST /api/v2/revocations/verify`` — INDEPENDENTLY verify a proof from its
  own fields (no live lookup): recompute the decision hash and check the HMAC.

Hard rules honored here:

* **Sardis owns the decision + proof.**  The route hands the kill to the shared
  :class:`~sardis.core.revocation_engine.RevocationEngine` (the SAME instance the
  orchestrator denies revoked mandates from) and returns its signed proof.  The
  caller never supplies the proof or the kill outcomes.
* **Fail-closed.**  If the engine is not configured, the surface returns ``503``
  rather than silently doing nothing.  A partial propagation is reported as
  ``blocked_pending_downstream`` — NEVER as fully ``propagated`` — and the proof
  lists each rail's honest ``kill_status``.  The authority is still denied at
  execution time (the mandate is revoked), so no authority stays silently alive.
* **Auth + org-scope.**  The actor is the authenticated
  :class:`~server.authz.Principal`; the owning ``organization_id`` is stamped
  into the revocation so a caller from another org cannot read it (404, not 403).
* **Idempotent.**  A re-revoke of an already-revoked target returns the SAME
  revocation + proof without re-propagating.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sardis.core.revocation import (
    KillStatus,
    PropagationKind,
    Revocation,
    RevocationProof,
    RevocationTargetKind,
)

from server.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])

# Metadata key under which the owning org is stamped on a revocation opened via
# this API surface, so reads are org-scoped (mirrors the escrow/recourse surface).
_ORG_KEY = "organization_id"


# ── Engine resolution (fail-closed) ────────────────────────────────────


def _resolve_revocation_engine(request: Request):
    """Resolve the shared RevocationEngine wired in main.py.

    Fail-closed: if the engine is not configured, the surface refuses (503)
    rather than pretend a kill happened.  The orchestrator's execution-time
    mandate denial is a separate backstop, but the kill-switch API itself must
    never claim success it did not perform."""
    engine = getattr(request.app.state, "revocation_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="revocation engine unavailable; kill switch cannot propagate",
        )
    return engine


async def _require_revocation_in_org(
    engine: Any, revocation_id: str, principal: Principal
) -> Revocation:
    """Fetch a revocation and enforce org ownership — fail-closed.

    A revocation created through this API records the actor's
    ``organization_id`` in metadata; a caller from another org gets a 404 (not
    403) so the surface does not even confirm the revocation exists.  A
    revocation with no org stamp (e.g. a system kill) is also invisible here,
    which is the intended tenant boundary."""
    rev = await engine.get(revocation_id)
    if rev is None:
        raise HTTPException(
            status_code=404, detail=f"revocation {revocation_id} not found"
        )
    owner = (rev.metadata or {}).get(_ORG_KEY)
    if owner != principal.organization_id:
        raise HTTPException(
            status_code=404, detail=f"revocation {revocation_id} not found"
        )
    return rev


# ── Models ──────────────────────────────────────────────────────────────


class RevokeRequest(BaseModel):
    """Request ONE atomic kill across every rail.

    The actor is the authenticated principal (not the body), so a forged
    ``requested_by`` cannot move tenancy or attribution.
    """

    target_kind: RevocationTargetKind = Field(
        default=RevocationTargetKind.AGENT,
        description="agent | mandate | principal — what authority to kill.",
        examples=["agent", "mandate"],
    )
    target_ref: str = Field(
        ...,
        description="The agent_id / mandate_id / principal_id to revoke.",
        examples=["agent_kill_me"],
    )
    reason: str = Field(default="", description="Why (recorded in the proof's metadata).")
    scope: str = Field(
        default="all",
        description="Free-text/structured scope of the kill (default 'all' rails).",
    )
    agent_id: str | None = Field(
        default=None,
        description=(
            "Optional hint to reach agent-scoped rails (cards, approvals, "
            "in-flight) when revoking a MANDATE (a mandate carries an agent)."
        ),
    )


class PropagationTargetModel(BaseModel):
    """One derived authority the kill touched, and its honest outcome."""

    kind: str  # PropagationKind value
    ref: str
    kill_status: str  # KillStatus value
    detail: str = ""
    killed_at: str | None = None


class RevocationProofModel(BaseModel):
    """The signed, independently-verifiable proof-of-revocation.

    Self-contained: every field needed to recompute the ``decision_hash`` and
    check the HMAC ``signature`` is carried here, so an auditor can verify it
    offline (POST it back to ``/verify``) with no live-system access.
    """

    revocation_id: str
    target_kind: str
    target_ref: str
    scope: str
    requested_by: str
    revoked_at: str
    outcome: str
    targets: list[dict[str, Any]]
    decision_hash: str
    signature: str

    @staticmethod
    def from_proof(proof: RevocationProof) -> RevocationProofModel:
        return RevocationProofModel(**proof.to_dict())


class PropagationSummary(BaseModel):
    """The headline the UI shows: exactly what one revoke killed, per rail.

    ``confirmed_dead`` counts targets confirmed gone on their own rail
    (``killed`` / ``already_dead``).  ``blocked_pending`` counts targets the kill
    could not confirm downstream — those are STILL denied at execution time (the
    mandate is revoked) but are honestly NOT reported as dead.  The per-rail
    counts (cards / spend objects / approvals / in-flight / mandates) let the UI
    render "N cards frozen, M spend objects killed, K pending blocked".
    """

    outcome: str  # propagated | blocked_pending_downstream
    fully_propagated: bool
    total_targets: int
    confirmed_dead: int
    blocked_pending: int
    mandates_revoked: int
    cards_frozen: int
    spend_objects_killed: int
    approvals_blocked: int
    in_flight_blocked: int


class RevocationModel(BaseModel):
    """A durable revocation decision + the full propagation record + its proof."""

    id: str
    target_kind: str
    target_ref: str
    scope: str
    requested_by: str
    requested_at: str
    status: str
    revoked_at: str | None = None
    targets: list[PropagationTargetModel]
    summary: PropagationSummary
    proof: RevocationProofModel | None = None

    @staticmethod
    def from_revocation(rev: Revocation) -> RevocationModel:
        d = rev.to_dict()
        return RevocationModel(
            id=d["id"],
            target_kind=d["target_kind"],
            target_ref=d["target_ref"],
            scope=d["scope"],
            requested_by=d["requested_by"],
            requested_at=d["requested_at"],
            status=d["status"],
            revoked_at=d["revoked_at"],
            targets=[PropagationTargetModel(**t) for t in d["targets"]],
            summary=_summarize(rev),
            proof=(
                RevocationProofModel.from_proof(rev.proof)
                if rev.proof is not None
                else None
            ),
        )


class RevokeResponse(BaseModel):
    """What ``POST /revocations`` returns: the summary + the signed proof.

    ``idempotent_replay`` is True when the target was already revoked and this
    call returned the existing revocation without re-propagating.
    """

    revocation: RevocationModel
    summary: PropagationSummary
    proof: RevocationProofModel | None = None
    idempotent_replay: bool = False


class VerifyProofRequest(BaseModel):
    """A proof to verify INDEPENDENTLY from its own fields (no live lookup).

    Carries exactly the proof shape ``RevocationProofModel`` returns, so a UI /
    auditor can round-trip a stored proof straight back into ``/verify``.
    """

    revocation_id: str
    target_kind: str
    target_ref: str
    scope: str
    requested_by: str
    revoked_at: str
    outcome: str
    targets: list[dict[str, Any]]
    decision_hash: str
    signature: str


class VerifyProofResponse(BaseModel):
    """Result of independent verification.

    ``valid`` is the bottom line: the bound fields recompute to the carried
    ``decision_hash`` AND the HMAC matches.  ``hash_matches`` /
    ``signature_matches`` split the two checks so a tampered target list (hash
    fails) is distinguishable from a wrong/forged key (signature fails)."""

    valid: bool
    hash_matches: bool
    signature_matches: bool
    revocation_id: str
    outcome: str
    detail: str


# ── Summary derivation ─────────────────────────────────────────────────

_CONFIRMED = {KillStatus.KILLED.value, KillStatus.ALREADY_DEAD.value}


def _summarize(rev: Revocation) -> PropagationSummary:
    """Derive the per-rail propagation summary from the recorded targets.

    Counts only CONFIRMED-dead targets toward the per-rail "killed/frozen"
    headline (``killed`` / ``already_dead``); a ``blocked_pending`` / ``failed``
    target is counted in ``blocked_pending``, never as frozen, so the UI never
    over-claims."""
    targets = [t.to_dict() for t in rev.targets]

    def confirmed(kind: PropagationKind) -> int:
        return sum(
            1
            for t in targets
            if t["kind"] == kind.value and t["kill_status"] in _CONFIRMED
        )

    confirmed_dead = sum(1 for t in targets if t["kill_status"] in _CONFIRMED)
    blocked = len(targets) - confirmed_dead
    return PropagationSummary(
        outcome=rev.status.value,
        fully_propagated=not rev.has_unconfirmed(),
        total_targets=len(targets),
        confirmed_dead=confirmed_dead,
        blocked_pending=blocked,
        mandates_revoked=confirmed(PropagationKind.MANDATE),
        cards_frozen=confirmed(PropagationKind.CARD),
        spend_objects_killed=confirmed(PropagationKind.SPEND_OBJECT),
        approvals_blocked=confirmed(PropagationKind.APPROVAL),
        in_flight_blocked=confirmed(PropagationKind.IN_FLIGHT),
    )


# ── Endpoints ───────────────────────────────────────────────────────────


@router.post("", response_model=RevokeResponse, status_code=status.HTTP_200_OK)
async def revoke(
    body: RevokeRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Atomically propagate a revocation across every rail; return summary + proof.

    ONE kill switch across card, crypto, and every protocol.  The engine marks
    the mandate(s) revoked (the authority root — the orchestrator denies on it at
    execution time), freezes the agent's cards, revokes outstanding spend
    objects, denies pending approvals, and blocks in-flight payments — recording
    each as a target with its honest ``kill_status`` — then signs a
    :class:`RevocationProof`.

    Fail-closed: a downstream kill that cannot be confirmed is ``blocked_pending``
    and the overall outcome is ``blocked_pending_downstream`` (never
    ``propagated``); the authority is still denied at execution.  Idempotent: a
    re-revoke returns the same revocation + proof."""
    engine = _resolve_revocation_engine(request)

    # Detect an idempotent replay so the UI can tell "killed now" from "already
    # killed": the engine returns the SAME revocation for an already-revoked
    # target. We check the store BEFORE the call (the engine itself is idempotent).
    pre_existing = None
    try:
        pre_existing = await engine._store.get_active_for_target(
            target_kind=body.target_kind.value, target_ref=body.target_ref
        )
    except Exception:  # noqa: BLE001 - replay detection is best-effort, not load-bearing
        pre_existing = None

    try:
        rev = await engine.revoke(
            target_kind=body.target_kind,
            target_ref=body.target_ref,
            requested_by=principal.user_id,
            reason=body.reason,
            scope=body.scope,
            agent_id=body.agent_id,
            metadata={_ORG_KEY: principal.organization_id},
        )
    except Exception as exc:  # noqa: BLE001 - engine failure must not 200 silently
        logger.error(
            "revocation failed for %s/%s: %s",
            body.target_kind.value, body.target_ref, exc,
        )
        raise HTTPException(
            status_code=500, detail="revocation propagation failed"
        ) from exc

    replay = pre_existing is not None and pre_existing.id == rev.id

    # Org boundary on the idempotent-replay path: an existing revocation created
    # by another org must not be readable/returned here. A fresh kill always
    # carries this org's stamp, so this only guards the replay case.
    owner = (rev.metadata or {}).get(_ORG_KEY)
    if replay and owner != principal.organization_id:
        raise HTTPException(
            status_code=409,
            detail=(
                f"target {body.target_ref} already revoked by another tenant; "
                "cannot return its proof"
            ),
        )

    model = RevocationModel.from_revocation(rev)
    logger.info(
        "revocation %s by %s: target=%s/%s outcome=%s confirmed=%d/%d replay=%s",
        rev.id, principal.user_id, body.target_kind.value, body.target_ref,
        model.summary.outcome, model.summary.confirmed_dead,
        model.summary.total_targets, replay,
    )
    return RevokeResponse(
        revocation=model,
        summary=model.summary,
        proof=model.proof,
        idempotent_replay=replay,
    )


@router.get("", response_model=list[RevocationModel])
async def list_revocations(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(require_principal),
):
    """List this org's recent revocations (newest first), each with its proof."""
    engine = _resolve_revocation_engine(request)
    recent = await engine.list_recent(limit=limit)
    mine = [
        r for r in recent if (r.metadata or {}).get(_ORG_KEY) == principal.organization_id
    ]
    return [RevocationModel.from_revocation(r) for r in mine]


@router.get("/{revocation_id}", response_model=RevocationModel)
async def get_revocation(
    revocation_id: str,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Fetch one revocation + its full propagation record and signed proof."""
    engine = _resolve_revocation_engine(request)
    rev = await _require_revocation_in_org(engine, revocation_id, principal)
    return RevocationModel.from_revocation(rev)


@router.post("/verify", response_model=VerifyProofResponse)
async def verify_proof(body: VerifyProofRequest):
    """Independently verify a proof-of-revocation from its own fields.

    No live lookup, no org scope: a proof is self-contained and verifiable by
    anyone holding the HMAC key, so this endpoint reconstructs the
    :class:`RevocationProof` from the posted fields and recomputes both the
    decision hash and the HMAC.  This is the auditor's check: a tampered or
    truncated target list breaks ``hash_matches``; a wrong/forged signature or
    key breaks ``signature_matches``; ``valid`` requires both."""
    proof = RevocationProof.from_dict(body.model_dump())
    hash_ok = proof.decision_hash == proof.compute_decision_hash()
    # verify() short-circuits on a hash mismatch; compute the signature check
    # independently so the response can attribute the failure precisely.
    try:
        sig_ok = proof.signature == proof.compute_signature()
    except RuntimeError as exc:
        # Signing key not configured (fail-closed in prod) — cannot verify.
        raise HTTPException(
            status_code=503,
            detail=f"cannot verify proof: signing key unavailable ({exc})",
        ) from exc
    valid = hash_ok and sig_ok
    if valid:
        detail = "proof is authentic: decision hash and signature both verify"
    elif not hash_ok:
        detail = "decision hash mismatch — target list or identity fields tampered"
    else:
        detail = "signature mismatch — wrong signing key or forged signature"
    return VerifyProofResponse(
        valid=valid,
        hash_matches=hash_ok,
        signature_matches=sig_ok,
        revocation_id=proof.revocation_id,
        outcome=proof.outcome,
        detail=detail,
    )
