"""
Checkout analytics and event tracking.

This module provides comprehensive analytics capabilities for tracking
checkout events, measuring conversion rates, and monitoring payment performance.

Audit fix #3: Add checkout analytics and event tracking.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, TypeVar
from functools import wraps
import uuid

from sardis_checkout.models import (
    CheckoutAnalyticsEvent,
    CheckoutEventType,
    PaymentStatus,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AnalyticsBackend(ABC):
    """Abstract interface for analytics storage/publishing backends."""

    @abstractmethod
    async def publish(self, event: CheckoutAnalyticsEvent) -> None:
        """Publish an analytics event."""
        pass

    @abstractmethod
    async def publish_batch(self, events: List[CheckoutAnalyticsEvent]) -> None:
        """Publish a batch of analytics events."""
        pass

    @abstractmethod
    async def query(
        self,
        event_types: Optional[List[CheckoutEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        checkout_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckoutAnalyticsEvent]:
        """Query analytics events."""
        pass


class InMemoryAnalyticsBackend(AnalyticsBackend):
    """
    In-memory analytics backend for development and testing.

    Note: This backend is not suitable for production use.
    Use a persistent backend like ClickHouse, BigQuery, or a time-series database.
    """

    def __init__(self, max_events: int = 100000):
        self._events: List[CheckoutAnalyticsEvent] = []
        self._max_events = max_events
        self._lock = asyncio.Lock()

    async def publish(self, event: CheckoutAnalyticsEvent) -> None:
        async with self._lock:
            self._events.append(event)
            # Trim old events if needed
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

    async def publish_batch(self, events: List[CheckoutAnalyticsEvent]) -> None:
        async with self._lock:
            self._events.extend(events)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

    async def query(
        self,
        event_types: Optional[List[CheckoutEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        checkout_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckoutAnalyticsEvent]:
        async with self._lock:
            results = []
            for event in reversed(self._events):
                if event_types and event.event_type not in event_types:
                    continue
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                if agent_id and event.agent_id != agent_id:
                    continue
                if checkout_id and event.checkout_id != checkout_id:
                    continue
                results.append(event)
                if len(results) >= limit:
                    break
            return results


class LoggingAnalyticsBackend(AnalyticsBackend):
    """Analytics backend that logs events for debugging."""

    def __init__(self, log_level: int = logging.INFO):
        self._log_level = log_level

    async def publish(self, event: CheckoutAnalyticsEvent) -> None:
        logger.log(
            self._log_level,
            "Analytics event: type=%s checkout_id=%s agent_id=%s amount=%s",
            event.event_type.value,
            event.checkout_id,
            event.agent_id,
            event.amount,
        )

    async def publish_batch(self, events: List[CheckoutAnalyticsEvent]) -> None:
        for event in events:
            await self.publish(event)

    async def query(
        self,
        event_types: Optional[List[CheckoutEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        checkout_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckoutAnalyticsEvent]:
        # Logging backend doesn't support queries
        return []


class CompositeAnalyticsBackend(AnalyticsBackend):
    """Analytics backend that publishes to multiple backends."""

    def __init__(self, backends: List[AnalyticsBackend]):
        self._backends = backends

    async def publish(self, event: CheckoutAnalyticsEvent) -> None:
        await asyncio.gather(
            *[backend.publish(event) for backend in self._backends],
            return_exceptions=True,
        )

    async def publish_batch(self, events: List[CheckoutAnalyticsEvent]) -> None:
        await asyncio.gather(
            *[backend.publish_batch(events) for backend in self._backends],
            return_exceptions=True,
        )

    async def query(
        self,
        event_types: Optional[List[CheckoutEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        checkout_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckoutAnalyticsEvent]:
        # Query from first backend that supports it
        for backend in self._backends:
            try:
                results = await backend.query(
                    event_types, start_time, end_time, agent_id, checkout_id, limit
                )
                if results:
                    return results
            except Exception:
                continue
        return []


class BufferedAnalyticsBackend(AnalyticsBackend):
    """
    Analytics backend with buffering for high-throughput scenarios.

    Events are buffered and flushed periodically or when buffer is full.
    """

    def __init__(
        self,
        backend: AnalyticsBackend,
        buffer_size: int = 100,
        flush_interval_seconds: float = 5.0,
    ):
        self._backend = backend
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval_seconds
        self._buffer: List[CheckoutAnalyticsEvent] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Stop the background flush task and flush remaining events."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self.flush()

    async def _flush_loop(self) -> None:
        """Background task to periodically flush events."""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self.flush()

    async def flush(self) -> None:
        """Flush buffered events to the underlying backend."""
        async with self._lock:
            if not self._buffer:
                return
            events = self._buffer.copy()
            self._buffer.clear()

        try:
            await self._backend.publish_batch(events)
        except Exception as e:
            logger.error(f"Failed to flush analytics events: {e}")
            # Re-add events to buffer on failure
            async with self._lock:
                self._buffer = events + self._buffer

    async def publish(self, event: CheckoutAnalyticsEvent) -> None:
        async with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self._buffer_size:
                # Trigger immediate flush
                events = self._buffer.copy()
                self._buffer.clear()

        if len(events) >= self._buffer_size:
            await self._backend.publish_batch(events)

    async def publish_batch(self, events: List[CheckoutAnalyticsEvent]) -> None:
        async with self._lock:
            self._buffer.extend(events)
            if len(self._buffer) >= self._buffer_size:
                flush_events = self._buffer.copy()
                self._buffer.clear()
            else:
                flush_events = []

        if flush_events:
            await self._backend.publish_batch(flush_events)

    async def query(
        self,
        event_types: Optional[List[CheckoutEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        checkout_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CheckoutAnalyticsEvent]:
        # Flush before querying to include recent events
        await self.flush()
        return await self._backend.query(
            event_types, start_time, end_time, agent_id, checkout_id, limit
        )


class CheckoutAnalytics:
    """
    Main analytics manager for checkout operations.

    Provides methods to track various checkout events and query analytics data.
    """

    def __init__(
        self,
        backend: Optional[AnalyticsBackend] = None,
        enabled: bool = True,
    ):
        self._backend = backend or InMemoryAnalyticsBackend()
        self._enabled = enabled
        self._context: Dict[str, Any] = {}

    def set_context(self, **kwargs: Any) -> None:
        """Set global context that will be added to all events."""
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """Clear the global context."""
        self._context.clear()

    async def track(
        self,
        event_type: CheckoutEventType,
        checkout_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        psp_name: Optional[str] = None,
        amount: Optional[Decimal] = None,
        currency: Optional[str] = None,
        status: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """
        Track a checkout analytics event.

        Args:
            event_type: Type of event
            checkout_id: Checkout session ID
            session_id: Customer session ID
            agent_id: Agent ID
            customer_id: Customer ID
            psp_name: Payment service provider name
            amount: Payment amount
            currency: Payment currency
            status: Payment/checkout status
            error_code: Error code if applicable
            error_message: Error message if applicable
            duration_ms: Operation duration in milliseconds
            metadata: Additional event metadata
            **kwargs: Additional fields added to metadata

        Returns:
            The created analytics event
        """
        if not self._enabled:
            return CheckoutAnalyticsEvent(event_type=event_type)

        # Merge context, metadata, and kwargs
        event_metadata = {**self._context, **(metadata or {}), **kwargs}

        event = CheckoutAnalyticsEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            checkout_id=checkout_id,
            session_id=session_id,
            agent_id=agent_id,
            customer_id=customer_id,
            psp_name=psp_name,
            amount=amount,
            currency=currency,
            status=status,
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata=event_metadata,
            timestamp=datetime.utcnow(),
        )

        try:
            await self._backend.publish(event)
        except Exception as e:
            logger.error(f"Failed to publish analytics event: {e}")

        return event

    async def track_session_created(
        self,
        checkout_id: str,
        agent_id: str,
        amount: Decimal,
        currency: str,
        psp_name: Optional[str] = None,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """Track checkout session creation."""
        return await self.track(
            event_type=CheckoutEventType.SESSION_CREATED,
            checkout_id=checkout_id,
            agent_id=agent_id,
            amount=amount,
            currency=currency,
            psp_name=psp_name,
            status=PaymentStatus.PENDING.value,
            **kwargs,
        )

    async def track_session_completed(
        self,
        checkout_id: str,
        agent_id: str,
        amount: Decimal,
        currency: str,
        psp_name: Optional[str] = None,
        duration_ms: Optional[int] = None,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """Track checkout session completion."""
        return await self.track(
            event_type=CheckoutEventType.SESSION_COMPLETED,
            checkout_id=checkout_id,
            agent_id=agent_id,
            amount=amount,
            currency=currency,
            psp_name=psp_name,
            status=PaymentStatus.COMPLETED.value,
            duration_ms=duration_ms,
            **kwargs,
        )

    async def track_session_expired(
        self,
        checkout_id: str,
        agent_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """Track checkout session expiration."""
        return await self.track(
            event_type=CheckoutEventType.SESSION_EXPIRED,
            checkout_id=checkout_id,
            agent_id=agent_id,
            status=PaymentStatus.EXPIRED.value,
            **kwargs,
        )

    async def track_payment_succeeded(
        self,
        checkout_id: str,
        agent_id: str,
        amount: Decimal,
        currency: str,
        psp_name: Optional[str] = None,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """Track successful payment."""
        return await self.track(
            event_type=CheckoutEventType.PAYMENT_SUCCEEDED,
            checkout_id=checkout_id,
            agent_id=agent_id,
            amount=amount,
            currency=currency,
            psp_name=psp_name,
            status=PaymentStatus.COMPLETED.value,
            **kwargs,
        )

    async def track_payment_failed(
        self,
        checkout_id: str,
        agent_id: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """Track failed payment."""
        return await self.track(
            event_type=CheckoutEventType.PAYMENT_FAILED,
            checkout_id=checkout_id,
            agent_id=agent_id,
            status=PaymentStatus.FAILED.value,
            error_code=error_code,
            error_message=error_message,
            **kwargs,
        )

    async def track_fraud_check(
        self,
        checkout_id: str,
        decision: str,
        risk_score: float,
        agent_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """Track fraud check result."""
        if decision == "approve":
            event_type = CheckoutEventType.FRAUD_CHECK_PASSED
        elif decision == "decline":
            event_type = CheckoutEventType.FRAUD_CHECK_FAILED
        else:
            event_type = CheckoutEventType.FRAUD_CHECK_REVIEW

        return await self.track(
            event_type=event_type,
            checkout_id=checkout_id,
            agent_id=agent_id,
            metadata={"decision": decision, "risk_score": risk_score, **kwargs},
        )

    async def track_webhook(
        self,
        event_type: CheckoutEventType,
        checkout_id: Optional[str] = None,
        psp_name: Optional[str] = None,
        webhook_event_type: Optional[str] = None,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """Track webhook events."""
        return await self.track(
            event_type=event_type,
            checkout_id=checkout_id,
            psp_name=psp_name,
            metadata={"webhook_event_type": webhook_event_type, **kwargs},
        )

    async def track_currency_conversion(
        self,
        checkout_id: str,
        from_currency: str,
        to_currency: str,
        from_amount: Decimal,
        to_amount: Decimal,
        exchange_rate: Decimal,
        **kwargs: Any,
    ) -> CheckoutAnalyticsEvent:
        """Track currency conversion."""
        return await self.track(
            event_type=CheckoutEventType.CURRENCY_CONVERTED,
            checkout_id=checkout_id,
            amount=to_amount,
            currency=to_currency,
            metadata={
                "from_currency": from_currency,
                "to_currency": to_currency,
                "from_amount": str(from_amount),
                "to_amount": str(to_amount),
                "exchange_rate": str(exchange_rate),
                **kwargs,
            },
        )

    async def get_conversion_rate(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate checkout conversion rate.

        Returns:
            Dict with conversion metrics
        """
        created = await self._backend.query(
            event_types=[CheckoutEventType.SESSION_CREATED],
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            limit=10000,
        )

        completed = await self._backend.query(
            event_types=[CheckoutEventType.SESSION_COMPLETED],
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            limit=10000,
        )

        total_created = len(created)
        total_completed = len(completed)

        return {
            "sessions_created": total_created,
            "sessions_completed": total_completed,
            "conversion_rate": (
                total_completed / total_created if total_created > 0 else 0.0
            ),
            "period_start": start_time,
            "period_end": end_time,
        }

    async def get_payment_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get payment metrics.

        Returns:
            Dict with payment metrics
        """
        succeeded = await self._backend.query(
            event_types=[CheckoutEventType.PAYMENT_SUCCEEDED],
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            limit=10000,
        )

        failed = await self._backend.query(
            event_types=[CheckoutEventType.PAYMENT_FAILED],
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            limit=10000,
        )

        total_amount = sum(
            event.amount for event in succeeded
            if event.amount is not None
        )

        amounts_by_currency: Dict[str, Decimal] = defaultdict(Decimal)
        for event in succeeded:
            if event.amount and event.currency:
                amounts_by_currency[event.currency] += event.amount

        return {
            "payments_succeeded": len(succeeded),
            "payments_failed": len(failed),
            "success_rate": (
                len(succeeded) / (len(succeeded) + len(failed))
                if (len(succeeded) + len(failed)) > 0
                else 0.0
            ),
            "total_amount": total_amount,
            "amounts_by_currency": dict(amounts_by_currency),
            "period_start": start_time,
            "period_end": end_time,
        }


@dataclass
class AnalyticsTimer:
    """Context manager for timing operations and tracking analytics."""

    analytics: CheckoutAnalytics
    event_type: CheckoutEventType
    checkout_id: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _start_time: Optional[float] = None

    async def __aenter__(self) -> "AnalyticsTimer":
        self._start_time = time.monotonic()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        duration_ms = int((time.monotonic() - self._start_time) * 1000)

        error_code = None
        error_message = None
        if exc_type:
            error_code = exc_type.__name__
            error_message = str(exc_val) if exc_val else None

        await self.analytics.track(
            event_type=self.event_type,
            checkout_id=self.checkout_id,
            agent_id=self.agent_id,
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
            metadata=self.metadata,
        )


def track_analytics(
    event_type: CheckoutEventType,
    checkout_id_param: Optional[str] = None,
    agent_id_param: Optional[str] = None,
):
    """
    Decorator to automatically track analytics for a method.

    Usage:
        @track_analytics(CheckoutEventType.SESSION_CREATED, checkout_id_param="checkout_id")
        async def create_checkout(self, checkout_id: str) -> CheckoutResponse:
            ...
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        async def wrapper(self, *args, **kwargs) -> T:
            analytics: Optional[CheckoutAnalytics] = getattr(self, "analytics", None)
            if not analytics:
                return await fn(self, *args, **kwargs)

            checkout_id = kwargs.get(checkout_id_param) if checkout_id_param else None
            agent_id = kwargs.get(agent_id_param) if agent_id_param else None

            start_time = time.monotonic()
            error_code = None
            error_message = None

            try:
                result = await fn(self, *args, **kwargs)
                return result
            except Exception as e:
                error_code = type(e).__name__
                error_message = str(e)
                raise
            finally:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await analytics.track(
                    event_type=event_type,
                    checkout_id=checkout_id,
                    agent_id=agent_id,
                    duration_ms=duration_ms,
                    error_code=error_code,
                    error_message=error_message,
                )

        return wrapper
    return decorator
