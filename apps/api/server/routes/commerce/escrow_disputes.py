"""Escrow and Dispute API endpoints — backed by real RecourseHolds.

Previously this surface was DB-only: it recorded escrow/dispute *rows* but moved
zero money, which was misleading. It is now backed onto the Programmable
Recourse primitive (:class:`sardis.core.recourse_engine.RecourseEngine`):

* creating an escrow opens a durable, signed :class:`RecourseHold` (the funds /
  claim are parked via the swappable executor — the vendored Circle
  RefundProtocol when ``SARDIS_RECOURSE_MODE=live``, a no-op otherwise);
* confirming delivery RELEASES the hold to the recipient (signed evidence);
* filing a dispute opens a recourse DISPUTE (auto-release paused);
* resolving a dispute settles down exactly one path (refund | release) with the
  reverse-transfer / withdrawal executed by the engine.

The DB ``disputes``/``evidence`` records remain for evidence collection, but the
*money decision* now flows through the single fail-closed recourse path. The
RecourseHold (not these rows) is the source of truth for hold state and amounts.

Escrow lifecycle:  held → released / refunded / disputed → resolved
Dispute lifecycle: FILED → EVIDENCE_COLLECTION → UNDER_REVIEW → RESOLVED_*
"""
from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from server.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)

# Default recourse/dispute window when a caller gives hours; converted to seconds
# for the engine. Bounded by the same 1h..720h range the API already accepted.


def _resolve_recourse_engine(request: Request):
    """Resolve the shared RecourseEngine wired in main.py.

    Fail-closed: if the engine is not configured, the escrow surface refuses
    rather than silently recording a DB row that moves no money (the exact bug
    this rework fixes)."""
    engine = getattr(request.app.state, "recourse_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="recourse engine unavailable; escrow holds cannot be created",
        )
    return engine


def _to_minor(amount: Decimal, *, decimals: int = 6) -> int:
    """USDC/EURC-style 6-decimal minor units. Exact via Decimal (no float)."""
    return int((amount * (Decimal(10) ** decimals)).to_integral_value())


# Metadata key under which the owning organization is stamped on a hold opened
# via this API surface, so reads/transitions can be org-scoped.
_ORG_KEY = "organization_id"


async def _require_hold_in_org(engine, hold_id: str, principal: Principal):
    """Fetch a hold and enforce org ownership — fail-closed.

    A hold opened through this API records the creator's ``organization_id`` in
    metadata; a caller from another org gets a 404 (not 403) so the surface does
    not even confirm the hold exists. Holds opened by the orchestrator (no org
    stamp) are not visible here, which is the intended boundary."""
    hold = await engine.get(hold_id)
    if hold is None:
        raise HTTPException(status_code=404, detail=f"escrow hold {hold_id} not found")
    owner = (hold.metadata or {}).get(_ORG_KEY)
    if owner != principal.organization_id:
        raise HTTPException(status_code=404, detail=f"escrow hold {hold_id} not found")
    return hold


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class CreateEscrowRequest(BaseModel):
    payment_object_id: str
    merchant_id: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USDC")
    timelock_hours: int = Field(default=72, ge=1, le=720)
    chain: str = Field(default="tempo")
    metadata: dict | None = None


class EscrowResponse(BaseModel):
    hold_id: str
    payment_object_id: str
    payer_id: str
    merchant_id: str
    amount: str
    currency: str
    chain: str
    status: str
    timelock_expires_at: str | None
    released_at: str | None
    delivery_confirmed_at: str | None
    created_at: str


class ConfirmDeliveryRequest(BaseModel):
    evidence: dict | None = None


class RefundEscrowRequest(BaseModel):
    # Optional partial-refund amount (<= held). Omit for a full refund of the
    # remaining balance. The engine enforces refund <= held (fail-closed).
    amount: Decimal | None = Field(default=None, gt=0)
    reason: str | None = None


class FileDisputeRequest(BaseModel):
    reason: str = Field(
        default="other",
        pattern="^(not_delivered|not_as_described|unauthorized|duplicate|service_quality|overcharge|other)$",
    )
    description: str | None = None


class DisputeResponse(BaseModel):
    dispute_id: str
    escrow_hold_id: str
    payment_object_id: str
    payer_id: str
    merchant_id: str
    reason: str
    description: str | None
    amount: str
    currency: str
    status: str
    evidence_count: int
    evidence_deadline: str | None
    resolved_at: str | None
    created_at: str


class SubmitEvidenceRequest(BaseModel):
    party: str = Field(..., pattern="^(payer|merchant)$")
    evidence_type: str = Field(..., description="screenshot, receipt, log, communication, other")
    content: dict = Field(default_factory=dict)
    description: str | None = None


class EvidenceResponse(BaseModel):
    evidence_id: str
    dispute_id: str
    submitted_by: str
    party: str
    evidence_type: str
    description: str | None
    created_at: str


class ResolveDisputeRequest(BaseModel):
    outcome: str = Field(..., pattern="^(resolved_refund|resolved_release|resolved_split)$")
    payer_amount: Decimal = Field(default=Decimal("0"), ge=0)
    merchant_amount: Decimal = Field(default=Decimal("0"), ge=0)
    reasoning: str | None = None


class ResolutionResponse(BaseModel):
    resolution_id: str
    dispute_id: str
    outcome: str
    resolved_by: str
    payer_amount: str
    merchant_amount: str
    reasoning: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Escrow Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/escrow",
    response_model=EscrowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an escrow hold",
)
async def create_escrow(
    req: CreateEscrowRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    engine = _resolve_recourse_engine(request)
    amount_minor = _to_minor(req.amount)
    try:
        hold = await engine.open_hold(
            payment_ref=req.payment_object_id,
            mandate_id=req.payment_object_id,
            agent_id=principal.user_id,
            amount=req.amount,
            amount_minor=amount_minor,
            currency=req.currency,
            payer=principal.user_id,
            recipient=req.merchant_id,
            window_seconds=req.timelock_hours * 3600,
            metadata={
                "chain": req.chain,
                _ORG_KEY: principal.organization_id,
                **(req.metadata or {}),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _recourse_to_response(hold)


@router.get(
    "/escrow",
    response_model=list[EscrowResponse],
    summary="List open escrow/recourse holds for the org",
)
async def list_escrow(
    request: Request,
    principal: Principal = Depends(require_principal),
    limit: int = 100,
) -> list[EscrowResponse]:
    """List non-terminal (``held``/``disputed``) holds owned by the caller's org.

    Org-scoped: only holds opened through this API with the caller's org stamp
    are returned. Terminal holds are excluded (use GET by id for those)."""
    engine = _resolve_recourse_engine(request)
    holds = await engine.list_open(limit=max(1, min(int(limit), 500)))
    mine = [
        h
        for h in holds
        if (h.metadata or {}).get(_ORG_KEY) == principal.organization_id
    ]
    return [_recourse_to_response(h) for h in mine]


@router.get(
    "/escrow/{hold_id}",
    response_model=EscrowResponse,
    summary="Get an escrow/recourse hold by id",
)
async def get_escrow(
    hold_id: str,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    engine = _resolve_recourse_engine(request)
    hold = await _require_hold_in_org(engine, hold_id, principal)
    return _recourse_to_response(hold)


@router.post(
    "/escrow/{hold_id}/refund",
    response_model=EscrowResponse,
    summary="Refund an escrow hold within its recourse window",
)
async def refund_escrow(
    hold_id: str,
    req: RefundEscrowRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    """Return funds to the payer WITHIN the window (full or partial).

    This is the direct refund leg of the recourse window — distinct from
    resolving a dispute. The engine reverse-transfers via the swappable executor
    and the domain enforces ``refund <= held`` (fail-closed). A released /
    refunded / disputed hold cannot be refunded here (409)."""
    from sardis.core.recourse_hold import RecourseAmountError, RecourseStateError

    engine = _resolve_recourse_engine(request)
    hold = await _require_hold_in_org(engine, hold_id, principal)
    if req.reason:
        hold.metadata["refund_reason"] = req.reason
    amount_minor = _to_minor(req.amount) if req.amount is not None else None
    try:
        refunded = await engine.refund(
            hold_id, amount_minor=amount_minor, actor=principal.user_id
        )
    except (RecourseStateError, RecourseAmountError) as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _recourse_to_response(refunded)


@router.post(
    "/escrow/{hold_id}/confirm-delivery",
    response_model=EscrowResponse,
    summary="Confirm delivery and release escrow",
)
async def confirm_delivery(
    hold_id: str,
    req: ConfirmDeliveryRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    from sardis.core.recourse_hold import RecourseStateError

    engine = _resolve_recourse_engine(request)
    hold = await _require_hold_in_org(engine, hold_id, principal)
    if req.evidence:
        hold.metadata["delivery_evidence"] = req.evidence
        hold.metadata["delivery_confirmed_by"] = principal.user_id
    try:
        # Confirming delivery RELEASES the held funds to the recipient. The
        # engine enforces no-double-release; a refunded/resolved hold raises.
        released = await engine.release(hold_id, actor=principal.user_id)
    except RecourseStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _recourse_to_response(released)


@router.post(
    "/escrow/{hold_id}/dispute",
    response_model=DisputeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="File a dispute on an escrow hold",
)
async def file_dispute(
    hold_id: str,
    req: FileDisputeRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> DisputeResponse:
    from sardis.core.database import Database
    from sardis.core.dispute import DisputeProtocol, DisputeReason
    from sardis.core.recourse_hold import RecourseStateError

    engine = _resolve_recourse_engine(request)
    hold = await _require_hold_in_org(engine, hold_id, principal)

    # Open a recourse DISPUTE on the real hold (auto-release paused; no money
    # moves until the dispute resolves down a single path).
    try:
        hold = await engine.dispute(
            hold_id,
            actor=principal.user_id,
            reason=req.description or req.reason,
        )
    except RecourseStateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Keep the DB dispute record for evidence collection (genuinely a record,
    # not a money decision — the money decision is on the RecourseHold).
    pool = await Database.get_pool()
    protocol = DisputeProtocol(pool)
    dispute = await protocol.file_dispute(
        escrow_hold_id=hold_id,
        payment_object_id=hold.payment_ref,
        payer_id=hold.payer,
        merchant_id=hold.recipient,
        filed_by=principal.user_id,
        reason=DisputeReason(req.reason),
        description=req.description,
        amount=hold.amount,
        currency=hold.currency,
    )
    return _dispute_to_response(dispute)


# ---------------------------------------------------------------------------
# Dispute Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/disputes/{dispute_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit evidence for a dispute",
)
async def submit_evidence(
    dispute_id: str,
    req: SubmitEvidenceRequest,
    principal: Principal = Depends(require_principal),
) -> EvidenceResponse:
    from sardis.core.database import Database
    from sardis.core.dispute import DisputeProtocol

    pool = await Database.get_pool()
    protocol = DisputeProtocol(pool)
    try:
        evidence = await protocol.submit_evidence(
            dispute_id=dispute_id,
            submitted_by=principal.user_id,
            party=req.party,
            evidence_type=req.evidence_type,
            content=req.content,
            description=req.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return EvidenceResponse(
        evidence_id=evidence.evidence_id,
        dispute_id=evidence.dispute_id,
        submitted_by=evidence.submitted_by,
        party=evidence.party,
        evidence_type=evidence.evidence_type,
        description=evidence.description,
        created_at=evidence.created_at.isoformat(),
    )


@router.post(
    "/disputes/{dispute_id}/resolve",
    response_model=ResolutionResponse,
    summary="Resolve a dispute",
)
async def resolve_dispute(
    dispute_id: str,
    req: ResolveDisputeRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
) -> ResolutionResponse:
    from sardis.core.database import Database
    from sardis.core.dispute import DisputeProtocol, DisputeStatus
    from sardis.core.recourse_hold import RecourseAmountError, RecourseStateError, Resolution

    pool = await Database.get_pool()

    # The DB dispute row links to the RecourseHold via escrow_hold_id; resolving
    # the dispute settles the REAL hold down a single fail-closed path. A
    # resolved_split is treated as a refund of payer_amount (the remainder stays
    # the recipient's), keeping the light primitive's single-resolution contract.
    drow = await Database.fetchrow(
        "SELECT escrow_hold_id FROM disputes WHERE dispute_id = $1", dispute_id
    )
    if not drow:
        raise HTTPException(status_code=404, detail="Dispute not found")
    hold_id = drow["escrow_hold_id"]

    engine = _resolve_recourse_engine(request)
    # Org-scope: the dispute's hold must belong to the caller's org (404 hides
    # cross-org holds, matching the rest of the surface).
    await _require_hold_in_org(engine, hold_id, principal)
    resolution = (
        Resolution.RELEASE if req.outcome == "resolved_release" else Resolution.REFUND
    )
    refund_minor = None
    if resolution == Resolution.REFUND and req.payer_amount > 0:
        refund_minor = _to_minor(req.payer_amount)
    try:
        await engine.resolve(
            hold_id,
            resolution=resolution,
            actor=principal.user_id,
            amount_minor=refund_minor,
        )
    except (RecourseStateError, RecourseAmountError) as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Record the resolution outcome on the DB dispute row (audit/evidence).
    protocol = DisputeProtocol(pool)
    try:
        resolution_rec = await protocol.resolve(
            dispute_id=dispute_id,
            outcome=DisputeStatus(req.outcome),
            resolved_by=principal.user_id,
            payer_amount=req.payer_amount,
            merchant_amount=req.merchant_amount,
            reasoning=req.reasoning,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return ResolutionResponse(
        resolution_id=resolution_rec.resolution_id,
        dispute_id=resolution_rec.dispute_id,
        outcome=resolution_rec.outcome.value,
        resolved_by=resolution_rec.resolved_by,
        payer_amount=str(resolution_rec.payer_amount),
        merchant_amount=str(resolution_rec.merchant_amount),
        reasoning=resolution_rec.reasoning,
        created_at=resolution_rec.created_at.isoformat(),
    )


@router.get(
    "/disputes/{dispute_id}",
    response_model=DisputeResponse,
    summary="Get a dispute by ID",
)
async def get_dispute(
    dispute_id: str,
    principal: Principal = Depends(require_principal),
) -> DisputeResponse:
    from sardis.core.database import Database

    row = await Database.fetchrow(
        "SELECT * FROM disputes WHERE dispute_id = $1", dispute_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return _dispute_row_to_response(row)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recourse_to_response(hold) -> EscrowResponse:
    """Map a :class:`RecourseHold` onto the legacy EscrowResponse shape so the
    API contract is unchanged while the money decision now flows through the
    real recourse path."""
    status_val = hold.status.value if hasattr(hold.status, "value") else hold.status
    return EscrowResponse(
        hold_id=hold.id,
        payment_object_id=hold.payment_ref,
        payer_id=hold.payer,
        merchant_id=hold.recipient,
        amount=str(hold.amount),
        currency=hold.currency,
        chain=str(hold.metadata.get("chain", "")) if hold.metadata else "",
        status=status_val,
        timelock_expires_at=hold.expires_at.isoformat() if hold.expires_at else None,
        released_at=hold.resolved_at.isoformat() if hold.resolved_at else None,
        delivery_confirmed_at=hold.resolved_at.isoformat() if hold.resolved_at else None,
        created_at=hold.opened_at.isoformat(),
    )


def _dispute_to_response(dispute) -> DisputeResponse:
    return DisputeResponse(
        dispute_id=dispute.dispute_id,
        escrow_hold_id=dispute.escrow_hold_id,
        payment_object_id=dispute.payment_object_id,
        payer_id=dispute.payer_id,
        merchant_id=dispute.merchant_id,
        reason=dispute.reason.value if hasattr(dispute.reason, "value") else dispute.reason,
        description=dispute.description,
        amount=str(dispute.amount),
        currency=dispute.currency,
        status=dispute.status.value if hasattr(dispute.status, "value") else dispute.status,
        evidence_count=dispute.evidence_count,
        evidence_deadline=dispute.evidence_deadline.isoformat() if dispute.evidence_deadline else None,
        resolved_at=dispute.resolved_at.isoformat() if dispute.resolved_at else None,
        created_at=dispute.created_at.isoformat(),
    )


def _dispute_row_to_response(row) -> DisputeResponse:
    return DisputeResponse(
        dispute_id=row["dispute_id"],
        escrow_hold_id=row["escrow_hold_id"],
        payment_object_id=row["payment_object_id"],
        payer_id=row["payer_id"],
        merchant_id=row["merchant_id"],
        reason=row["reason"],
        description=row.get("description"),
        amount=str(row["amount"]),
        currency=row["currency"],
        status=row["status"],
        evidence_count=row.get("evidence_count", 0),
        evidence_deadline=row["evidence_deadline"].isoformat() if row.get("evidence_deadline") else None,
        resolved_at=row["resolved_at"].isoformat() if row.get("resolved_at") else None,
        created_at=row["created_at"].isoformat(),
    )
