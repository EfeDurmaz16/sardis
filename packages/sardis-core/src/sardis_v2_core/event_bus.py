"""Centralized event bus for Sardis events.

Decouples event producers (policy engine, payment orchestrator, etc.)
from event consumers (webhooks, audit log, notifications).
"""
from __future__ import annotations

import asyncio
import fnmatch
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .webhooks import EventType, WebhookEvent, WebhookService

logger = logging.getLogger(__name__)


@dataclass
class EventBus:
    """Central event bus for Sardis events.

    Decouples event producers (policy engine, payment orchestrator, etc.)
    from event consumers (webhooks, audit log, notifications).

    Example:
        bus = EventBus()

        # Subscribe to all policy events
        bus.subscribe("policy.*", my_handler)

        # Subscribe to specific event
        bus.subscribe("payment.completed", payment_handler)

        # Emit event
        await bus.emit(
            EventType.POLICY_VIOLATED,
            data={"policy_id": "pol_123", "reason": "Limit exceeded"},
            agent_id="agent_456",
        )
    """

    _subscribers: dict[str, list[Callable]] = field(default_factory=dict)
    _webhook_service: Optional[WebhookService] = None
    _background_tasks: set[asyncio.Task[Any]] = field(default_factory=set)

    def subscribe(self, event_pattern: str, handler: Callable) -> None:
        """Subscribe to events matching a pattern.

        Args:
            event_pattern: Event type or pattern (supports wildcards like 'policy.*')
            handler: Async callable that receives (event: WebhookEvent) -> None

        Example:
            async def on_policy_event(event: WebhookEvent):
                print(f"Policy event: {event.event_type}")

            bus.subscribe("policy.*", on_policy_event)
        """
        if event_pattern not in self._subscribers:
            self._subscribers[event_pattern] = []

        if handler not in self._subscribers[event_pattern]:
            self._subscribers[event_pattern].append(handler)
            logger.debug(f"Subscribed {handler.__name__} to {event_pattern}")

    def unsubscribe(self, event_pattern: str, handler: Callable) -> None:
        """Remove a subscription.

        Args:
            event_pattern: Event type or pattern used during subscribe
            handler: The same handler that was subscribed
        """
        if event_pattern in self._subscribers:
            try:
                self._subscribers[event_pattern].remove(handler)
                logger.debug(f"Unsubscribed {handler.__name__} from {event_pattern}")
            except ValueError:
                pass

            # Clean up empty lists
            if not self._subscribers[event_pattern]:
                del self._subscribers[event_pattern]

    async def emit(
        self,
        event_type: EventType,
        data: dict,
        agent_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        fire_and_forget: bool = True,
    ) -> None:
        """Emit an event - routes to all matching subscribers and webhook service.

        Args:
            event_type: Type of event to emit
            data: Event payload data
            agent_id: Optional agent ID for filtering
            organization_id: Optional organization ID for filtering
            fire_and_forget: If True, run handlers in background (default)

        Example:
            await bus.emit(
                EventType.POLICY_VIOLATED,
                data={"policy_id": "pol_123", "reason": "Daily limit exceeded"},
                agent_id="agent_456",
                fire_and_forget=True,
            )
        """
        # Create webhook event
        event = WebhookEvent(
            event_type=event_type,
            data=data,
        )

        # Add metadata to data if provided
        if agent_id:
            event.data["agent_id"] = agent_id
        if organization_id:
            event.data["organization_id"] = organization_id

        # Find matching subscribers
        matching_handlers = []
        for pattern, handlers in self._subscribers.items():
            if self._matches_pattern(event_type.value, pattern):
                matching_handlers.extend(handlers)

        # Execute handlers
        if matching_handlers:
            if fire_and_forget:
                # Fire and forget with task tracking to avoid unbounded growth.
                self._schedule_background(self._execute_handlers(event, matching_handlers))
            else:
                # Wait for handlers to complete
                await self._execute_handlers(event, matching_handlers)

        # Emit to webhook service if configured
        if self._webhook_service:
            if fire_and_forget:
                self._schedule_background(self._webhook_service.emit(event))
            else:
                await self._webhook_service.emit(event)

        logger.debug(
            f"Emitted {event_type.value} to {len(matching_handlers)} handlers + webhooks"
        )

    async def _execute_handlers(
        self,
        event: WebhookEvent,
        handlers: list[Callable],
    ) -> None:
        """Execute all handlers for an event."""
        for handler in handlers:
            try:
                # Support both sync and async handlers
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(
                    f"Handler {handler.__name__} failed for {event.event_type}: {e}",
                    exc_info=True,
                )

    def _schedule_background(self, coro: Any) -> None:
        """Schedule a background coroutine while tracking task lifecycle."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._on_background_task_done)

    def _on_background_task_done(self, task: asyncio.Task[Any]) -> None:
        """Remove completed task and surface errors in logs."""
        self._background_tasks.discard(task)
        if task.cancelled():
            return
        try:
            task.result()
        except Exception:
            logger.exception("Event bus background task failed")

    async def wait_for_background_tasks(self, timeout: Optional[float] = None) -> None:
        """Wait for all currently tracked background tasks to complete."""
        if not self._background_tasks:
            return
        pending = list(self._background_tasks)
        await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=timeout)

    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches subscription pattern (wildcard support).

        Args:
            event_type: Full event type (e.g., "policy.violated")
            pattern: Subscription pattern (e.g., "policy.*" or "payment.completed")

        Returns:
            True if event type matches pattern

        Examples:
            _matches_pattern("policy.violated", "policy.*") -> True
            _matches_pattern("payment.completed", "payment.*") -> True
            _matches_pattern("payment.completed", "policy.*") -> False
            _matches_pattern("card.created", "*.created") -> True
            _matches_pattern("card.created", "*") -> True
        """
        return fnmatch.fnmatch(event_type, pattern)

    def set_webhook_service(self, service: WebhookService) -> None:
        """Configure webhook service for event delivery.

        Args:
            service: WebhookService instance
        """
        self._webhook_service = service
        logger.info("Webhook service configured for event bus")

    def clear_subscribers(self) -> None:
        """Clear all subscriptions (useful for testing)."""
        self._subscribers.clear()
        logger.debug("Cleared all event subscriptions")


# Singleton instance for global event bus
_default_bus: Optional[EventBus] = None


def get_default_bus() -> EventBus:
    """Get or create the default global event bus.

    Returns:
        Singleton EventBus instance
    """
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


# Helper functions for common event types

async def emit_policy_event(
    event_type: EventType,
    policy_id: str,
    agent_id: str,
    reason: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Emit a policy-related event.

    Args:
        event_type: One of POLICY_CREATED, POLICY_UPDATED, POLICY_VIOLATED, POLICY_CHECK_PASSED
        policy_id: ID of the policy
        agent_id: ID of the agent
        reason: Optional reason for violation/update
        details: Additional event details

    Example:
        await emit_policy_event(
            EventType.POLICY_VIOLATED,
            policy_id="pol_123",
            agent_id="agent_456",
            reason="Daily spending limit exceeded",
            details={"limit": "1000.00", "attempted": "1200.00"},
        )
    """
    data = {
        "policy_id": policy_id,
        "agent_id": agent_id,
    }

    if reason:
        data["reason"] = reason

    if details:
        data.update(details)

    await get_default_bus().emit(event_type, data, agent_id=agent_id)


async def emit_spend_event(
    event_type: EventType,
    agent_id: str,
    amount: str,
    limit: str,
    period: str,
    percentage: Optional[float] = None,
    details: Optional[dict] = None,
) -> None:
    """Emit a spending threshold event.

    Args:
        event_type: One of SPEND_THRESHOLD_WARNING, SPEND_THRESHOLD_REACHED, SPEND_DAILY_SUMMARY
        agent_id: ID of the agent
        amount: Current spending amount
        limit: Spending limit
        period: Time period (e.g., "daily", "monthly")
        percentage: Optional percentage of limit used
        details: Additional event details

    Example:
        await emit_spend_event(
            EventType.SPEND_THRESHOLD_WARNING,
            agent_id="agent_123",
            amount="800.00",
            limit="1000.00",
            period="daily",
            percentage=80.0,
        )
    """
    data = {
        "agent_id": agent_id,
        "amount": amount,
        "limit": limit,
        "period": period,
    }

    if percentage is not None:
        data["percentage"] = percentage

    if details:
        data.update(details)

    await get_default_bus().emit(event_type, data, agent_id=agent_id)


async def emit_approval_event(
    event_type: EventType,
    approval_id: str,
    agent_id: str,
    transaction_id: Optional[str] = None,
    approver_id: Optional[str] = None,
    reason: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Emit an approval-related event.

    Args:
        event_type: One of APPROVAL_REQUESTED, APPROVAL_GRANTED, APPROVAL_DENIED, APPROVAL_EXPIRED
        approval_id: ID of the approval request
        agent_id: ID of the agent
        transaction_id: Optional transaction ID
        approver_id: Optional ID of approver
        reason: Optional reason for denial/expiry
        details: Additional event details

    Example:
        await emit_approval_event(
            EventType.APPROVAL_GRANTED,
            approval_id="appr_789",
            agent_id="agent_123",
            transaction_id="tx_456",
            approver_id="user_999",
        )
    """
    data = {
        "approval_id": approval_id,
        "agent_id": agent_id,
    }

    if transaction_id:
        data["transaction_id"] = transaction_id

    if approver_id:
        data["approver_id"] = approver_id

    if reason:
        data["reason"] = reason

    if details:
        data.update(details)

    await get_default_bus().emit(event_type, data, agent_id=agent_id)


async def emit_card_event(
    event_type: EventType,
    card_id: str,
    agent_id: str,
    transaction_id: Optional[str] = None,
    amount: Optional[str] = None,
    merchant: Optional[str] = None,
    reason: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Emit a card-related event.

    Args:
        event_type: One of CARD_CREATED, CARD_ACTIVATED, CARD_TRANSACTION, CARD_DECLINED, CARD_FROZEN
        card_id: ID of the virtual card
        agent_id: ID of the agent
        transaction_id: Optional transaction ID
        amount: Optional transaction amount
        merchant: Optional merchant name
        reason: Optional reason for decline/freeze
        details: Additional event details

    Example:
        await emit_card_event(
            EventType.CARD_DECLINED,
            card_id="card_123",
            agent_id="agent_456",
            amount="150.00",
            merchant="Amazon",
            reason="Insufficient balance",
        )
    """
    data = {
        "card_id": card_id,
        "agent_id": agent_id,
    }

    if transaction_id:
        data["transaction_id"] = transaction_id

    if amount:
        data["amount"] = amount

    if merchant:
        data["merchant"] = merchant

    if reason:
        data["reason"] = reason

    if details:
        data.update(details)

    await get_default_bus().emit(event_type, data, agent_id=agent_id)


async def emit_compliance_event(
    event_type: EventType,
    agent_id: str,
    check_type: str,
    result: str,
    reason: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Emit a compliance-related event.

    Args:
        event_type: One of COMPLIANCE_CHECK_PASSED, COMPLIANCE_CHECK_FAILED, COMPLIANCE_ALERT
        agent_id: ID of the agent
        check_type: Type of compliance check (e.g., "kyc", "sanctions", "aml")
        result: Result of the check (e.g., "pass", "fail", "alert")
        reason: Optional reason for failure/alert
        details: Additional event details

    Example:
        await emit_compliance_event(
            EventType.COMPLIANCE_CHECK_FAILED,
            agent_id="agent_123",
            check_type="sanctions",
            result="hit",
            reason="Match on OFAC list",
            details={"list": "OFAC", "confidence": 0.95},
        )
    """
    data = {
        "agent_id": agent_id,
        "check_type": check_type,
        "result": result,
    }

    if reason:
        data["reason"] = reason

    if details:
        data.update(details)

    await get_default_bus().emit(event_type, data, agent_id=agent_id)


async def emit_group_event(
    event_type: EventType,
    group_id: str,
    amount: str,
    limit: str,
    period: str,
    percentage: Optional[float] = None,
    details: Optional[dict] = None,
) -> None:
    """Emit a group budget event.

    Args:
        event_type: One of GROUP_BUDGET_WARNING, GROUP_BUDGET_EXCEEDED
        group_id: ID of the agent group
        amount: Current spending amount
        limit: Budget limit
        period: Time period (e.g., "daily", "monthly")
        percentage: Optional percentage of budget used
        details: Additional event details

    Example:
        await emit_group_event(
            EventType.GROUP_BUDGET_WARNING,
            group_id="group_123",
            amount="8000.00",
            limit="10000.00",
            period="monthly",
            percentage=80.0,
        )
    """
    data = {
        "group_id": group_id,
        "amount": amount,
        "limit": limit,
        "period": period,
    }

    if percentage is not None:
        data["percentage"] = percentage

    if details:
        data.update(details)

    await get_default_bus().emit(event_type, data)
