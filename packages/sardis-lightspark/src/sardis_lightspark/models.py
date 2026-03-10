"""Lightspark Grid data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum


class GridTransferStatus(str, Enum):
    """Grid transfer lifecycle status."""
    QUOTED = "quoted"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class GridPaymentRail(str, Enum):
    """Supported Grid payment rails."""
    ACH = "ach"
    ACH_SAME_DAY = "ach_same_day"
    RTP = "rtp"
    FEDNOW = "fednow"
    WIRE = "wire"
    SEPA = "sepa"
    LIGHTNING = "lightning"


class GridCustomerStatus(str, Enum):
    """Grid customer verification status."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class UMAAddressStatus(str, Enum):
    """UMA address lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


@dataclass
class GridQuote:
    """A quote for a Grid transfer (FX or payout)."""
    quote_id: str
    source_currency: str
    source_amount_cents: int
    target_currency: str
    target_amount_cents: int
    exchange_rate: Decimal
    fee_cents: int
    rail: GridPaymentRail | None = None
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires_at

    @property
    def source_amount(self) -> Decimal:
        return Decimal(self.source_amount_cents) / Decimal(100)

    @property
    def target_amount(self) -> Decimal:
        return Decimal(self.target_amount_cents) / Decimal(100)


@dataclass
class GridTransfer:
    """A Grid transfer (payout, FX, or UMA payment)."""
    transfer_id: str
    quote_id: str | None = None
    source_currency: str = "USD"
    source_amount_cents: int = 0
    target_currency: str = "USD"
    target_amount_cents: int = 0
    rail: GridPaymentRail = GridPaymentRail.ACH
    status: GridTransferStatus = GridTransferStatus.PENDING
    destination: str = ""  # bank account, UMA address, etc.
    reference: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    failure_reason: str | None = None

    @property
    def source_amount(self) -> Decimal:
        return Decimal(self.source_amount_cents) / Decimal(100)

    @property
    def target_amount(self) -> Decimal:
        return Decimal(self.target_amount_cents) / Decimal(100)


@dataclass
class UMAAddress:
    """A UMA address ($user@domain)."""
    uma_id: str
    address: str  # $agent@sardis.sh
    wallet_id: str
    user_id: str | None = None
    currency: str = "USD"
    status: UMAAddressStatus = UMAAddressStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def local_part(self) -> str:
        """Get the local part before @."""
        return self.address.lstrip("$").split("@")[0]

    @property
    def domain(self) -> str:
        """Get the domain part after @."""
        parts = self.address.split("@")
        return parts[1] if len(parts) > 1 else ""


@dataclass
class PlaidLinkToken:
    """Plaid Link token for bank account linking."""
    link_token: str
    expiration: datetime
    request_id: str = ""


@dataclass
class GridCustomer:
    """A Grid customer account."""
    customer_id: str
    email: str = ""
    status: GridCustomerStatus = GridCustomerStatus.PENDING
    plaid_access_token: str | None = None
    bank_account_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
