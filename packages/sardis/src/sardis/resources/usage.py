"""
Usage metering resource for Sardis SDK.

Sardis Protocol v1.0 -- Report and query usage meters for
consumption-based billing. Meters track agent resource usage
and feed into invoicing pipelines.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from .._client import TimeoutConfig


class AsyncUsageResource(AsyncBaseResource):
    """Async resource for usage metering operations.

    Report usage events and query meters for consumption-based
    billing.

    Example:
        ```python
        async with AsyncSardis(api_key="...") as client:
            # Report usage
            event = await client.usage.report(
                meter_id="mtr_abc123",
                quantity=42,
                idempotency_key="evt_unique_001",
            )

            # Get a specific meter
            meter = await client.usage.get_meter(
                meter_id="mtr_abc123",
            )

            # List all meters
            meters = await client.usage.list_meters(limit=20)
        ```
    """

    async def report(
        self,
        meter_id: str,
        quantity: int,
        timestamp: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Report a usage event.

        Records a metered usage event against a specific meter.
        Supports idempotency keys for safe retry behavior.

        Args:
            meter_id: The meter to record usage against
            quantity: Number of units consumed
            timestamp: Optional event timestamp (ISO 8601); defaults to now
            idempotency_key: Optional key for deduplication
            metadata: Optional metadata dict
            timeout: Optional request timeout

        Returns:
            Recorded usage event with event_id and timestamp
        """
        payload: dict[str, Any] = {
            "meter_id": meter_id,
            "quantity": quantity,
        }

        if timestamp is not None:
            payload["timestamp"] = timestamp

        if idempotency_key is not None:
            payload["idempotency_key"] = idempotency_key

        if metadata is not None:
            payload["metadata"] = metadata

        return await self._post("usage/report", payload, timeout=timeout)

    async def get_meter(
        self,
        meter_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a specific usage meter.

        Returns the current state of a meter including total and
        current-period usage.

        Args:
            meter_id: The meter ID to retrieve
            timeout: Optional request timeout

        Returns:
            Meter details with usage totals and period info
        """
        return await self._get(
            f"usage/meters/{meter_id}", timeout=timeout
        )

    async def list_meters(
        self,
        limit: int | None = None,
        offset: int | None = None,
        agent_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """List usage meters.

        Returns a paginated list of meters, optionally filtered
        by agent.

        Args:
            limit: Maximum number of meters to return
            offset: Pagination offset
            agent_id: Optional agent ID filter
            timeout: Optional request timeout

        Returns:
            Paginated list of usage meters
        """
        params: dict[str, Any] = {}

        if limit is not None:
            params["limit"] = limit

        if offset is not None:
            params["offset"] = offset

        if agent_id is not None:
            params["agent_id"] = agent_id

        return await self._get("usage/meters", params=params, timeout=timeout)


class UsageResource(SyncBaseResource):
    """Sync resource for usage metering operations.

    Report usage events and query meters for consumption-based
    billing.

    Example:
        ```python
        with Sardis(api_key="...") as client:
            # Report usage
            event = client.usage.report(
                meter_id="mtr_abc123",
                quantity=42,
                idempotency_key="evt_unique_001",
            )

            # Get a specific meter
            meter = client.usage.get_meter(
                meter_id="mtr_abc123",
            )

            # List all meters
            meters = client.usage.list_meters(limit=20)
        ```
    """

    def report(
        self,
        meter_id: str,
        quantity: int,
        timestamp: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Report a usage event.

        Records a metered usage event against a specific meter.
        Supports idempotency keys for safe retry behavior.

        Args:
            meter_id: The meter to record usage against
            quantity: Number of units consumed
            timestamp: Optional event timestamp (ISO 8601); defaults to now
            idempotency_key: Optional key for deduplication
            metadata: Optional metadata dict
            timeout: Optional request timeout

        Returns:
            Recorded usage event with event_id and timestamp
        """
        payload: dict[str, Any] = {
            "meter_id": meter_id,
            "quantity": quantity,
        }

        if timestamp is not None:
            payload["timestamp"] = timestamp

        if idempotency_key is not None:
            payload["idempotency_key"] = idempotency_key

        if metadata is not None:
            payload["metadata"] = metadata

        return self._post("usage/report", payload, timeout=timeout)

    def get_meter(
        self,
        meter_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a specific usage meter.

        Returns the current state of a meter including total and
        current-period usage.

        Args:
            meter_id: The meter ID to retrieve
            timeout: Optional request timeout

        Returns:
            Meter details with usage totals and period info
        """
        return self._get(
            f"usage/meters/{meter_id}", timeout=timeout
        )

    def list_meters(
        self,
        limit: int | None = None,
        offset: int | None = None,
        agent_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """List usage meters.

        Returns a paginated list of meters, optionally filtered
        by agent.

        Args:
            limit: Maximum number of meters to return
            offset: Pagination offset
            agent_id: Optional agent ID filter
            timeout: Optional request timeout

        Returns:
            Paginated list of usage meters
        """
        params: dict[str, Any] = {}

        if limit is not None:
            params["limit"] = limit

        if offset is not None:
            params["offset"] = offset

        if agent_id is not None:
            params["agent_id"] = agent_id

        return self._get("usage/meters", params=params, timeout=timeout)


__all__ = [
    "AsyncUsageResource",
    "UsageResource",
]
