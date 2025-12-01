"""
Core ledger service for append-only double-entry bookkeeping.

This service provides:
- Append-only ledger operations
- Double-entry transaction creation
- Atomic balance updates
- Double-spend prevention
- Transaction history and audit trail
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
import threading

from .models import (
    LedgerEntry,
    LedgerTransaction,
    LedgerCheckpoint,
    BalanceProof,
    EntryType,
    EntryStatus,
)


@dataclass
class TransferResult:
    """Result of a ledger transfer operation."""
    success: bool
    ledger_transaction: Optional[LedgerTransaction] = None
    error: Optional[str] = None


class LedgerService:
    """
    Core ledger service implementing append-only double-entry bookkeeping.
    
    Design principles:
    1. Append-only: Entries are never modified or deleted
    2. Double-entry: Every transaction has balanced debits and credits
    3. Atomic: Transactions either complete fully or not at all
    4. Auditable: Complete history with checksums for integrity
    
    This in-memory implementation can be replaced with a database backend
    for production use while maintaining the same interface.
    """
    
    def __init__(self):
        """Initialize the ledger service."""
        self._lock = threading.RLock()
        
        # Append-only entry log (ordered by sequence number)
        self._entries: list[LedgerEntry] = []
        
        # Transaction index
        self._transactions: dict[str, LedgerTransaction] = {}
        
        # Current sequence number (monotonically increasing)
        self._sequence_number: int = 0
        
        # Last checksum for chaining
        self._last_checksum: str = "genesis"
        
        # Balance cache: wallet_id -> {currency -> balance}
        self._balances: dict[str, dict[str, Decimal]] = {}
        
        # Held amounts: wallet_id -> {currency -> held_amount}
        self._holds: dict[str, dict[str, Decimal]] = {}
        
        # Checkpoints
        self._checkpoints: list[LedgerCheckpoint] = []
    
    # ==================== Core Transfer Operations ====================
    
    def transfer(
        self,
        from_wallet_id: str,
        to_wallet_id: str,
        amount: Decimal,
        currency: str = "USDC",
        fee: Decimal = Decimal("0"),
        fee_wallet_id: str = "sardis_fee_pool",
        description: Optional[str] = None,
        payment_tx_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> TransferResult:
        """
        Execute a transfer between wallets with double-entry bookkeeping.
        
        Creates entries:
        1. DEBIT from source wallet (amount + fee)
        2. CREDIT to destination wallet (amount)
        3. FEE to fee wallet (fee, if > 0)
        
        Args:
            from_wallet_id: Source wallet
            to_wallet_id: Destination wallet
            amount: Transfer amount
            currency: Currency code
            fee: Transaction fee
            fee_wallet_id: Wallet to receive fees
            description: Optional description
            payment_tx_id: Optional reference to payment transaction
            metadata: Optional metadata
            
        Returns:
            TransferResult with success status and ledger transaction
        """
        if amount <= Decimal("0"):
            return TransferResult(success=False, error="Amount must be positive")
        
        if fee < Decimal("0"):
            return TransferResult(success=False, error="Fee cannot be negative")
        
        total_debit = amount + fee
        
        with self._lock:
            # Check balance
            available = self.get_available_balance(from_wallet_id, currency)
            if available < total_debit:
                return TransferResult(
                    success=False,
                    error=f"Insufficient balance: have {available}, need {total_debit}"
                )
            
            # Create transaction
            tx = LedgerTransaction(
                transaction_type="transfer",
                payment_tx_id=payment_tx_id,
                description=description,
                metadata=metadata or {},
            )
            
            # Create debit entry (from source)
            debit_entry = self._create_entry(
                entry_type=EntryType.DEBIT,
                wallet_id=from_wallet_id,
                amount=total_debit,
                currency=currency,
                description=f"Transfer to {to_wallet_id}",
            )
            tx.add_entry(debit_entry)
            
            # Create credit entry (to destination)
            credit_entry = self._create_entry(
                entry_type=EntryType.CREDIT,
                wallet_id=to_wallet_id,
                amount=amount,
                currency=currency,
                description=f"Transfer from {from_wallet_id}",
                counterpart_entry_id=debit_entry.entry_id,
            )
            tx.add_entry(credit_entry)
            debit_entry.counterpart_entry_id = credit_entry.entry_id
            
            # Create fee entry if applicable
            if fee > Decimal("0"):
                fee_entry = self._create_entry(
                    entry_type=EntryType.FEE,
                    wallet_id=fee_wallet_id,
                    amount=fee,
                    currency=currency,
                    description=f"Fee for transfer {tx.transaction_id}",
                )
                tx.add_entry(fee_entry)
            
            # Verify transaction is balanced
            if not tx.is_balanced():
                return TransferResult(
                    success=False,
                    error="Transaction is not balanced - internal error"
                )
            
            # Commit entries
            for entry in tx.entries:
                self._commit_entry(entry)
            
            # Update balances
            self._update_balance(from_wallet_id, currency, -total_debit)
            self._update_balance(to_wallet_id, currency, amount)
            if fee > Decimal("0"):
                self._update_balance(fee_wallet_id, currency, fee)
            
            # Confirm transaction
            tx.confirm_all()
            self._transactions[tx.transaction_id] = tx
            
            return TransferResult(success=True, ledger_transaction=tx)
    
    def refund(
        self,
        original_tx_id: str,
        amount: Optional[Decimal] = None,
        description: Optional[str] = None
    ) -> TransferResult:
        """
        Refund a previous transaction (full or partial).
        
        Creates reverse entries with REFUND type.
        
        Args:
            original_tx_id: Transaction to refund
            amount: Amount to refund (None = full refund)
            description: Optional refund reason
            
        Returns:
            TransferResult with refund transaction
        """
        with self._lock:
            original_tx = self._transactions.get(original_tx_id)
            if not original_tx:
                return TransferResult(
                    success=False,
                    error=f"Transaction {original_tx_id} not found"
                )
            
            if original_tx.status != "confirmed":
                return TransferResult(
                    success=False,
                    error=f"Cannot refund transaction with status {original_tx.status}"
                )
            
            # Find the credit and debit entries
            credit_entries = [e for e in original_tx.entries if e.is_credit() and e.entry_type == EntryType.CREDIT]
            debit_entries = [e for e in original_tx.entries if e.entry_type == EntryType.DEBIT]
            
            if not credit_entries or not debit_entries:
                return TransferResult(
                    success=False,
                    error="Cannot determine original transfer parties"
                )
            
            original_amount = credit_entries[0].amount
            refund_amount = amount if amount is not None else original_amount
            
            if refund_amount > original_amount:
                return TransferResult(
                    success=False,
                    error=f"Refund amount {refund_amount} exceeds original {original_amount}"
                )
            
            # Create refund as reverse transfer
            from_wallet = credit_entries[0].wallet_id  # Original recipient
            to_wallet = debit_entries[0].wallet_id     # Original sender
            currency = credit_entries[0].currency
            
            # Check refund source has balance
            available = self.get_available_balance(from_wallet, currency)
            if available < refund_amount:
                return TransferResult(
                    success=False,
                    error=f"Insufficient balance for refund: have {available}, need {refund_amount}"
                )
            
            # Create refund transaction
            tx = LedgerTransaction(
                transaction_type="refund",
                payment_tx_id=original_tx.payment_tx_id,
                description=description or f"Refund of {original_tx_id}",
                metadata={"original_transaction_id": original_tx_id},
            )
            
            # Debit from original recipient
            debit_entry = self._create_entry(
                entry_type=EntryType.DEBIT,
                wallet_id=from_wallet,
                amount=refund_amount,
                currency=currency,
                description=f"Refund debit for {original_tx_id}",
            )
            tx.add_entry(debit_entry)
            
            # Credit to original sender
            credit_entry = self._create_entry(
                entry_type=EntryType.REFUND,
                wallet_id=to_wallet,
                amount=refund_amount,
                currency=currency,
                description=f"Refund credit for {original_tx_id}",
                counterpart_entry_id=debit_entry.entry_id,
            )
            tx.add_entry(credit_entry)
            debit_entry.counterpart_entry_id = credit_entry.entry_id
            
            # Commit
            for entry in tx.entries:
                self._commit_entry(entry)
            
            self._update_balance(from_wallet, currency, -refund_amount)
            self._update_balance(to_wallet, currency, refund_amount)
            
            tx.confirm_all()
            self._transactions[tx.transaction_id] = tx
            
            return TransferResult(success=True, ledger_transaction=tx)
    
    # ==================== Hold Operations (Pre-auth) ====================
    
    def create_hold(
        self,
        wallet_id: str,
        amount: Decimal,
        currency: str = "USDC",
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> TransferResult:
        """
        Create a hold (pre-authorization) on funds.
        
        Held funds are reserved but not yet transferred.
        
        Args:
            wallet_id: Wallet to hold funds in
            amount: Amount to hold
            currency: Currency code
            description: Optional description
            expires_at: Optional expiration time
            
        Returns:
            TransferResult with hold transaction
        """
        if amount <= Decimal("0"):
            return TransferResult(success=False, error="Amount must be positive")
        
        with self._lock:
            available = self.get_available_balance(wallet_id, currency)
            if available < amount:
                return TransferResult(
                    success=False,
                    error=f"Insufficient balance for hold: have {available}, need {amount}"
                )
            
            tx = LedgerTransaction(
                transaction_type="hold",
                description=description,
                metadata={"expires_at": expires_at.isoformat() if expires_at else None},
            )
            
            hold_entry = self._create_entry(
                entry_type=EntryType.HOLD,
                wallet_id=wallet_id,
                amount=amount,
                currency=currency,
                description=description,
            )
            tx.add_entry(hold_entry)
            
            self._commit_entry(hold_entry)
            
            # Add to holds (not deducted from balance yet)
            if wallet_id not in self._holds:
                self._holds[wallet_id] = {}
            if currency not in self._holds[wallet_id]:
                self._holds[wallet_id][currency] = Decimal("0")
            self._holds[wallet_id][currency] += amount
            
            tx.confirm_all()
            self._transactions[tx.transaction_id] = tx
            
            return TransferResult(success=True, ledger_transaction=tx)
    
    def capture_hold(
        self,
        hold_tx_id: str,
        to_wallet_id: str,
        amount: Optional[Decimal] = None,
        fee: Decimal = Decimal("0"),
        fee_wallet_id: str = "sardis_fee_pool"
    ) -> TransferResult:
        """
        Capture (complete) a previous hold.
        
        Converts held funds into a completed transfer.
        """
        with self._lock:
            hold_tx = self._transactions.get(hold_tx_id)
            if not hold_tx or hold_tx.transaction_type != "hold":
                return TransferResult(
                    success=False,
                    error=f"Hold transaction {hold_tx_id} not found"
                )
            
            hold_entry = hold_tx.entries[0]
            hold_amount = hold_entry.amount
            capture_amount = amount if amount is not None else hold_amount
            
            if capture_amount > hold_amount:
                return TransferResult(
                    success=False,
                    error=f"Capture amount {capture_amount} exceeds hold {hold_amount}"
                )
            
            from_wallet = hold_entry.wallet_id
            currency = hold_entry.currency
            
            # Release the hold
            if from_wallet in self._holds and currency in self._holds[from_wallet]:
                self._holds[from_wallet][currency] -= hold_amount
            
            # Execute the actual transfer
            return self.transfer(
                from_wallet_id=from_wallet,
                to_wallet_id=to_wallet_id,
                amount=capture_amount,
                currency=currency,
                fee=fee,
                fee_wallet_id=fee_wallet_id,
                description=f"Capture of hold {hold_tx_id}",
                metadata={"hold_transaction_id": hold_tx_id},
            )
    
    def void_hold(self, hold_tx_id: str) -> TransferResult:
        """
        Void (cancel) a hold, releasing the reserved funds.
        """
        with self._lock:
            hold_tx = self._transactions.get(hold_tx_id)
            if not hold_tx or hold_tx.transaction_type != "hold":
                return TransferResult(
                    success=False,
                    error=f"Hold transaction {hold_tx_id} not found"
                )
            
            hold_entry = hold_tx.entries[0]
            wallet_id = hold_entry.wallet_id
            amount = hold_entry.amount
            currency = hold_entry.currency
            
            # Create void transaction
            tx = LedgerTransaction(
                transaction_type="void",
                description=f"Void of hold {hold_tx_id}",
                metadata={"hold_transaction_id": hold_tx_id},
            )
            
            release_entry = self._create_entry(
                entry_type=EntryType.RELEASE,
                wallet_id=wallet_id,
                amount=amount,
                currency=currency,
                description=f"Release of hold {hold_tx_id}",
            )
            tx.add_entry(release_entry)
            
            self._commit_entry(release_entry)
            
            # Release the hold
            if wallet_id in self._holds and currency in self._holds[wallet_id]:
                self._holds[wallet_id][currency] -= amount
            
            # Mark original hold entry as void
            hold_entry.status = EntryStatus.VOID
            
            tx.confirm_all()
            self._transactions[tx.transaction_id] = tx
            
            return TransferResult(success=True, ledger_transaction=tx)
    
    # ==================== Balance Operations ====================
    
    def get_balance(self, wallet_id: str, currency: str = "USDC") -> Decimal:
        """Get total balance for a wallet (including held funds)."""
        with self._lock:
            if wallet_id not in self._balances:
                return Decimal("0")
            return self._balances[wallet_id].get(currency, Decimal("0"))
    
    def get_held_amount(self, wallet_id: str, currency: str = "USDC") -> Decimal:
        """Get amount currently held (pre-authorized)."""
        with self._lock:
            if wallet_id not in self._holds:
                return Decimal("0")
            return self._holds[wallet_id].get(currency, Decimal("0"))
    
    def get_available_balance(self, wallet_id: str, currency: str = "USDC") -> Decimal:
        """Get available balance (total minus held)."""
        return self.get_balance(wallet_id, currency) - self.get_held_amount(wallet_id, currency)
    
    def get_all_balances(self, wallet_id: str) -> dict[str, Decimal]:
        """Get all currency balances for a wallet."""
        with self._lock:
            return dict(self._balances.get(wallet_id, {}))
    
    def set_balance(self, wallet_id: str, currency: str, amount: Decimal) -> None:
        """
        Set balance directly (for initialization).
        
        Warning: This bypasses double-entry bookkeeping.
        Use only for system initialization.
        """
        with self._lock:
            if wallet_id not in self._balances:
                self._balances[wallet_id] = {}
            self._balances[wallet_id][currency] = amount
    
    # ==================== Query Operations ====================
    
    def get_transaction(self, transaction_id: str) -> Optional[LedgerTransaction]:
        """Get a transaction by ID."""
        return self._transactions.get(transaction_id)
    
    def get_entries_for_wallet(
        self,
        wallet_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[LedgerEntry]:
        """Get ledger entries for a wallet."""
        with self._lock:
            wallet_entries = [e for e in self._entries if e.wallet_id == wallet_id]
            # Sort by sequence number descending (newest first)
            wallet_entries.sort(key=lambda e: e.sequence_number, reverse=True)
            return wallet_entries[offset:offset + limit]
    
    def get_entries_since(self, sequence_number: int) -> list[LedgerEntry]:
        """Get all entries since a sequence number."""
        with self._lock:
            return [e for e in self._entries if e.sequence_number > sequence_number]
    
    def get_balance_proof(self, wallet_id: str, currency: str) -> BalanceProof:
        """
        Generate a proof of balance for auditing.
        
        Returns the balance and list of all contributing entries.
        """
        with self._lock:
            entries = [
                e for e in self._entries
                if e.wallet_id == wallet_id and e.currency == currency
            ]
            
            balance = sum(e.signed_amount() for e in entries)
            
            return BalanceProof(
                wallet_id=wallet_id,
                currency=currency,
                balance=balance,
                as_of_sequence=self._sequence_number,
                contributing_entries=[e.entry_id for e in entries],
            )
    
    # ==================== Internal Operations ====================
    
    def _create_entry(
        self,
        entry_type: EntryType,
        wallet_id: str,
        amount: Decimal,
        currency: str,
        description: Optional[str] = None,
        counterpart_entry_id: Optional[str] = None,
    ) -> LedgerEntry:
        """Create a new ledger entry (not yet committed)."""
        entry = LedgerEntry(
            entry_type=entry_type,
            wallet_id=wallet_id,
            amount=amount,
            currency=currency,
            description=description,
            counterpart_entry_id=counterpart_entry_id,
        )
        return entry
    
    def _commit_entry(self, entry: LedgerEntry) -> None:
        """Commit an entry to the ledger (append-only)."""
        self._sequence_number += 1
        entry.sequence_number = self._sequence_number
        entry.previous_checksum = self._last_checksum
        entry.checksum = entry.compute_checksum()
        self._last_checksum = entry.checksum
        entry.confirm()
        self._entries.append(entry)
    
    def _update_balance(self, wallet_id: str, currency: str, delta: Decimal) -> None:
        """Update cached balance."""
        if wallet_id not in self._balances:
            self._balances[wallet_id] = {}
        if currency not in self._balances[wallet_id]:
            self._balances[wallet_id][currency] = Decimal("0")
        self._balances[wallet_id][currency] += delta
    
    # ==================== Checkpointing ====================
    
    def create_checkpoint(self) -> LedgerCheckpoint:
        """
        Create a checkpoint of current ledger state.
        
        Checkpoints can be used for:
        - Fast balance recovery
        - Periodic reconciliation
        - Audit snapshots
        """
        with self._lock:
            last_checkpoint = self._checkpoints[-1] if self._checkpoints else None
            
            checkpoint = LedgerCheckpoint(
                period_start=last_checkpoint.period_end if last_checkpoint else None,
                period_end=datetime.now(timezone.utc),
                last_sequence_number=self._sequence_number,
                last_entry_checksum=self._last_checksum,
                wallet_balances={
                    wallet_id: dict(currencies)
                    for wallet_id, currencies in self._balances.items()
                },
                entries_count=len(self._entries),
            )
            
            # Calculate volume since last checkpoint
            start_seq = last_checkpoint.last_sequence_number if last_checkpoint else 0
            new_entries = [e for e in self._entries if e.sequence_number > start_seq]
            checkpoint.total_volume = sum(e.amount for e in new_entries if e.is_credit())
            
            checkpoint.checksum = checkpoint.compute_checksum()
            self._checkpoints.append(checkpoint)
            
            return checkpoint
    
    def get_latest_checkpoint(self) -> Optional[LedgerCheckpoint]:
        """Get the most recent checkpoint."""
        return self._checkpoints[-1] if self._checkpoints else None
    
    def verify_integrity(self) -> Tuple[bool, Optional[str]]:
        """
        Verify ledger integrity by checking the hash chain.
        
        Returns (is_valid, error_message).
        """
        with self._lock:
            if not self._entries:
                return True, None
            
            expected_checksum = "genesis"
            for entry in self._entries:
                if entry.previous_checksum != expected_checksum:
                    return False, f"Checksum chain broken at entry {entry.entry_id}"
                
                computed = entry.compute_checksum()
                if computed != entry.checksum:
                    return False, f"Entry {entry.entry_id} checksum mismatch"
                
                expected_checksum = entry.checksum
            
            return True, None


# Global ledger service instance
_ledger_service: Optional[LedgerService] = None


def get_ledger_service() -> LedgerService:
    """Get the global ledger service instance."""
    global _ledger_service
    if _ledger_service is None:
        _ledger_service = LedgerService()
    return _ledger_service

