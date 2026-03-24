"""
Pay resource for Sardis SDK — the simplest way to execute a payment.

Calls POST /api/v2/pay which validates inputs, enforces policy, and
executes the payment on-chain in a single call.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncPayResource(AsyncBaseResource):
    """Async resource for the unified pay endpoint.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            result = await client.pay.execute(
                to="0xabc...",
                amount="25.00",
                currency="USDC",
                chain="base",
            )
        ```
    """

    async def execute(
        self,
        to: str,
        amount: str,
        currency: str = "USDC",
        chain: str = "base",
        mandate_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute a payment.

        Args:
            to: Recipient address or merchant domain
            amount: Payment amount as string (e.g. "25.00")
            currency: Token (default USDC)
            chain: Target blockchain (default base)
            mandate_id: Optional spending mandate ID
            timeout: Optional request timeout

        Returns:
            Dict with status, tx_hash, ledger_tx_id, chain, message, mandate_id
        """
        payload: dict[str, Any] = {
            "to": to,
            "amount": amount,
            "currency": currency,
            "chain": chain,
        }
        if mandate_id is not None:
            payload["mandate_id"] = mandate_id

        return await self._post("pay", payload, timeout=timeout)


class PayResource(SyncBaseResource):
    """Sync resource for the unified pay endpoint.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            result = client.pay.execute(
                to="0xabc...",
                amount="25.00",
                currency="USDC",
                chain="base",
            )
        ```
    """

    def execute(
        self,
        to: str,
        amount: str,
        currency: str = "USDC",
        chain: str = "base",
        mandate_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute a payment.

        Args:
            to: Recipient address or merchant domain
            amount: Payment amount as string (e.g. "25.00")
            currency: Token (default USDC)
            chain: Target blockchain (default base)
            mandate_id: Optional spending mandate ID
            timeout: Optional request timeout

        Returns:
            Dict with status, tx_hash, ledger_tx_id, chain, message, mandate_id
        """
        payload: dict[str, Any] = {
            "to": to,
            "amount": amount,
            "currency": currency,
            "chain": chain,
        }
        if mandate_id is not None:
            payload["mandate_id"] = mandate_id

        return self._post("pay", payload, timeout=timeout)


__all__ = [
    "AsyncPayResource",
    "PayResource",
]
