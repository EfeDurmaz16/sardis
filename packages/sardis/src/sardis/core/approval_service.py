"""Approval service for managing human approval workflows.

This module provides business logic for approval requests when agent actions
exceed policy limits or require manual review.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from .approval_repository import Approval, ApprovalRepository

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
        agent_id: str | None = None,
        wallet_id: str | None = None,
        vendor: str | None = None,
        amount: Decimal | None = None,
        purpose: str | None = None,
        reason: str | None = None,
        card_limit: Decimal | None = None,
        urgency: ApprovalUrgency = 'medium',
        expires_in_hours: int = 24,
        organization_id: str | None = None,
        metadata: dict | None = None,
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
        expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)

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
    ) -> Approval | None:
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
        reviewed_at = datetime.now(UTC)
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
        reason: str | None = None,
    ) -> Approval | None:
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
        reviewed_at = datetime.now(UTC)
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
        reason: str | None = None,
    ) -> Approval | None:
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

    async def get_approval(self, approval_id: str) -> Approval | None:
        """Get an approval by ID."""
        return await self._repository.get(approval_id)

    async def list_approvals(
        self,
        *,
        status: ApprovalStatus | None = None,
        agent_id: str | None = None,
        wallet_id: str | None = None,
        organization_id: str | None = None,
        requested_by: str | None = None,
        urgency: ApprovalUrgency | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Approval]:
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
        urgency: ApprovalUrgency | None = None,
        limit: int = 50,
    ) -> list[Approval]:
        """List pending approvals."""
        return await self.list_approvals(
            status='pending',
            urgency=urgency,
            limit=limit,
        )
