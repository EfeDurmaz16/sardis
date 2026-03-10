"""Lightspark Grid FX service — cross-currency exchange rates."""
from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any

from .client import GridClient

logger = logging.getLogger(__name__)


class GridFXService:
    """
    FX service wrapping Grid's foreign exchange API.

    Features:
    - Exchange rate retrieval with caching (~5 min TTL)
    - Cross-currency conversion
    - Rate comparison for settlement path selection
    """

    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(self, client: GridClient):
        self._client = client
        self._rate_cache: dict[str, tuple[Decimal, float]] = {}  # key -> (rate, timestamp)

    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """
        Get exchange rate between two currencies.

        Cached for ~5 minutes to reduce API calls.

        Args:
            from_currency: Source currency (USD, EUR, etc.)
            to_currency: Target currency

        Returns:
            Exchange rate as Decimal
        """
        cache_key = f"{from_currency.upper()}_{to_currency.upper()}"

        # Check cache
        cached = self._rate_cache.get(cache_key)
        if cached:
            rate, ts = cached
            if time.time() - ts < self.CACHE_TTL_SECONDS:
                return rate

        # Fetch from Grid
        result = await self._client.request(
            "GET",
            "/fx/rates",
            params={
                "from": from_currency.upper(),
                "to": to_currency.upper(),
            },
        )

        rate = Decimal(result.get("rate", result.get("exchangeRate", "1.0")))

        # Cache the rate
        self._rate_cache[cache_key] = (rate, time.time())

        # Also cache inverse
        if rate > 0:
            inverse_key = f"{to_currency.upper()}_{from_currency.upper()}"
            self._rate_cache[inverse_key] = (Decimal("1") / rate, time.time())

        return rate

    async def convert(
        self,
        amount_cents: int,
        from_currency: str,
        to_currency: str,
    ) -> dict[str, Any]:
        """
        Convert amount between currencies using Grid FX.

        Args:
            amount_cents: Amount in source currency cents
            from_currency: Source currency
            to_currency: Target currency

        Returns:
            Dict with converted amount, rate, and fee
        """
        rate = await self.get_exchange_rate(from_currency, to_currency)

        # Apply rate
        converted_cents = int(Decimal(amount_cents) * rate)

        # Estimate fee (~0.5% for FX)
        fee_cents = max(1, amount_cents * 50 // 10000)

        return {
            "source_currency": from_currency.upper(),
            "source_amount_cents": amount_cents,
            "target_currency": to_currency.upper(),
            "target_amount_cents": converted_cents - fee_cents,
            "exchange_rate": str(rate),
            "fee_cents": fee_cents,
            "fee_percent": "0.50",
        }

    def clear_cache(self) -> None:
        """Clear the rate cache."""
        self._rate_cache.clear()

    def get_cached_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Decimal | None:
        """Get cached rate without API call. Returns None if not cached or expired."""
        cache_key = f"{from_currency.upper()}_{to_currency.upper()}"
        cached = self._rate_cache.get(cache_key)
        if cached:
            rate, ts = cached
            if time.time() - ts < self.CACHE_TTL_SECONDS:
                return rate
        return None
