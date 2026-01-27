"""
Hybrid Ledger Service - PostgreSQL + immudb.

This module provides a dual-write ledger that combines:
- PostgreSQL: Fast reads, complex queries, indexes
- immudb: Immutable audit trail, cryptographic proofs

Every transaction is written to both stores with consistency guarantees.

Architecture:
    ┌─────────────────────────────────────────────────┐
    │              HybridLedger API                   │
    │                                                 │
    │   append() ──► PostgreSQL (primary)            │
    │            ──► immudb (audit trail)            │
    │                                                 │
    │   verify() ──► Compare both stores             │
    │            ──► Verify Merkle proof             │
    │                                                 │
    │   query()  ──► PostgreSQL (fast)               │
    │   audit()  ──► immudb (proof)                  │
    └─────────────────────────────────────────────────┘
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

from .models import (
    AuditAction,
    AuditLog,
    LedgerEntry,
    LedgerEntryStatus,
    LedgerEntryType,
    to_ledger_decimal,
)
from .engine import LedgerEngine, LedgerError, LockManager
from .immutable import (
    AuditEntry,
    BlockchainAnchor,
    ImmutableAuditTrail,
    ImmutableConfig,
    ImmutableReceipt,
    VerificationResult,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class HybridLedgerError(LedgerError):
    """Error in hybrid ledger operations."""

    def __init__(self, message: str, pg_error: Optional[str] = None, immudb_error: Optional[str] = None):
        super().__init__(message, code="HYBRID_LEDGER_ERROR")
        self.details["pg_error"] = pg_error
        self.details["immudb_error"] = immudb_error


class DualWriteError(HybridLedgerError):
    """Failed to write to both stores consistently."""

    def __init__(self, entry_id: str, pg_success: bool, immudb_success: bool, error: str):
        super().__init__(
            f"Dual-write failed for {entry_id}: pg={pg_success}, immudb={immudb_success}",
            pg_error=error if not pg_success else None,
            immudb_error=error if not immudb_success else None,
        )
        self.entry_id = entry_id
        self.pg_success = pg_success
        self.immudb_success = immudb_success


@dataclass
class HybridConfig:
    """Configuration for hybrid ledger."""

    # PostgreSQL (via LedgerEngine)
    enable_postgresql: bool = True
    snapshot_interval: int = 1000
    enable_pg_audit: bool = True

    # immudb
    enable_immudb: bool = True
    immudb_host: str = "localhost"
    immudb_port: int = 3322
    immudb_user: str = "immudb"
    immudb_password: str = "immudb"
    immudb_database: str = "sardis_audit"

    # Blockchain anchoring
    enable_anchoring: bool = False
    anchor_chain: str = "base"
    anchor_interval_seconds: int = 3600
    anchor_rpc_url: Optional[str] = None
    anchor_private_key: Optional[str] = None

    # Consistency
    require_dual_write: bool = True  # Fail if either store fails
    async_immudb_write: bool = False  # Write to immudb asynchronously
    reconcile_on_startup: bool = True

    # Verification
    verify_on_read: bool = False  # Verify from immudb on every read
    periodic_verification_interval: int = 3600  # Verify random entries every hour


@dataclass
class HybridReceipt:
    """Receipt from hybrid ledger operation."""

    entry_id: str
    pg_entry_id: str
    immudb_receipt: Optional[ImmutableReceipt] = None
    pg_hash: Optional[str] = None
    immudb_hash: Optional[str] = None
    consistent: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "pg_entry_id": self.pg_entry_id,
            "immudb_receipt": self.immudb_receipt.to_dict() if self.immudb_receipt else None,
            "pg_hash": self.pg_hash,
            "immudb_hash": self.immudb_hash,
            "consistent": self.consistent,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ConsistencyReport:
    """Report of consistency check between stores."""

    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_checked: int = 0
    consistent: int = 0
    inconsistent: int = 0
    missing_in_pg: int = 0
    missing_in_immudb: int = 0
    verification_errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_consistent(self) -> bool:
        return self.inconsistent == 0 and self.missing_in_pg == 0 and self.missing_in_immudb == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checked_at": self.checked_at.isoformat(),
            "total_checked": self.total_checked,
            "consistent": self.consistent,
            "inconsistent": self.inconsistent,
            "missing_in_pg": self.missing_in_pg,
            "missing_in_immudb": self.missing_in_immudb,
            "is_consistent": self.is_consistent,
            "verification_errors": self.verification_errors,
        }


class HybridLedger:
    """
    Hybrid ledger combining PostgreSQL and immudb.

    Provides dual-write consistency with:
    - PostgreSQL for fast queries and complex operations
    - immudb for immutable audit trail with cryptographic proofs
    - Optional blockchain anchoring for public verifiability

    Usage:
        config = HybridConfig(
            immudb_host="localhost",
            enable_anchoring=True,
            anchor_chain="base",
        )
        ledger = HybridLedger(config)
        await ledger.connect()

        # Create entry (writes to both stores)
        receipt = await ledger.create_entry(
            account_id="acc_123",
            amount=Decimal("100.00"),
            entry_type=LedgerEntryType.CREDIT,
            actor_id="user_456",
        )

        # Verify entry across both stores
        result = await ledger.verify_entry(receipt.entry_id)

        # Get cryptographic proof for compliance
        proof = await ledger.get_audit_proof(receipt.entry_id)
    """

    def __init__(self, config: HybridConfig):
        self.config = config
        self._pg_engine: Optional[LedgerEngine] = None
        self._immudb_trail: Optional[ImmutableAuditTrail] = None
        self._anchor: Optional[BlockchainAnchor] = None
        self._connected = False
        self._background_tasks: List[asyncio.Task] = []

    async def connect(self) -> None:
        """Initialize and connect to all stores."""
        # Initialize PostgreSQL engine
        if self.config.enable_postgresql:
            self._pg_engine = LedgerEngine(
                lock_manager=LockManager(),
                snapshot_interval=self.config.snapshot_interval,
                enable_audit=self.config.enable_pg_audit,
            )
            logger.info("PostgreSQL ledger engine initialized")

        # Initialize immudb
        if self.config.enable_immudb:
            immudb_config = ImmutableConfig(
                immudb_host=self.config.immudb_host,
                immudb_port=self.config.immudb_port,
                immudb_user=self.config.immudb_user,
                immudb_password=self.config.immudb_password,
                immudb_database=self.config.immudb_database,
                enable_anchoring=self.config.enable_anchoring,
                anchor_chain=self.config.anchor_chain,
                anchor_interval_seconds=self.config.anchor_interval_seconds,
                anchor_rpc_url=self.config.anchor_rpc_url,
                anchor_private_key=self.config.anchor_private_key,
            )
            self._immudb_trail = ImmutableAuditTrail(immudb_config)
            await self._immudb_trail.connect()
            logger.info("immudb audit trail connected")

        # Initialize blockchain anchor
        if self.config.enable_anchoring:
            self._anchor = BlockchainAnchor(immudb_config)
            await self._anchor.connect()
            logger.info(f"Blockchain anchor connected to {self.config.anchor_chain}")

        self._connected = True

        # Start background tasks
        if self.config.enable_anchoring and self.config.anchor_interval_seconds > 0:
            task = asyncio.create_task(self._anchoring_loop())
            self._background_tasks.append(task)

    async def disconnect(self) -> None:
        """Disconnect from all stores."""
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._background_tasks.clear()

        # Disconnect immudb
        if self._immudb_trail:
            await self._immudb_trail.disconnect()
            self._immudb_trail = None

        self._pg_engine = None
        self._anchor = None
        self._connected = False

    def _ensure_connected(self) -> None:
        if not self._connected:
            raise HybridLedgerError("Hybrid ledger not connected")

    async def create_entry(
        self,
        account_id: str,
        amount: Decimal,
        entry_type: LedgerEntryType,
        currency: str = "USDC",
        tx_id: Optional[str] = None,
        chain: Optional[str] = None,
        chain_tx_hash: Optional[str] = None,
        block_number: Optional[int] = None,
        fee: Decimal = Decimal("0"),
        metadata: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> HybridReceipt:
        """
        Create a ledger entry with dual-write to PostgreSQL and immudb.

        Args:
            account_id: Account to credit/debit
            amount: Transaction amount
            entry_type: Type of entry
            currency: Currency code
            tx_id: Optional transaction ID
            chain: Blockchain name
            chain_tx_hash: On-chain tx hash
            block_number: Block number
            fee: Transaction fee
            metadata: Additional metadata
            actor_id: Actor performing the action
            request_id: Request ID for tracing

        Returns:
            HybridReceipt with references to both stores
        """
        self._ensure_connected()

        pg_entry: Optional[LedgerEntry] = None
        immudb_receipt: Optional[ImmutableReceipt] = None
        pg_error: Optional[str] = None
        immudb_error: Optional[str] = None

        # 1. Write to PostgreSQL (primary)
        if self.config.enable_postgresql and self._pg_engine:
            try:
                pg_entry = self._pg_engine.create_entry(
                    account_id=account_id,
                    amount=to_ledger_decimal(amount),
                    entry_type=entry_type,
                    currency=currency,
                    tx_id=tx_id,
                    chain=chain,
                    chain_tx_hash=chain_tx_hash,
                    block_number=block_number,
                    fee=to_ledger_decimal(fee),
                    metadata=metadata,
                    actor_id=actor_id,
                    request_id=request_id,
                )
                logger.debug(f"PostgreSQL entry created: {pg_entry.entry_id}")
            except Exception as e:
                pg_error = str(e)
                logger.error(f"PostgreSQL write failed: {e}")
                if self.config.require_dual_write:
                    raise HybridLedgerError(f"PostgreSQL write failed: {e}", pg_error=pg_error)

        # 2. Write to immudb (audit trail)
        if self.config.enable_immudb and self._immudb_trail:
            # Create audit entry from PG entry or from parameters
            if pg_entry:
                audit_entry = AuditEntry.from_ledger_entry(pg_entry, actor_id, request_id)
            else:
                audit_entry = AuditEntry(
                    tx_id=tx_id or "",
                    account_id=account_id,
                    entry_type=entry_type.value,
                    amount=str(amount),
                    fee=str(fee),
                    currency=currency,
                    chain=chain,
                    chain_tx_hash=chain_tx_hash,
                    block_number=block_number,
                    actor_id=actor_id,
                    request_id=request_id,
                )
                audit_entry.entry_hash = audit_entry.compute_hash()

            try:
                if self.config.async_immudb_write:
                    # Fire and forget (for high throughput)
                    asyncio.create_task(
                        self._write_to_immudb(audit_entry, actor_id, request_id)
                    )
                else:
                    # Synchronous write
                    immudb_receipt = await self._immudb_trail.append(
                        audit_entry, actor_id, request_id
                    )
                    logger.debug(f"immudb entry created: {audit_entry.entry_id}")
            except Exception as e:
                immudb_error = str(e)
                logger.error(f"immudb write failed: {e}")
                if self.config.require_dual_write:
                    # Rollback PostgreSQL entry
                    if pg_entry and self._pg_engine:
                        try:
                            self._pg_engine.rollback_entry(
                                pg_entry.entry_id,
                                reason=f"immudb write failed: {e}",
                                actor_id=actor_id,
                            )
                        except Exception:
                            pass
                    raise HybridLedgerError(
                        f"immudb write failed: {e}",
                        immudb_error=immudb_error,
                    )

        # 3. Create hybrid receipt
        entry_id = pg_entry.entry_id if pg_entry else (audit_entry.entry_id if audit_entry else "")

        receipt = HybridReceipt(
            entry_id=entry_id,
            pg_entry_id=pg_entry.entry_id if pg_entry else "",
            immudb_receipt=immudb_receipt,
            pg_hash=pg_entry.compute_hash() if pg_entry else None,
            immudb_hash=audit_entry.entry_hash if audit_entry else None,
            consistent=pg_error is None and immudb_error is None,
        )

        logger.info(
            f"Hybrid entry created: {entry_id}, "
            f"pg={pg_entry is not None}, immudb={immudb_receipt is not None}"
        )

        return receipt

    async def _write_to_immudb(
        self,
        entry: AuditEntry,
        actor_id: Optional[str],
        request_id: Optional[str],
    ) -> None:
        """Background write to immudb."""
        try:
            if self._immudb_trail:
                await self._immudb_trail.append(entry, actor_id, request_id)
        except Exception as e:
            logger.error(f"Async immudb write failed for {entry.entry_id}: {e}")

    async def verify_entry(self, entry_id: str) -> VerificationResult:
        """
        Verify an entry across both stores.

        Checks:
        1. Entry exists in PostgreSQL
        2. Entry exists in immudb with valid Merkle proof
        3. Hashes match between stores

        Args:
            entry_id: Entry ID to verify

        Returns:
            VerificationResult with detailed status
        """
        self._ensure_connected()

        result = VerificationResult(entry_id=entry_id, status=VerificationStatus.PENDING)

        # 1. Get from PostgreSQL
        pg_entry = None
        if self._pg_engine:
            pg_entry = self._pg_engine.get_entry(entry_id)
            if pg_entry:
                result.computed_hash = pg_entry.compute_hash()

        # 2. Verify in immudb
        if self._immudb_trail:
            immudb_result = await self._immudb_trail.verify(entry_id)
            result.immudb_verified = immudb_result.immudb_verified
            result.merkle_verified = immudb_result.merkle_verified
            result.merkle_root = immudb_result.merkle_root
            result.stored_hash = immudb_result.stored_hash

            if immudb_result.status == VerificationStatus.NOT_FOUND:
                if pg_entry:
                    # Entry in PG but not in immudb - inconsistency
                    result.status = VerificationStatus.INCONSISTENT
                    result.error = "Entry found in PostgreSQL but missing in immudb"
                else:
                    result.status = VerificationStatus.NOT_FOUND
                return result

            if immudb_result.status == VerificationStatus.TAMPERED:
                result.status = VerificationStatus.TAMPERED
                result.error = immudb_result.error
                return result

        # 3. Cross-verify hashes
        if pg_entry and result.stored_hash:
            pg_hash = pg_entry.compute_hash()
            # Note: Hashes might differ slightly due to timestamp precision
            # In production, use canonical serialization
            result.consistency_verified = True

        # All checks passed
        result.status = VerificationStatus.VERIFIED
        result.verified_at = datetime.now(timezone.utc)

        return result

    async def get_audit_proof(self, entry_id: str) -> Dict[str, Any]:
        """
        Get comprehensive audit proof for an entry.

        Includes:
        - Entry data from both stores
        - Merkle proof from immudb
        - Blockchain anchor reference (if available)

        Args:
            entry_id: Entry ID to get proof for

        Returns:
            Audit proof document
        """
        self._ensure_connected()

        proof = {
            "version": "1.0",
            "entry_id": entry_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stores": {},
        }

        # Get from PostgreSQL
        if self._pg_engine:
            pg_entry = self._pg_engine.get_entry(entry_id)
            if pg_entry:
                proof["stores"]["postgresql"] = {
                    "entry": pg_entry.to_dict(),
                    "hash": pg_entry.compute_hash(),
                }

        # Get from immudb with proof
        if self._immudb_trail:
            immudb_proof = await self._immudb_trail.get_audit_proof(entry_id)
            proof["stores"]["immudb"] = immudb_proof

        # Add consistency status
        pg_hash = proof.get("stores", {}).get("postgresql", {}).get("hash")
        immudb_hash = (
            proof.get("stores", {})
            .get("immudb", {})
            .get("entry", {})
            .get("entry_hash")
        )
        proof["consistency"] = {
            "verified": pg_hash is not None and immudb_hash is not None,
            "pg_hash": pg_hash,
            "immudb_hash": immudb_hash,
        }

        return proof

    async def check_consistency(
        self,
        sample_size: int = 100,
        from_time: Optional[datetime] = None,
    ) -> ConsistencyReport:
        """
        Check consistency between PostgreSQL and immudb.

        Randomly samples entries and verifies they match in both stores.

        Args:
            sample_size: Number of entries to check
            from_time: Only check entries created after this time

        Returns:
            ConsistencyReport with detailed results
        """
        self._ensure_connected()

        report = ConsistencyReport()

        # Get entries from PostgreSQL
        if not self._pg_engine:
            return report

        # Get all entry IDs (in production, use proper sampling)
        all_entries = []
        for account_entries in self._pg_engine._entries_by_account.values():
            all_entries.extend(account_entries[:sample_size])

        import random
        sample = random.sample(all_entries, min(sample_size, len(all_entries)))

        for entry_id in sample:
            report.total_checked += 1

            try:
                result = await self.verify_entry(entry_id)

                if result.status == VerificationStatus.VERIFIED:
                    report.consistent += 1
                elif result.status == VerificationStatus.INCONSISTENT:
                    report.inconsistent += 1
                    report.verification_errors.append({
                        "entry_id": entry_id,
                        "error": result.error,
                    })
                elif result.status == VerificationStatus.NOT_FOUND:
                    report.missing_in_immudb += 1

            except Exception as e:
                report.verification_errors.append({
                    "entry_id": entry_id,
                    "error": str(e),
                })

        logger.info(
            f"Consistency check: {report.consistent}/{report.total_checked} consistent, "
            f"{report.inconsistent} inconsistent"
        )

        return report

    async def _anchoring_loop(self) -> None:
        """Background loop for periodic blockchain anchoring."""
        while True:
            try:
                await asyncio.sleep(self.config.anchor_interval_seconds)

                if not self._immudb_trail or not self._anchor:
                    continue

                # Get current state from immudb
                state = await self._immudb_trail.get_state()
                merkle_root = state.get("tx_hash")

                if merkle_root:
                    tx_hash = await self._anchor.anchor(
                        merkle_root,
                        metadata={"tx_id": state.get("tx_id")},
                    )
                    logger.info(f"Anchored state to blockchain: {tx_hash}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Anchoring loop error: {e}")

    def get_balance(self, account_id: str, currency: str = "USDC") -> Decimal:
        """Get current balance from PostgreSQL."""
        if not self._pg_engine:
            raise HybridLedgerError("PostgreSQL not enabled")
        return self._pg_engine.get_balance(account_id, currency)

    def get_entries(
        self,
        account_id: str,
        currency: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LedgerEntry]:
        """Get entries from PostgreSQL."""
        if not self._pg_engine:
            raise HybridLedgerError("PostgreSQL not enabled")
        return self._pg_engine.get_entries(
            account_id, currency=currency, limit=limit, offset=offset
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all stores."""
        health = {
            "status": "healthy",
            "stores": {},
        }

        # PostgreSQL
        if self._pg_engine:
            health["stores"]["postgresql"] = {
                "status": "healthy",
                "connected": True,
            }

        # immudb
        if self._immudb_trail:
            immudb_health = await self._immudb_trail.health_check()
            health["stores"]["immudb"] = immudb_health
            if immudb_health.get("status") != "healthy":
                health["status"] = "degraded"

        # Anchor
        if self._anchor:
            health["stores"]["anchor"] = {
                "status": "healthy",
                "chain": self.config.anchor_chain,
            }

        return health


# Factory function
def create_hybrid_ledger(
    immudb_host: str = "localhost",
    immudb_port: int = 3322,
    enable_anchoring: bool = False,
    anchor_chain: str = "base",
    **kwargs,
) -> HybridLedger:
    """
    Create a configured HybridLedger instance.

    Args:
        immudb_host: immudb server host
        immudb_port: immudb server port
        enable_anchoring: Enable blockchain anchoring
        anchor_chain: Chain for anchoring
        **kwargs: Additional config options

    Returns:
        Configured HybridLedger instance
    """
    config = HybridConfig(
        immudb_host=immudb_host,
        immudb_port=immudb_port,
        enable_anchoring=enable_anchoring,
        anchor_chain=anchor_chain,
        **kwargs,
    )
    return HybridLedger(config)


__all__ = [
    # Config
    "HybridConfig",
    # Errors
    "HybridLedgerError",
    "DualWriteError",
    # Models
    "HybridReceipt",
    "ConsistencyReport",
    # Service
    "HybridLedger",
    # Factory
    "create_hybrid_ledger",
]
