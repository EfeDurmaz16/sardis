"""
Streaming payments resource for Sardis SDK.

Sardis Protocol v1.0 -- Open, consume, and settle continuous payment
streams between agents and services. Supports usage-based billing
with real-time settlement.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from .._client import TimeoutConfig


class AsyncStreamingResource(AsyncBaseResource):
    """Async resource for streaming payment operations.

    Open, consume, and settle continuous payment streams for
    usage-based billing between agents and services.

    Example:
        ```python
        async with AsyncSardis(api_key="...") as client:
            # Open a payment stream
            stream = await client.streaming.open(
                from_wallet="wal_abc123",
                to="0xdef...",
                token="USDC",
                max_amount="1000.00",
                rate_per_unit="0.01",
            )

            # Consume units
            result = await client.streaming.consume(
                stream_id=stream["stream_id"],
                units=50,
            )

            # Settle when done
            settlement = await client.streaming.settle(
                stream_id=stream["stream_id"],
            )
        ```
    """

    async def open(
        self,
        from_wallet: str,
        to: str,
        token: str,
        max_amount: str,
        rate_per_unit: str | None = None,
        chain: str | None = None,
        mandate_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Open a new payment stream.

        Creates a continuous payment channel between a wallet and a
        recipient. Funds are reserved up to max_amount but only
        consumed incrementally.

        Args:
            from_wallet: Source wallet ID
            to: Recipient address or wallet ID
            token: Token for the stream (e.g., "USDC")
            max_amount: Maximum amount that can be consumed
            rate_per_unit: Optional cost per consumption unit
            chain: Optional chain identifier
            mandate_id: Optional mandate ID for policy enforcement
            metadata: Optional metadata dict
            timeout: Optional request timeout

        Returns:
            Stream details with stream_id and status
        """
        payload: dict[str, Any] = {
            "from_wallet": from_wallet,
            "to": to,
            "token": token,
            "max_amount": max_amount,
        }

        if rate_per_unit is not None:
            payload["rate_per_unit"] = rate_per_unit

        if chain is not None:
            payload["chain"] = chain

        if mandate_id is not None:
            payload["mandate_id"] = mandate_id

        if metadata is not None:
            payload["metadata"] = metadata

        return await self._post("payments/stream/open", payload, timeout=timeout)

    async def consume(
        self,
        stream_id: str,
        units: int,
        memo: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Consume units from an active payment stream.

        Deducts the specified number of units from the stream at the
        configured rate per unit.

        Args:
            stream_id: The stream ID to consume from
            units: Number of units to consume
            memo: Optional memo for the consumption
            timeout: Optional request timeout

        Returns:
            Consumption result with updated balances
        """
        payload: dict[str, Any] = {
            "units": units,
        }

        if memo is not None:
            payload["memo"] = memo

        return await self._post(
            f"payments/stream/{stream_id}/consume", payload, timeout=timeout
        )

    async def settle(
        self,
        stream_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Settle and close a payment stream.

        Finalizes the stream, settling any remaining balance. Unconsumed
        funds are returned to the source wallet.

        Args:
            stream_id: The stream ID to settle
            timeout: Optional request timeout

        Returns:
            Settlement result with final amounts
        """
        return await self._post(
            f"payments/stream/{stream_id}/settle", timeout=timeout
        )


class StreamingResource(SyncBaseResource):
    """Sync resource for streaming payment operations.

    Open, consume, and settle continuous payment streams for
    usage-based billing between agents and services.

    Example:
        ```python
        with Sardis(api_key="...") as client:
            # Open a payment stream
            stream = client.streaming.open(
                from_wallet="wal_abc123",
                to="0xdef...",
                token="USDC",
                max_amount="1000.00",
                rate_per_unit="0.01",
            )

            # Consume units
            result = client.streaming.consume(
                stream_id=stream["stream_id"],
                units=50,
            )

            # Settle when done
            settlement = client.streaming.settle(
                stream_id=stream["stream_id"],
            )
        ```
    """

    def open(
        self,
        from_wallet: str,
        to: str,
        token: str,
        max_amount: str,
        rate_per_unit: str | None = None,
        chain: str | None = None,
        mandate_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Open a new payment stream.

        Creates a continuous payment channel between a wallet and a
        recipient. Funds are reserved up to max_amount but only
        consumed incrementally.

        Args:
            from_wallet: Source wallet ID
            to: Recipient address or wallet ID
            token: Token for the stream (e.g., "USDC")
            max_amount: Maximum amount that can be consumed
            rate_per_unit: Optional cost per consumption unit
            chain: Optional chain identifier
            mandate_id: Optional mandate ID for policy enforcement
            metadata: Optional metadata dict
            timeout: Optional request timeout

        Returns:
            Stream details with stream_id and status
        """
        payload: dict[str, Any] = {
            "from_wallet": from_wallet,
            "to": to,
            "token": token,
            "max_amount": max_amount,
        }

        if rate_per_unit is not None:
            payload["rate_per_unit"] = rate_per_unit

        if chain is not None:
            payload["chain"] = chain

        if mandate_id is not None:
            payload["mandate_id"] = mandate_id

        if metadata is not None:
            payload["metadata"] = metadata

        return self._post("payments/stream/open", payload, timeout=timeout)

    def consume(
        self,
        stream_id: str,
        units: int,
        memo: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Consume units from an active payment stream.

        Deducts the specified number of units from the stream at the
        configured rate per unit.

        Args:
            stream_id: The stream ID to consume from
            units: Number of units to consume
            memo: Optional memo for the consumption
            timeout: Optional request timeout

        Returns:
            Consumption result with updated balances
        """
        payload: dict[str, Any] = {
            "units": units,
        }

        if memo is not None:
            payload["memo"] = memo

        return self._post(
            f"payments/stream/{stream_id}/consume", payload, timeout=timeout
        )

    def settle(
        self,
        stream_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Settle and close a payment stream.

        Finalizes the stream, settling any remaining balance. Unconsumed
        funds are returned to the source wallet.

        Args:
            stream_id: The stream ID to settle
            timeout: Optional request timeout

        Returns:
            Settlement result with final amounts
        """
        return self._post(
            f"payments/stream/{stream_id}/settle", timeout=timeout
        )


__all__ = [
    "AsyncStreamingResource",
    "StreamingResource",
]
