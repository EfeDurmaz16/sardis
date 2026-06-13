"""
Batch payments resource for Sardis SDK.

Sardis Protocol v1.0 -- Execute multiple payment transfers in a single
atomic operation. Supports cross-chain batching with optional mandate
enforcement.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from .._client import TimeoutConfig


class AsyncBatchResource(AsyncBaseResource):
    """Async resource for batch payment operations.

    Execute multiple transfers atomically with optional mandate
    and chain constraints.

    Example:
        ```python
        async with AsyncSardis(api_key="...") as client:
            result = await client.batch.execute(
                transfers=[
                    {"to": "0xabc...", "amount": "100.00", "token": "USDC"},
                    {"to": "0xdef...", "amount": "50.00", "token": "USDC"},
                ],
                chain="base",
                mandate_id="mnd_abc123",
            )
        ```
    """

    async def execute(
        self,
        transfers: list[dict[str, Any]],
        chain: str | None = None,
        mandate_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute a batch of payment transfers.

        Submits multiple transfers for atomic execution. All transfers
        are validated against the spending mandate (if provided) before
        any are executed.

        Args:
            transfers: List of transfer dicts with to, amount, token, and optional memo
            chain: Optional chain identifier (e.g., "base", "ethereum")
            mandate_id: Optional mandate ID for policy enforcement
            timeout: Optional request timeout

        Returns:
            Batch result with batch_id, status, and per-transfer results
        """
        payload: dict[str, Any] = {
            "transfers": transfers,
        }

        if chain is not None:
            payload["chain"] = chain

        if mandate_id is not None:
            payload["mandate_id"] = mandate_id

        return await self._post("payments/batch", payload, timeout=timeout)


class BatchResource(SyncBaseResource):
    """Sync resource for batch payment operations.

    Execute multiple transfers atomically with optional mandate
    and chain constraints.

    Example:
        ```python
        with Sardis(api_key="...") as client:
            result = client.batch.execute(
                transfers=[
                    {"to": "0xabc...", "amount": "100.00", "token": "USDC"},
                    {"to": "0xdef...", "amount": "50.00", "token": "USDC"},
                ],
                chain="base",
                mandate_id="mnd_abc123",
            )
        ```
    """

    def execute(
        self,
        transfers: list[dict[str, Any]],
        chain: str | None = None,
        mandate_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute a batch of payment transfers.

        Submits multiple transfers for atomic execution. All transfers
        are validated against the spending mandate (if provided) before
        any are executed.

        Args:
            transfers: List of transfer dicts with to, amount, token, and optional memo
            chain: Optional chain identifier (e.g., "base", "ethereum")
            mandate_id: Optional mandate ID for policy enforcement
            timeout: Optional request timeout

        Returns:
            Batch result with batch_id, status, and per-transfer results
        """
        payload: dict[str, Any] = {
            "transfers": transfers,
        }

        if chain is not None:
            payload["chain"] = chain

        if mandate_id is not None:
            payload["mandate_id"] = mandate_id

        return self._post("payments/batch", payload, timeout=timeout)


__all__ = [
    "AsyncBatchResource",
    "BatchResource",
]
