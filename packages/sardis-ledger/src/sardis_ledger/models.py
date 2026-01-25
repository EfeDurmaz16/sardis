"""Ledger data models with production-grade precision and typing."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
import hashlib
import uuid


# Decimal precision constants for financial accuracy
# 38 total digits, 18 decimal places (matches Ethereum uint256 / 10^18)
DECIMAL_PRECISION = 38
DECIMAL_SCALE = 18
DECIMAL_CONTEXT_PREC = 50  # Extra precision for intermediate calculations

# Quantize pattern for consistent decimal representation
DECIMAL_QUANTIZE = Decimal(10) ** -DECIMAL_SCALE


def to_ledger_decimal(value: Any) -> Decimal:
    """
    Convert any numeric value to a properly quantized ledger Decimal.

    Args:
        value: Number, string, or Decimal to convert

    Returns:
        Decimal with proper precision (38, 18)

    Raises:
        ValueError: If value cannot be converted to a valid decimal
    """
    try:
        if isinstance(value, Decimal):
            d = value
        elif isinstance(value, float):
            # Avoid float precision issues by converting via string
            d = Decimal(str(value))
        elif isinstance(value, (int, str)):
            d = Decimal(value)
        else:
            raise ValueError(f"Cannot convert {type(value).__name__} to Decimal")

        # Quantize to 18 decimal places with banker's rounding
        return d.quantize(DECIMAL_QUANTIZE, rounding=ROUND_HALF_UP)
    except InvalidOperation as e:
        raise ValueError(f"Invalid decimal value: {value}") from e


def validate_amount(amount: Decimal, allow_zero: bool = False, allow_negative: bool = False) -> None:
    """
    Validate a monetary amount.

    Args:
        amount: The amount to validate
        allow_zero: Whether zero is a valid amount
        allow_negative: Whether negative amounts are allowed

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(amount, Decimal):
        raise ValueError(f"Amount must be Decimal, got {type(amount).__name__}")

    if not allow_negative and amount < 0:
        raise ValueError(f"Amount cannot be negative: {amount}")

    if not allow_zero and amount == 0:
        raise ValueError("Amount cannot be zero")

    # Check precision limits
    sign, digits, exponent = amount.as_tuple()
    total_digits = len(digits)

    if total_digits > DECIMAL_PRECISION:
        raise ValueError(f"Amount exceeds maximum precision of {DECIMAL_PRECISION} digits")


class LedgerEntryType(str, Enum):
    """Type of ledger entry."""
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    FEE = "fee"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"
    SNAPSHOT = "snapshot"


class LedgerEntryStatus(str, Enum):
    """Status of a ledger entry."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERSED = "reversed"
    CANCELLED = "cancelled"


class ReconciliationStatus(str, Enum):
    """Status of reconciliation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    DISPUTED = "disputed"
    RESOLVED = "resolved"


class AuditAction(str, Enum):
    """Type of audit action."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOCK = "lock"
    UNLOCK = "unlock"
    RECONCILE = "reconcile"
    SNAPSHOT = "snapshot"
    ROLLBACK = "rollback"


@dataclass(slots=True)
class LedgerEntry:
    """
    Core ledger entry with full financial precision.

    Uses Decimal(38, 18) for amounts to support:
    - Up to 20 digits for whole units (enough for quadrillions)
    - 18 decimal places (matching crypto token precision)
    """
    entry_id: str = field(default_factory=lambda: f"le_{uuid.uuid4().hex[:20]}")
    tx_id: str = ""  # Reference to parent transaction
    account_id: str = ""  # Account affected
    entry_type: LedgerEntryType = LedgerEntryType.TRANSFER

    # Amounts with full precision
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    fee: Decimal = field(default_factory=lambda: Decimal("0"))
    running_balance: Decimal = field(default_factory=lambda: Decimal("0"))

    currency: str = "USDC"

    # Chain reference
    chain: Optional[str] = None
    chain_tx_hash: Optional[str] = None
    block_number: Optional[int] = None

    # Audit fields
    audit_anchor: Optional[str] = None
    merkle_root: Optional[str] = None

    # Status and timing
    status: LedgerEntryStatus = LedgerEntryStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Lock version for optimistic concurrency
    version: int = 1

    def __post_init__(self):
        """Validate and normalize amounts after initialization."""
        self.amount = to_ledger_decimal(self.amount)
        self.fee = to_ledger_decimal(self.fee)
        self.running_balance = to_ledger_decimal(self.running_balance)

    def total_amount(self) -> Decimal:
        """Get total amount including fees."""
        return self.amount + self.fee

    def compute_hash(self) -> str:
        """Compute deterministic hash of entry for audit trail."""
        data = "|".join([
            self.entry_id,
            self.tx_id,
            self.account_id,
            self.entry_type.value,
            str(self.amount),
            str(self.fee),
            self.currency,
            self.chain or "",
            self.chain_tx_hash or "",
            str(self.block_number or 0),
            self.created_at.isoformat(),
        ])
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entry_id": self.entry_id,
            "tx_id": self.tx_id,
            "account_id": self.account_id,
            "entry_type": self.entry_type.value,
            "amount": str(self.amount),
            "fee": str(self.fee),
            "running_balance": str(self.running_balance),
            "currency": self.currency,
            "chain": self.chain,
            "chain_tx_hash": self.chain_tx_hash,
            "block_number": self.block_number,
            "audit_anchor": self.audit_anchor,
            "merkle_root": self.merkle_root,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "version": self.version,
        }


@dataclass(slots=True)
class BalanceSnapshot:
    """
    Point-in-time balance snapshot for historical queries.

    Snapshots are created periodically and allow efficient
    balance calculations at any historical point.
    """
    snapshot_id: str = field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:16]}")
    account_id: str = ""
    currency: str = "USDC"

    # Balance at snapshot time
    balance: Decimal = field(default_factory=lambda: Decimal("0"))

    # Reference to last entry included
    last_entry_id: str = ""
    last_entry_created_at: Optional[datetime] = None

    # Entry count for validation
    entry_count: int = 0

    # Snapshot metadata
    snapshot_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    merkle_root: Optional[str] = None

    def __post_init__(self):
        """Normalize balance."""
        self.balance = to_ledger_decimal(self.balance)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "snapshot_id": self.snapshot_id,
            "account_id": self.account_id,
            "currency": self.currency,
            "balance": str(self.balance),
            "last_entry_id": self.last_entry_id,
            "last_entry_created_at": self.last_entry_created_at.isoformat() if self.last_entry_created_at else None,
            "entry_count": self.entry_count,
            "snapshot_at": self.snapshot_at.isoformat(),
            "merkle_root": self.merkle_root,
        }


@dataclass(slots=True)
class AuditLog:
    """
    Audit trail entry for all ledger operations.

    Captures who did what, when, and provides
    tamper-evident logging.
    """
    audit_id: str = field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:16]}")

    # What happened
    action: AuditAction = AuditAction.CREATE
    entity_type: str = ""  # e.g., "ledger_entry", "snapshot", "reconciliation"
    entity_id: str = ""

    # Actor information
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None  # "system", "user", "agent"

    # Change details
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None

    # Context
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Hash chain for tamper evidence
    previous_hash: Optional[str] = None
    entry_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute hash including previous entry for chain."""
        import json
        data = json.dumps({
            "audit_id": self.audit_id,
            "action": self.action.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actor_id": self.actor_id,
            "created_at": self.created_at.isoformat(),
            "previous_hash": self.previous_hash or "",
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "audit_id": self.audit_id,
            "action": self.action.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat(),
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


@dataclass(slots=True)
class ReconciliationRecord:
    """
    Record of ledger-to-chain reconciliation.

    Tracks the matching of ledger entries with
    on-chain transactions for verification.
    """
    reconciliation_id: str = field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:16]}")

    # Ledger side
    ledger_entry_id: str = ""
    ledger_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    ledger_currency: str = "USDC"

    # Chain side
    chain: str = ""
    chain_tx_hash: str = ""
    chain_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    chain_block_number: Optional[int] = None
    chain_timestamp: Optional[datetime] = None

    # Reconciliation result
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    discrepancy_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    discrepancy_reason: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reconciled_at: Optional[datetime] = None

    def __post_init__(self):
        """Normalize decimal amounts."""
        self.ledger_amount = to_ledger_decimal(self.ledger_amount)
        self.chain_amount = to_ledger_decimal(self.chain_amount)
        self.discrepancy_amount = to_ledger_decimal(self.discrepancy_amount)

    def calculate_discrepancy(self) -> Decimal:
        """Calculate amount discrepancy between ledger and chain."""
        self.discrepancy_amount = abs(self.ledger_amount - self.chain_amount)
        return self.discrepancy_amount

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "reconciliation_id": self.reconciliation_id,
            "ledger_entry_id": self.ledger_entry_id,
            "ledger_amount": str(self.ledger_amount),
            "ledger_currency": self.ledger_currency,
            "chain": self.chain,
            "chain_tx_hash": self.chain_tx_hash,
            "chain_amount": str(self.chain_amount),
            "chain_block_number": self.chain_block_number,
            "chain_timestamp": self.chain_timestamp.isoformat() if self.chain_timestamp else None,
            "status": self.status.value,
            "discrepancy_amount": str(self.discrepancy_amount),
            "discrepancy_reason": self.discrepancy_reason,
            "created_at": self.created_at.isoformat(),
            "reconciled_at": self.reconciled_at.isoformat() if self.reconciled_at else None,
        }


@dataclass(slots=True)
class BatchTransaction:
    """
    Batch of related transactions processed atomically.

    Enables efficient processing of multiple entries
    with all-or-nothing semantics.
    """
    batch_id: str = field(default_factory=lambda: f"batch_{uuid.uuid4().hex[:16]}")

    # Entries in this batch
    entries: List[LedgerEntry] = field(default_factory=list)

    # Batch status
    status: LedgerEntryStatus = LedgerEntryStatus.PENDING
    error_message: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    # Rollback support
    is_rolled_back: bool = False
    rollback_reason: Optional[str] = None
    rollback_at: Optional[datetime] = None

    def total_amount(self) -> Decimal:
        """Calculate total amount across all entries."""
        return sum((e.amount for e in self.entries), Decimal("0"))

    def total_fees(self) -> Decimal:
        """Calculate total fees across all entries."""
        return sum((e.fee for e in self.entries), Decimal("0"))

    def entry_count(self) -> int:
        """Get number of entries in batch."""
        return len(self.entries)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "batch_id": self.batch_id,
            "entry_count": self.entry_count(),
            "total_amount": str(self.total_amount()),
            "total_fees": str(self.total_fees()),
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_rolled_back": self.is_rolled_back,
            "rollback_reason": self.rollback_reason,
        }


@dataclass(slots=True)
class CurrencyRate:
    """
    Exchange rate for currency conversion.

    Rates are stored with full precision to avoid
    rounding errors in conversion calculations.
    """
    rate_id: str = field(default_factory=lambda: f"rate_{uuid.uuid4().hex[:12]}")

    from_currency: str = "USD"
    to_currency: str = "USDC"

    # Rate with full precision
    rate: Decimal = field(default_factory=lambda: Decimal("1"))
    inverse_rate: Decimal = field(default_factory=lambda: Decimal("1"))

    # Source and validity
    source: str = "internal"  # e.g., "coingecko", "chainlink", "internal"
    valid_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None

    # Market data
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    spread: Optional[Decimal] = None

    def __post_init__(self):
        """Normalize rates."""
        self.rate = to_ledger_decimal(self.rate)
        self.inverse_rate = to_ledger_decimal(self.inverse_rate)
        if self.bid:
            self.bid = to_ledger_decimal(self.bid)
        if self.ask:
            self.ask = to_ledger_decimal(self.ask)
        if self.spread:
            self.spread = to_ledger_decimal(self.spread)

    def convert(self, amount: Decimal) -> Decimal:
        """Convert amount from source to target currency."""
        return to_ledger_decimal(amount * self.rate)

    def convert_inverse(self, amount: Decimal) -> Decimal:
        """Convert amount from target to source currency."""
        return to_ledger_decimal(amount * self.inverse_rate)

    def is_valid(self, at_time: Optional[datetime] = None) -> bool:
        """Check if rate is valid at given time."""
        check_time = at_time or datetime.now(timezone.utc)
        if check_time < self.valid_from:
            return False
        if self.valid_until and check_time > self.valid_until:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rate_id": self.rate_id,
            "from_currency": self.from_currency,
            "to_currency": self.to_currency,
            "rate": str(self.rate),
            "inverse_rate": str(self.inverse_rate),
            "source": self.source,
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "bid": str(self.bid) if self.bid else None,
            "ask": str(self.ask) if self.ask else None,
            "spread": str(self.spread) if self.spread else None,
        }


@dataclass(slots=True)
class LockRecord:
    """
    Record of a row-level lock for concurrent transaction safety.

    Used to implement pessimistic locking for accounts
    during multi-step transactions.
    """
    lock_id: str = field(default_factory=lambda: f"lock_{uuid.uuid4().hex[:12]}")

    # What is locked
    resource_type: str = ""  # "account", "entry", "batch"
    resource_id: str = ""

    # Lock holder
    holder_id: str = ""  # Transaction or process ID
    holder_type: str = "transaction"

    # Lock status
    acquired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    released_at: Optional[datetime] = None

    # Lock mode
    is_exclusive: bool = True

    def is_active(self) -> bool:
        """Check if lock is still active."""
        if self.released_at:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "lock_id": self.lock_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "holder_id": self.holder_id,
            "holder_type": self.holder_type,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "is_exclusive": self.is_exclusive,
            "is_active": self.is_active(),
        }


__all__ = [
    # Constants
    "DECIMAL_PRECISION",
    "DECIMAL_SCALE",
    "DECIMAL_QUANTIZE",
    # Utilities
    "to_ledger_decimal",
    "validate_amount",
    # Enums
    "LedgerEntryType",
    "LedgerEntryStatus",
    "ReconciliationStatus",
    "AuditAction",
    # Models
    "LedgerEntry",
    "BalanceSnapshot",
    "AuditLog",
    "ReconciliationRecord",
    "BatchTransaction",
    "CurrencyRate",
    "LockRecord",
]
