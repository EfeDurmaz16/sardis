"""
Pay resource for Sardis SDK — the simplest way to execute a payment.

Calls POST /api/v2/pay which validates inputs, enforces policy, and
executes the payment on-chain in a single call.

Phase 2: `chain` is now optional. When omitted, Sardis auto-selects
the cheapest route across supported chains.

Phase 3: Cross-currency FX. When ``currency`` differs from the sender's
token (e.g. sender has USDC, ``currency="EUR"``), Sardis auto-swaps via
the best FX adapter (Tempo DEX or Uniswap V3) before transferring.
The response includes an ``fx`` field with rate, provider, and slippage.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from .._client import TimeoutConfig


class AsyncPayResource(AsyncBaseResource):
    """Async resource for the unified pay endpoint.

    Example:
        ```python
        async with AsyncSardis(api_key="...") as client:
            # Auto-route (cheapest chain)
            result = await client.pay.execute(
                to="0xabc...",
                amount="25.00",
            )

            # Explicit chain (iron rule — always wins)
            result = await client.pay.execute(
                to="0xabc...",
                amount="25.00",
                chain="base",
            )

            # Cross-currency: send EUR (auto-swaps USDC→EURC)
            result = await client.pay.execute(
                to="merchant@eu",
                amount="100.00",
                currency="EUR",
            )
            print(result["fx"])
            # {"from_currency": "USDC", "to_currency": "EURC",
            #  "rate": "0.9215", "provider": "tempo_dex", ...}
        ```
    """

    async def execute(
        self,
        to: str,
        amount: str,
        currency: str = "USDC",
        chain: str | None = None,
        mandate_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute a payment.

        Args:
            to: Recipient address or merchant domain
            amount: Payment amount as string (e.g. "25.00")
            currency: Token or fiat currency code. Supported values:
                USDC, EURC, USDT, USD, EUR. When a fiat code is used
                (e.g. "EUR"), Sardis auto-swaps the sender's token
                to the corresponding stablecoin (USDC->EURC).
            chain: Target blockchain. If omitted, Sardis auto-selects
                   the cheapest route across supported chains.
            mandate_id: Optional spending mandate ID
            timeout: Optional request timeout

        Returns:
            Dict with status, tx_hash, ledger_tx_id, chain, message,
            mandate_id, route (chain/provider/fee metadata), and
            fx (FX swap details, only present for cross-currency payments).
        """
        payload: dict[str, Any] = {
            "to": to,
            "amount": amount,
            "currency": currency,
        }
        if chain is not None:
            payload["chain"] = chain
        if mandate_id is not None:
            payload["mandate_id"] = mandate_id

        return await self._post("pay", payload, timeout=timeout)


class PayResource(SyncBaseResource):
    """Sync resource for the unified pay endpoint.

    Example:
        ```python
        with Sardis(api_key="...") as client:
            # Auto-route (cheapest chain)
            result = client.pay.execute(
                to="0xabc...",
                amount="25.00",
            )

            # Explicit chain (iron rule — always wins)
            result = client.pay.execute(
                to="0xabc...",
                amount="25.00",
                chain="base",
            )

            # Cross-currency: send EUR (auto-swaps USDC→EURC)
            result = client.pay.execute(
                to="merchant@eu",
                amount="100.00",
                currency="EUR",
            )
            print(result["fx"])
            # {"from_currency": "USDC", "to_currency": "EURC",
            #  "rate": "0.9215", "provider": "tempo_dex", ...}
        ```
    """

    def execute(
        self,
        to: str,
        amount: str,
        currency: str = "USDC",
        chain: str | None = None,
        mandate_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute a payment.

        Args:
            to: Recipient address or merchant domain
            amount: Payment amount as string (e.g. "25.00")
            currency: Token or fiat currency code. Supported values:
                USDC, EURC, USDT, USD, EUR. When a fiat code is used
                (e.g. "EUR"), Sardis auto-swaps the sender's token
                to the corresponding stablecoin (USDC->EURC).
            chain: Target blockchain. If omitted, Sardis auto-selects
                   the cheapest route across supported chains.
            mandate_id: Optional spending mandate ID
            timeout: Optional request timeout

        Returns:
            Dict with status, tx_hash, ledger_tx_id, chain, message,
            mandate_id, route (chain/provider/fee metadata), and
            fx (FX swap details, only present for cross-currency payments).
        """
        payload: dict[str, Any] = {
            "to": to,
            "amount": amount,
            "currency": currency,
        }
        if chain is not None:
            payload["chain"] = chain
        if mandate_id is not None:
            payload["mandate_id"] = mandate_id

        return self._post("pay", payload, timeout=timeout)


__all__ = [
    "AsyncPayResource",
    "PayResource",
]
