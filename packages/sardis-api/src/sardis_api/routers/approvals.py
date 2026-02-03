"""Approval API endpoints for managing human approval workflows.

This module provides REST endpoints for creating, managing, and reviewing
approval requests when agent actions exceed policy limits.
"""
from __future__ import annotations

import logging
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_v2_core.approval_service import ApprovalService, ApprovalStatus, ApprovalUrgency
from sardis_v2_core.approval_repository import ApprovalRepository, Approval

from sardis_api.authz import require_principal

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
