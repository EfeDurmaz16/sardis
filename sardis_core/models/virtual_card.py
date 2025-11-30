"""Virtual card model for wallet payment abstraction."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid
import secrets
import hashlib


# Sardis BIN range (fictional - would be registered with card networks)
SARDIS_BIN = "489031"


class CardStatus(str, Enum):
    """Card lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CardType(str, Enum):
    """Types of virtual cards."""
    SINGLE_USE = "single_use"      # One-time use
    MULTI_USE = "multi_use"        # Standard card
    MERCHANT_LOCKED = "merchant_locked"  # Locked to specific merchant


def generate_card_number() -> str:
    """
    Generate a realistic card number with Sardis BIN.
    
    Format: 489031XXXXXXXXXX (16 digits total)
    Uses Luhn algorithm for valid checksum.
    """
    # Generate 9 random digits (BIN is 6, check digit is 1, leaves 9)
    partial = SARDIS_BIN + ''.join([str(secrets.randbelow(10)) for _ in range(9)])
    
    # Calculate Luhn check digit
    check_digit = calculate_luhn_check(partial)
    return partial + str(check_digit)


def calculate_luhn_check(partial_number: str) -> int:
    """Calculate Luhn check digit for a partial card number."""
    digits = [int(d) for d in partial_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))
    
    return (10 - (checksum % 10)) % 10


def mask_card_number(full_number: str) -> str:
    """Mask a card number showing only last 4 digits."""
    return f"**** **** **** {full_number[-4:]}"


def generate_cvv() -> str:
    """Generate a 3-digit CVV."""
    return f"{secrets.randbelow(1000):03d}"


def generate_expiry() -> tuple[int, int]:
    """Generate expiry date (3 years from now)."""
    now = datetime.now(timezone.utc)
    expiry_year = now.year + 3
    expiry_month = now.month
    return expiry_month, expiry_year


class VirtualCard(BaseModel):
    """
    Virtual card abstraction for a wallet.
    
    This represents a virtual payment identity that can be used
    for transactions. Provides realistic card details that can
    be used for testing or with card network integrations.
    
    Card Details:
    - 16-digit card number with valid Luhn checksum
    - CVV for verification
    - Expiry date
    - Spending controls
    
    Authorization Flow:
    - Supports authorize/capture/void pattern
    - Tracks pending authorizations
    - Enforces per-card spending limits
    """
    
    card_id: str = Field(default_factory=lambda: f"vc_{uuid.uuid4().hex[:16]}")
    wallet_id: str
    
    # Card details (full number stored encrypted in production)
    card_number: str = Field(default_factory=generate_card_number)
    masked_number: str = ""
    cvv: str = Field(default_factory=generate_cvv)
    expiry_month: int = 0
    expiry_year: int = 0
    
    # Card type and status
    card_type: CardType = CardType.MULTI_USE
    status: CardStatus = CardStatus.ACTIVE
    
    # Optional merchant lock (for merchant-locked cards)
    locked_merchant_id: Optional[str] = None
    
    # Spending limits
    limit_per_tx: Decimal = Field(default=Decimal("500.00"))
    limit_daily: Decimal = Field(default=Decimal("2000.00"))
    limit_monthly: Decimal = Field(default=Decimal("10000.00"))
    
    # Spending tracking
    spent_today: Decimal = Field(default=Decimal("0.00"))
    spent_this_month: Decimal = Field(default=Decimal("0.00"))
    total_spent: Decimal = Field(default=Decimal("0.00"))
    
    # Authorization tracking
    pending_authorizations: Decimal = Field(default=Decimal("0.00"))
    authorization_count: int = 0
    
    # Lifecycle
    is_active: bool = True  # Kept for backwards compatibility
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # For single-use cards
    is_used: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
    
    def __init__(self, **data):
        super().__init__(**data)
        # Generate masked number from full number
        if self.card_number and not self.masked_number:
            self.masked_number = mask_card_number(self.card_number)
        # Generate expiry if not set
        if self.expiry_month == 0:
            self.expiry_month, self.expiry_year = generate_expiry()
    
    @property
    def is_valid(self) -> bool:
        """Check if card is valid for use."""
        if self.status != CardStatus.ACTIVE:
            return False
        
        if self.card_type == CardType.SINGLE_USE and self.is_used:
            return False
        
        # Check expiry
        now = datetime.now(timezone.utc)
        if self.expiry_year < now.year:
            return False
        if self.expiry_year == now.year and self.expiry_month < now.month:
            return False
        
        return True
    
    @property
    def available_balance(self) -> Decimal:
        """Get available balance (daily limit minus spent and pending)."""
        return max(
            Decimal("0"),
            self.limit_daily - self.spent_today - self.pending_authorizations
        )
    
    def can_authorize(self, amount: Decimal, merchant_id: Optional[str] = None) -> tuple[bool, str]:
        """
        Check if an authorization can be approved.
        
        Returns (can_authorize, reason).
        """
        if not self.is_valid:
            return False, f"Card is not valid: status={self.status.value}"
        
        if self.card_type == CardType.SINGLE_USE and self.is_used:
            return False, "Single-use card has already been used"
        
        if self.card_type == CardType.MERCHANT_LOCKED:
            if merchant_id != self.locked_merchant_id:
                return False, f"Card is locked to merchant {self.locked_merchant_id}"
        
        if amount > self.limit_per_tx:
            return False, f"Amount {amount} exceeds per-transaction limit {self.limit_per_tx}"
        
        if amount > self.available_balance:
            return False, f"Amount {amount} exceeds available balance {self.available_balance}"
        
        return True, "OK"
    
    def authorize(self, amount: Decimal) -> bool:
        """Create a hold for the amount."""
        can_auth, _ = self.can_authorize(amount)
        if not can_auth:
            return False
        
        self.pending_authorizations += amount
        self.authorization_count += 1
        return True
    
    def capture(self, amount: Decimal) -> bool:
        """Capture (complete) an authorization."""
        if amount > self.pending_authorizations:
            return False
        
        self.pending_authorizations -= amount
        self.spent_today += amount
        self.spent_this_month += amount
        self.total_spent += amount
        self.last_used_at = datetime.now(timezone.utc)
        
        if self.card_type == CardType.SINGLE_USE:
            self.is_used = True
        
        return True
    
    def void_authorization(self, amount: Decimal) -> bool:
        """Void (cancel) an authorization."""
        if amount > self.pending_authorizations:
            return False
        
        self.pending_authorizations -= amount
        return True
    
    def suspend(self):
        """Suspend the card."""
        self.status = CardStatus.SUSPENDED
        self.suspended_at = datetime.now(timezone.utc)
        self.is_active = False
    
    def reactivate(self):
        """Reactivate a suspended card."""
        if self.status == CardStatus.SUSPENDED:
            self.status = CardStatus.ACTIVE
            self.is_active = True
    
    def cancel(self):
        """Permanently cancel the card."""
        self.status = CardStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
        self.is_active = False
    
    def reset_daily_spending(self):
        """Reset daily spending (called at midnight)."""
        self.spent_today = Decimal("0.00")
    
    def reset_monthly_spending(self):
        """Reset monthly spending (called at month start)."""
        self.spent_this_month = Decimal("0.00")
    
    def get_card_details(self, include_sensitive: bool = False) -> dict:
        """
        Get card details for display.
        
        Args:
            include_sensitive: If True, includes full card number and CVV
        """
        details = {
            "card_id": self.card_id,
            "masked_number": self.masked_number,
            "expiry": f"{self.expiry_month:02d}/{str(self.expiry_year)[-2:]}",
            "card_type": self.card_type.value,
            "status": self.status.value,
            "limit_per_tx": str(self.limit_per_tx),
            "limit_daily": str(self.limit_daily),
            "available_balance": str(self.available_balance),
        }
        
        if include_sensitive:
            details["card_number"] = self.card_number
            details["cvv"] = self.cvv
        
        return details

