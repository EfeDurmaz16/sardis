"""
FX resource for Sardis SDK.

Sardis Protocol v1.0 -- Foreign exchange and cross-chain bridging
operations. Provides real-time quotes, execution of currency swaps,
live rate feeds, and cross-chain token bridging.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from decimal import Decimal

    from ..client import TimeoutConfig


class AsyncFXResource(AsyncBaseResource):
    """Async resource for foreign exchange and bridging operations.

    Provides currency conversion quotes, execution, live rate feeds,
    and cross-chain token bridging.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Get a quote for USDC -> EURC conversion
            quote = await client.fx.quote(
                from_currency="USDC",
                to_currency="EURC",
                from_amount=Decimal("1000.00"),
            )

            # Execute the quoted swap
            result = await client.fx.execute(quote_id=quote["id"])

            # Bridge tokens cross-chain
            bridge_result = await client.fx.bridge(
                from_chain="ethereum",
                to_chain="base",
                token="USDC",
                amount=Decimal("500.00"),
            )
        ```
    """

    async def quote(
        self,
        from_currency: str,
        to_currency: str,
        from_amount: Decimal,
        chain: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a foreign exchange quote.

        Args:
            from_currency: Source currency code (e.g., "USDC")
            to_currency: Target currency code (e.g., "EURC")
            from_amount: Amount to convert in source currency
            chain: Optional chain for on-chain swap routing
            timeout: Optional request timeout

        Returns:
            Quote with exchange rate, output amount, and expiry
        """
        payload: dict[str, Any] = {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "from_amount": str(from_amount),
        }

        if chain is not None:
            payload["chain"] = chain

        return await self._post("fx/quote", payload, timeout=timeout)

    async def execute(
        self,
        quote_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute a previously obtained FX quote.

        Args:
            quote_id: The quote ID to execute
            timeout: Optional request timeout

        Returns:
            Execution result with transaction details
        """
        payload: dict[str, Any] = {
            "quote_id": quote_id,
        }

        return await self._post("fx/execute", payload, timeout=timeout)

    async def rates(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get current FX rates for all supported currency pairs.

        Args:
            timeout: Optional request timeout

        Returns:
            Dictionary of currency pair rates
        """
        return await self._get("fx/rates", timeout=timeout)

    async def bridge(
        self,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: Decimal,
        provider: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Bridge tokens between chains.

        Args:
            from_chain: Source chain identifier (e.g., "ethereum")
            to_chain: Destination chain identifier (e.g., "base")
            token: Token to bridge (e.g., "USDC")
            amount: Amount to bridge
            provider: Optional bridge provider (e.g., "cctp", "stargate")
            timeout: Optional request timeout

        Returns:
            Bridge transaction result with status and tracking info
        """
        payload: dict[str, Any] = {
            "from_chain": from_chain,
            "to_chain": to_chain,
            "token": token,
            "amount": str(amount),
        }

        if provider is not None:
            payload["provider"] = provider

        return await self._post("fx/bridge", payload, timeout=timeout)


class FXResource(SyncBaseResource):
    """Sync resource for foreign exchange and bridging operations.

    Provides currency conversion quotes, execution, live rate feeds,
    and cross-chain token bridging.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Get a quote for USDC -> EURC conversion
            quote = client.fx.quote(
                from_currency="USDC",
                to_currency="EURC",
                from_amount=Decimal("1000.00"),
            )

            # Execute the quoted swap
            result = client.fx.execute(quote_id=quote["id"])

            # Bridge tokens cross-chain
            bridge_result = client.fx.bridge(
                from_chain="ethereum",
                to_chain="base",
                token="USDC",
                amount=Decimal("500.00"),
            )
        ```
    """

    def quote(
        self,
        from_currency: str,
        to_currency: str,
        from_amount: Decimal,
        chain: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a foreign exchange quote.

        Args:
            from_currency: Source currency code (e.g., "USDC")
            to_currency: Target currency code (e.g., "EURC")
            from_amount: Amount to convert in source currency
            chain: Optional chain for on-chain swap routing
            timeout: Optional request timeout

        Returns:
            Quote with exchange rate, output amount, and expiry
        """
        payload: dict[str, Any] = {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "from_amount": str(from_amount),
        }

        if chain is not None:
            payload["chain"] = chain

        return self._post("fx/quote", payload, timeout=timeout)

    def execute(
        self,
        quote_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute a previously obtained FX quote.

        Args:
            quote_id: The quote ID to execute
            timeout: Optional request timeout

        Returns:
            Execution result with transaction details
        """
        payload: dict[str, Any] = {
            "quote_id": quote_id,
        }

        return self._post("fx/execute", payload, timeout=timeout)

    def rates(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get current FX rates for all supported currency pairs.

        Args:
            timeout: Optional request timeout

        Returns:
            Dictionary of currency pair rates
        """
        return self._get("fx/rates", timeout=timeout)

    def bridge(
        self,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: Decimal,
        provider: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Bridge tokens between chains.

        Args:
            from_chain: Source chain identifier (e.g., "ethereum")
            to_chain: Destination chain identifier (e.g., "base")
            token: Token to bridge (e.g., "USDC")
            amount: Amount to bridge
            provider: Optional bridge provider (e.g., "cctp", "stargate")
            timeout: Optional request timeout

        Returns:
            Bridge transaction result with status and tracking info
        """
        payload: dict[str, Any] = {
            "from_chain": from_chain,
            "to_chain": to_chain,
            "token": token,
            "amount": str(amount),
        }

        if provider is not None:
            payload["provider"] = provider

        return self._post("fx/bridge", payload, timeout=timeout)


__all__ = [
    "AsyncFXResource",
    "FXResource",
]
