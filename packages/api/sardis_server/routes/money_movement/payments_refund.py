"""Refund endpoints for completed payments."""
from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_server.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class RefundRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Reason for the refund")
    amount: Decimal | None = Field(
        None, gt=0, description="Partial refund amount (omit for full refund)"
    )


class RefundResponse(BaseModel):
    refund_id: str
    payment_id: str
    amount: str
    currency: str
    reason: str
    status: str
    reverse_tx_hash: str | None
    error: str | None
    created_at: str
    completed_at: str | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{payment_id}/refund", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def initiate_refund(
    payment_id: str,
    request: RefundRequest,
    principal: Principal = Depends(require_principal),
) -> RefundResponse:
    """Initiate a full or partial refund for a completed payment."""
    from sardis_v2_core.database import Database
    from sardis_v2_core.notification_service import NotificationService
    from sardis_v2_core.refund import RefundService

    svc = RefundService(
        database=Database,
        notification_service=NotificationService(database=Database),
    )

    try:
        refund = await svc.initiate_refund(
            payment_id=payment_id,
            org_id=principal.organization_id,
            reason=request.reason,
            amount=request.amount,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "already been refunded" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        if "exceeds" in msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg
            )
        # Status not completed or other validation error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return RefundResponse(
        refund_id=refund.refund_id,
        payment_id=refund.payment_id,
        amount=str(refund.amount),
        currency=refund.currency,
        reason=refund.reason,
        status=refund.status.value,
        reverse_tx_hash=refund.reverse_tx_hash,
        error=refund.error,
        created_at=refund.created_at.isoformat(),
        completed_at=refund.completed_at.isoformat() if refund.completed_at else None,
    )


@router.get("/{payment_id}/refund", response_model=RefundResponse)
async def get_refund_status(
    payment_id: str,
    principal: Principal = Depends(require_principal),
) -> RefundResponse:
    """Get the refund status for a payment."""
    from sardis_v2_core.database import Database
    from sardis_v2_core.refund import RefundService

    svc = RefundService(database=Database)
    refund = await svc.get_refund(
        payment_id=payment_id,
        org_id=principal.organization_id,
    )

    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No refund found for payment {payment_id}",
        )

    return RefundResponse(
        refund_id=refund.refund_id,
        payment_id=refund.payment_id,
        amount=str(refund.amount),
        currency=refund.currency,
        reason=refund.reason,
        status=refund.status.value,
        reverse_tx_hash=refund.reverse_tx_hash,
        error=refund.error,
        created_at=refund.created_at.isoformat(),
        completed_at=refund.completed_at.isoformat() if refund.completed_at else None,
    )
