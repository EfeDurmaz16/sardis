"""Escrow and Dispute API endpoints.

Escrow lifecycle: HELD → CONFIRMING → RELEASED / DISPUTING
Dispute lifecycle: FILED → EVIDENCE_COLLECTION → UNDER_REVIEW → RESOLVED_*
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


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
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    from sardis_v2_core.database import Database
    from sardis_v2_core.escrow import EscrowManager

    pool = await Database.get_pool()
    manager = EscrowManager(pool)
    hold = await manager.create_hold(
        payment_object_id=req.payment_object_id,
        payer_id=principal.principal_id,
        merchant_id=req.merchant_id,
        amount=req.amount,
        currency=req.currency,
        timelock_hours=req.timelock_hours,
        chain=req.chain,
        metadata=req.metadata,
    )
    return _hold_to_response(hold)


@router.post(
    "/escrow/{hold_id}/confirm-delivery",
    response_model=EscrowResponse,
    summary="Confirm delivery and release escrow",
)
async def confirm_delivery(
    hold_id: str,
    req: ConfirmDeliveryRequest,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    from sardis_v2_core.database import Database
    from sardis_v2_core.escrow import EscrowManager

    pool = await Database.get_pool()
    manager = EscrowManager(pool)
    try:
        hold = await manager.confirm_delivery(
            hold_id=hold_id,
            confirmed_by=principal.principal_id,
            evidence=req.evidence,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _hold_to_response(hold)


@router.post(
    "/escrow/{hold_id}/dispute",
    response_model=DisputeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="File a dispute on an escrow hold",
)
async def file_dispute(
    hold_id: str,
    req: FileDisputeRequest,
    principal: Principal = Depends(require_principal),
) -> DisputeResponse:
    from sardis_v2_core.database import Database
    from sardis_v2_core.dispute import DisputeProtocol, DisputeReason
    from sardis_v2_core.escrow import EscrowManager

    pool = await Database.get_pool()

    # Mark escrow as disputing
    escrow_mgr = EscrowManager(pool)
    try:
        hold = await escrow_mgr.file_dispute(
            hold_id=hold_id,
            filed_by=principal.principal_id,
            reason=req.description or req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Create dispute record
    protocol = DisputeProtocol(pool)
    dispute = await protocol.file_dispute(
        escrow_hold_id=hold_id,
        payment_object_id=hold.payment_object_id,
        payer_id=hold.payer_id,
        merchant_id=hold.merchant_id,
        filed_by=principal.principal_id,
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
    from sardis_v2_core.database import Database
    from sardis_v2_core.dispute import DisputeProtocol

    pool = await Database.get_pool()
    protocol = DisputeProtocol(pool)
    try:
        evidence = await protocol.submit_evidence(
            dispute_id=dispute_id,
            submitted_by=principal.principal_id,
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
    principal: Principal = Depends(require_principal),
) -> ResolutionResponse:
    from sardis_v2_core.database import Database
    from sardis_v2_core.dispute import DisputeProtocol, DisputeStatus

    pool = await Database.get_pool()
    protocol = DisputeProtocol(pool)
    try:
        resolution = await protocol.resolve(
            dispute_id=dispute_id,
            outcome=DisputeStatus(req.outcome),
            resolved_by=principal.principal_id,
            payer_amount=req.payer_amount,
            merchant_amount=req.merchant_amount,
            reasoning=req.reasoning,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return ResolutionResponse(
        resolution_id=resolution.resolution_id,
        dispute_id=resolution.dispute_id,
        outcome=resolution.outcome.value,
        resolved_by=resolution.resolved_by,
        payer_amount=str(resolution.payer_amount),
        merchant_amount=str(resolution.merchant_amount),
        reasoning=resolution.reasoning,
        created_at=resolution.created_at.isoformat(),
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
    from sardis_v2_core.database import Database

    row = await Database.fetchrow(
        "SELECT * FROM disputes WHERE dispute_id = $1", dispute_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return _dispute_row_to_response(row)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hold_to_response(hold) -> EscrowResponse:
    return EscrowResponse(
        hold_id=hold.hold_id,
        payment_object_id=hold.payment_object_id,
        payer_id=hold.payer_id,
        merchant_id=hold.merchant_id,
        amount=str(hold.amount),
        currency=hold.currency,
        chain=hold.chain,
        status=hold.status.value if hasattr(hold.status, "value") else hold.status,
        timelock_expires_at=hold.timelock_expires_at.isoformat() if hold.timelock_expires_at else None,
        released_at=hold.released_at.isoformat() if hold.released_at else None,
        delivery_confirmed_at=hold.delivery_confirmed_at.isoformat() if hold.delivery_confirmed_at else None,
        created_at=hold.created_at.isoformat(),
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
