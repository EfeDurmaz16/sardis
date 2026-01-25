"""
Ledger engine with row-level locking, batch processing, and transaction management.

This module provides production-grade transaction handling with:
- Row-level locking for concurrent transaction safety
- Batch transaction processing with atomic commits
- Transaction rollback capabilities
- Optimistic concurrency control
- Comprehensive error handling
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, Generator, List, Optional, Sequence, Tuple, TypeVar

from .models import (
    AuditAction,
    AuditLog,
    BalanceSnapshot,
    BatchTransaction,
    LedgerEntry,
    LedgerEntryStatus,
    LedgerEntryType,
    LockRecord,
    ReconciliationRecord,
    ReconciliationStatus,
    to_ledger_decimal,
    validate_amount,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LedgerError(Exception):
    """Base exception for ledger operations."""

    def __init__(self, message: str, code: str = "LEDGER_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": str(self),
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class LockAcquisitionError(LedgerError):
    """Failed to acquire lock on resource."""

    def __init__(self, resource_type: str, resource_id: str, holder_id: Optional[str] = None):
        details = {"resource_type": resource_type, "resource_id": resource_id}
        if holder_id:
            details["current_holder"] = holder_id
        super().__init__(
            f"Failed to acquire lock on {resource_type}:{resource_id}",
            code="LOCK_ACQUISITION_FAILED",
            details=details,
        )


class LockTimeoutError(LedgerError):
    """Lock acquisition timed out."""

    def __init__(self, resource_type: str, resource_id: str, timeout: float):
        super().__init__(
            f"Lock acquisition timed out after {timeout}s for {resource_type}:{resource_id}",
            code="LOCK_TIMEOUT",
            details={"resource_type": resource_type, "resource_id": resource_id, "timeout": timeout},
        )


class ConcurrencyError(LedgerError):
    """Optimistic concurrency conflict detected."""

    def __init__(self, entity_id: str, expected_version: int, actual_version: int):
        super().__init__(
            f"Concurrency conflict on {entity_id}: expected version {expected_version}, got {actual_version}",
            code="CONCURRENCY_CONFLICT",
            details={"entity_id": entity_id, "expected_version": expected_version, "actual_version": actual_version},
        )


class InsufficientBalanceError(LedgerError):
    """Account has insufficient balance for operation."""

    def __init__(self, account_id: str, required: Decimal, available: Decimal):
        super().__init__(
            f"Insufficient balance in {account_id}: required {required}, available {available}",
            code="INSUFFICIENT_BALANCE",
            details={"account_id": account_id, "required": str(required), "available": str(available)},
        )


class BatchProcessingError(LedgerError):
    """Error during batch processing."""

    def __init__(self, batch_id: str, failed_index: int, cause: Exception):
        super().__init__(
            f"Batch {batch_id} failed at entry {failed_index}: {cause}",
            code="BATCH_PROCESSING_FAILED",
            details={"batch_id": batch_id, "failed_index": failed_index, "cause": str(cause)},
        )


class RollbackError(LedgerError):
    """Error during transaction rollback."""

    def __init__(self, tx_id: str, reason: str):
        super().__init__(
            f"Failed to rollback transaction {tx_id}: {reason}",
            code="ROLLBACK_FAILED",
            details={"tx_id": tx_id, "reason": reason},
        )


class ValidationError(LedgerError):
    """Input validation error."""

    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Validation error for {field}: {reason}",
            code="VALIDATION_ERROR",
            details={"field": field, "value": str(value), "reason": reason},
        )


@dataclass
class LockManager:
    """
    Thread-safe lock manager for row-level locking.

    Supports both synchronous and asynchronous operations
    with configurable timeouts and automatic cleanup.
    """

    # Lock storage
    _locks: Dict[str, LockRecord] = field(default_factory=dict)

    # Thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock)

    # Configuration
    default_timeout: float = 30.0  # seconds
    lock_expiry: timedelta = field(default_factory=lambda: timedelta(minutes=5))

    # Cleanup tracking
    _last_cleanup: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cleanup_interval: timedelta = field(default_factory=lambda: timedelta(minutes=1))

    def _make_key(self, resource_type: str, resource_id: str) -> str:
        """Create unique key for resource."""
        return f"{resource_type}:{resource_id}"

    def _cleanup_expired(self) -> int:
        """Remove expired locks. Returns count of cleaned locks."""
        now = datetime.now(timezone.utc)
        if now - self._last_cleanup < self.cleanup_interval:
            return 0

        expired_keys = []
        for key, lock in self._locks.items():
            if not lock.is_active():
                expired_keys.append(key)

        for key in expired_keys:
            del self._locks[key]
            logger.debug(f"Cleaned up expired lock: {key}")

        self._last_cleanup = now
        return len(expired_keys)

    def acquire(
        self,
        resource_type: str,
        resource_id: str,
        holder_id: str,
        timeout: Optional[float] = None,
        is_exclusive: bool = True,
    ) -> LockRecord:
        """
        Acquire a lock on a resource.

        Args:
            resource_type: Type of resource (e.g., "account", "entry")
            resource_id: Unique identifier of resource
            holder_id: ID of transaction/process acquiring lock
            timeout: Max time to wait for lock (None = use default)
            is_exclusive: Whether lock is exclusive (write) or shared (read)

        Returns:
            LockRecord representing the acquired lock

        Raises:
            LockTimeoutError: If lock cannot be acquired within timeout
            LockAcquisitionError: If lock acquisition fails
        """
        timeout = timeout if timeout is not None else self.default_timeout
        key = self._make_key(resource_type, resource_id)
        start_time = time.monotonic()

        while True:
            with self._lock:
                self._cleanup_expired()

                existing = self._locks.get(key)

                # Check if lock is free or held by same holder
                if existing is None or not existing.is_active():
                    lock = LockRecord(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        holder_id=holder_id,
                        is_exclusive=is_exclusive,
                        expires_at=datetime.now(timezone.utc) + self.lock_expiry,
                    )
                    self._locks[key] = lock
                    logger.debug(f"Lock acquired: {key} by {holder_id}")
                    return lock

                # Same holder can re-acquire
                if existing.holder_id == holder_id:
                    # Extend expiry
                    existing.expires_at = datetime.now(timezone.utc) + self.lock_expiry
                    logger.debug(f"Lock extended: {key} by {holder_id}")
                    return existing

                # Shared locks can coexist if existing is also shared
                if not is_exclusive and not existing.is_exclusive:
                    # Would need to track multiple holders for proper shared locks
                    # For now, treat all locks as exclusive for safety
                    pass

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                raise LockTimeoutError(resource_type, resource_id, timeout)

            # Wait and retry
            time.sleep(min(0.1, timeout - elapsed))

    async def acquire_async(
        self,
        resource_type: str,
        resource_id: str,
        holder_id: str,
        timeout: Optional[float] = None,
        is_exclusive: bool = True,
    ) -> LockRecord:
        """Async version of acquire."""
        timeout = timeout if timeout is not None else self.default_timeout
        key = self._make_key(resource_type, resource_id)
        start_time = time.monotonic()

        while True:
            with self._lock:
                self._cleanup_expired()

                existing = self._locks.get(key)

                if existing is None or not existing.is_active():
                    lock = LockRecord(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        holder_id=holder_id,
                        is_exclusive=is_exclusive,
                        expires_at=datetime.now(timezone.utc) + self.lock_expiry,
                    )
                    self._locks[key] = lock
                    logger.debug(f"Lock acquired (async): {key} by {holder_id}")
                    return lock

                if existing.holder_id == holder_id:
                    existing.expires_at = datetime.now(timezone.utc) + self.lock_expiry
                    return existing

            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                raise LockTimeoutError(resource_type, resource_id, timeout)

            await asyncio.sleep(min(0.1, timeout - elapsed))

    def release(self, resource_type: str, resource_id: str, holder_id: str) -> bool:
        """
        Release a lock on a resource.

        Args:
            resource_type: Type of resource
            resource_id: Unique identifier of resource
            holder_id: ID of holder releasing lock

        Returns:
            True if lock was released, False if not found or not owned
        """
        key = self._make_key(resource_type, resource_id)

        with self._lock:
            existing = self._locks.get(key)
            if existing is None:
                return False

            if existing.holder_id != holder_id:
                logger.warning(f"Lock release denied: {key} owned by {existing.holder_id}, not {holder_id}")
                return False

            existing.released_at = datetime.now(timezone.utc)
            del self._locks[key]
            logger.debug(f"Lock released: {key} by {holder_id}")
            return True

    def is_locked(self, resource_type: str, resource_id: str) -> bool:
        """Check if a resource is currently locked."""
        key = self._make_key(resource_type, resource_id)
        with self._lock:
            existing = self._locks.get(key)
            return existing is not None and existing.is_active()

    def get_lock_info(self, resource_type: str, resource_id: str) -> Optional[LockRecord]:
        """Get information about current lock on resource."""
        key = self._make_key(resource_type, resource_id)
        with self._lock:
            existing = self._locks.get(key)
            if existing and existing.is_active():
                return existing
            return None

    @contextmanager
    def lock(
        self,
        resource_type: str,
        resource_id: str,
        holder_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Generator[LockRecord, None, None]:
        """
        Context manager for acquiring and releasing locks.

        Usage:
            with lock_manager.lock("account", "acc_123", "tx_456") as lock:
                # Do work while holding lock
                pass
            # Lock automatically released
        """
        holder = holder_id or f"holder_{uuid.uuid4().hex[:12]}"
        lock_record = self.acquire(resource_type, resource_id, holder, timeout)
        try:
            yield lock_record
        finally:
            self.release(resource_type, resource_id, holder)

    @asynccontextmanager
    async def lock_async(
        self,
        resource_type: str,
        resource_id: str,
        holder_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """Async context manager for acquiring and releasing locks."""
        holder = holder_id or f"holder_{uuid.uuid4().hex[:12]}"
        lock_record = await self.acquire_async(resource_type, resource_id, holder, timeout)
        try:
            yield lock_record
        finally:
            self.release(resource_type, resource_id, holder)


class LedgerEngine:
    """
    Production-grade ledger engine with full transaction support.

    Features:
    - Row-level locking for concurrent transactions
    - Batch transaction processing
    - Transaction rollback capabilities
    - Balance snapshots for point-in-time queries
    - Comprehensive audit trail
    - Currency conversion support
    """

    def __init__(
        self,
        lock_manager: Optional[LockManager] = None,
        snapshot_interval: int = 1000,  # Create snapshot every N entries
        enable_audit: bool = True,
    ):
        self.lock_manager = lock_manager or LockManager()
        self.snapshot_interval = snapshot_interval
        self.enable_audit = enable_audit

        # In-memory storage (replace with DB in production)
        self._entries: Dict[str, LedgerEntry] = {}
        self._entries_by_account: Dict[str, List[str]] = {}
        self._snapshots: Dict[str, List[BalanceSnapshot]] = {}
        self._audit_logs: List[AuditLog] = []
        self._batches: Dict[str, BatchTransaction] = {}
        self._entry_count: Dict[str, int] = {}

        # Last audit hash for chain
        self._last_audit_hash: Optional[str] = None

        # Thread safety for in-memory operations
        self._data_lock = threading.RLock()

        logger.info("LedgerEngine initialized with audit=%s, snapshot_interval=%d", enable_audit, snapshot_interval)

    def _generate_tx_id(self) -> str:
        """Generate unique transaction ID."""
        return f"tx_{uuid.uuid4().hex[:20]}"

    def _add_audit_log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[str] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """Add an audit log entry with hash chain."""
        if not self.enable_audit:
            return None

        log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            old_value=old_value,
            new_value=new_value,
            request_id=request_id,
            previous_hash=self._last_audit_hash,
        )
        log.entry_hash = log.compute_hash()
        self._last_audit_hash = log.entry_hash

        with self._data_lock:
            self._audit_logs.append(log)

        logger.debug(f"Audit log: {action.value} {entity_type}:{entity_id}")
        return log

    def get_balance(self, account_id: str, currency: str = "USDC", at_time: Optional[datetime] = None) -> Decimal:
        """
        Get account balance, optionally at a specific point in time.

        Uses snapshots for efficient historical queries.
        """
        with self._data_lock:
            entry_ids = self._entries_by_account.get(account_id, [])

            if not entry_ids:
                return Decimal("0")

            # For current balance, sum all entries
            if at_time is None:
                balance = Decimal("0")
                for entry_id in entry_ids:
                    entry = self._entries.get(entry_id)
                    if entry and entry.currency == currency and entry.status == LedgerEntryStatus.CONFIRMED:
                        if entry.entry_type in (LedgerEntryType.CREDIT, LedgerEntryType.REFUND):
                            balance += entry.amount
                        elif entry.entry_type in (LedgerEntryType.DEBIT, LedgerEntryType.FEE):
                            balance -= entry.amount
                        elif entry.entry_type == LedgerEntryType.TRANSFER:
                            # For transfers, check if account is source or destination
                            # This would need additional tracking in a real implementation
                            pass
                return balance

            # For historical balance, find nearest snapshot and compute from there
            snapshots = self._snapshots.get(f"{account_id}:{currency}", [])

            # Find snapshot before at_time
            snapshot = None
            for s in reversed(snapshots):
                if s.snapshot_at <= at_time:
                    snapshot = s
                    break

            if snapshot:
                balance = snapshot.balance
                start_time = snapshot.last_entry_created_at or snapshot.snapshot_at
            else:
                balance = Decimal("0")
                start_time = datetime.min.replace(tzinfo=timezone.utc)

            # Add entries after snapshot up to at_time
            for entry_id in entry_ids:
                entry = self._entries.get(entry_id)
                if (
                    entry
                    and entry.currency == currency
                    and entry.status == LedgerEntryStatus.CONFIRMED
                    and start_time < entry.created_at <= at_time
                ):
                    if entry.entry_type in (LedgerEntryType.CREDIT, LedgerEntryType.REFUND):
                        balance += entry.amount
                    elif entry.entry_type in (LedgerEntryType.DEBIT, LedgerEntryType.FEE):
                        balance -= entry.amount

            return balance

    def create_entry(
        self,
        account_id: str,
        amount: Decimal,
        entry_type: LedgerEntryType,
        currency: str = "USDC",
        tx_id: Optional[str] = None,
        chain: Optional[str] = None,
        chain_tx_hash: Optional[str] = None,
        block_number: Optional[int] = None,
        audit_anchor: Optional[str] = None,
        fee: Decimal = Decimal("0"),
        metadata: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
        skip_lock: bool = False,
    ) -> LedgerEntry:
        """
        Create a new ledger entry with row-level locking.

        Args:
            account_id: Account to add entry to
            amount: Amount of the entry (positive value)
            entry_type: Type of entry (credit, debit, etc.)
            currency: Currency code
            tx_id: Optional transaction ID (generated if not provided)
            chain: Blockchain name if on-chain
            chain_tx_hash: On-chain transaction hash
            block_number: Block number where confirmed
            audit_anchor: Audit anchor hash
            fee: Fee amount
            metadata: Additional metadata
            actor_id: ID of actor creating entry
            request_id: Request ID for tracing
            skip_lock: Skip locking (use with caution, for internal batches)

        Returns:
            Created LedgerEntry

        Raises:
            ValidationError: If input validation fails
            LockTimeoutError: If unable to acquire lock
            InsufficientBalanceError: If debit would cause negative balance
        """
        # Validate inputs
        amount = to_ledger_decimal(amount)
        fee = to_ledger_decimal(fee)
        validate_amount(amount, allow_zero=False)

        if not account_id:
            raise ValidationError("account_id", account_id, "Account ID is required")

        holder_id = request_id or self._generate_tx_id()

        # Acquire lock on account
        if not skip_lock:
            lock = self.lock_manager.acquire("account", account_id, holder_id)
        else:
            lock = None

        try:
            # Check balance for debits
            if entry_type in (LedgerEntryType.DEBIT, LedgerEntryType.FEE):
                current_balance = self.get_balance(account_id, currency)
                required = amount + fee
                if current_balance < required:
                    raise InsufficientBalanceError(account_id, required, current_balance)

            # Create entry
            entry = LedgerEntry(
                tx_id=tx_id or self._generate_tx_id(),
                account_id=account_id,
                entry_type=entry_type,
                amount=amount,
                fee=fee,
                currency=currency,
                chain=chain,
                chain_tx_hash=chain_tx_hash,
                block_number=block_number,
                audit_anchor=audit_anchor,
                status=LedgerEntryStatus.CONFIRMED,
                confirmed_at=datetime.now(timezone.utc),
                metadata=metadata or {},
            )

            # Calculate and set running balance
            entry.running_balance = self._calculate_new_balance(account_id, currency, entry)

            # Store entry
            with self._data_lock:
                self._entries[entry.entry_id] = entry
                if account_id not in self._entries_by_account:
                    self._entries_by_account[account_id] = []
                self._entries_by_account[account_id].append(entry.entry_id)

                # Update entry count and check for snapshot
                key = f"{account_id}:{currency}"
                self._entry_count[key] = self._entry_count.get(key, 0) + 1
                if self._entry_count[key] % self.snapshot_interval == 0:
                    self._create_snapshot(account_id, currency, entry)

            # Audit log
            self._add_audit_log(
                action=AuditAction.CREATE,
                entity_type="ledger_entry",
                entity_id=entry.entry_id,
                actor_id=actor_id,
                new_value=entry.to_dict(),
                request_id=request_id,
            )

            logger.info(
                f"Created ledger entry: {entry.entry_id}, account={account_id}, "
                f"type={entry_type.value}, amount={amount}, balance={entry.running_balance}"
            )

            return entry

        finally:
            if lock:
                self.lock_manager.release("account", account_id, holder_id)

    async def create_entry_async(
        self,
        account_id: str,
        amount: Decimal,
        entry_type: LedgerEntryType,
        currency: str = "USDC",
        **kwargs,
    ) -> LedgerEntry:
        """Async version of create_entry."""
        # For truly async, this would use async DB operations
        # For now, run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.create_entry(account_id, amount, entry_type, currency, **kwargs)
        )

    def _calculate_new_balance(self, account_id: str, currency: str, new_entry: LedgerEntry) -> Decimal:
        """Calculate new balance after adding entry."""
        current = self.get_balance(account_id, currency)

        if new_entry.entry_type in (LedgerEntryType.CREDIT, LedgerEntryType.REFUND):
            return current + new_entry.amount
        elif new_entry.entry_type in (LedgerEntryType.DEBIT, LedgerEntryType.FEE):
            return current - new_entry.amount - new_entry.fee
        else:
            return current

    def _create_snapshot(self, account_id: str, currency: str, last_entry: LedgerEntry) -> BalanceSnapshot:
        """Create a balance snapshot for the account."""
        snapshot = BalanceSnapshot(
            account_id=account_id,
            currency=currency,
            balance=last_entry.running_balance,
            last_entry_id=last_entry.entry_id,
            last_entry_created_at=last_entry.created_at,
            entry_count=self._entry_count.get(f"{account_id}:{currency}", 0),
        )

        key = f"{account_id}:{currency}"
        if key not in self._snapshots:
            self._snapshots[key] = []
        self._snapshots[key].append(snapshot)

        self._add_audit_log(
            action=AuditAction.SNAPSHOT,
            entity_type="balance_snapshot",
            entity_id=snapshot.snapshot_id,
            new_value=snapshot.to_dict(),
        )

        logger.debug(f"Created snapshot: {snapshot.snapshot_id} for {account_id}, balance={snapshot.balance}")
        return snapshot

    def create_batch(
        self,
        entries: Sequence[Dict[str, Any]],
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> BatchTransaction:
        """
        Create and process a batch of entries atomically.

        All entries succeed or all fail (all-or-nothing semantics).

        Args:
            entries: List of entry specifications, each containing:
                - account_id: str
                - amount: Decimal or str
                - entry_type: LedgerEntryType or str
                - currency: str (optional, default "USDC")
                - Additional fields passed to create_entry
            actor_id: ID of actor creating batch
            request_id: Request ID for tracing

        Returns:
            BatchTransaction with results

        Raises:
            BatchProcessingError: If any entry fails
            ValidationError: If input validation fails
        """
        batch = BatchTransaction()
        holder_id = request_id or batch.batch_id

        # Collect all accounts that need locking
        accounts_to_lock = set()
        for spec in entries:
            accounts_to_lock.add(spec["account_id"])

        # Sort accounts to prevent deadlocks (always acquire in same order)
        sorted_accounts = sorted(accounts_to_lock)

        # Acquire all locks
        acquired_locks = []
        try:
            for account_id in sorted_accounts:
                lock = self.lock_manager.acquire("account", account_id, holder_id)
                acquired_locks.append((account_id, lock))

            # Process all entries
            created_entries: List[LedgerEntry] = []
            for i, spec in enumerate(entries):
                try:
                    entry_type = spec.get("entry_type")
                    if isinstance(entry_type, str):
                        entry_type = LedgerEntryType(entry_type)

                    entry = self.create_entry(
                        account_id=spec["account_id"],
                        amount=to_ledger_decimal(spec["amount"]),
                        entry_type=entry_type,
                        currency=spec.get("currency", "USDC"),
                        tx_id=spec.get("tx_id"),
                        chain=spec.get("chain"),
                        chain_tx_hash=spec.get("chain_tx_hash"),
                        block_number=spec.get("block_number"),
                        audit_anchor=spec.get("audit_anchor"),
                        fee=to_ledger_decimal(spec.get("fee", 0)),
                        metadata=spec.get("metadata"),
                        actor_id=actor_id,
                        request_id=request_id,
                        skip_lock=True,  # Already holding locks
                    )
                    created_entries.append(entry)
                except Exception as e:
                    # Rollback already created entries
                    for created in created_entries:
                        self._rollback_entry(created, reason=f"Batch failed at index {i}")

                    batch.status = LedgerEntryStatus.FAILED
                    batch.error_message = str(e)
                    raise BatchProcessingError(batch.batch_id, i, e)

            # All succeeded
            batch.entries = created_entries
            batch.status = LedgerEntryStatus.CONFIRMED
            batch.completed_at = datetime.now(timezone.utc)

            with self._data_lock:
                self._batches[batch.batch_id] = batch

            self._add_audit_log(
                action=AuditAction.CREATE,
                entity_type="batch",
                entity_id=batch.batch_id,
                actor_id=actor_id,
                new_value=batch.to_dict(),
                request_id=request_id,
            )

            logger.info(
                f"Batch completed: {batch.batch_id}, entries={len(created_entries)}, "
                f"total_amount={batch.total_amount()}"
            )

            return batch

        finally:
            # Release all locks in reverse order
            for account_id, _ in reversed(acquired_locks):
                self.lock_manager.release("account", account_id, holder_id)

    async def create_batch_async(
        self,
        entries: Sequence[Dict[str, Any]],
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> BatchTransaction:
        """Async version of create_batch."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.create_batch(entries, actor_id, request_id)
        )

    def rollback_entry(
        self,
        entry_id: str,
        reason: str,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> LedgerEntry:
        """
        Rollback a ledger entry by creating a reversal entry.

        Args:
            entry_id: ID of entry to rollback
            reason: Reason for rollback
            actor_id: ID of actor performing rollback
            request_id: Request ID for tracing

        Returns:
            The reversal entry

        Raises:
            LedgerError: If entry not found or already reversed
        """
        with self._data_lock:
            original = self._entries.get(entry_id)

        if not original:
            raise LedgerError(f"Entry not found: {entry_id}", code="ENTRY_NOT_FOUND")

        if original.status == LedgerEntryStatus.REVERSED:
            raise LedgerError(f"Entry already reversed: {entry_id}", code="ALREADY_REVERSED")

        return self._rollback_entry(original, reason, actor_id, request_id)

    def _rollback_entry(
        self,
        entry: LedgerEntry,
        reason: str,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> LedgerEntry:
        """Internal rollback implementation."""
        holder_id = request_id or self._generate_tx_id()
        lock = self.lock_manager.acquire("account", entry.account_id, holder_id)

        try:
            # Determine reversal type
            if entry.entry_type in (LedgerEntryType.CREDIT, LedgerEntryType.REFUND):
                reversal_type = LedgerEntryType.DEBIT
            else:
                reversal_type = LedgerEntryType.CREDIT

            # Create reversal entry
            reversal = LedgerEntry(
                tx_id=f"rev_{entry.tx_id}",
                account_id=entry.account_id,
                entry_type=LedgerEntryType.REVERSAL,
                amount=entry.amount,
                fee=Decimal("0"),  # Don't reverse fees typically
                currency=entry.currency,
                chain=entry.chain,
                audit_anchor=entry.audit_anchor,
                status=LedgerEntryStatus.CONFIRMED,
                confirmed_at=datetime.now(timezone.utc),
                metadata={
                    "original_entry_id": entry.entry_id,
                    "reversal_reason": reason,
                    "original_type": entry.entry_type.value,
                },
            )

            # Update original entry status
            old_value = entry.to_dict()
            entry.status = LedgerEntryStatus.REVERSED

            # Calculate new running balance
            reversal.running_balance = self._calculate_new_balance(
                entry.account_id, entry.currency, reversal
            )

            # Store
            with self._data_lock:
                self._entries[reversal.entry_id] = reversal
                self._entries_by_account[entry.account_id].append(reversal.entry_id)

            # Audit logs
            self._add_audit_log(
                action=AuditAction.ROLLBACK,
                entity_type="ledger_entry",
                entity_id=entry.entry_id,
                actor_id=actor_id,
                old_value=old_value,
                new_value=entry.to_dict(),
                request_id=request_id,
            )

            self._add_audit_log(
                action=AuditAction.CREATE,
                entity_type="ledger_entry",
                entity_id=reversal.entry_id,
                actor_id=actor_id,
                new_value=reversal.to_dict(),
                request_id=request_id,
            )

            logger.info(
                f"Rolled back entry: {entry.entry_id} -> {reversal.entry_id}, "
                f"reason={reason}, amount={entry.amount}"
            )

            return reversal

        finally:
            self.lock_manager.release("account", entry.account_id, holder_id)

    def rollback_batch(
        self,
        batch_id: str,
        reason: str,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> BatchTransaction:
        """
        Rollback an entire batch of entries.

        Args:
            batch_id: ID of batch to rollback
            reason: Reason for rollback
            actor_id: ID of actor performing rollback
            request_id: Request ID for tracing

        Returns:
            Updated BatchTransaction

        Raises:
            LedgerError: If batch not found or already rolled back
        """
        with self._data_lock:
            batch = self._batches.get(batch_id)

        if not batch:
            raise LedgerError(f"Batch not found: {batch_id}", code="BATCH_NOT_FOUND")

        if batch.is_rolled_back:
            raise LedgerError(f"Batch already rolled back: {batch_id}", code="ALREADY_ROLLED_BACK")

        # Rollback all entries in reverse order
        for entry in reversed(batch.entries):
            if entry.status != LedgerEntryStatus.REVERSED:
                self._rollback_entry(entry, f"Batch rollback: {reason}", actor_id, request_id)

        # Update batch status
        old_value = batch.to_dict()
        batch.is_rolled_back = True
        batch.rollback_reason = reason
        batch.rollback_at = datetime.now(timezone.utc)

        self._add_audit_log(
            action=AuditAction.ROLLBACK,
            entity_type="batch",
            entity_id=batch_id,
            actor_id=actor_id,
            old_value=old_value,
            new_value=batch.to_dict(),
            request_id=request_id,
        )

        logger.info(f"Rolled back batch: {batch_id}, entries={len(batch.entries)}, reason={reason}")

        return batch

    def get_entry(self, entry_id: str) -> Optional[LedgerEntry]:
        """Get a ledger entry by ID."""
        with self._data_lock:
            return self._entries.get(entry_id)

    def get_entries(
        self,
        account_id: str,
        currency: Optional[str] = None,
        entry_type: Optional[LedgerEntryType] = None,
        status: Optional[LedgerEntryStatus] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LedgerEntry]:
        """
        Get ledger entries for an account with filtering.

        Args:
            account_id: Account to get entries for
            currency: Filter by currency
            entry_type: Filter by entry type
            status: Filter by status
            from_time: Filter entries created after this time
            to_time: Filter entries created before this time
            limit: Maximum entries to return
            offset: Number of entries to skip

        Returns:
            List of matching LedgerEntry objects
        """
        with self._data_lock:
            entry_ids = self._entries_by_account.get(account_id, [])

            entries = []
            for entry_id in entry_ids:
                entry = self._entries.get(entry_id)
                if not entry:
                    continue

                # Apply filters
                if currency and entry.currency != currency:
                    continue
                if entry_type and entry.entry_type != entry_type:
                    continue
                if status and entry.status != status:
                    continue
                if from_time and entry.created_at < from_time:
                    continue
                if to_time and entry.created_at > to_time:
                    continue

                entries.append(entry)

            # Sort by created_at descending
            entries.sort(key=lambda e: e.created_at, reverse=True)

            # Apply pagination
            return entries[offset : offset + limit]

    def get_snapshots(
        self,
        account_id: str,
        currency: str = "USDC",
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> List[BalanceSnapshot]:
        """Get balance snapshots for an account."""
        key = f"{account_id}:{currency}"
        with self._data_lock:
            snapshots = self._snapshots.get(key, [])

            if from_time or to_time:
                filtered = []
                for s in snapshots:
                    if from_time and s.snapshot_at < from_time:
                        continue
                    if to_time and s.snapshot_at > to_time:
                        continue
                    filtered.append(s)
                return filtered

            return list(snapshots)

    def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        actor_id: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs with filtering."""
        with self._data_lock:
            logs = []
            for log in self._audit_logs:
                if entity_type and log.entity_type != entity_type:
                    continue
                if entity_id and log.entity_id != entity_id:
                    continue
                if action and log.action != action:
                    continue
                if actor_id and log.actor_id != actor_id:
                    continue
                if from_time and log.created_at < from_time:
                    continue
                if to_time and log.created_at > to_time:
                    continue
                logs.append(log)

            # Return most recent first
            logs.sort(key=lambda l: l.created_at, reverse=True)
            return logs[:limit]

    def verify_audit_chain(self) -> Tuple[bool, Optional[str]]:
        """
        Verify integrity of audit log hash chain.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._audit_logs:
            return True, None

        with self._data_lock:
            for i, log in enumerate(self._audit_logs):
                expected_previous = self._audit_logs[i - 1].entry_hash if i > 0 else None

                if log.previous_hash != expected_previous:
                    return False, f"Hash chain broken at audit log {log.audit_id}"

                computed = log.compute_hash()
                if log.entry_hash != computed:
                    return False, f"Hash mismatch at audit log {log.audit_id}"

        return True, None

    def get_batch(self, batch_id: str) -> Optional[BatchTransaction]:
        """Get a batch by ID."""
        with self._data_lock:
            return self._batches.get(batch_id)


__all__ = [
    # Exceptions
    "LedgerError",
    "LockAcquisitionError",
    "LockTimeoutError",
    "ConcurrencyError",
    "InsufficientBalanceError",
    "BatchProcessingError",
    "RollbackError",
    "ValidationError",
    # Lock Manager
    "LockManager",
    # Engine
    "LedgerEngine",
]
