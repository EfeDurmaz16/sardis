"""Striga data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum


class StrigaUserStatus(str, Enum):
    """Striga user verification status."""
    CREATED = "created"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class StrigaWalletStatus(str, Enum):
    """Striga wallet status."""
    ACTIVE = "active"
    BLOCKED = "blocked"
    CLOSED = "closed"


class StrigaCardStatus(str, Enum):
    """Striga card lifecycle status."""
    CREATED = "created"
    ACTIVE = "active"
    FROZEN = "frozen"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class StrigaCardType(str, Enum):
    """Striga card types."""
    VIRTUAL = "virtual"
    PHYSICAL = "physical"


class StrigaTransactionStatus(str, Enum):
    """Striga transaction status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class StrigaTransactionType(str, Enum):
    """Striga transaction types."""
    CARD_PURCHASE = "card_purchase"
    CARD_REFUND = "card_refund"
    SEPA_IN = "sepa_in"
    SEPA_OUT = "sepa_out"
    CRYPTO_DEPOSIT = "crypto_deposit"
    CRYPTO_WITHDRAWAL = "crypto_withdrawal"
    SWAP = "swap"
    FEE = "fee"


class StrigaVIBANStatus(str, Enum):
    """Striga vIBAN status."""
    ACTIVE = "active"
    BLOCKED = "blocked"
    CLOSED = "closed"


class StandingOrderFrequency(str, Enum):
    """Standing order execution frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class StandingOrderStatus(str, Enum):
    """Standing order lifecycle status."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class StrigaUser:
    """A Striga user (KYC-linked cardholder)."""
    user_id: str
    email: str
    status: StrigaUserStatus = StrigaUserStatus.CREATED
    first_name: str = ""
    last_name: str = ""
    country: str = ""
    kyc_level: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)


@dataclass
class StrigaWallet:
    """A Striga wallet (holds EUR, USDC, etc.)."""
    wallet_id: str
    user_id: str
    currency: str = "EUR"
    balance_cents: int = 0
    status: StrigaWalletStatus = StrigaWalletStatus.ACTIVE
    blockchain_address: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def balance(self) -> Decimal:
        return Decimal(self.balance_cents) / Decimal(100)


@dataclass
class StrigaCard:
    """A Striga virtual Visa card (EUR-denominated)."""
    card_id: str
    user_id: str
    wallet_id: str
    card_type: StrigaCardType = StrigaCardType.VIRTUAL
    status: StrigaCardStatus = StrigaCardStatus.CREATED
    currency: str = "EUR"
    last_four: str = ""
    expiry_month: int = 0
    expiry_year: int = 0
    spending_limit_cents: int = 0
    daily_limit_cents: int = 0
    monthly_limit_cents: int = 0
    apple_pay_eligible: bool = False
    google_pay_eligible: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    activated_at: datetime | None = None


@dataclass
class StrigaTransaction:
    """A Striga transaction record."""
    transaction_id: str
    wallet_id: str
    transaction_type: StrigaTransactionType = StrigaTransactionType.CARD_PURCHASE
    status: StrigaTransactionStatus = StrigaTransactionStatus.PENDING
    amount_cents: int = 0
    currency: str = "EUR"
    fee_cents: int = 0
    merchant_name: str | None = None
    merchant_mcc: str | None = None
    description: str = ""
    reference: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @property
    def amount(self) -> Decimal:
        return Decimal(self.amount_cents) / Decimal(100)


@dataclass
class StrigaVIBAN:
    """A Striga virtual IBAN for SEPA payments."""
    viban_id: str
    wallet_id: str
    user_id: str
    iban: str
    bic: str = ""
    currency: str = "EUR"
    status: StrigaVIBANStatus = StrigaVIBANStatus.ACTIVE
    bank_name: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class StandingOrder:
    """A recurring swap/withdrawal standing order."""
    order_id: str
    wallet_id: str
    user_id: str
    frequency: StandingOrderFrequency = StandingOrderFrequency.MONTHLY
    status: StandingOrderStatus = StandingOrderStatus.ACTIVE
    source_currency: str = "EURC"
    target_currency: str = "EUR"
    amount_cents: int = 0
    next_execution: datetime | None = None
    last_execution: datetime | None = None
    execution_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def amount(self) -> Decimal:
        return Decimal(self.amount_cents) / Decimal(100)
