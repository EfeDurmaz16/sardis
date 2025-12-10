"""Data models for virtual card integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class CardStatus(str, Enum):
    """Card lifecycle status."""
    PENDING = "pending"
    ACTIVE = "active"
    FROZEN = "frozen"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CardType(str, Enum):
    """Type of virtual card."""
    SINGLE_USE = "single_use"
    MULTI_USE = "multi_use"
    MERCHANT_LOCKED = "merchant_locked"


class FundingSource(str, Enum):
    """Source of card funding."""
    STABLECOIN = "stablecoin"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"


class TransactionStatus(str, Enum):
    """Card transaction status."""
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    REVERSED = "reversed"
    SETTLED = "settled"


@dataclass
class Card:
    """Virtual card linked to an agent wallet."""
    
    card_id: str = field(default_factory=lambda: f"card_{uuid.uuid4().hex[:16]}")
    wallet_id: str = ""
    
    # Provider info
    provider: str = "lithic"
    provider_card_id: str = ""
    
    # Card details (masked)
    card_number_last4: str = ""
    expiry_month: int = 0
    expiry_year: int = 0
    
    # Card configuration
    card_type: CardType = CardType.MULTI_USE
    status: CardStatus = CardStatus.PENDING
    locked_merchant_id: Optional[str] = None
    
    # Funding
    funding_source: FundingSource = FundingSource.STABLECOIN
    funded_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    pending_funds: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Spending limits
    limit_per_tx: Decimal = field(default_factory=lambda: Decimal("500.00"))
    limit_daily: Decimal = field(default_factory=lambda: Decimal("2000.00"))
    limit_monthly: Decimal = field(default_factory=lambda: Decimal("10000.00"))
    
    # Spending tracking
    spent_today: Decimal = field(default_factory=lambda: Decimal("0.00"))
    spent_this_month: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_spent: Decimal = field(default_factory=lambda: Decimal("0.00"))
    pending_authorizations: Decimal = field(default_factory=lambda: Decimal("0.00"))
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: Optional[datetime] = None
    frozen_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        """Check if card can be used for transactions."""
        return self.status == CardStatus.ACTIVE
    
    @property
    def available_balance(self) -> Decimal:
        """Calculate available balance for transactions."""
        daily_available = self.limit_daily - self.spent_today - self.pending_authorizations
        funded_available = self.funded_amount - self.pending_authorizations
        return max(Decimal("0"), min(daily_available, funded_available))
    
    def can_authorize(self, amount: Decimal, merchant_id: Optional[str] = None) -> tuple[bool, str]:
        """Check if a transaction can be authorized."""
        if self.status != CardStatus.ACTIVE:
            return False, f"Card is {self.status.value}"
        
        if self.card_type == CardType.MERCHANT_LOCKED and merchant_id != self.locked_merchant_id:
            return False, f"Card is locked to merchant {self.locked_merchant_id}"
        
        if amount > self.limit_per_tx:
            return False, f"Amount {amount} exceeds per-transaction limit {self.limit_per_tx}"
        
        if amount > self.available_balance:
            return False, f"Amount {amount} exceeds available balance {self.available_balance}"
        
        return True, "OK"


@dataclass
class CardTransaction:
    """A transaction on a virtual card."""
    
    transaction_id: str = field(default_factory=lambda: f"ctx_{uuid.uuid4().hex[:16]}")
    card_id: str = ""
    
    # Provider info
    provider_tx_id: str = ""
    
    # Transaction details
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USD"
    merchant_name: str = ""
    merchant_category: str = ""
    merchant_id: str = ""
    
    # Status
    status: TransactionStatus = TransactionStatus.PENDING
    decline_reason: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    settled_at: Optional[datetime] = None
    
    @property
    def is_settled(self) -> bool:
        """Check if transaction is settled."""
        return self.status == TransactionStatus.SETTLED
