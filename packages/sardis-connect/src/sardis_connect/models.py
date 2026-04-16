"""Models for Sardis Connect merchant SDK."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class PricingModel(str, Enum):
    """How the endpoint is priced."""
    PER_CALL = "per_call"
    PER_UNIT = "per_unit"  # e.g., per token, per image, per MB
    SUBSCRIPTION = "subscription"


@dataclass(frozen=True)
class PricingTier:
    """A pricing tier for an endpoint."""
    name: str = "default"
    price: Decimal = Decimal("0.01")
    currency: str = "USD"
    model: PricingModel = PricingModel.PER_CALL
    unit_name: str | None = None  # e.g., "token", "image", "request"
    description: str | None = None


@dataclass(frozen=True)
class PricedEndpoint:
    """An API endpoint with pricing metadata.

    Example:
        PricedEndpoint(
            path="/api/generate",
            method="POST",
            price=Decimal("0.05"),
            description="Generate text using our model",
        )
    """
    path: str
    method: str = "POST"
    price: Decimal = Decimal("0.01")
    currency: str = "USD"
    description: str = ""
    pricing_model: PricingModel = PricingModel.PER_CALL
    unit_name: str | None = None
    tiers: list[PricingTier] = field(default_factory=list)
    requires_auth: bool = False
    category: str | None = None  # e.g., "compute", "data", "ai"
    rate_limit: int | None = None  # requests per minute


@dataclass
class UsageRecord:
    """A metered usage record for per-unit billing.

    Merchants report usage after the API call completes.
    Sardis calculates the charge and settles.

    Example:
        record = UsageRecord(
            session_id="mcs_xxx",
            endpoint="/api/generate",
            units=1500,        # tokens consumed
            unit_name="token",
            unit_price=Decimal("0.001"),
        )
        # Charge: 1500 * 0.001 = $1.50
    """
    session_id: str
    endpoint: str
    units: int
    unit_name: str = "unit"
    unit_price: Decimal = Decimal("0.001")
    metadata: dict = field(default_factory=dict)

    @property
    def total_charge(self) -> Decimal:
        return Decimal(str(self.units)) * self.unit_price


@dataclass
class PaymentResult:
    """Result of a payment verification."""
    verified: bool
    session_id: str | None = None
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    payer_id: str | None = None
    error: str | None = None


@dataclass
class ServiceManifest:
    """Machine-readable service description for agent discovery.

    Served at /.well-known/sardis.json — agents use this to discover
    what the API offers and how much it costs.
    """
    name: str
    description: str
    base_url: str
    endpoints: list[PricedEndpoint]
    merchant_id: str | None = None
    version: str = "1.0"
    accepts: list[str] = field(default_factory=lambda: ["sardis", "x402", "mpp"])
