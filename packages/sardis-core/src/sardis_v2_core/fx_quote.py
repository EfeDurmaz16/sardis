"""FX Quote — cross-currency exchange rate quotes for stablecoin swaps.

Sardis routes FX through chain-native infrastructure:
- Tempo: enshrined DEX orderbook at 0xdec0...
- Base: Uniswap V3/V4 pools
- Other EVM: DEX aggregators

Usage::

    quote = FXQuote(
        from_currency="USDC",
        to_currency="EURC",
        from_amount=Decimal("100.00"),
        rate=Decimal("0.9215"),
        provider="tempo_dex",
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.fx")


class FXProvider(str, Enum):
    """Available FX execution venues."""
    TEMPO_DEX = "tempo_dex"          # Tempo enshrined orderbook
    UNISWAP_V3 = "uniswap_v3"       # Uniswap V3 on Base/ETH
    UNISWAP_V4 = "uniswap_v4"       # Uniswap V4
    ONE_INCH = "1inch"               # 1inch aggregator
    PARASWAP = "paraswap"            # Paraswap aggregator


class QuoteStatus(str, Enum):
    """Lifecycle states for an FX quote."""
    PENDING = "pending"              # Quote requested, awaiting price
    QUOTED = "quoted"                # Price received, awaiting execution
    EXECUTING = "executing"          # Swap in progress
    COMPLETED = "completed"          # Swap settled
    EXPIRED = "expired"              # Quote expired before execution
    FAILED = "failed"                # Swap failed on-chain


@dataclass
class FXQuote:
    """A foreign exchange quote for a stablecoin swap."""

    # Identity
    quote_id: str = field(default_factory=lambda: f"fxq_{uuid4().hex[:12]}")

    # Currencies
    from_currency: str = "USDC"
    to_currency: str = "EURC"

    # Amounts
    from_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    to_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    rate: Decimal = field(default_factory=lambda: Decimal("1.0"))
    slippage_bps: int = 50  # 0.5% default slippage tolerance

    # Execution
    provider: FXProvider = FXProvider.TEMPO_DEX
    chain: str = "tempo"
    tx_hash: str | None = None

    # Lifecycle
    status: QuoteStatus = QuoteStatus.QUOTED
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(seconds=30)
    )

    # Audit
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires_at

    @property
    def effective_rate(self) -> Decimal:
        """The effective rate including fees."""
        if self.from_amount > 0:
            return self.to_amount / self.from_amount
        return self.rate

    def compute_to_amount(self) -> Decimal:
        """Calculate to_amount from from_amount and rate."""
        return (self.from_amount * self.rate).quantize(Decimal("0.000001"))


@dataclass
class BridgeTransfer:
    """A cross-chain bridge transfer."""

    transfer_id: str = field(default_factory=lambda: f"brt_{uuid4().hex[:12]}")

    # Route
    from_chain: str = "tempo"
    to_chain: str = "base"
    token: str = "USDC"
    amount: Decimal = field(default_factory=lambda: Decimal("0"))

    # Bridge
    bridge_provider: str = "relay"  # relay, across, squid, bungee, layerzero
    bridge_fee: Decimal = field(default_factory=lambda: Decimal("0"))

    # Hashes
    source_tx_hash: str | None = None
    destination_tx_hash: str | None = None

    # Status
    status: str = "pending"  # pending, bridging, completed, failed
    estimated_seconds: int = 60

    # Audit
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
