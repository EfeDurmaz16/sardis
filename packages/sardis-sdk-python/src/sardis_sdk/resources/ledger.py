"""
Ledger resource for Sardis SDK.

This module provides both async and sync interfaces for ledger operations.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    from ..client import TimeoutConfig


class LedgerEntry(BaseModel):
    """A ledger entry."""

    tx_id: str
    mandate_id: str | None = None
    from_wallet: str | None = None
    to_wallet: str | None = None
    amount: Decimal
    currency: str
    chain: str | None = None
    chain_tx_hash: str | None = None
    audit_anchor: str | None = None
    created_at: datetime


class AsyncLedgerResource(AsyncBaseResource):
    """Async resource for ledger operations.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # List ledger entries
            entries = await client.ledger.list_entries(wallet_id="wallet_123")

            # Verify an entry
            result = await client.ledger.verify_entry(tx_id="tx_123")
        ```
    """

    async def list_entries(
        self,
        wallet_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[LedgerEntry]:
        """List ledger entries.

        Args:
            wallet_id: Filter by wallet ID
            limit: Maximum number of entries
            offset: Pagination offset
            timeout: Optional request timeout

        Returns:
            List of ledger entries
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if wallet_id:
            params["wallet_id"] = wallet_id
        response = await self._get("/api/v2/ledger/entries", params=params, timeout=timeout)
        return [LedgerEntry.model_validate(e) for e in response.get("entries", [])]

    async def get_entry(
        self,
        tx_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> LedgerEntry:
        """Get a ledger entry by transaction ID.

        Args:
            tx_id: Transaction ID
            timeout: Optional request timeout

        Returns:
            Ledger entry
        """
        response = await self._get(f"/api/v2/ledger/entries/{tx_id}", timeout=timeout)
        return LedgerEntry.model_validate(response)

    async def verify_entry(
        self,
        tx_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, bool]:
        """Verify a ledger entry's audit anchor.

        Args:
            tx_id: Transaction ID
            timeout: Optional request timeout

        Returns:
            Verification result
        """
        return await self._get(f"/api/v2/ledger/entries/{tx_id}/verify", timeout=timeout)


class LedgerResource(SyncBaseResource):
    """Sync resource for ledger operations.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # List ledger entries
            entries = client.ledger.list_entries(wallet_id="wallet_123")

            # Verify an entry
            result = client.ledger.verify_entry(tx_id="tx_123")
        ```
    """

    def list_entries(
        self,
        wallet_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[LedgerEntry]:
        """List ledger entries.

        Args:
            wallet_id: Filter by wallet ID
            limit: Maximum number of entries
            offset: Pagination offset
            timeout: Optional request timeout

        Returns:
            List of ledger entries
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if wallet_id:
            params["wallet_id"] = wallet_id
        response = self._get("/api/v2/ledger/entries", params=params, timeout=timeout)
        return [LedgerEntry.model_validate(e) for e in response.get("entries", [])]

    def get_entry(
        self,
        tx_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> LedgerEntry:
        """Get a ledger entry by transaction ID.

        Args:
            tx_id: Transaction ID
            timeout: Optional request timeout

        Returns:
            Ledger entry
        """
        response = self._get(f"/api/v2/ledger/entries/{tx_id}", timeout=timeout)
        return LedgerEntry.model_validate(response)

    def verify_entry(
        self,
        tx_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, bool]:
        """Verify a ledger entry's audit anchor.

        Args:
            tx_id: Transaction ID
            timeout: Optional request timeout

        Returns:
            Verification result
        """
        return self._get(f"/api/v2/ledger/entries/{tx_id}/verify", timeout=timeout)


__all__ = [
    "AsyncLedgerResource",
    "LedgerEntry",
    "LedgerResource",
]
