"""Stripe Shared Payment Token (SPT) — agent-granted payment credentials.

SPTs enable AI agents to grant sellers scoped payment credentials:
- Agent provisions an SPT with usage_limits (currency, max_amount, expires_at)
- Seller uses the SPT to create a PaymentIntent
- Stripe clones the original payment method for the seller
- SPT can be revoked by the agent at any time

This maps directly to Sardis spending mandates:
  mandate.amount_per_tx → spt.usage_limits.max_amount
  mandate.currency → spt.usage_limits.currency
  mandate.expires_at → spt.usage_limits.expires_at
  mandate.merchant_scope → spt.seller_details

Reference: https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.spt")


@dataclass
class SPTUsageLimits:
    """Usage constraints on a Shared Payment Token."""
    currency: str = "usd"
    max_amount: int = 0  # In smallest currency unit (cents)
    expires_at: int = 0  # Unix timestamp


@dataclass
class SPTSellerDetails:
    """Seller identification for SPT scoping."""
    network_id: str = "internal"
    external_id: str = ""  # Links to specific seller/cart/order


@dataclass
class SharedPaymentToken:
    """A Stripe Shared Payment Token granted by an agent."""

    token_id: str = field(default_factory=lambda: f"spt_{uuid4().hex[:16]}")
    mandate_id: str | None = None  # Sardis mandate backing this SPT
    agent_id: str | None = None

    # Stripe fields
    stripe_spt_id: str | None = None  # spt_xxx from Stripe API
    payment_method_id: str | None = None  # pm_xxx

    # Limits (from mandate)
    usage_limits: SPTUsageLimits = field(default_factory=SPTUsageLimits)
    seller_details: SPTSellerDetails = field(default_factory=SPTSellerDetails)

    # Lifecycle
    status: str = "active"  # active, used, deactivated
    used_at: datetime | None = None
    deactivated_at: datetime | None = None
    deactivated_reason: str | None = None

    # Audit
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_mandate(cls, mandate, seller_network_id: str = "internal", seller_external_id: str = "") -> SharedPaymentToken:
        """Create an SPT from a Sardis spending mandate."""
        limits = SPTUsageLimits(
            currency=mandate.currency.lower() if mandate.currency else "usd",
            max_amount=int(mandate.amount_per_tx * 100) if mandate.amount_per_tx else 0,
            expires_at=int(mandate.expires_at.timestamp()) if mandate.expires_at else 0,
        )
        seller = SPTSellerDetails(
            network_id=seller_network_id,
            external_id=seller_external_id,
        )
        return cls(
            mandate_id=mandate.id,
            agent_id=mandate.agent_id,
            usage_limits=limits,
            seller_details=seller,
        )
