"""
Ledger entry models for double-entry bookkeeping.

The Sardis ledger uses double-entry accounting where every transaction
creates balanced debit and credit entries. This ensures integrity
and provides a complete audit trail.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import hashlib
import uuid


class EntryType(str, Enum):
    """Types of ledger entries."""
    DEBIT = "debit"      # Money leaving an account
    CREDIT = "credit"    # Money entering an account
    FEE = "fee"          # Fee collection
    REFUND = "refund"    # Refund of previous transaction
    SETTLEMENT = "settlement"  # On-chain settlement record
    MINT = "mint"        # Demo token minting
    BURN = "burn"        # Demo token burning
    HOLD = "hold"        # Pre-authorization hold
    RELEASE = "release"  # Release of held funds


class EntryStatus(str, Enum):
    """Status of a ledger entry."""
    PENDING = "pending"      # Entry created but not finalized
    CONFIRMED = "confirmed"  # Entry is final
    REVERSED = "reversed"    # Entry has been reversed (refund)
    VOID = "void"           # Entry was voided (pre-auth cancelled)


@dataclass
class LedgerEntry:
    """
    A single entry in the append-only ledger.
    
    Each financial operation creates one or more entries following
    double-entry bookkeeping principles:
    - Every debit must have a corresponding credit
    - Total debits must equal total credits
    
    Entries are immutable once confirmed. To reverse a transaction,
    new entries are created with opposite signs.
    """
    
    entry_id: str = field(default_factory=lambda: f"le_{uuid.uuid4().hex[:20]}")
    
    # Entry classification
    entry_type: EntryType = EntryType.DEBIT
    status: EntryStatus = EntryStatus.PENDING
    
    # Account affected
    wallet_id: str = ""
    
    # Amount (always positive - direction determined by entry_type)
    amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    currency: str = "USDC"
    
    # Reference to parent transaction
    transaction_id: str = ""
    
    # For double-entry: link to corresponding entry
    counterpart_entry_id: Optional[str] = None
    
    # Ordering and integrity
    sequence_number: int = 0  # Global sequence for ordering
    checksum: str = ""  # SHA-256 of entry data for integrity
    previous_checksum: str = ""  # Chain entries together
    
    # Metadata
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    
    def compute_checksum(self) -> str:
        """
        Compute SHA-256 checksum of entry data.
        
        This creates a hash chain where each entry depends on the previous,
        making tampering detectable.
        """
        data = (
            f"{self.entry_id}|"
            f"{self.entry_type.value}|"
            f"{self.wallet_id}|"
            f"{self.amount}|"
            f"{self.currency}|"
            f"{self.transaction_id}|"
            f"{self.sequence_number}|"
            f"{self.previous_checksum}|"
            f"{self.created_at.isoformat()}"
        )
        return hashlib.sha256(data.encode()).hexdigest()
    
    def confirm(self) -> None:
        """Mark entry as confirmed."""
        self.status = EntryStatus.CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)
    
    def is_debit(self) -> bool:
        """Check if this is a debit entry (money out)."""
        return self.entry_type in (EntryType.DEBIT, EntryType.FEE, EntryType.HOLD, EntryType.BURN)
    
    def is_credit(self) -> bool:
        """Check if this is a credit entry (money in)."""
        return self.entry_type in (EntryType.CREDIT, EntryType.REFUND, EntryType.RELEASE, EntryType.MINT)
    
    def signed_amount(self) -> Decimal:
        """Get amount with sign based on entry type."""
        if self.is_debit():
            return -self.amount
        return self.amount


@dataclass
class LedgerTransaction:
    """
    A logical transaction containing multiple ledger entries.
    
    Every transaction must be balanced: sum of debits equals sum of credits.
    """
    
    transaction_id: str = field(default_factory=lambda: f"ltx_{uuid.uuid4().hex[:16]}")
    
    # Transaction type
    transaction_type: str = "transfer"  # transfer, fee, refund, settlement, mint, etc.
    
    # All entries in this transaction
    entries: list[LedgerEntry] = field(default_factory=list)
    
    # Status
    status: str = "pending"  # pending, confirmed, failed
    
    # Original payment transaction reference (if applicable)
    payment_tx_id: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    
    def is_balanced(self) -> bool:
        """Check if debits equal credits."""
        total_debits = sum(
            e.amount for e in self.entries 
            if e.is_debit() and e.status != EntryStatus.VOID
        )
        total_credits = sum(
            e.amount for e in self.entries 
            if e.is_credit() and e.status != EntryStatus.VOID
        )
        return total_debits == total_credits
    
    def total_amount(self) -> Decimal:
        """Get total transfer amount (sum of credits)."""
        return sum(
            e.amount for e in self.entries 
            if e.is_credit() and e.status != EntryStatus.VOID
        )
    
    def add_entry(self, entry: LedgerEntry) -> None:
        """Add an entry to this transaction."""
        entry.transaction_id = self.transaction_id
        self.entries.append(entry)
    
    def confirm_all(self) -> None:
        """Confirm all entries in the transaction."""
        for entry in self.entries:
            entry.confirm()
        self.status = "confirmed"
        self.confirmed_at = datetime.now(timezone.utc)


@dataclass
class LedgerCheckpoint:
    """
    A periodic checkpoint of ledger state for reconciliation.
    
    Checkpoints are created daily and store:
    - Total balance per wallet
    - Last sequence number
    - Hash of all entries since last checkpoint
    """
    
    checkpoint_id: str = field(default_factory=lambda: f"cp_{uuid.uuid4().hex[:16]}")
    
    # Checkpoint timing
    checkpoint_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # State at checkpoint
    last_sequence_number: int = 0
    last_entry_checksum: str = ""
    
    # Aggregated balances: wallet_id -> {currency -> balance}
    wallet_balances: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    
    # Verification
    entries_count: int = 0
    total_volume: Decimal = field(default_factory=lambda: Decimal("0.00"))
    checksum: str = ""  # Hash of this checkpoint
    
    def compute_checksum(self) -> str:
        """Compute checksum for this checkpoint."""
        # Convert balances to deterministic string
        balance_str = "|".join(
            f"{w}:{c}:{b}" 
            for w, currencies in sorted(self.wallet_balances.items())
            for c, b in sorted(currencies.items())
        )
        data = (
            f"{self.checkpoint_id}|"
            f"{self.checkpoint_date.isoformat()}|"
            f"{self.last_sequence_number}|"
            f"{self.last_entry_checksum}|"
            f"{balance_str}|"
            f"{self.entries_count}|"
            f"{self.total_volume}"
        )
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class BalanceProof:
    """
    Proof of balance for a wallet at a specific point in time.
    
    Used for auditing and reconciliation.
    """
    
    wallet_id: str
    currency: str
    balance: Decimal
    
    # The sequence number this balance is valid at
    as_of_sequence: int
    
    # List of entry IDs that contribute to this balance
    contributing_entries: list[str] = field(default_factory=list)
    
    # Verification
    checksum: str = ""
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

