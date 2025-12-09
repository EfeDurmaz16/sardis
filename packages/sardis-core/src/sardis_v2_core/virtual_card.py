"""Virtual card abstraction reused by wallets."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import secrets
import uuid

SARDIS_BIN = "489031"


class CardStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CardType(str, Enum):
    SINGLE_USE = "single_use"
    MULTI_USE = "multi_use"
    MERCHANT_LOCKED = "merchant_locked"


def _calculate_luhn_check(partial_number: str) -> int:
    digits = [int(d) for d in partial_number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for digit in even_digits:
        checksum += sum(divmod(digit * 2, 10))
    return (10 - (checksum % 10)) % 10


def _generate_card_number() -> str:
    partial = SARDIS_BIN + "".join(str(secrets.randbelow(10)) for _ in range(9))
    check_digit = _calculate_luhn_check(partial)
    return partial + str(check_digit)


def _mask_card_number(full_number: str) -> str:
    return f"**** **** **** {full_number[-4:]}"


def _generate_cvv() -> str:
    return f"{secrets.randbelow(1000):03d}"


def _generate_expiry() -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    return now.month, now.year + 3


@dataclass(slots=True)
class VirtualCard:
    card_id: str = field(default_factory=lambda: f"vc_{uuid.uuid4().hex[:16]}")
    wallet_id: str = ""
    card_number: str = field(default_factory=_generate_card_number)
    masked_number: str = ""
    cvv: str = field(default_factory=_generate_cvv)
    expiry_month: int = 0
    expiry_year: int = 0
    card_type: CardType = CardType.MULTI_USE
    status: CardStatus = CardStatus.ACTIVE
    locked_merchant_id: Optional[str] = None
    limit_per_tx: Decimal = field(default_factory=lambda: Decimal("500.00"))
    limit_daily: Decimal = field(default_factory=lambda: Decimal("2000.00"))
    limit_monthly: Decimal = field(default_factory=lambda: Decimal("10000.00"))
    spent_today: Decimal = field(default_factory=lambda: Decimal("0.00"))
    spent_this_month: Decimal = field(default_factory=lambda: Decimal("0.00"))
    total_spent: Decimal = field(default_factory=lambda: Decimal("0.00"))
    pending_authorizations: Decimal = field(default_factory=lambda: Decimal("0.00"))
    authorization_count: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    is_used: bool = False

    def __post_init__(self) -> None:
        if not self.masked_number and self.card_number:
            self.masked_number = _mask_card_number(self.card_number)
        if self.expiry_month == 0:
            self.expiry_month, self.expiry_year = _generate_expiry()

    @property
    def is_valid(self) -> bool:
        if self.status != CardStatus.ACTIVE:
            return False
        if self.card_type == CardType.SINGLE_USE and self.is_used:
            return False
        now = datetime.now(timezone.utc)
        if self.expiry_year < now.year:
            return False
        if self.expiry_year == now.year and self.expiry_month < now.month:
            return False
        return True

    @property
    def available_balance(self) -> Decimal:
        return max(Decimal("0"), self.limit_daily - self.spent_today - self.pending_authorizations)

    def can_authorize(self, amount: Decimal, merchant_id: Optional[str] = None) -> tuple[bool, str]:
        if not self.is_valid:
            return False, f"card invalid ({self.status.value})"
        if self.card_type == CardType.SINGLE_USE and self.is_used:
            return False, "single-use card already consumed"
        if self.card_type == CardType.MERCHANT_LOCKED and merchant_id != self.locked_merchant_id:
            return False, f"card locked to merchant {self.locked_merchant_id}"
        if amount > self.limit_per_tx:
            return False, f"amount {amount} exceeds per-tx limit {self.limit_per_tx}"
        if amount > self.available_balance:
            return False, f"amount {amount} exceeds available {self.available_balance}"
        return True, "OK"
