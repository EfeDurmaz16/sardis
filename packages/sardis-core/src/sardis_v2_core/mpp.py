"""MPP (Machine Payments Protocol) session model.

MPP sessions authorize streaming payments within a spending mandate.
A session is created with a spending limit, and payments are executed
within that session until it's closed or the limit is reached.

Maps to MPP protocol's "sessions" primitive: authorize once, stream payments.
Links to existing SpendingMandate model for policy enforcement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4


class MPPSessionStatus(str, Enum):
    """Lifecycle states for an MPP session."""
    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"  # Spending limit reached


class MPPPaymentStatus(str, Enum):
    """Status of an individual MPP payment within a session."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MPPSession:
    """An MPP payment session — authorize once, stream payments.

    Links a spending mandate to a series of MPP payments on a specific
    chain using a specific payment method.
    """
    session_id: str = field(default_factory=lambda: f"mpp_sess_{uuid4().hex[:16]}")
    mandate_id: str | None = None
    wallet_id: str | None = None
    agent_id: str | None = None
    org_id: str = ""

    # Payment configuration
    method: str = "tempo"  # tempo, stripe_spt, bolt11
    chain: str = "tempo"
    currency: str = "USDC"

    # Spending limits for this session
    spending_limit: Decimal = Decimal("0")
    remaining: Decimal = Decimal("0")
    total_spent: Decimal = Decimal("0")
    payment_count: int = 0

    # Lifecycle
    status: MPPSessionStatus = MPPSessionStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None
    expires_at: datetime | None = None

    # Metadata
    metadata: dict = field(default_factory=dict)

    def can_spend(self, amount: Decimal) -> bool:
        """Check if this session can accommodate a payment of the given amount."""
        if self.status != MPPSessionStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(UTC) >= self.expires_at:
            return False
        return self.remaining >= amount

    def record_payment(self, amount: Decimal) -> None:
        """Record a successful payment against this session."""
        self.remaining -= amount
        self.total_spent += amount
        self.payment_count += 1
        if self.remaining <= Decimal("0"):
            self.status = MPPSessionStatus.EXHAUSTED

    def close(self) -> None:
        """Close this session."""
        self.status = MPPSessionStatus.CLOSED
        self.closed_at = datetime.now(UTC)


@dataclass
class MPPPayment:
    """Record of an individual payment within an MPP session."""
    payment_id: str = field(default_factory=lambda: f"mpp_pay_{uuid4().hex[:16]}")
    session_id: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "USDC"
    merchant: str = ""
    merchant_url: str = ""
    status: MPPPaymentStatus = MPPPaymentStatus.PENDING
    tx_hash: str | None = None
    chain: str = "tempo"
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    metadata: dict = field(default_factory=dict)
