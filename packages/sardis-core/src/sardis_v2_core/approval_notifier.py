"""Approval notification system via webhooks."""
from __future__ import annotations

import logging
from typing import Optional
from decimal import Decimal

from .webhooks import WebhookEvent, WebhookService, EventType

logger = logging.getLogger(__name__)


class ApprovalNotifier:
    """Notifies humans of approval requests via webhooks."""

    def __init__(self, webhook_service: WebhookService):
        self._webhook_service = webhook_service

    async def notify_approval_requested(
        self,
        approval_id: str,
        action: str,
        requested_by: str,
        urgency: str,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        vendor: Optional[str] = None,
        amount: Optional[Decimal] = None,
        purpose: Optional[str] = None,
        reason: Optional[str] = None,
        card_limit: Optional[Decimal] = None,
        expires_at: Optional[str] = None,
    ) -> None:
        """Notify that an approval request was created."""
        event = self._create_approval_event(
            event_type=EventType.RISK_ALERT,  # Using existing event type for approvals
            approval_id=approval_id,
            action=action,
            status="pending",
            requested_by=requested_by,
            urgency=urgency,
            agent_id=agent_id,
            wallet_id=wallet_id,
            vendor=vendor,
            amount=amount,
            purpose=purpose,
            reason=reason,
            card_limit=card_limit,
            expires_at=expires_at,
        )
        await self._webhook_service.emit(event)
        logger.info(f"Sent approval.requested notification for {approval_id}")

    async def notify_approval_approved(
        self,
        approval_id: str,
        action: str,
        reviewed_by: str,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
    ) -> None:
        """Notify that an approval was approved."""
        event = self._create_approval_event(
            event_type=EventType.RISK_ALERT,
            approval_id=approval_id,
            action=action,
            status="approved",
            reviewed_by=reviewed_by,
            agent_id=agent_id,
            wallet_id=wallet_id,
        )
        await self._webhook_service.emit(event)
        logger.info(f"Sent approval.approved notification for {approval_id}")

    async def notify_approval_denied(
        self,
        approval_id: str,
        action: str,
        reviewed_by: str,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
    ) -> None:
        """Notify that an approval was denied."""
        event = self._create_approval_event(
            event_type=EventType.RISK_ALERT,
            approval_id=approval_id,
            action=action,
            status="denied",
            reviewed_by=reviewed_by,
            agent_id=agent_id,
            wallet_id=wallet_id,
        )
        await self._webhook_service.emit(event)
        logger.info(f"Sent approval.denied notification for {approval_id}")

    async def notify_approval_expired(
        self,
        approval_id: str,
        action: str,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
    ) -> None:
        """Notify that an approval request expired."""
        event = self._create_approval_event(
            event_type=EventType.RISK_ALERT,
            approval_id=approval_id,
            action=action,
            status="expired",
            agent_id=agent_id,
            wallet_id=wallet_id,
        )
        await self._webhook_service.emit(event)
        logger.info(f"Sent approval.expired notification for {approval_id}")

    async def notify_approval_cancelled(
        self,
        approval_id: str,
        action: str,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
    ) -> None:
        """Notify that an approval request was cancelled."""
        event = self._create_approval_event(
            event_type=EventType.RISK_ALERT,
            approval_id=approval_id,
            action=action,
            status="cancelled",
            agent_id=agent_id,
            wallet_id=wallet_id,
        )
        await self._webhook_service.emit(event)
        logger.info(f"Sent approval.cancelled notification for {approval_id}")

    def _create_approval_event(
        self,
        event_type: EventType,
        approval_id: str,
        action: str,
        status: str,
        requested_by: Optional[str] = None,
        reviewed_by: Optional[str] = None,
        urgency: Optional[str] = None,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        vendor: Optional[str] = None,
        amount: Optional[Decimal] = None,
        purpose: Optional[str] = None,
        reason: Optional[str] = None,
        card_limit: Optional[Decimal] = None,
        expires_at: Optional[str] = None,
    ) -> WebhookEvent:
        """Create a webhook event for approval notification."""
        data = {
            "approval": {
                "id": approval_id,
                "action": action,
                "status": status,
            }
        }

        # Add optional fields if present
        if requested_by:
            data["approval"]["requested_by"] = requested_by
        if reviewed_by:
            data["approval"]["reviewed_by"] = reviewed_by
        if urgency:
            data["approval"]["urgency"] = urgency
        if agent_id:
            data["approval"]["agent_id"] = agent_id
        if wallet_id:
            data["approval"]["wallet_id"] = wallet_id
        if vendor:
            data["approval"]["vendor"] = vendor
        if amount is not None:
            data["approval"]["amount"] = amount
        if purpose:
            data["approval"]["purpose"] = purpose
        if reason:
            data["approval"]["reason"] = reason
        if card_limit is not None:
            data["approval"]["card_limit"] = card_limit
        if expires_at:
            data["approval"]["expires_at"] = expires_at

        return WebhookEvent(event_type=event_type, data=data)
