"""
Exception handling workflows for payment failures.

When payments fail or policies block, provides structured recovery flows:
- Retry with backoff
- Escalate to human
- Auto-adjust and retry
- Refund flow
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExceptionType(Enum):
    POLICY_BLOCKED = "policy_blocked"
    CHAIN_FAILURE = "chain_failure"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    COMPLIANCE_HOLD = "compliance_hold"
    TIMEOUT = "timeout"
    MERCHANT_REJECTED = "merchant_rejected"
    KILL_SWITCH_ACTIVE = "kill_switch_active"


class ExceptionStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"


class ResolutionStrategy(Enum):
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    AUTO_ADJUST = "auto_adjust"
    REFUND = "refund"
    WAIT_AND_RETRY = "wait_and_retry"


@dataclass
class PaymentException:
    exception_id: str
    transaction_id: str
    agent_id: str
    exception_type: ExceptionType
    status: ExceptionStatus
    description: str
    original_amount: Decimal
    currency: str
    merchant_id: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    suggested_strategy: ResolutionStrategy | None = None
    resolution_notes: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class ExceptionWorkflowEngine:
    """Manages payment exception handling workflows."""

    def __init__(self):
        self._exceptions: dict[str, PaymentException] = {}
        self._strategy_map: dict[ExceptionType, ResolutionStrategy] = {
            ExceptionType.CHAIN_FAILURE: ResolutionStrategy.RETRY_WITH_BACKOFF,
            ExceptionType.TIMEOUT: ResolutionStrategy.RETRY_WITH_BACKOFF,
            ExceptionType.INSUFFICIENT_FUNDS: ResolutionStrategy.ESCALATE_TO_HUMAN,
            ExceptionType.POLICY_BLOCKED: ResolutionStrategy.AUTO_ADJUST,
            ExceptionType.COMPLIANCE_HOLD: ResolutionStrategy.ESCALATE_TO_HUMAN,
            ExceptionType.MERCHANT_REJECTED: ResolutionStrategy.ESCALATE_TO_HUMAN,
            ExceptionType.KILL_SWITCH_ACTIVE: ResolutionStrategy.WAIT_AND_RETRY,
        }

    def create_exception(
        self,
        *,
        transaction_id: str,
        agent_id: str,
        exception_type: ExceptionType,
        description: str,
        original_amount: Decimal,
        currency: str,
        merchant_id: str | None = None,
        max_retries: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentException:
        """Create a new payment exception."""
        exception_id = f"exc_{uuid.uuid4().hex[:16]}"
        suggested = self._strategy_map.get(exception_type)
        exc = PaymentException(
            exception_id=exception_id,
            transaction_id=transaction_id,
            agent_id=agent_id,
            exception_type=exception_type,
            status=ExceptionStatus.OPEN,
            description=description,
            original_amount=original_amount,
            currency=currency,
            merchant_id=merchant_id,
            max_retries=max_retries,
            suggested_strategy=suggested,
            metadata=metadata or {},
        )
        self._exceptions[exception_id] = exc
        logger.info(
            "Created payment exception %s type=%s agent=%s",
            exception_id,
            exception_type.value,
            agent_id,
        )
        return exc

    def suggest_strategy(self, exception: PaymentException) -> ResolutionStrategy:
        """Suggest resolution strategy based on exception type."""
        return self._strategy_map.get(
            exception.exception_type, ResolutionStrategy.ESCALATE_TO_HUMAN
        )

    async def execute_strategy(
        self,
        exception_id: str,
        strategy: ResolutionStrategy | None = None,
        retry_fn: Callable[[], Coroutine[Any, Any, bool]] | None = None,
    ) -> PaymentException:
        """Execute the resolution strategy.

        retry_fn, if provided, is an async callable that returns True on success.
        """
        exc = self._exceptions.get(exception_id)
        if exc is None:
            raise KeyError(f"Exception not found: {exception_id}")

        if strategy is None:
            strategy = exc.suggested_strategy or self.suggest_strategy(exc)

        exc.status = ExceptionStatus.IN_PROGRESS
        exc.updated_at = datetime.now(UTC)

        logger.info(
            "Executing strategy %s for exception %s (retry_count=%d)",
            strategy.value,
            exception_id,
            exc.retry_count,
        )

        if strategy == ResolutionStrategy.RETRY:
            if retry_fn is not None and exc.retry_count < exc.max_retries:
                exc.retry_count += 1
                exc.updated_at = datetime.now(UTC)
                try:
                    success = await retry_fn()
                    if success:
                        exc.status = ExceptionStatus.RESOLVED
                        exc.resolution_notes = f"Resolved via immediate retry (attempt {exc.retry_count})"
                        exc.resolved_at = datetime.now(UTC)
                    else:
                        exc.status = ExceptionStatus.OPEN
                        exc.resolution_notes = f"Retry attempt {exc.retry_count} failed"
                except Exception as e:
                    exc.status = ExceptionStatus.OPEN
                    exc.resolution_notes = f"Retry attempt {exc.retry_count} raised: {e}"
            else:
                exc.status = ExceptionStatus.ESCALATED
                exc.resolution_notes = (
                    "Max retries reached or no retry function provided; escalated"
                )

        elif strategy == ResolutionStrategy.RETRY_WITH_BACKOFF:
            if exc.retry_count >= exc.max_retries:
                exc.status = ExceptionStatus.ESCALATED
                exc.resolution_notes = (
                    f"Max retries ({exc.max_retries}) exhausted; escalated to human"
                )
            elif retry_fn is not None:
                backoff_seconds = 2 ** exc.retry_count
                logger.info(
                    "Backoff wait %ds before retry for exception %s",
                    backoff_seconds,
                    exception_id,
                )
                await asyncio.sleep(backoff_seconds)
                exc.retry_count += 1
                exc.updated_at = datetime.now(UTC)
                try:
                    success = await retry_fn()
                    if success:
                        exc.status = ExceptionStatus.RESOLVED
                        exc.resolution_notes = (
                            f"Resolved via backoff retry (attempt {exc.retry_count}, "
                            f"backoff {backoff_seconds}s)"
                        )
                        exc.resolved_at = datetime.now(UTC)
                    else:
                        exc.status = ExceptionStatus.OPEN
                        exc.resolution_notes = (
                            f"Backoff retry attempt {exc.retry_count} failed"
                        )
                except Exception as e:
                    exc.status = ExceptionStatus.OPEN
                    exc.resolution_notes = (
                        f"Backoff retry attempt {exc.retry_count} raised: {e}"
                    )
            else:
                exc.status = ExceptionStatus.ESCALATED
                exc.resolution_notes = "No retry function provided; escalated"

        elif strategy == ResolutionStrategy.ESCALATE_TO_HUMAN:
            exc.status = ExceptionStatus.ESCALATED
            exc.resolution_notes = (
                f"Escalated to human review: {exc.exception_type.value}"
            )

        elif strategy == ResolutionStrategy.AUTO_ADJUST:
            logger.info(
                "AUTO_ADJUST: exception %s requires parameter adjustment before retry "
                "(amount=%s %s, type=%s)",
                exception_id,
                exc.original_amount,
                exc.currency,
                exc.exception_type.value,
            )
            exc.status = ExceptionStatus.ESCALATED
            exc.resolution_notes = (
                "Amount or request parameters must be adjusted before retrying. "
                "Escalated for human review."
            )

        elif strategy == ResolutionStrategy.WAIT_AND_RETRY:
            if exc.retry_count >= exc.max_retries:
                exc.status = ExceptionStatus.ESCALATED
                exc.resolution_notes = (
                    f"Max retries ({exc.max_retries}) exhausted after wait-and-retry; escalated"
                )
            elif retry_fn is not None:
                logger.info(
                    "WAIT_AND_RETRY: sleeping 60s for exception %s", exception_id
                )
                await asyncio.sleep(60)
                exc.retry_count += 1
                exc.updated_at = datetime.now(UTC)
                try:
                    success = await retry_fn()
                    if success:
                        exc.status = ExceptionStatus.RESOLVED
                        exc.resolution_notes = (
                            f"Resolved after 60s wait (attempt {exc.retry_count})"
                        )
                        exc.resolved_at = datetime.now(UTC)
                    else:
                        exc.status = ExceptionStatus.OPEN
                        exc.resolution_notes = (
                            f"Wait-and-retry attempt {exc.retry_count} failed"
                        )
                except Exception as e:
                    exc.status = ExceptionStatus.OPEN
                    exc.resolution_notes = (
                        f"Wait-and-retry attempt {exc.retry_count} raised: {e}"
                    )
            else:
                exc.status = ExceptionStatus.ESCALATED
                exc.resolution_notes = "No retry function provided for wait-and-retry; escalated"

        elif strategy == ResolutionStrategy.REFUND:
            exc.status = ExceptionStatus.RESOLVED
            exc.resolution_notes = (
                f"Refund required for {exc.original_amount} {exc.currency} "
                f"on transaction {exc.transaction_id}. Initiate refund flow."
            )
            exc.resolved_at = datetime.now(UTC)

        else:
            exc.status = ExceptionStatus.ESCALATED
            exc.resolution_notes = f"Unknown strategy {strategy}; escalated"

        exc.updated_at = datetime.now(UTC)
        return exc

    def resolve(
        self,
        exception_id: str,
        resolved_by: str,
        notes: str | None = None,
    ) -> PaymentException:
        """Manually resolve an exception."""
        exc = self._exceptions.get(exception_id)
        if exc is None:
            raise KeyError(f"Exception not found: {exception_id}")
        exc.status = ExceptionStatus.RESOLVED
        exc.resolved_by = resolved_by
        exc.resolved_at = datetime.now(UTC)
        exc.resolution_notes = notes
        exc.updated_at = datetime.now(UTC)
        logger.info("Exception %s manually resolved by %s", exception_id, resolved_by)
        return exc

    def escalate(self, exception_id: str, reason: str) -> PaymentException:
        """Escalate to human review."""
        exc = self._exceptions.get(exception_id)
        if exc is None:
            raise KeyError(f"Exception not found: {exception_id}")
        exc.status = ExceptionStatus.ESCALATED
        exc.resolution_notes = reason
        exc.updated_at = datetime.now(UTC)
        logger.info("Exception %s escalated: %s", exception_id, reason)
        return exc

    def get_open_exceptions(
        self, agent_id: str | None = None
    ) -> list[PaymentException]:
        """List open exceptions, optionally filtered by agent."""
        open_statuses = {ExceptionStatus.OPEN, ExceptionStatus.IN_PROGRESS}
        results = [
            exc
            for exc in self._exceptions.values()
            if exc.status in open_statuses
            and (agent_id is None or exc.agent_id == agent_id)
        ]
        results.sort(key=lambda x: x.created_at)
        return results

    def get_exception(self, exception_id: str) -> PaymentException | None:
        """Get a specific exception."""
        return self._exceptions.get(exception_id)
