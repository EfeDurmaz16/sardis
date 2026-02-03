"""Approval service for managing human approval workflows.

This module provides business logic for approval requests when agent actions
exceed policy limits or require manual review.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Literal
from dataclasses import dataclass, field

from .approval_repository import ApprovalRepository, Approval

logger = logging.getLogger("sardis.approval_service")


ApprovalStatus = Literal['pending', 'approved', 'denied', 'expired', 'cancelled']
ApprovalUrgency = Literal['low', 'medium', 'high']


class ApprovalService:
    """Service for managing approval workflows."""

    def __init__(self, repository: ApprovalRepository):
        self._repository = repository

    async def create_approval(
        self,
        *,
        action: str,
        requested_by: str,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        vendor: Optional[str] = None,
        amount: Optional[Decimal] = None,
        purpose: Optional[str] = None,
        reason: Optional[str] = None,
        card_limit: Optional[Decimal] = None,
        urgency: ApprovalUrgency = 'medium',
        expires_in_hours: int = 24,
        organization_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Approval:
        """Create a new approval request.

        Args:
            action: Type of action requiring approval (payment, create_card, etc.)
            requested_by: Agent ID that initiated the request
            agent_id: Agent ID for the action
            wallet_id: Wallet ID for the action
            vendor: Vendor name (for payments)
            amount: Payment amount
            purpose: Purpose description
            reason: Reason for approval request
            card_limit: Card limit (for create_card action)
            urgency: Urgency level (low, medium, high)
            expires_in_hours: Hours until request expires (default: 24)
            organization_id: Organization ID (optional)
            metadata: Additional metadata

        Returns:
            Created Approval object
        """
        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        # Create approval via repository
        approval = await self._repository.create(
            action=action,
            requested_by=requested_by,
            expires_at=expires_at,
            urgency=urgency,
            vendor=vendor,
            amount=amount,
            purpose=purpose,
            reason=reason,
            card_limit=card_limit,
            agent_id=agent_id,
            wallet_id=wallet_id,
            organization_id=organization_id,
            metadata=metadata,
        )

        logger.info(
            f"Created approval request {approval.id} for action '{action}' "
            f"by {requested_by} (expires: {expires_at.isoformat()})"
        )

        return approval

    async def approve(
        self,
        approval_id: str,
        reviewed_by: str,
    ) -> Optional[Approval]:
        """Approve a pending approval request.

        Args:
            approval_id: Approval ID to approve
            reviewed_by: Email/ID of approver

        Returns:
            Updated Approval or None if not found/not pending
        """
        approval = await self._repository.get(approval_id)
        if not approval:
            logger.warning(f"Approval {approval_id} not found")
            return None

        if approval.status != 'pending':
            logger.warning(
                f"Cannot approve {approval_id}: status is {approval.status}, not pending"
            )
            return None

        # Update status via repository
        reviewed_at = datetime.now(timezone.utc)
        updated = await self._repository.update(
            approval_id,
            status='approved',
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
        )

        logger.info(
            f"Approval {approval_id} approved by {reviewed_by} "
            f"(action: {approval.action})"
        )

        return updated

    async def deny(
        self,
        approval_id: str,
        reviewed_by: str,
        reason: Optional[str] = None,
    ) -> Optional[Approval]:
        """Deny a pending approval request.

        Args:
            approval_id: Approval ID to deny
            reviewed_by: Email/ID of denier
            reason: Reason for denial (optional)

        Returns:
            Updated Approval or None if not found/not pending
        """
        approval = await self._repository.get(approval_id)
        if not approval:
            logger.warning(f"Approval {approval_id} not found")
            return None

        if approval.status != 'pending':
            logger.warning(
                f"Cannot deny {approval_id}: status is {approval.status}, not pending"
            )
            return None

        # Update metadata with denial reason
        metadata = approval.metadata.copy()
        if reason:
            metadata['denial_reason'] = reason

        # Update status via repository
        reviewed_at = datetime.now(timezone.utc)
        updated = await self._repository.update(
            approval_id,
            status='denied',
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            metadata=metadata,
        )

        logger.info(
            f"Approval {approval_id} denied by {reviewed_by} "
            f"(action: {approval.action})"
        )

        return updated

    async def cancel(
        self,
        approval_id: str,
        reason: Optional[str] = None,
    ) -> Optional[Approval]:
        """Cancel a pending approval request.

        Args:
            approval_id: Approval ID to cancel
            reason: Reason for cancellation (optional)

        Returns:
            Updated Approval or None if not found/not pending
        """
        approval = await self._repository.get(approval_id)
        if not approval:
            logger.warning(f"Approval {approval_id} not found")
            return None

        if approval.status != 'pending':
            logger.warning(
                f"Cannot cancel {approval_id}: status is {approval.status}, not pending"
            )
            return None

        # Update metadata with cancellation reason
        metadata = approval.metadata.copy()
        if reason:
            metadata['cancellation_reason'] = reason

        # Update status via repository
        updated = await self._repository.update(
            approval_id,
            status='cancelled',
            metadata=metadata,
        )

        logger.info(f"Approval {approval_id} cancelled (action: {approval.action})")

        return updated

    async def expire_pending(self) -> int:
        """Expire all pending approvals that have passed their expiration time.

        This method should be called periodically by a background job.

        Returns:
            Number of approvals expired
        """
        expired_approvals = await self._repository.get_expired_pending()
        count = 0

        for approval in expired_approvals:
            await self._repository.update(
                approval.id,
                status='expired',
            )
            count += 1
            logger.info(f"Expired approval {approval.id} (action: {approval.action})")

        if count > 0:
            logger.info(f"Expired {count} approval request(s)")

        return count

    async def get_approval(self, approval_id: str) -> Optional[Approval]:
        """Get an approval by ID."""
        return await self._repository.get(approval_id)

    async def list_approvals(
        self,
        *,
        status: Optional[ApprovalStatus] = None,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        requested_by: Optional[str] = None,
        urgency: Optional[ApprovalUrgency] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Approval]:
        """List approvals with optional filters.

        Args:
            status: Filter by status
            agent_id: Filter by agent ID
            wallet_id: Filter by wallet ID
            organization_id: Filter by organization ID
            requested_by: Filter by requester
            urgency: Filter by urgency level
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of matching approvals
        """
        return await self._repository.list(
            status=status,
            agent_id=agent_id,
            wallet_id=wallet_id,
            organization_id=organization_id,
            requested_by=requested_by,
            urgency=urgency,
            limit=limit,
            offset=offset,
        )

    async def list_pending(
        self,
        *,
        urgency: Optional[ApprovalUrgency] = None,
        limit: int = 50,
    ) -> List[Approval]:
        """List pending approvals."""
        return await self.list_approvals(
            status='pending',
            urgency=urgency,
            limit=limit,
        )
