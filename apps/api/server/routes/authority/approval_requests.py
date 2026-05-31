"""Engine-side ApprovalRequest API — the routes the sardis-cloud Approvals page needs.

This is the API surface for the **new** human-in-the-loop engine (the ``apreq_``
:class:`~sardis.core.approval_request.ApprovalRequest`, distinct from the legacy
``appr_`` UI approvals served by :mod:`server.routes.authority.approvals`).  The
audit found the loop missing: an approvals UI existed, but
``requires_approval`` -> deliver -> approve -> **re-execute through the single
fail-closed path** was never wired.  These routes close it:

* ``GET  /api/v2/approval-requests``               — list pending requests
* ``GET  /api/v2/approval-requests/{id}``          — fetch one (with evidence)
* ``POST /api/v2/approval-requests/{id}/decision`` — record approve/deny and, on
  approve, RE-EXECUTE the payment through the orchestrator's single fail-closed
  path (mandate / policy / compliance / revocation are ALL re-checked).

Hard rules honored here:

* **Sardis owns the decision.**  The route records the human's decision as
  signed evidence via the :class:`~sardis.core.approval_gate.ApprovalGate`, then
  hands re-execution back to the :class:`PaymentOrchestrator`.  Delivery
  (Twilio / Photon) never decides — it only relays a decision *into* this route.
* **The approver is verified.**  The decision is attributed to the authenticated
  :class:`~server.authz.Principal` (``require_principal``), not to a value in the
  request body.  An anonymous/forged decision can never move money.
* **High-value step-up.**  When a request ``requires_step_up`` (high-value), the
  engine refuses to record an approval without ``step_up_verified`` — the route
  surfaces that as a ``409`` so the UI can run the OTP step before retrying.
* **Fail-closed.**  Denied / expired / already-re-executed requests are not
  executable; the orchestrator raises and the route returns ``409`` without
  moving money.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sardis.core.approval_gate import ApprovalGate
from sardis.core.approval_request import ApprovalState, DecisionChannel
from sardis.core.orchestrator import PaymentExecutionError

from server.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


# ── Dependency injection ────────────────────────────────────────────────


@dataclass
class ApprovalRequestDependencies:
    """Engine collaborators for the ApprovalRequest API.

    ``gate`` owns the durable signed store + decision recording; ``orchestrator``
    owns the single fail-closed re-execution path.  Both are the SAME instances
    the orchestrator uses, so a decision recorded here is the decision the
    re-execution reads.
    """

    gate: ApprovalGate
    orchestrator: Any  # PaymentOrchestrator (avoid import cycle on type)


_deps: ApprovalRequestDependencies | None = None


def get_deps() -> ApprovalRequestDependencies:
    if _deps is None:
        raise RuntimeError("ApprovalRequest dependencies not injected")
    return _deps


def set_deps(deps: ApprovalRequestDependencies | None) -> None:
    """Wire (or clear) the module-level dependencies. Used by the registry/tests."""
    global _deps
    _deps = deps


# ── Models ──────────────────────────────────────────────────────────────


class EvidenceModel(BaseModel):
    decision: str
    approver: str
    channel: str
    decided_at: datetime | None = None
    request_hash: str
    policy_hash: str
    mandate_hash: str
    decision_hash: str
    signature: str
    step_up_verified: bool = False


class ApprovalRequestModel(BaseModel):
    id: str
    agent_id: str | None = None
    mandate_id: str | None = None
    spending_mandate_id: str | None = None
    amount: Decimal
    currency: str
    counterparty: str | None = None
    reason: str
    status: str
    requested_at: datetime
    expires_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    requires_step_up: bool = False
    reexecuted: bool = False
    evidence: EvidenceModel | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def from_request(req: Any) -> ApprovalRequestModel:
        d = req.to_dict()
        ev = d.get("evidence")
        return ApprovalRequestModel(
            id=d["id"],
            agent_id=d["agent_id"],
            mandate_id=d["mandate_id"],
            spending_mandate_id=d["spending_mandate_id"],
            amount=Decimal(d["amount"]),
            currency=d["currency"],
            counterparty=d["counterparty"],
            reason=d["reason"],
            status=d["status"],
            requested_at=datetime.fromisoformat(d["requested_at"]),
            expires_at=datetime.fromisoformat(d["expires_at"]),
            decided_by=d["decided_by"],
            decided_at=(
                datetime.fromisoformat(d["decided_at"]) if d["decided_at"] else None
            ),
            requires_step_up=d["requires_step_up"],
            reexecuted=d["reexecuted"],
            evidence=(
                EvidenceModel(
                    decision=ev["decision"],
                    approver=ev["approver"],
                    channel=ev["channel"],
                    decided_at=(
                        datetime.fromisoformat(ev["decided_at"])
                        if ev.get("decided_at")
                        else None
                    ),
                    request_hash=ev["request_hash"],
                    policy_hash=ev["policy_hash"],
                    mandate_hash=ev["mandate_hash"],
                    decision_hash=ev["decision_hash"],
                    signature=ev["signature"],
                    step_up_verified=ev.get("step_up_verified", False),
                )
                if ev
                else None
            ),
            metadata=d.get("metadata") or {},
        )


class ApprovalRequestListResponse(BaseModel):
    requests: list[ApprovalRequestModel]
    total: int
    limit: int


class DecisionRequest(BaseModel):
    """A human decision relayed into the engine.

    The approver is taken from the authenticated principal, NOT from the body —
    so the body only carries the verb, an optional denial reason, the inbound
    channel for audit, and an optional OTP for high-value step-up.
    """

    decision: str = Field(
        ...,
        description="approve | deny",
        examples=["approve", "deny"],
    )
    reason: str | None = Field(
        default=None, description="Reason (recommended for denials)"
    )
    channel: DecisionChannel = Field(
        default=DecisionChannel.DASHBOARD,
        description="Where the decision was relayed from (audit only).",
    )
    step_up_verified: bool = Field(
        default=False,
        description=(
            "True only when an OTP/step-up was verified out-of-band for a "
            "high-value request. The engine refuses to approve a step-up "
            "request without this."
        ),
    )


class DecisionResponse(BaseModel):
    """Result of recording a decision (and, on approve, re-executing)."""

    request: ApprovalRequestModel
    executed: bool = False
    #: Populated on a successful re-execution.
    payment_status: str | None = None
    chain_tx_hash: str | None = None
    ledger_tx_id: str | None = None
    mandate_id: str | None = None
    #: Populated when re-execution was blocked fail-closed (e.g. revoked).
    blocked_reason: str | None = None


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("", response_model=ApprovalRequestListResponse)
async def list_pending_requests(
    limit: int = Query(default=50, ge=1, le=200),
    deps: ApprovalRequestDependencies = Depends(get_deps),
):
    """List pending approval requests for the human review queue.

    Returns the durable, signed requests still awaiting a decision, oldest
    first.  This is the feed the sardis-cloud Approvals page polls.
    """
    pending = await deps.gate._store.list_pending(limit=limit)
    return ApprovalRequestListResponse(
        requests=[ApprovalRequestModel.from_request(r) for r in pending],
        total=len(pending),
        limit=limit,
    )


@router.get("/{approval_id}", response_model=ApprovalRequestModel)
async def get_request(
    approval_id: str,
    deps: ApprovalRequestDependencies = Depends(get_deps),
):
    """Fetch a single approval request, including signed decision evidence."""
    req = await deps.gate.get(approval_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"approval request {approval_id} not found",
        )
    return ApprovalRequestModel.from_request(req)


@router.post("/{approval_id}/decision", response_model=DecisionResponse)
async def record_decision(
    approval_id: str,
    body: DecisionRequest,
    principal: Principal = Depends(require_principal),
    deps: ApprovalRequestDependencies = Depends(get_deps),
):
    """Record a human decision and, on approve, re-execute the payment.

    Closes the loop:

    1. The decision is attributed to the authenticated principal and recorded as
       signed evidence (the engine fails closed on expired requests and on
       missing step-up for high-value).
    2. On **approve**, the payment is re-executed through the orchestrator's
       single fail-closed path — mandate / policy / compliance / revocation are
       all re-checked, so a request approved before a revocation is STILL blocked
       at re-execution.  Idempotent: a duplicate approve cannot settle twice.
    3. On **deny**, the denial + evidence is recorded; no money moves.
    """
    req = await deps.gate.get(approval_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"approval request {approval_id} not found",
        )

    approver = principal.user_id

    # 1) Record the decision (signed evidence). Fail-closed on illegal state.
    try:
        decided = await deps.gate.record_decision(
            approval_id=approval_id,
            decision=body.decision,
            approver=approver,
            channel=body.channel,
            step_up_verified=body.step_up_verified,
            reason=body.reason,
        )
    except ValueError as exc:
        # Unknown verb or not-found -> client error.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:  # ApprovalStateError etc. (e.g. step-up required)
        # The engine refuses (e.g. high-value approval without OTP step-up, or a
        # terminal request). Surface as a conflict so the UI can run step-up.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    model = ApprovalRequestModel.from_request(decided)

    # 2) Not an approval -> nothing to execute; return the recorded decision.
    if decided.status != ApprovalState.APPROVED:
        logger.info(
            "approval %s recorded as %s by %s",
            approval_id, decided.status.value, approver,
        )
        return DecisionResponse(request=model, executed=False)

    # 3) Approved -> re-execute through the single fail-closed path.
    try:
        result = await deps.orchestrator.execute_on_approval(approval_id)
    except PaymentExecutionError as exc:
        # Fail-closed: e.g. mandate revoked after approval, or already
        # re-executed. No money moved. Return the (now approved) request plus the
        # block reason so the UI shows why settlement did not proceed.
        logger.warning(
            "approval %s re-execution blocked fail-closed: %s", approval_id, exc
        )
        refreshed = await deps.gate.get(approval_id)
        return DecisionResponse(
            request=ApprovalRequestModel.from_request(refreshed or decided),
            executed=False,
            blocked_reason=str(exc),
        )

    refreshed = await deps.gate.get(approval_id)
    logger.info(
        "approval %s approved by %s and re-executed: status=%s tx=%s",
        approval_id, approver, result.status, result.chain_tx_hash,
    )
    return DecisionResponse(
        request=ApprovalRequestModel.from_request(refreshed or decided),
        executed=True,
        payment_status=result.status,
        chain_tx_hash=result.chain_tx_hash or None,
        ledger_tx_id=result.ledger_tx_id or None,
        mandate_id=result.mandate_id or None,
    )


@router.post("/expire", response_model=dict)
async def sweep_expired(
    deps: ApprovalRequestDependencies = Depends(get_deps),
):
    """Expire all past-deadline pending requests (fail-closed).

    Intended for a periodic background job. Expired requests are terminal and
    can never be re-executed.
    """
    count = await deps.gate.sweep_expired()
    return {"success": True, "expired_count": count}
