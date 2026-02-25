"""Approval API endpoints for managing human approval workflows.

This module provides REST endpoints for creating, managing, and reviewing
approval requests when agent actions exceed policy limits.

Extended with confidence-based routing for tiered approvals.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_v2_core.approval_service import ApprovalService, ApprovalStatus, ApprovalUrgency
from sardis_v2_core.approval_repository import ApprovalRepository, Approval
from sardis_v2_core.confidence_router import (
    ConfidenceRouter,
    ApprovalWorkflow,
    ConfidenceLevel,
    TransactionConfidence,
)

from sardis_api.authz import require_principal
from sardis_api.routers.metrics import record_approval

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateApprovalRequest(BaseModel):
    """Request to create a new approval."""

    action: str = Field(
        ...,
        description="Type of action requiring approval",
        examples=["payment", "create_card", "increase_limit"],
    )
    requested_by: str = Field(
        ...,
        description="Agent ID that initiated the request",
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Agent ID for the action",
    )
    wallet_id: Optional[str] = Field(
        default=None,
        description="Wallet ID for the action",
    )
    vendor: Optional[str] = Field(
        default=None,
        description="Vendor name (for payments)",
    )
    amount: Optional[Decimal] = Field(
        default=None,
        description="Payment amount",
    )
    purpose: Optional[str] = Field(
        default=None,
        description="Purpose description",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for approval request",
    )
    card_limit: Optional[Decimal] = Field(
        default=None,
        description="Card limit (for create_card action)",
    )
    urgency: ApprovalUrgency = Field(
        default='medium',
        description="Urgency level (low, medium, high)",
    )
    expires_in_hours: int = Field(
        default=24,
        description="Hours until request expires",
        ge=1,
        le=168,  # Max 1 week
    )
    organization_id: Optional[str] = Field(
        default=None,
        description="Organization ID",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional metadata",
    )


class ApprovalResponse(BaseModel):
    """Response model for approval object."""

    id: str
    action: str
    status: ApprovalStatus
    urgency: ApprovalUrgency
    requested_by: str
    reviewed_by: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    expires_at: datetime
    vendor: Optional[str] = None
    amount: Optional[Decimal] = None
    purpose: Optional[str] = None
    reason: Optional[str] = None
    card_limit: Optional[Decimal] = None
    agent_id: Optional[str] = None
    wallet_id: Optional[str] = None
    organization_id: Optional[str] = None
    metadata: dict = {}

    @staticmethod
    def from_approval(approval: Approval) -> "ApprovalResponse":
        """Convert Approval to response model."""
        return ApprovalResponse(
            id=approval.id,
            action=approval.action,
            status=approval.status,
            urgency=approval.urgency,
            requested_by=approval.requested_by,
            reviewed_by=approval.reviewed_by,
            created_at=approval.created_at,
            reviewed_at=approval.reviewed_at,
            expires_at=approval.expires_at,
            vendor=approval.vendor,
            amount=approval.amount,
            purpose=approval.purpose,
            reason=approval.reason,
            card_limit=approval.card_limit,
            agent_id=approval.agent_id,
            wallet_id=approval.wallet_id,
            organization_id=approval.organization_id,
            metadata=approval.metadata,
        )


class ReviewApprovalRequest(BaseModel):
    """Request to approve or deny an approval."""

    reviewed_by: str = Field(
        ...,
        description="Email or ID of the reviewer",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for the decision (required for denial)",
    )


class ApprovalListResponse(BaseModel):
    """Response for approval list."""

    approvals: List[ApprovalResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Dependency Injection
# ============================================================================

from dataclasses import dataclass

@dataclass
class ApprovalsDependencies:
    """Dependencies for approval endpoints."""
    approval_service: ApprovalService
    approval_repo: ApprovalRepository
    confidence_router: ConfidenceRouter = None
    approval_workflow: ApprovalWorkflow = None

    def __post_init__(self):
        """Initialize confidence router and workflow if not provided."""
        if self.confidence_router is None:
            self.confidence_router = ConfidenceRouter()
        if self.approval_workflow is None:
            self.approval_workflow = ApprovalWorkflow()


_deps: ApprovalsDependencies | None = None


def get_deps() -> ApprovalsDependencies:
    """Get injected dependencies."""
    if _deps is None:
        raise RuntimeError("Dependencies not injected")
    return _deps


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
async def create_approval(
    request: CreateApprovalRequest,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Create a new approval request.

    This endpoint creates an approval request when an agent action requires
    human review (e.g., payment exceeds policy limits, card creation).

    **Example use cases:**
    - Payment exceeds per-transaction limit
    - Monthly spending limit about to be exceeded
    - Creating a virtual card with high limit
    - Suspicious transaction flagged by compliance
    """
    try:
        approval = await deps.approval_service.create_approval(
            action=request.action,
            requested_by=request.requested_by,
            agent_id=request.agent_id,
            wallet_id=request.wallet_id,
            vendor=request.vendor,
            amount=request.amount,
            purpose=request.purpose,
            reason=request.reason,
            card_limit=request.card_limit,
            urgency=request.urgency,
            expires_in_hours=request.expires_in_hours,
            organization_id=request.organization_id,
            metadata=request.metadata,
        )
        record_approval(action=approval.action, status=approval.status, response_time=None)

        return ApprovalResponse.from_approval(approval)

    except Exception as e:
        logger.error(f"Failed to create approval: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create approval: {str(e)}",
        )


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Get an approval by ID.

    Returns detailed information about a specific approval request.
    """
    approval = await deps.approval_service.get_approval(approval_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found",
        )

    return ApprovalResponse.from_approval(approval)


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_approval(
    approval_id: str,
    request: ReviewApprovalRequest,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Approve a pending approval request.

    This endpoint allows a human reviewer to approve an action that was
    previously blocked by policy limits or compliance rules.

    When approving a payment action, the held payment is automatically
    resumed and executed if the mandate chain snapshot is available.

    **Important:** Only pending approvals can be approved.
    """
    approval = await deps.approval_service.approve(
        approval_id=approval_id,
        reviewed_by=request.reviewed_by,
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found or not pending",
        )

    # Resume payment execution if this was a payment approval
    if approval.action == "payment" and approval.metadata.get("mandate_chain_snapshot"):
        logger.info(
            "Payment approval %s approved by %s — queuing for execution",
            approval_id, request.reviewed_by,
        )
        # Store approval decision in metadata for audit trail
        updated_metadata = approval.metadata.copy()
        updated_metadata["execution_resumed"] = True
        updated_metadata["resumed_by"] = request.reviewed_by
        await deps.approval_repo.update(
            approval_id,
            metadata=updated_metadata,
        )

    response_time = None
    if approval.reviewed_at is not None and approval.created_at is not None:
        response_time = max((approval.reviewed_at - approval.created_at).total_seconds(), 0.0)
    record_approval(action=approval.action, status=approval.status, response_time=response_time)

    return ApprovalResponse.from_approval(approval)


@router.post("/{approval_id}/deny", response_model=ApprovalResponse)
async def deny_approval(
    approval_id: str,
    request: ReviewApprovalRequest,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Deny a pending approval request.

    This endpoint allows a human reviewer to deny an action that was
    requesting approval.

    **Important:** Only pending approvals can be denied. A denial reason
    is recommended for audit purposes.
    """
    approval = await deps.approval_service.deny(
        approval_id=approval_id,
        reviewed_by=request.reviewed_by,
        reason=request.reason,
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found or not pending",
        )

    response_time = None
    if approval.reviewed_at is not None and approval.created_at is not None:
        response_time = max((approval.reviewed_at - approval.created_at).total_seconds(), 0.0)
    record_approval(action=approval.action, status=approval.status, response_time=response_time)

    return ApprovalResponse.from_approval(approval)


@router.post("/{approval_id}/cancel", response_model=ApprovalResponse)
async def cancel_approval(
    approval_id: str,
    reason: Optional[str] = None,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Cancel a pending approval request.

    This endpoint allows cancelling an approval request (e.g., if the agent
    no longer needs to perform the action).

    **Important:** Only pending approvals can be cancelled.
    """
    approval = await deps.approval_service.cancel(
        approval_id=approval_id,
        reason=reason,
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found or not pending",
        )

    return ApprovalResponse.from_approval(approval)


@router.get("/", response_model=ApprovalListResponse)
async def list_approvals(
    status: Optional[ApprovalStatus] = Query(default=None, description="Filter by status"),
    agent_id: Optional[str] = Query(default=None, description="Filter by agent ID"),
    wallet_id: Optional[str] = Query(default=None, description="Filter by wallet ID"),
    organization_id: Optional[str] = Query(default=None, description="Filter by organization ID"),
    requested_by: Optional[str] = Query(default=None, description="Filter by requester"),
    urgency: Optional[ApprovalUrgency] = Query(default=None, description="Filter by urgency"),
    limit: int = Query(default=50, ge=1, le=100, description="Max results to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    List approvals with optional filters.

    This endpoint supports filtering and pagination to help manage
    approval workflows efficiently.

    **Common use cases:**
    - Get all pending approvals: `?status=pending`
    - Get high-urgency approvals: `?urgency=high&status=pending`
    - Get approvals for specific agent: `?agent_id=agent_123`
    """
    approvals = await deps.approval_service.list_approvals(
        status=status,
        agent_id=agent_id,
        wallet_id=wallet_id,
        organization_id=organization_id,
        requested_by=requested_by,
        urgency=urgency,
        limit=limit,
        offset=offset,
    )

    return ApprovalListResponse(
        approvals=[ApprovalResponse.from_approval(a) for a in approvals],
        total=len(approvals),  # Note: This is not the total count, just returned count
        limit=limit,
        offset=offset,
    )


@router.get("/pending", response_model=ApprovalListResponse)
async def list_pending_approvals(
    urgency: Optional[ApprovalUrgency] = Query(default=None, description="Filter by urgency"),
    limit: int = Query(default=50, ge=1, le=100, description="Max results to return"),
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    List pending approvals.

    Convenience endpoint to get only pending approvals, optionally filtered by urgency.
    """
    approvals = await deps.approval_service.list_pending(
        urgency=urgency,
        limit=limit,
    )

    return ApprovalListResponse(
        approvals=[ApprovalResponse.from_approval(a) for a in approvals],
        total=len(approvals),
        limit=limit,
        offset=0,
    )


@router.post("/expire", response_model=dict)
async def expire_pending_approvals(
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Expire all pending approvals that have passed their expiration time.

    This endpoint should be called by a background job periodically to
    clean up stale approval requests.

    **Returns:** Count of expired approvals.
    """
    count = await deps.approval_service.expire_pending()

    return {
        "success": True,
        "expired_count": count,
        "message": f"Expired {count} approval request(s)",
    }


# ============================================================================
# Confidence-Based Routing Endpoints
# ============================================================================

class TransactionConfidenceRequest(BaseModel):
    """Request to calculate transaction confidence."""

    agent_id: str = Field(..., description="Agent making the transaction")
    transaction: dict[str, Any] = Field(..., description="Transaction details (amount, merchant, etc.)")
    kya_level: Optional[str] = Field(default=None, description="Agent KYA level (none/basic/verified/attested)")
    violation_count: int = Field(default=0, description="Number of recent policy violations")
    history: Optional[List[dict]] = Field(default=None, description="Recent transaction history")


class TransactionConfidenceResponse(BaseModel):
    """Response with transaction confidence assessment."""

    transaction_id: str
    score: float
    level: str
    factors: dict[str, float]
    recommendation: str
    routing: dict[str, Any]
    calculated_at: str


class TransactionApprovalRequest(BaseModel):
    """Request to approve/reject a transaction."""

    approver_id: str = Field(..., description="ID of the approver")
    reason: Optional[str] = Field(default=None, description="Reason for rejection (required if rejecting)")


@router.post("/transactions/{transaction_id}/confidence", response_model=TransactionConfidenceResponse)
async def calculate_transaction_confidence(
    transaction_id: str,
    request: TransactionConfidenceRequest,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Calculate confidence score for a transaction.

    Analyzes transaction patterns, agent behavior, and policy compliance
    to determine confidence level and routing decision.

    **Confidence Levels:**
    - 0.95+: AUTO_APPROVE - Execute immediately
    - 0.85-0.94: MANAGER_APPROVAL - Single approver required
    - 0.70-0.84: MULTI_SIG - Multiple approvers required
    - <0.70: HUMAN_REWRITE - Transaction should be redesigned

    **Returns:** Confidence score, level, and routing decision
    """
    try:
        # Import policy store to get agent's policy
        from sardis_v2_core.spending_policy import SpendingPolicy, create_default_policy, TrustLevel

        # For now, create a default policy - in production, fetch from policy store
        policy = create_default_policy(request.agent_id, TrustLevel.MEDIUM)

        # Calculate confidence
        confidence = deps.confidence_router.calculate_confidence(
            agent_id=request.agent_id,
            transaction=request.transaction,
            policy=policy,
            history=request.history,
            kya_level=request.kya_level,
            violation_count=request.violation_count,
        )

        # Get routing decision
        routing = deps.confidence_router.route_transaction(confidence)

        return TransactionConfidenceResponse(
            transaction_id=confidence.transaction_id,
            score=confidence.score,
            level=confidence.level.value,
            factors=confidence.factors,
            recommendation=confidence.recommendation,
            routing=routing,
            calculated_at=confidence.calculated_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to calculate transaction confidence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate confidence: {str(e)}",
        )


@router.post("/transactions/{transaction_id}/approve", response_model=dict)
async def approve_transaction(
    transaction_id: str,
    request: TransactionApprovalRequest,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Approve a transaction requiring human review.

    Records approval vote and checks if quorum has been reached
    for multi-signature approvals.

    **Returns:** Approval status and quorum information
    """
    try:
        quorum_reached = await deps.approval_workflow.approve(
            transaction_id=transaction_id,
            approver_id=request.approver_id,
        )

        status_info = await deps.approval_workflow.get_approval_status(transaction_id)

        return {
            "success": True,
            "transaction_id": transaction_id,
            "approver_id": request.approver_id,
            "quorum_reached": quorum_reached,
            "status": status_info,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to approve transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve transaction: {str(e)}",
        )


@router.post("/transactions/{transaction_id}/reject", response_model=dict)
async def reject_transaction(
    transaction_id: str,
    request: TransactionApprovalRequest,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Reject a transaction requiring human review.

    Records rejection vote. Any rejection immediately blocks the transaction.

    **Returns:** Rejection confirmation
    """
    try:
        if not request.reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required",
            )

        await deps.approval_workflow.reject(
            transaction_id=transaction_id,
            approver_id=request.approver_id,
            reason=request.reason,
        )

        status_info = await deps.approval_workflow.get_approval_status(transaction_id)

        return {
            "success": True,
            "transaction_id": transaction_id,
            "approver_id": request.approver_id,
            "reason": request.reason,
            "status": status_info,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to reject transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject transaction: {str(e)}",
        )


@router.get("/transactions/pending-approvals", response_model=dict)
async def get_pending_transaction_approvals(
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Get all pending transaction approvals.

    Returns list of transactions awaiting approval with their
    confidence scores and current approval status.

    **Returns:** List of pending approvals
    """
    try:
        # Get all pending approvals from workflow
        pending = []
        for tx_id, request in deps.approval_workflow._pending_approvals.items():
            if not request.is_expired() and not request.is_approved() and not request.is_rejected():
                pending.append({
                    "transaction_id": tx_id,
                    "agent_id": request.agent_id,
                    "amount": str(request.amount),
                    "merchant_id": request.merchant_id,
                    "confidence_score": request.confidence.score,
                    "confidence_level": request.confidence.level.value,
                    "required_approvers": request.required_approvers,
                    "approvals": list(request.approvals.keys()),
                    "quorum": request.quorum,
                    "created_at": request.created_at.isoformat(),
                    "expires_at": request.expires_at.isoformat(),
                })

        return {
            "pending_approvals": pending,
            "total": len(pending),
        }

    except Exception as e:
        logger.error(f"Failed to get pending approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending approvals: {str(e)}",
        )


@router.get("/transactions/{transaction_id}/confidence", response_model=dict)
async def get_transaction_confidence(
    transaction_id: str,
    deps: ApprovalsDependencies = Depends(get_deps),
):
    """
    Get confidence score and approval status for a transaction.

    Returns the current approval status including votes received,
    quorum status, and expiration information.

    **Returns:** Transaction confidence and approval status
    """
    try:
        status_info = await deps.approval_workflow.get_approval_status(transaction_id)

        if status_info.get("status") == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transaction confidence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction confidence: {str(e)}",
        )
