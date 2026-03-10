"""Cross-currency settlement orchestrator.

Picks the cheapest path for cross-currency payments:
1. USDC → Bridge → USD (existing path)
2. USDC → Grid FX → EUR → SEPA (new)
3. EURC → Striga → EUR → SEPA (new)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SettlementPath(str, Enum):
    """Available settlement paths."""
    USDC_BRIDGE_USD = "usdc_bridge_usd"
    USDC_GRID_FX_EUR = "usdc_grid_fx_eur"
    EURC_STRIGA_EUR = "eurc_striga_eur"
    DIRECT_STABLECOIN = "direct_stablecoin"


@dataclass
class SettlementQuote:
    """Quote for a cross-currency settlement."""
    path: SettlementPath
    source_currency: str
    source_amount_cents: int
    target_currency: str
    target_amount_cents: int
    exchange_rate: Decimal
    total_fee_cents: int
    fee_breakdown: dict[str, int]
    estimated_time_seconds: int

    @property
    def fee_percent(self) -> Decimal:
        if self.source_amount_cents == 0:
            return Decimal("0")
        return Decimal(self.total_fee_cents * 100) / Decimal(self.source_amount_cents)


@dataclass
class SettlementResult:
    """Result of a cross-currency settlement execution."""
    settlement_id: str
    path: SettlementPath
    source_currency: str
    source_amount_cents: int
    target_currency: str
    target_amount_cents: int
    status: str  # pending, processing, completed, failed
    provider_tx_ids: list[str]
    metadata: dict[str, Any]


class CrossCurrencySettlementService:
    """
    Orchestrates cross-currency settlement by selecting the cheapest path.

    Compares fees across available providers:
    - Bridge (USDC → USD): ~0.5%
    - Grid FX (USD ↔ EUR): ~0.5% + FX spread
    - Striga (EURC → EUR): ~0.3%

    Pattern follows FiatPaymentOrchestrator.
    """

    def __init__(
        self,
        bridge_fee_bps: int = 50,
        grid_fx_fee_bps: int = 50,
        striga_swap_fee_bps: int = 30,
    ):
        self._bridge_fee_bps = bridge_fee_bps
        self._grid_fx_fee_bps = grid_fx_fee_bps
        self._striga_swap_fee_bps = striga_swap_fee_bps

    async def get_settlement_quotes(
        self,
        source_currency: str,
        target_currency: str,
        amount_cents: int,
        fx_rate: Decimal | None = None,
    ) -> list[SettlementQuote]:
        """
        Get all available settlement quotes sorted by cheapest.

        Args:
            source_currency: Source (USDC, EURC, USD, EUR)
            target_currency: Target currency
            amount_cents: Amount in source currency cents
            fx_rate: Optional FX rate (USD/EUR). If None, uses 1.0

        Returns:
            List of SettlementQuote sorted by total_fee_cents (cheapest first)
        """
        rate = fx_rate or Decimal("1.0")
        quotes: list[SettlementQuote] = []

        # Path 1: USDC → Bridge → USD
        if source_currency.upper() in ("USDC", "USD") and target_currency.upper() == "USD":
            fee = amount_cents * self._bridge_fee_bps // 10000
            quotes.append(SettlementQuote(
                path=SettlementPath.USDC_BRIDGE_USD,
                source_currency=source_currency,
                source_amount_cents=amount_cents,
                target_currency="USD",
                target_amount_cents=amount_cents - fee,
                exchange_rate=Decimal("1.0"),
                total_fee_cents=fee,
                fee_breakdown={"bridge_offramp": fee},
                estimated_time_seconds=3600,  # ~1 hour
            ))

        # Path 2: USDC → Grid FX → EUR
        if source_currency.upper() in ("USDC", "USD") and target_currency.upper() == "EUR":
            bridge_fee = amount_cents * self._bridge_fee_bps // 10000
            eur_amount = int(Decimal(amount_cents - bridge_fee) * rate)
            fx_fee = eur_amount * self._grid_fx_fee_bps // 10000
            total_fee = bridge_fee + fx_fee
            quotes.append(SettlementQuote(
                path=SettlementPath.USDC_GRID_FX_EUR,
                source_currency=source_currency,
                source_amount_cents=amount_cents,
                target_currency="EUR",
                target_amount_cents=eur_amount - fx_fee,
                exchange_rate=rate,
                total_fee_cents=total_fee,
                fee_breakdown={"bridge_offramp": bridge_fee, "grid_fx": fx_fee},
                estimated_time_seconds=7200,  # ~2 hours
            ))

        # Path 3: EURC → Striga → EUR
        if source_currency.upper() == "EURC" and target_currency.upper() == "EUR":
            fee = amount_cents * self._striga_swap_fee_bps // 10000
            quotes.append(SettlementQuote(
                path=SettlementPath.EURC_STRIGA_EUR,
                source_currency="EURC",
                source_amount_cents=amount_cents,
                target_currency="EUR",
                target_amount_cents=amount_cents - fee,
                exchange_rate=Decimal("1.0"),
                total_fee_cents=fee,
                fee_breakdown={"striga_swap": fee},
                estimated_time_seconds=1800,  # ~30 min
            ))

        # Path for same-currency stablecoin
        if source_currency.upper() == target_currency.upper():
            quotes.append(SettlementQuote(
                path=SettlementPath.DIRECT_STABLECOIN,
                source_currency=source_currency,
                source_amount_cents=amount_cents,
                target_currency=target_currency,
                target_amount_cents=amount_cents,
                exchange_rate=Decimal("1.0"),
                total_fee_cents=0,
                fee_breakdown={},
                estimated_time_seconds=60,
            ))

        # Sort by cheapest
        quotes.sort(key=lambda q: q.total_fee_cents)
        return quotes

    async def select_optimal_path(
        self,
        source_currency: str,
        target_currency: str,
        amount_cents: int,
        fx_rate: Decimal | None = None,
    ) -> SettlementQuote | None:
        """Select the cheapest settlement path."""
        quotes = await self.get_settlement_quotes(
            source_currency, target_currency, amount_cents, fx_rate
        )
        return quotes[0] if quotes else None
