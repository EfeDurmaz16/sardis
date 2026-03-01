"""Sardis platform fee calculation and collection.

Fee is deducted from the payment amount before dispatch:
  User sends $100 → $99.50 to recipient + $0.50 to Sardis treasury.

Configuration via environment variables:
  SARDIS_PLATFORM_FEE_BPS=50        # 50 basis points = 0.50%
  SARDIS_TREASURY_ADDRESS=0x...     # Fee collection address (Base)
  SARDIS_FEE_MIN_AMOUNT=1.00        # Skip fee for amounts under $1
  SARDIS_FEE_EXEMPT_ADDRESSES=0x... # Comma-separated exempt addresses
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

logger = logging.getLogger("sardis.platform_fee")

# Default: 50 bps = 0.50%
DEFAULT_FEE_BPS = 50
# Skip fee for transfers under this amount (in token units, e.g. USDC)
DEFAULT_MIN_AMOUNT = Decimal("1.00")


@dataclass(frozen=True)
class FeeCalculation:
    """Result of a platform fee calculation."""

    original_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal  # amount that goes to recipient
    fee_bps: int
    fee_exempt: bool
    exempt_reason: str | None = None

    @property
    def fee_percentage(self) -> str:
        return f"{self.fee_bps / 100:.2f}%"


def get_fee_config() -> tuple[int, Decimal, str, set[str]]:
    """Load fee configuration from environment.

    Returns:
        (fee_bps, min_amount, treasury_address, exempt_addresses)
    """
    fee_bps = int(os.getenv("SARDIS_PLATFORM_FEE_BPS", str(DEFAULT_FEE_BPS)))
    min_amount = Decimal(os.getenv("SARDIS_FEE_MIN_AMOUNT", str(DEFAULT_MIN_AMOUNT)))
    treasury_address = os.getenv("SARDIS_TREASURY_ADDRESS", "")
    exempt_raw = os.getenv("SARDIS_FEE_EXEMPT_ADDRESSES", "")
    exempt_addresses = {
        addr.strip().lower()
        for addr in exempt_raw.split(",")
        if addr.strip()
    }
    return fee_bps, min_amount, treasury_address, exempt_addresses


def calculate_fee(
    amount: Decimal,
    *,
    destination: str = "",
    fee_bps: int | None = None,
    min_amount: Decimal | None = None,
    exempt_addresses: set[str] | None = None,
) -> FeeCalculation:
    """Calculate platform fee for a payment.

    Args:
        amount: Payment amount in token units (e.g. 50.00 USDC)
        destination: Recipient address (checked against exempt list)
        fee_bps: Override fee basis points (default from env)
        min_amount: Override minimum amount threshold
        exempt_addresses: Override exempt address set

    Returns:
        FeeCalculation with fee_amount, net_amount, and metadata
    """
    if fee_bps is None or min_amount is None or exempt_addresses is None:
        env_bps, env_min, _, env_exempt = get_fee_config()
        if fee_bps is None:
            fee_bps = env_bps
        if min_amount is None:
            min_amount = env_min
        if exempt_addresses is None:
            exempt_addresses = env_exempt

    # Fee disabled
    if fee_bps <= 0:
        return FeeCalculation(
            original_amount=amount,
            fee_amount=Decimal("0"),
            net_amount=amount,
            fee_bps=0,
            fee_exempt=True,
            exempt_reason="fee_disabled",
        )

    # Amount too small
    if amount < min_amount:
        return FeeCalculation(
            original_amount=amount,
            fee_amount=Decimal("0"),
            net_amount=amount,
            fee_bps=fee_bps,
            fee_exempt=True,
            exempt_reason="below_minimum",
        )

    # Exempt address (e.g. Sardis treasury, internal transfers)
    if destination and destination.lower() in exempt_addresses:
        return FeeCalculation(
            original_amount=amount,
            fee_amount=Decimal("0"),
            net_amount=amount,
            fee_bps=fee_bps,
            fee_exempt=True,
            exempt_reason="exempt_address",
        )

    # Calculate fee: amount * (bps / 10000), rounded down to 6 decimals (USDC precision)
    fee_amount = (amount * Decimal(fee_bps) / Decimal(10000)).quantize(
        Decimal("0.000001"), rounding=ROUND_DOWN
    )

    # Ensure fee doesn't exceed amount
    if fee_amount >= amount:
        fee_amount = Decimal("0")
        return FeeCalculation(
            original_amount=amount,
            fee_amount=Decimal("0"),
            net_amount=amount,
            fee_bps=fee_bps,
            fee_exempt=True,
            exempt_reason="fee_exceeds_amount",
        )

    net_amount = amount - fee_amount

    return FeeCalculation(
        original_amount=amount,
        fee_amount=fee_amount,
        net_amount=net_amount,
        fee_bps=fee_bps,
        fee_exempt=False,
    )


def get_treasury_address() -> str | None:
    """Get the Sardis treasury address for fee collection.

    Returns None if not configured (fees will be skipped).
    """
    addr = os.getenv("SARDIS_TREASURY_ADDRESS", "").strip()
    if not addr or not addr.startswith("0x") or len(addr) != 42:
        return None
    return addr
