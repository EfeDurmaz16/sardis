"""
Ledger storage abstractions with production-grade features.

This module provides:
- Append-only ledger with Merkle tree receipts
- SQLite (dev) and PostgreSQL (production) support
- Row-level locking for concurrent transactions
- Batch processing with atomic commits
- Balance snapshots for point-in-time queries
- Comprehensive reconciliation queue
- Full audit trail
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Sequence, Tuple

from sardis_v2_core.transactions import Transaction, OnChainRecord
from sardis_v2_core.tokens import normalize_token_amount

from .models import (
    DECIMAL_PRECISION,
    DECIMAL_SCALE,
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

# Configure module-level logging
logging.getLogger(__name__).addHandler(logging.NullHandler())


@dataclass
class ChainReceipt:
    """
    Receipt for an on-chain transaction.

    Captures the essential details needed to link
    a ledger entry to its blockchain settlement.
    """
    tx_hash: str
    chain: str
    block_number: int
    audit_anchor: str

    # Optional additional fields
    gas_used: Optional[int] = None
    gas_price: Optional[Decimal] = None
    timestamp: Optional[datetime] = None
    confirmed: bool = True
    execution_path: str = "legacy_tx"
    user_op_hash: Optional[str] = None
    proof_artifact_path: Optional[str] = None
    proof_artifact_sha256: Optional[str] = None

    def __post_init__(self):
        if self.gas_price is not None:
            self.gas_price = to_ledger_decimal(self.gas_price)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tx_hash": self.tx_hash,
            "chain": self.chain,
            "block_number": self.block_number,
            "audit_anchor": self.audit_anchor,
            "gas_used": self.gas_used,
            "gas_price": str(self.gas_price) if self.gas_price else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "confirmed": self.confirmed,
            "execution_path": self.execution_path,
            "user_op_hash": self.user_op_hash,
            "proof_artifact_path": self.proof_artifact_path,
            "proof_artifact_sha256": self.proof_artifact_sha256,
        }


@dataclass
class PendingReconciliation:
    """
    Entry for failed ledger appends requiring reconciliation.

    When a payment succeeds on-chain but the ledger append fails,
    this record captures all the data needed to retry the append.
    """
    id: str
    mandate_id: str
    chain_tx_hash: str
    chain: str
    audit_anchor: str
    from_wallet: str
    to_wallet: str
    amount: str
    currency: str
    error: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    last_retry: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    # Priority for retry ordering
    priority: int = 0

    # Additional context
    block_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "mandate_id": self.mandate_id,
            "chain_tx_hash": self.chain_tx_hash,
            "chain": self.chain,
            "audit_anchor": self.audit_anchor,
            "from_wallet": self.from_wallet,
            "to_wallet": self.to_wallet,
            "amount": self.amount,
            "currency": self.currency,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
            "last_retry": self.last_retry.isoformat() if self.last_retry else None,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "priority": self.priority,
            "block_number": self.block_number,
        }


class LedgerStore:
    """
    Production-grade ledger storage with full transaction support.

    Features:
    - SQLite (development) and PostgreSQL (production) backends
    - Row-level locking for concurrent transactions
    - Batch transaction processing
    - Balance snapshots for point-in-time queries
    - Merkle tree receipts for audit proofs
    - Comprehensive reconciliation queue

    Thread Safety:
    - All public methods are thread-safe
    - Uses connection pooling for PostgreSQL
    - Uses a single connection with threading lock for SQLite
    """

    # Schema version for migrations
    SCHEMA_VERSION = 2

    def __init__(self, dsn: str, enable_wal: bool = True):
        """
        Initialize the ledger store.

        Args:
            dsn: Database connection string
                 - "sqlite:///path/to/db.sqlite" for SQLite
                 - "postgresql://user:pass@host/db" for PostgreSQL
            enable_wal: Enable Write-Ahead Logging for SQLite (recommended)
        """
        self._dsn = dsn
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._pg_pool = None
        self._records: list[Transaction] = []
        self._receipt_mem: Dict[str, Dict[str, Any]] = {}
        self._use_postgres = False

        # Thread safety
        self._lock = threading.RLock()

        # Audit tracking
        self._last_audit_hash: Optional[str] = None
        self._audit_logs: List[AuditLog] = []

        # Balance snapshot tracking
        self._snapshots: Dict[str, List[BalanceSnapshot]] = {}
        self._entry_counts: Dict[str, int] = {}
        self._snapshot_interval = 1000  # Create snapshot every N entries

        logger.info(f"Initializing LedgerStore with DSN type: {dsn.split(':')[0]}")

        if dsn.startswith("sqlite:///"):
            self._init_sqlite(dsn, enable_wal)
        elif dsn.startswith("postgresql://") or dsn.startswith("postgres://"):
            self._use_postgres = True
            logger.info("PostgreSQL mode enabled - pool will be created on first use")
        else:
            logger.warning("Unknown DSN format - using in-memory fallback")
            self._use_postgres = False

    def _init_sqlite(self, dsn: str, enable_wal: bool) -> None:
        """Initialize SQLite database with all tables."""
        path = Path(dsn.removeprefix("sqlite:///"))
        path.parent.mkdir(parents=True, exist_ok=True)

        self._sqlite_conn = sqlite3.connect(path, check_same_thread=False)

        # Enable WAL mode for better concurrent read performance
        if enable_wal:
            self._sqlite_conn.execute("PRAGMA journal_mode=WAL")
            self._sqlite_conn.execute("PRAGMA synchronous=NORMAL")

        # Create tables with enhanced schema
        self._sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_entries (
                tx_id TEXT PRIMARY KEY,
                entry_id TEXT UNIQUE,
                mandate_id TEXT,
                from_wallet TEXT NOT NULL,
                to_wallet TEXT NOT NULL,
                amount TEXT NOT NULL,
                fee TEXT DEFAULT '0',
                running_balance TEXT,
                currency TEXT NOT NULL,
                entry_type TEXT DEFAULT 'transfer',
                chain TEXT,
                chain_tx_hash TEXT,
                block_number INTEGER,
                audit_anchor TEXT,
                merkle_root TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at TEXT NOT NULL,
                confirmed_at TEXT,
                version INTEGER DEFAULT 1,
                metadata_json TEXT
            )
            """
        )

        # Enhanced indexes for common queries
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ledger_created ON ledger_entries(created_at)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ledger_from_wallet ON ledger_entries(from_wallet)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ledger_to_wallet ON ledger_entries(to_wallet)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ledger_chain_tx ON ledger_entries(chain_tx_hash)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ledger_status ON ledger_entries(status)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ledger_mandate ON ledger_entries(mandate_id)"
        )

        # Receipts + accumulator state for deterministic proofs
        self._sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                mandate_id TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                chain TEXT NOT NULL,
                audit_anchor TEXT,
                merkle_root TEXT NOT NULL,
                leaf_hash TEXT NOT NULL,
                proof_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_receipts_created ON receipts(created_at)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_receipts_tx_hash ON receipts(tx_hash)"
        )

        # Ledger metadata (merkle root, schema version, etc.)
        self._sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT
            )
            """
        )

        # Balance snapshots for point-in-time queries
        self._sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS balance_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                currency TEXT NOT NULL,
                balance TEXT NOT NULL,
                last_entry_id TEXT,
                last_entry_created_at TEXT,
                entry_count INTEGER,
                snapshot_at TEXT NOT NULL,
                merkle_root TEXT
            )
            """
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_account ON balance_snapshots(account_id, currency)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_time ON balance_snapshots(snapshot_at)"
        )

        # Reconciliation queue for failed appends (enhanced)
        self._sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_reconciliation (
                id TEXT PRIMARY KEY,
                mandate_id TEXT NOT NULL,
                chain_tx_hash TEXT NOT NULL,
                chain TEXT NOT NULL,
                audit_anchor TEXT,
                from_wallet TEXT NOT NULL,
                to_wallet TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                error TEXT NOT NULL,
                created_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_retry TEXT,
                resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                priority INTEGER DEFAULT 0,
                block_number INTEGER,
                metadata_json TEXT
            )
            """
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reconciliation_resolved ON pending_reconciliation(resolved)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reconciliation_mandate ON pending_reconciliation(mandate_id)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reconciliation_priority ON pending_reconciliation(priority, created_at)"
        )

        # Audit log table
        self._sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                actor_id TEXT,
                actor_type TEXT,
                old_value_json TEXT,
                new_value_json TEXT,
                request_id TEXT,
                created_at TEXT NOT NULL,
                previous_hash TEXT,
                entry_hash TEXT
            )
            """
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id)"
        )
        self._sqlite_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at)"
        )

        # Row locks table (for pessimistic locking)
        self._sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS row_locks (
                lock_id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                holder_id TEXT NOT NULL,
                holder_type TEXT DEFAULT 'transaction',
                acquired_at TEXT NOT NULL,
                expires_at TEXT,
                released_at TEXT,
                is_exclusive INTEGER DEFAULT 1,
                UNIQUE(resource_type, resource_id)
            )
            """
        )

        # Set schema version
        self._sqlite_conn.execute(
            "INSERT OR REPLACE INTO ledger_meta (key, value, updated_at) VALUES (?, ?, ?)",
            ("schema_version", str(self.SCHEMA_VERSION), datetime.now(timezone.utc).isoformat())
        )

        self._sqlite_conn.commit()
        logger.info(f"SQLite database initialized at {path}")
    
    async def _get_pg_pool(self):
        """Lazy initialization of PostgreSQL pool."""
        if self._pg_pool is None:
            from sardis_v2_core.database import Database
            self._pg_pool = await Database.get_pool()
        return self._pg_pool

    def append(self, payment_mandate, chain_receipt: ChainReceipt) -> Transaction:
        """Append a transaction to the ledger (sync version for SQLite)."""
        with self._lock:
            amount = normalize_token_amount(payment_mandate.token, int(payment_mandate.amount_minor))
            from_wallet_id = getattr(payment_mandate, "wallet_id", None) or payment_mandate.subject
            tx = Transaction(
                from_wallet=from_wallet_id,
                to_wallet=payment_mandate.destination,
                amount=amount,
                currency=payment_mandate.token,
                audit_anchor=chain_receipt.audit_anchor,
            )
            tx.add_on_chain_record(
                OnChainRecord(
                    chain=chain_receipt.chain,
                    tx_hash=chain_receipt.tx_hash,
                    from_address=from_wallet_id,
                    to_address=payment_mandate.destination,
                    block_number=chain_receipt.block_number,
                    status="confirmed" if chain_receipt.block_number else "pending",
                )
            )
            created_at = tx.created_at.isoformat()
            if self._sqlite_conn:
                self._sqlite_conn.execute(
                    """
                    INSERT INTO ledger_entries (
                        tx_id, mandate_id, from_wallet, to_wallet, amount, currency, chain,
                        chain_tx_hash, audit_anchor, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tx.tx_id,
                        payment_mandate.mandate_id,
                        from_wallet_id,
                        payment_mandate.destination,
                        str(amount),
                        payment_mandate.token,
                        chain_receipt.chain,
                        chain_receipt.tx_hash,
                        chain_receipt.audit_anchor,
                        created_at,
                    ),
                )
                self._sqlite_conn.commit()
            else:
                self._records.append(tx)
            return tx

    def _get_last_root_sqlite(self) -> str:
        cur = self._sqlite_conn.execute("SELECT value FROM ledger_meta WHERE key = 'merkle_root'")
        row = cur.fetchone()
        return row[0] if row else "0" * 64

    def _set_last_root_sqlite(self, root: str) -> None:
        self._sqlite_conn.execute(
            "INSERT OR REPLACE INTO ledger_meta (key, value) VALUES ('merkle_root', ?)",
            (root,),
        )
        self._sqlite_conn.commit()

    def create_receipt(self, payment_mandate, chain_receipt: ChainReceipt) -> Dict[str, Any]:
        """
        Create deterministic receipt with hash-chained Merkle root.
        - leaf_hash = sha256(mandate_id|tx_hash|timestamp|audit_anchor)
        - merkle_root = sha256(prev_root|leaf_hash)
        Proof contains leaf + previous_root.

        Uses deterministic timestamp from chain receipt if available,
        otherwise falls back to mandate timestamp for determinism.
        """
        # Use deterministic timestamp: chain receipt timestamp > wall-clock time
        if chain_receipt.timestamp:
            timestamp = chain_receipt.timestamp.isoformat()
        else:
            # Fallback: use current time but this is less deterministic
            timestamp = datetime.now(timezone.utc).isoformat()

        payload = "|".join(
            [
                payment_mandate.mandate_id,
                chain_receipt.tx_hash,
                timestamp,
                chain_receipt.audit_anchor or "",
            ]
        )
        leaf_hash = hashlib.sha256(payload.encode()).hexdigest()
        if self._sqlite_conn:
            prev_root = self._get_last_root_sqlite()
        else:
            prev_root = getattr(self, "_last_root_mem", "0" * 64)
        merkle_root = hashlib.sha256(f"{prev_root}{leaf_hash}".encode()).hexdigest()
        receipt_id = f"rct_{leaf_hash[:20]}"
        proof = {"leaf": leaf_hash, "previous_root": prev_root}

        receipt = {
            "receipt_id": receipt_id,
            "mandate_id": payment_mandate.mandate_id,
            "tx_hash": chain_receipt.tx_hash,
            "chain": chain_receipt.chain,
            "audit_anchor": chain_receipt.audit_anchor,
            "merkle_root": merkle_root,
            "merkle_proof": proof,
            "timestamp": timestamp,
        }

        if self._sqlite_conn:
            self._sqlite_conn.execute(
                """
                INSERT INTO receipts (
                    receipt_id, mandate_id, tx_hash, chain, audit_anchor,
                    merkle_root, leaf_hash, proof_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    payment_mandate.mandate_id,
                    chain_receipt.tx_hash,
                    chain_receipt.chain,
                    chain_receipt.audit_anchor,
                    merkle_root,
                    leaf_hash,
                    json.dumps(proof),
                    timestamp,
                ),
            )
            self._set_last_root_sqlite(merkle_root)
        else:
            self._receipt_mem[receipt_id] = receipt
            setattr(self, "_last_root_mem", merkle_root)

        return receipt

    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        if self._sqlite_conn:
            row = self._sqlite_conn.execute(
                "SELECT receipt_id, mandate_id, tx_hash, chain, audit_anchor, merkle_root, proof_json, created_at FROM receipts WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
            if not row:
                return None
            proof = json.loads(row[6])
            return {
                "receipt_id": row[0],
                "mandate_id": row[1],
                "tx_hash": row[2],
                "chain": row[3],
                "audit_anchor": row[4],
                "merkle_root": row[5],
                "merkle_proof": proof,
                "timestamp": row[7],
            }
        return self._receipt_mem.get(receipt_id)

    def get_receipt_by_tx_hash(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get the most recent receipt for a given chain transaction hash (sync)."""
        if self._use_postgres:
            raise RuntimeError("PostgreSQL mode requires get_receipt_by_tx_hash_async()")

        if self._sqlite_conn:
            row = self._sqlite_conn.execute(
                """
                SELECT receipt_id, mandate_id, tx_hash, chain, audit_anchor, merkle_root, proof_json, created_at
                FROM receipts
                WHERE tx_hash = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (tx_hash,),
            ).fetchone()
            if not row:
                return None
            proof = json.loads(row[6])
            return {
                "receipt_id": row[0],
                "mandate_id": row[1],
                "tx_hash": row[2],
                "chain": row[3],
                "audit_anchor": row[4],
                "merkle_root": row[5],
                "merkle_proof": proof,
                "timestamp": row[7],
            }

        candidates = [r for r in self._receipt_mem.values() if r.get("tx_hash") == tx_hash]
        if not candidates:
            return None
        candidates.sort(key=lambda r: str(r.get("timestamp", "")), reverse=True)
        return candidates[0]

    async def create_receipt_async(self, payment_mandate, chain_receipt: ChainReceipt) -> Dict[str, Any]:
        """Create receipt with Merkle proof (async, PostgreSQL supported)."""
        if not self._use_postgres:
            return self.create_receipt(payment_mandate, chain_receipt)

        if chain_receipt.timestamp:
            timestamp_dt = chain_receipt.timestamp
        else:
            timestamp_dt = datetime.now(timezone.utc)
        timestamp = timestamp_dt.isoformat()

        payload = "|".join([
            payment_mandate.mandate_id,
            chain_receipt.tx_hash,
            timestamp,
            chain_receipt.audit_anchor or "",
        ])
        leaf_hash = hashlib.sha256(payload.encode()).hexdigest()

        # Get previous root from DB
        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM ledger_meta WHERE key = 'merkle_root'"
            )
            prev_root = row["value"] if row else "0" * 64

        merkle_root = hashlib.sha256(f"{prev_root}{leaf_hash}".encode()).hexdigest()
        receipt_id = f"rct_{leaf_hash[:20]}"
        proof = {"leaf": leaf_hash, "previous_root": prev_root}

        receipt = {
            "receipt_id": receipt_id,
            "mandate_id": payment_mandate.mandate_id,
            "tx_hash": chain_receipt.tx_hash,
            "chain": chain_receipt.chain,
            "audit_anchor": chain_receipt.audit_anchor,
            "merkle_root": merkle_root,
            "merkle_proof": proof,
            "timestamp": timestamp,
        }

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO receipts (
                        tx_id, receipt_id, mandate_id, tx_hash, chain, audit_anchor,
                        merkle_root, leaf_hash, proof_json, status, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (tx_id) DO UPDATE SET
                        merkle_root = EXCLUDED.merkle_root,
                        leaf_hash = EXCLUDED.leaf_hash,
                        proof_json = EXCLUDED.proof_json,
                        created_at = EXCLUDED.created_at
                    """,
                    chain_receipt.tx_hash,
                    receipt_id,
                    payment_mandate.mandate_id,
                    chain_receipt.tx_hash,
                    chain_receipt.chain,
                    chain_receipt.audit_anchor,
                    merkle_root,
                    leaf_hash,
                    json.dumps(proof),
                    "confirmed",
                    timestamp_dt,
                )
                await conn.execute(
                    """
                    INSERT INTO ledger_meta (key, value, updated_at)
                    VALUES ('merkle_root', $1, NOW())
                    ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = NOW()
                    """,
                    merkle_root,
                )

        return receipt

    async def get_receipt_async(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        """Get receipt by ID (async, PostgreSQL supported)."""
        if not self._use_postgres:
            return self.get_receipt(receipt_id)

        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT receipt_id, mandate_id, tx_hash, chain, audit_anchor,
                       merkle_root, proof_json, created_at
                FROM receipts WHERE receipt_id = $1
                """,
                receipt_id,
            )
        if not row:
            return None
        proof = row["proof_json"] if isinstance(row["proof_json"], dict) else json.loads(row["proof_json"] or "{}")
        created_at = row["created_at"]
        return {
            "receipt_id": row["receipt_id"],
            "mandate_id": row["mandate_id"],
            "tx_hash": row["tx_hash"],
            "chain": row["chain"],
            "audit_anchor": row["audit_anchor"],
            "merkle_root": row["merkle_root"],
            "merkle_proof": proof,
            "timestamp": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
        }

    async def get_receipt_by_tx_hash_async(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get the most recent receipt for a given chain transaction hash (async)."""
        if not self._use_postgres:
            return self.get_receipt_by_tx_hash(tx_hash)

        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT receipt_id, mandate_id, tx_hash, chain, audit_anchor,
                       merkle_root, proof_json, created_at
                FROM receipts
                WHERE tx_hash = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                tx_hash,
            )
        if not row:
            return None

        proof = row["proof_json"] if isinstance(row["proof_json"], dict) else json.loads(row["proof_json"] or "{}")
        created_at = row["created_at"]
        return {
            "receipt_id": row["receipt_id"],
            "mandate_id": row["mandate_id"],
            "tx_hash": row["tx_hash"],
            "chain": row["chain"],
            "audit_anchor": row["audit_anchor"],
            "merkle_root": row["merkle_root"],
            "merkle_proof": proof,
            "timestamp": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
        }

    def get_current_merkle_root(self) -> str:
        """Get current accumulator Merkle root (sync)."""
        if self._use_postgres:
            raise RuntimeError("PostgreSQL mode requires get_current_merkle_root_async()")
        if self._sqlite_conn:
            return self._get_last_root_sqlite()
        return str(getattr(self, "_last_root_mem", "0" * 64))

    async def get_current_merkle_root_async(self) -> str:
        """Get current accumulator Merkle root (async)."""
        if not self._use_postgres:
            return self.get_current_merkle_root()

        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM ledger_meta WHERE key = 'merkle_root'"
            )
        return str(row["value"]) if row and row["value"] else ("0" * 64)

    @staticmethod
    def _compute_leaf_hash(
        mandate_id: str,
        tx_hash: str,
        timestamp: str,
        audit_anchor: str,
    ) -> str:
        payload = "|".join([mandate_id, tx_hash, timestamp, audit_anchor])
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _compute_root(previous_root: str, leaf_hash: str) -> str:
        return hashlib.sha256(f"{previous_root}{leaf_hash}".encode()).hexdigest()

    def verify_receipt_integrity(
        self,
        receipt: Dict[str, Any],
        *,
        current_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify a receipt's Merkle leaf/root derivation.

        Returns a structured report with per-check booleans.
        """
        proof = receipt.get("merkle_proof")
        leaf_from_proof = proof.get("leaf") if isinstance(proof, dict) else None
        previous_root = proof.get("previous_root") if isinstance(proof, dict) else None
        stored_root = str(receipt.get("merkle_root", ""))
        timestamp = str(receipt.get("timestamp", ""))
        mandate_id = str(receipt.get("mandate_id", ""))
        tx_hash = str(receipt.get("tx_hash", ""))
        audit_anchor = str(receipt.get("audit_anchor", "") or "")

        recomputed_leaf = ""
        recomputed_root = ""
        if mandate_id and tx_hash and timestamp:
            recomputed_leaf = self._compute_leaf_hash(mandate_id, tx_hash, timestamp, audit_anchor)
        if previous_root and leaf_from_proof:
            recomputed_root = self._compute_root(str(previous_root), str(leaf_from_proof))

        checks = {
            "proof_present": isinstance(proof, dict),
            "leaf_matches_payload": bool(leaf_from_proof) and bool(recomputed_leaf) and str(leaf_from_proof) == recomputed_leaf,
            "root_matches_chain_step": bool(recomputed_root) and stored_root == recomputed_root,
            "anchor_present": bool(audit_anchor),
        }

        is_current_root = None
        if current_root is not None:
            is_current_root = stored_root == str(current_root)

        return {
            "valid": all(checks.values()),
            "checks": checks,
            "recomputed_leaf": recomputed_leaf,
            "recomputed_root": recomputed_root,
            "stored_merkle_root": stored_root,
            "is_current_root": is_current_root,
        }

    async def queue_for_reconciliation_async(
        self,
        payment_mandate,
        chain_receipt: ChainReceipt,
        error: str,
    ) -> str:
        """Queue a failed ledger append for reconciliation (async, PostgreSQL)."""
        if not self._use_postgres:
            return self.queue_for_reconciliation(payment_mandate, chain_receipt, error)

        from_wallet_id = getattr(payment_mandate, "wallet_id", None) or payment_mandate.subject
        metadata = {
            "subject": payment_mandate.subject,
            "issuer": payment_mandate.issuer,
            "domain": getattr(payment_mandate, "domain", "sardis.sh"),
            "purpose": getattr(payment_mandate, "purpose", "checkout"),
        }

        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO pending_reconciliation (
                    mandate_id, chain_tx_hash, chain, audit_anchor,
                    from_wallet, to_wallet, amount, currency, error,
                    metadata_json
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
                """,
                payment_mandate.mandate_id,
                chain_receipt.tx_hash,
                chain_receipt.chain,
                chain_receipt.audit_anchor,
                from_wallet_id,
                payment_mandate.destination,
                float(payment_mandate.amount_minor),
                payment_mandate.token,
                error,
                json.dumps(metadata),
            )
        entry_id = str(row["id"])
        logger.warning(
            f"Queued for reconciliation (async): id={entry_id}, "
            f"mandate={payment_mandate.mandate_id}, tx={chain_receipt.tx_hash}"
        )
        return entry_id
    
    async def append_async(self, payment_mandate, chain_receipt: ChainReceipt) -> Transaction:
        """Append a transaction to the ledger (async version for PostgreSQL)."""
        amount = normalize_token_amount(payment_mandate.token, int(payment_mandate.amount_minor))
        from_wallet_id = getattr(payment_mandate, "wallet_id", None) or payment_mandate.subject
        tx = Transaction(
            from_wallet=from_wallet_id,
            to_wallet=payment_mandate.destination,
            amount=amount,
            currency=payment_mandate.token,
            audit_anchor=chain_receipt.audit_anchor,
        )
        tx.add_on_chain_record(
            OnChainRecord(
                chain=chain_receipt.chain,
                tx_hash=chain_receipt.tx_hash,
                from_address=from_wallet_id,
                to_address=payment_mandate.destination,
                block_number=chain_receipt.block_number,
                status="confirmed" if chain_receipt.block_number else "pending",
            )
        )
        
        if hasattr(self, '_use_postgres') and self._use_postgres:
            pool = await self._get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO ledger_entries (
                        tx_id, mandate_id, from_wallet, to_wallet, amount, currency, chain,
                        chain_tx_hash, audit_anchor, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    """,
                    tx.tx_id,
                    payment_mandate.mandate_id,
                    from_wallet_id,
                    payment_mandate.destination,
                    str(amount),
                    payment_mandate.token,
                    chain_receipt.chain,
                    chain_receipt.tx_hash,
                    chain_receipt.audit_anchor,
                )
        elif self._sqlite_conn:
            # Fall back to sync SQLite
            return self.append(payment_mandate, chain_receipt)
        else:
            self._records.append(tx)
        
        return tx

    def list_recent(self, limit: int = 50) -> list[Transaction]:
        """List recent transactions (sync version for SQLite)."""
        if not self._sqlite_conn:
            return self._records[-limit:]
        rows = self._sqlite_conn.execute(
            "SELECT tx_id, from_wallet, to_wallet, amount, currency, chain, chain_tx_hash, audit_anchor, created_at"
            " FROM ledger_entries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return self._rows_to_transactions(rows)
    
    async def list_recent_async(self, limit: int = 50) -> list[Transaction]:
        """List recent transactions (async version for PostgreSQL)."""
        if hasattr(self, '_use_postgres') and self._use_postgres:
            pool = await self._get_pg_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT tx_id, from_wallet, to_wallet, amount, currency, chain, 
                           chain_tx_hash, audit_anchor, created_at
                    FROM ledger_entries 
                    ORDER BY created_at DESC 
                    LIMIT $1
                    """,
                    limit,
                )
                return self._rows_to_transactions(rows, is_asyncpg=True)
        else:
            return self.list_recent(limit)

    def list_entry_records(
        self,
        *,
        wallet_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Dict[str, Any]]:
        """
        List ledger entry records for API responses (sync).

        Returns a stable, JSON-ready representation of ledger rows, including
        mandate_id when available (SQLite / in-memory).

        For PostgreSQL, use `list_entry_records_async`.
        """
        if self._use_postgres:
            raise RuntimeError("PostgreSQL mode requires list_entry_records_async()")

        with self._lock:
            if self._sqlite_conn:
                if wallet_id:
                    rows = self._sqlite_conn.execute(
                        """
                        SELECT tx_id, mandate_id, from_wallet, to_wallet, amount, currency,
                               chain, chain_tx_hash, audit_anchor, created_at
                        FROM ledger_entries
                        WHERE (from_wallet = ? OR to_wallet = ?)
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (wallet_id, wallet_id, limit, offset),
                    ).fetchall()
                else:
                    rows = self._sqlite_conn.execute(
                        """
                        SELECT tx_id, mandate_id, from_wallet, to_wallet, amount, currency,
                               chain, chain_tx_hash, audit_anchor, created_at
                        FROM ledger_entries
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (limit, offset),
                    ).fetchall()

                out: list[Dict[str, Any]] = []
                for row in rows:
                    created_at = row[9]
                    out.append(
                        {
                            "tx_id": row[0],
                            "mandate_id": row[1],
                            "from_wallet": row[2],
                            "to_wallet": row[3],
                            "amount": str(row[4]),
                            "currency": row[5],
                            "chain": row[6],
                            "chain_tx_hash": row[7],
                            "audit_anchor": row[8],
                            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                        }
                    )
                return out

            # In-memory fallback: best-effort pagination
            records: list[Transaction] = self._records
            if wallet_id:
                records = [tx for tx in records if tx.from_wallet == wallet_id or tx.to_wallet == wallet_id]
            sorted_records = sorted(records, key=lambda tx: tx.created_at, reverse=True)
            sliced = sorted_records[offset : offset + limit]
            out: list[Dict[str, Any]] = []
            for tx in sliced:
                chain = tx.on_chain_records[0].chain if tx.on_chain_records else None
                chain_tx_hash = tx.on_chain_records[0].tx_hash if tx.on_chain_records else None
                out.append(
                    {
                        "tx_id": tx.tx_id,
                        "mandate_id": None,
                        "from_wallet": tx.from_wallet or None,
                        "to_wallet": tx.to_wallet or None,
                        "amount": str(tx.amount),
                        "currency": tx.currency,
                        "chain": chain,
                        "chain_tx_hash": chain_tx_hash,
                        "audit_anchor": tx.audit_anchor,
                        "created_at": tx.created_at.isoformat(),
                    }
                )
            return out

    async def list_entry_records_async(
        self,
        *,
        wallet_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Dict[str, Any]]:
        """List ledger entry records for API responses (async; PostgreSQL supported)."""
        if not self._use_postgres:
            return self.list_entry_records(wallet_id=wallet_id, limit=limit, offset=offset)

        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            if wallet_id:
                rows = await conn.fetch(
                    """
                    SELECT tx_id, mandate_id, from_wallet, to_wallet, amount, currency,
                           chain, chain_tx_hash, audit_anchor, created_at
                    FROM ledger_entries
                    WHERE (from_wallet = $1 OR to_wallet = $1)
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    wallet_id,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT tx_id, mandate_id, from_wallet, to_wallet, amount, currency,
                           chain, chain_tx_hash, audit_anchor, created_at
                    FROM ledger_entries
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )

        out: list[Dict[str, Any]] = []
        for row in rows:
            created_at = row["created_at"]
            out.append(
                {
                    "tx_id": str(row["tx_id"]),
                    "mandate_id": row["mandate_id"],
                    "from_wallet": row["from_wallet"],
                    "to_wallet": row["to_wallet"],
                    "amount": str(row["amount"]),
                    "currency": row["currency"],
                    "chain": row["chain"],
                    "chain_tx_hash": row["chain_tx_hash"],
                    "audit_anchor": row["audit_anchor"],
                    "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                }
            )
        return out

    def get_entry_record(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single ledger entry record for API responses (sync).

        For PostgreSQL, use `get_entry_record_async`.
        """
        if self._use_postgres:
            raise RuntimeError("PostgreSQL mode requires get_entry_record_async()")

        with self._lock:
            if self._sqlite_conn:
                row = self._sqlite_conn.execute(
                    """
                    SELECT tx_id, mandate_id, from_wallet, to_wallet, amount, currency,
                           chain, chain_tx_hash, audit_anchor, created_at
                    FROM ledger_entries
                    WHERE tx_id = ?
                    """,
                    (tx_id,),
                ).fetchone()
                if not row:
                    return None
                created_at = row[9]
                return {
                    "tx_id": row[0],
                    "mandate_id": row[1],
                    "from_wallet": row[2],
                    "to_wallet": row[3],
                    "amount": str(row[4]),
                    "currency": row[5],
                    "chain": row[6],
                    "chain_tx_hash": row[7],
                    "audit_anchor": row[8],
                    "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                }

            for tx in self._records:
                if tx.tx_id == tx_id:
                    chain = tx.on_chain_records[0].chain if tx.on_chain_records else None
                    chain_tx_hash = tx.on_chain_records[0].tx_hash if tx.on_chain_records else None
                    return {
                        "tx_id": tx.tx_id,
                        "mandate_id": None,
                        "from_wallet": tx.from_wallet or None,
                        "to_wallet": tx.to_wallet or None,
                        "amount": str(tx.amount),
                        "currency": tx.currency,
                        "chain": chain,
                        "chain_tx_hash": chain_tx_hash,
                        "audit_anchor": tx.audit_anchor,
                        "created_at": tx.created_at.isoformat(),
                    }
            return None

    async def get_entry_record_async(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get a single ledger entry record for API responses (async; PostgreSQL supported)."""
        if not self._use_postgres:
            return self.get_entry_record(tx_id)

        pool = await self._get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tx_id, mandate_id, from_wallet, to_wallet, amount, currency,
                       chain, chain_tx_hash, audit_anchor, created_at
                FROM ledger_entries
                WHERE tx_id = $1
                """,
                tx_id,
            )
        if not row:
            return None
        created_at = row["created_at"]
        return {
            "tx_id": str(row["tx_id"]),
            "mandate_id": row["mandate_id"],
            "from_wallet": row["from_wallet"],
            "to_wallet": row["to_wallet"],
            "amount": str(row["amount"]),
            "currency": row["currency"],
            "chain": row["chain"],
            "chain_tx_hash": row["chain_tx_hash"],
            "audit_anchor": row["audit_anchor"],
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
        }

    def _rows_to_transactions(self, rows, is_asyncpg: bool = False) -> list[Transaction]:
        """Convert database rows to Transaction objects."""
        entries: list[Transaction] = []
        for row in rows:
            if is_asyncpg:
                # asyncpg returns Record objects
                tx = Transaction(
                    tx_id=row['tx_id'],
                    from_wallet=row['from_wallet'],
                    to_wallet=row['to_wallet'],
                    amount=Decimal(str(row['amount'])),
                    currency=row['currency'],
                    audit_anchor=row['audit_anchor'],
                    created_at=row['created_at'],
                )
                tx.add_on_chain_record(
                    OnChainRecord(
                        chain=row['chain'],
                        tx_hash=row['chain_tx_hash'],
                        from_address=row['from_wallet'],
                        to_address=row['to_wallet'],
                        status="confirmed",
                    )
                )
            else:
                # SQLite returns tuples
                tx = Transaction(
                    tx_id=row[0],
                    from_wallet=row[1],
                    to_wallet=row[2],
                    amount=Decimal(row[3]),
                    currency=row[4],
                    audit_anchor=row[7],
                    created_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
                )
                tx.add_on_chain_record(
                    OnChainRecord(
                        chain=row[5],
                        tx_hash=row[6],
                        from_address=row[1],
                        to_address=row[2],
                        status="confirmed",
                    )
                )
            entries.append(tx)
        return entries

    # ============ Reconciliation Queue Methods ============

    def queue_for_reconciliation(
        self,
        payment_mandate,
        chain_receipt: ChainReceipt,
        error: str,
    ) -> str:
        """
        Queue a failed ledger append for later reconciliation.

        This is called when a payment succeeded on-chain but the ledger
        append failed (e.g., database error). The payment is real and
        must eventually be recorded.

        Args:
            payment_mandate: The payment mandate that was executed
            chain_receipt: The chain receipt from successful execution
            error: The error message from the failed append

        Returns:
            The reconciliation entry ID
        """
        import uuid
        entry_id = f"recon_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        if self._sqlite_conn:
            from_wallet_id = getattr(payment_mandate, "wallet_id", None) or payment_mandate.subject
            # Preserve original mandate data for reconciliation
            metadata = {
                "subject": payment_mandate.subject,
                "issuer": payment_mandate.issuer,
                "domain": getattr(payment_mandate, "domain", "sardis.sh"),
                "purpose": getattr(payment_mandate, "purpose", "checkout"),
            }
            self._sqlite_conn.execute(
                """
                INSERT INTO pending_reconciliation (
                    id, mandate_id, chain_tx_hash, chain, audit_anchor,
                    from_wallet, to_wallet, amount, currency, error, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    payment_mandate.mandate_id,
                    chain_receipt.tx_hash,
                    chain_receipt.chain,
                    chain_receipt.audit_anchor,
                    from_wallet_id,
                    payment_mandate.destination,
                    str(payment_mandate.amount_minor),
                    payment_mandate.token,
                    error,
                    now,
                    json.dumps(metadata),
                ),
            )
            self._sqlite_conn.commit()
            logger.warning(
                f"Queued for reconciliation: id={entry_id}, "
                f"mandate={payment_mandate.mandate_id}, tx={chain_receipt.tx_hash}"
            )
        else:
            # In-memory fallback
            if not hasattr(self, '_reconciliation_queue'):
                self._reconciliation_queue = {}
            from_wallet_id = getattr(payment_mandate, "wallet_id", None) or payment_mandate.subject
            # Preserve original mandate data for reconciliation
            metadata = {
                "subject": payment_mandate.subject,
                "issuer": payment_mandate.issuer,
                "domain": getattr(payment_mandate, "domain", "sardis.sh"),
                "purpose": getattr(payment_mandate, "purpose", "checkout"),
            }
            self._reconciliation_queue[entry_id] = PendingReconciliation(
                id=entry_id,
                mandate_id=payment_mandate.mandate_id,
                chain_tx_hash=chain_receipt.tx_hash,
                chain=chain_receipt.chain,
                audit_anchor=chain_receipt.audit_anchor,
                from_wallet=from_wallet_id,
                to_wallet=payment_mandate.destination,
                amount=str(payment_mandate.amount_minor),
                currency=payment_mandate.token,
                error=error,
                metadata=metadata,
            )

        return entry_id

    def get_pending_reconciliation(self, limit: int = 100) -> List[PendingReconciliation]:
        """
        Get pending reconciliation entries ordered by creation time.

        Only returns entries that are not resolved and have not exceeded
        the maximum retry count (5).
        """
        MAX_RETRIES = 5

        if self._sqlite_conn:
            rows = self._sqlite_conn.execute(
                """
                SELECT id, mandate_id, chain_tx_hash, chain, audit_anchor,
                       from_wallet, to_wallet, amount, currency, error,
                       created_at, retry_count, last_retry, resolved, resolved_at, metadata_json
                FROM pending_reconciliation
                WHERE resolved = 0 AND retry_count < ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (MAX_RETRIES, limit),
            ).fetchall()

            return [
                PendingReconciliation(
                    id=row[0],
                    mandate_id=row[1],
                    chain_tx_hash=row[2],
                    chain=row[3],
                    audit_anchor=row[4],
                    from_wallet=row[5],
                    to_wallet=row[6],
                    amount=row[7],
                    currency=row[8],
                    error=row[9],
                    created_at=datetime.fromisoformat(row[10]) if row[10] else datetime.now(timezone.utc),
                    retry_count=row[11] or 0,
                    last_retry=datetime.fromisoformat(row[12]) if row[12] else None,
                    resolved=bool(row[13]),
                    resolved_at=datetime.fromisoformat(row[14]) if row[14] else None,
                    metadata=json.loads(row[15]) if row[15] else {},
                )
                for row in rows
            ]
        else:
            # In-memory fallback
            if not hasattr(self, '_reconciliation_queue'):
                return []
            pending = [
                e for e in self._reconciliation_queue.values()
                if not e.resolved and e.retry_count < MAX_RETRIES
            ]
            return sorted(pending, key=lambda e: e.created_at)[:limit]

    def mark_reconciliation_resolved(self, entry_id: str) -> bool:
        """Mark a reconciliation entry as resolved."""
        now = datetime.now(timezone.utc).isoformat()

        if self._sqlite_conn:
            cursor = self._sqlite_conn.execute(
                """
                UPDATE pending_reconciliation
                SET resolved = 1, resolved_at = ?
                WHERE id = ?
                """,
                (now, entry_id),
            )
            self._sqlite_conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Reconciliation resolved: id={entry_id}")
                return True
            return False
        else:
            if hasattr(self, '_reconciliation_queue') and entry_id in self._reconciliation_queue:
                self._reconciliation_queue[entry_id].resolved = True
                self._reconciliation_queue[entry_id].resolved_at = datetime.now(timezone.utc)
                return True
            return False

    def increment_reconciliation_retry(self, entry_id: str) -> bool:
        """Increment retry count for a reconciliation entry."""
        now = datetime.now(timezone.utc).isoformat()

        if self._sqlite_conn:
            cursor = self._sqlite_conn.execute(
                """
                UPDATE pending_reconciliation
                SET retry_count = retry_count + 1, last_retry = ?
                WHERE id = ?
                """,
                (now, entry_id),
            )
            self._sqlite_conn.commit()
            return cursor.rowcount > 0
        else:
            if hasattr(self, '_reconciliation_queue') and entry_id in self._reconciliation_queue:
                entry = self._reconciliation_queue[entry_id]
                entry.retry_count += 1
                entry.last_retry = datetime.now(timezone.utc)
                return True
            return False

    def count_pending_reconciliation(self) -> int:
        """Count pending reconciliation entries."""
        if self._sqlite_conn:
            row = self._sqlite_conn.execute(
                "SELECT COUNT(*) FROM pending_reconciliation WHERE resolved = 0"
            ).fetchone()
            return row[0] if row else 0
        else:
            if not hasattr(self, '_reconciliation_queue'):
                return 0
            return len([e for e in self._reconciliation_queue.values() if not e.resolved])

    async def run_reconciliation(self, batch_size: int = 10) -> int:
        """
        Background job to reconcile failed ledger appends.

        This should be called periodically (e.g., every minute) to retry
        failed appends.

        Returns:
            Number of successfully reconciled entries
        """
        pending = self.get_pending_reconciliation(batch_size)
        reconciled = 0

        for entry in pending:
            try:
                # Reconstruct minimal mandate and receipt for append
                import time
                from sardis_v2_core.mandates import PaymentMandate, VCProof

                now = int(time.time())
                proof = VCProof(
                    verification_method="sardis:reconciliation#key-1",
                    created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    proof_value="reconciliation",
                )

                # Restore original mandate data from metadata
                subject = entry.metadata.get("subject", "agent:unknown") if entry.metadata else "agent:unknown"
                issuer = entry.metadata.get("issuer", f"wallet:{entry.from_wallet}") if entry.metadata else f"wallet:{entry.from_wallet}"
                domain = entry.metadata.get("domain", "sardis.sh") if entry.metadata else "sardis.sh"
                purpose = entry.metadata.get("purpose", "checkout") if entry.metadata else "checkout"

                mandate = PaymentMandate(
                    mandate_id=entry.mandate_id,
                    mandate_type="payment",
                    issuer=issuer,
                    subject=subject,
                    expires_at=now + 300,
                    nonce=f"recon:{entry.mandate_id}",
                    proof=proof,
                    domain=domain,
                    purpose=purpose,
                    chain=entry.chain,
                    token=entry.currency,
                    amount_minor=int(entry.amount),
                    destination=entry.to_wallet,
                    audit_hash=hashlib.sha256(
                        f"recon:{entry.mandate_id}:{entry.chain_tx_hash}:{entry.audit_anchor}".encode()
                    ).hexdigest(),
                    wallet_id=entry.from_wallet,
                )

                receipt = ChainReceipt(
                    tx_hash=entry.chain_tx_hash,
                    chain=entry.chain,
                    block_number=0,  # Unknown at reconciliation time
                    audit_anchor=entry.audit_anchor,
                )

                # Attempt append
                self.append(mandate, receipt)
                self.mark_reconciliation_resolved(entry.id)
                reconciled += 1
                logger.info(f"Reconciled entry: id={entry.id}, mandate={entry.mandate_id}")

            except Exception as e:
                self.increment_reconciliation_retry(entry.id)
                logger.warning(
                    f"Reconciliation retry failed: id={entry.id}, "
                    f"retry={entry.retry_count + 1}, error={e}"
                )

        return reconciled

    # ============ Row-Level Locking Methods ============

    def acquire_lock(
        self,
        resource_type: str,
        resource_id: str,
        holder_id: str,
        timeout_seconds: float = 30.0,
        expiry_seconds: float = 300.0,
    ) -> Optional[LockRecord]:
        """
        Acquire a row-level lock on a resource.

        This uses database-level locking for safety in concurrent environments.

        Args:
            resource_type: Type of resource (e.g., "account", "entry")
            resource_id: Unique identifier of the resource
            holder_id: ID of the transaction/process acquiring the lock
            timeout_seconds: Maximum time to wait for lock
            expiry_seconds: How long the lock is valid

        Returns:
            LockRecord if acquired, None if failed

        Note:
            For SQLite, this uses a simple table-based lock.
            For PostgreSQL, this uses SELECT FOR UPDATE.
        """
        import time

        start_time = time.monotonic()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expiry_seconds)

        while True:
            with self._lock:
                if self._sqlite_conn:
                    # Clean up expired locks first
                    self._sqlite_conn.execute(
                        "DELETE FROM row_locks WHERE expires_at < ?",
                        (now.isoformat(),)
                    )

                    # Try to acquire
                    try:
                        lock_id = f"lock_{uuid.uuid4().hex[:12]}"
                        self._sqlite_conn.execute(
                            """
                            INSERT INTO row_locks (
                                lock_id, resource_type, resource_id, holder_id,
                                acquired_at, expires_at, is_exclusive
                            ) VALUES (?, ?, ?, ?, ?, ?, 1)
                            """,
                            (
                                lock_id,
                                resource_type,
                                resource_id,
                                holder_id,
                                now.isoformat(),
                                expires_at.isoformat(),
                            ),
                        )
                        self._sqlite_conn.commit()

                        lock = LockRecord(
                            lock_id=lock_id,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            holder_id=holder_id,
                            acquired_at=now,
                            expires_at=expires_at,
                            is_exclusive=True,
                        )

                        logger.debug(f"Lock acquired: {resource_type}:{resource_id} by {holder_id}")
                        return lock

                    except sqlite3.IntegrityError:
                        # Lock already held
                        self._sqlite_conn.rollback()

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout_seconds:
                logger.warning(
                    f"Lock acquisition timed out: {resource_type}:{resource_id} "
                    f"after {timeout_seconds}s"
                )
                return None

            # Wait and retry
            time.sleep(min(0.1, timeout_seconds - elapsed))

    def release_lock(self, resource_type: str, resource_id: str, holder_id: str) -> bool:
        """
        Release a row-level lock.

        Args:
            resource_type: Type of resource
            resource_id: Unique identifier of the resource
            holder_id: ID of the holder releasing the lock

        Returns:
            True if lock was released, False if not found or not owned
        """
        with self._lock:
            if self._sqlite_conn:
                cursor = self._sqlite_conn.execute(
                    """
                    DELETE FROM row_locks
                    WHERE resource_type = ? AND resource_id = ? AND holder_id = ?
                    """,
                    (resource_type, resource_id, holder_id),
                )
                self._sqlite_conn.commit()

                if cursor.rowcount > 0:
                    logger.debug(f"Lock released: {resource_type}:{resource_id} by {holder_id}")
                    return True

                return False

        return False

    def is_locked(self, resource_type: str, resource_id: str) -> bool:
        """Check if a resource is currently locked."""
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            if self._sqlite_conn:
                row = self._sqlite_conn.execute(
                    """
                    SELECT 1 FROM row_locks
                    WHERE resource_type = ? AND resource_id = ?
                    AND (expires_at IS NULL OR expires_at > ?)
                    """,
                    (resource_type, resource_id, now),
                ).fetchone()
                return row is not None

        return False

    @contextmanager
    def lock_resource(
        self,
        resource_type: str,
        resource_id: str,
        holder_id: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> Generator[Optional[LockRecord], None, None]:
        """
        Context manager for acquiring and releasing locks.

        Usage:
            with ledger.lock_resource("account", account_id) as lock:
                if lock:
                    # Do work while holding lock
                    pass
            # Lock automatically released
        """
        holder = holder_id or f"holder_{uuid.uuid4().hex[:12]}"
        lock = self.acquire_lock(resource_type, resource_id, holder, timeout_seconds)

        try:
            yield lock
        finally:
            if lock:
                self.release_lock(resource_type, resource_id, holder)

    # ============ Batch Processing Methods ============

    def append_batch(
        self,
        entries: Sequence[Tuple[Any, ChainReceipt]],
        actor_id: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Append multiple transactions atomically.

        All entries succeed or all fail (all-or-nothing semantics).

        Args:
            entries: List of (payment_mandate, chain_receipt) tuples
            actor_id: ID of actor performing the operation

        Returns:
            List of created Transaction objects

        Raises:
            Exception: If any entry fails (all are rolled back)
        """
        if not entries:
            return []

        transactions: List[Transaction] = []

        with self._lock:
            if self._sqlite_conn:
                try:
                    # Begin transaction
                    self._sqlite_conn.execute("BEGIN IMMEDIATE")

                    for payment_mandate, chain_receipt in entries:
                        amount = normalize_token_amount(payment_mandate.token, int(payment_mandate.amount_minor))
                        amount = to_ledger_decimal(amount)
                        from_wallet_id = getattr(payment_mandate, "wallet_id", None) or payment_mandate.subject

                        tx = Transaction(
                            from_wallet=from_wallet_id,
                            to_wallet=payment_mandate.destination,
                            amount=amount,
                            currency=payment_mandate.token,
                            audit_anchor=chain_receipt.audit_anchor,
                        )
                        tx.add_on_chain_record(
                            OnChainRecord(
                                chain=chain_receipt.chain,
                                tx_hash=chain_receipt.tx_hash,
                                from_address=from_wallet_id,
                                to_address=payment_mandate.destination,
                                block_number=chain_receipt.block_number,
                                status="confirmed" if chain_receipt.block_number else "pending",
                            )
                        )

                        self._sqlite_conn.execute(
                            """
                            INSERT INTO ledger_entries (
                                tx_id, entry_id, mandate_id, from_wallet, to_wallet,
                                amount, fee, currency, entry_type, chain, chain_tx_hash,
                                block_number, audit_anchor, status, created_at, confirmed_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                tx.tx_id,
                                f"le_{uuid.uuid4().hex[:20]}",
                                payment_mandate.mandate_id,
                                from_wallet_id,
                                payment_mandate.destination,
                                str(amount),
                                "0",
                                payment_mandate.token,
                                "transfer",
                                chain_receipt.chain,
                                chain_receipt.tx_hash,
                                chain_receipt.block_number,
                                chain_receipt.audit_anchor,
                                "confirmed",
                                tx.created_at.isoformat(),
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )
                        transactions.append(tx)

                    self._sqlite_conn.commit()
                    logger.info(f"Batch append completed: {len(transactions)} entries")

                except Exception as e:
                    self._sqlite_conn.rollback()
                    logger.error(f"Batch append failed, rolling back: {e}")
                    raise

            else:
                # In-memory fallback
                self._records.extend(transactions)

        return transactions

    # ============ Balance Snapshot Methods ============

    def create_balance_snapshot(
        self,
        account_id: str,
        currency: str = "USDC",
    ) -> Optional[BalanceSnapshot]:
        """
        Create a balance snapshot for an account.

        Snapshots enable efficient point-in-time balance queries.

        Args:
            account_id: The account to snapshot
            currency: Currency to snapshot

        Returns:
            Created BalanceSnapshot or None if no entries
        """
        with self._lock:
            if self._sqlite_conn:
                # Calculate current balance
                row = self._sqlite_conn.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE
                            WHEN to_wallet = ? THEN CAST(amount AS NUMERIC)
                            WHEN from_wallet = ? THEN -CAST(amount AS NUMERIC)
                            ELSE 0
                        END), 0) as balance,
                        COUNT(*) as entry_count,
                        MAX(tx_id) as last_entry_id,
                        MAX(created_at) as last_entry_created_at
                    FROM ledger_entries
                    WHERE (from_wallet = ? OR to_wallet = ?)
                    AND currency = ?
                    AND status = 'confirmed'
                    """,
                    (account_id, account_id, account_id, account_id, currency),
                ).fetchone()

                if not row or row[1] == 0:
                    return None

                balance = to_ledger_decimal(row[0])
                snapshot = BalanceSnapshot(
                    account_id=account_id,
                    currency=currency,
                    balance=balance,
                    last_entry_id=row[2] or "",
                    last_entry_created_at=(
                        datetime.fromisoformat(row[3]) if row[3] else None
                    ),
                    entry_count=row[1],
                )

                self._sqlite_conn.execute(
                    """
                    INSERT INTO balance_snapshots (
                        snapshot_id, account_id, currency, balance,
                        last_entry_id, last_entry_created_at, entry_count, snapshot_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.snapshot_id,
                        account_id,
                        currency,
                        str(balance),
                        snapshot.last_entry_id,
                        snapshot.last_entry_created_at.isoformat() if snapshot.last_entry_created_at else None,
                        snapshot.entry_count,
                        snapshot.snapshot_at.isoformat(),
                    ),
                )
                self._sqlite_conn.commit()

                logger.info(
                    f"Created balance snapshot: {snapshot.snapshot_id} "
                    f"for {account_id}, balance={balance}"
                )
                return snapshot

        return None

    def get_balance_at(
        self,
        account_id: str,
        at_time: datetime,
        currency: str = "USDC",
    ) -> Decimal:
        """
        Get account balance at a specific point in time.

        Uses snapshots for efficiency when available.

        Args:
            account_id: Account to query
            at_time: Point in time to query
            currency: Currency to query

        Returns:
            Balance at the specified time
        """
        with self._lock:
            if self._sqlite_conn:
                # Find nearest snapshot before at_time
                snapshot_row = self._sqlite_conn.execute(
                    """
                    SELECT balance, snapshot_at
                    FROM balance_snapshots
                    WHERE account_id = ? AND currency = ?
                    AND snapshot_at <= ?
                    ORDER BY snapshot_at DESC
                    LIMIT 1
                    """,
                    (account_id, currency, at_time.isoformat()),
                ).fetchone()

                if snapshot_row:
                    base_balance = Decimal(snapshot_row[0])
                    start_time = snapshot_row[1]
                else:
                    base_balance = Decimal("0")
                    start_time = datetime.min.replace(tzinfo=timezone.utc).isoformat()

                # Add entries between snapshot and at_time
                delta_row = self._sqlite_conn.execute(
                    """
                    SELECT COALESCE(SUM(CASE
                        WHEN to_wallet = ? THEN CAST(amount AS NUMERIC)
                        WHEN from_wallet = ? THEN -CAST(amount AS NUMERIC)
                        ELSE 0
                    END), 0)
                    FROM ledger_entries
                    WHERE (from_wallet = ? OR to_wallet = ?)
                    AND currency = ?
                    AND status = 'confirmed'
                    AND created_at > ? AND created_at <= ?
                    """,
                    (
                        account_id, account_id,
                        account_id, account_id,
                        currency,
                        start_time, at_time.isoformat(),
                    ),
                ).fetchone()

                delta = Decimal(str(delta_row[0])) if delta_row else Decimal("0")
                return to_ledger_decimal(base_balance + delta)

        return Decimal("0")

    # ============ Audit Trail Methods ============

    def add_audit_log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[str] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Add an audit log entry.

        Audit logs are hash-chained for tamper evidence.

        Args:
            action: The action performed
            entity_type: Type of entity affected
            entity_id: ID of entity affected
            actor_id: Who performed the action
            old_value: Previous state (for updates)
            new_value: New state
            request_id: Request ID for tracing

        Returns:
            Created AuditLog entry
        """
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

        with self._lock:
            if self._sqlite_conn:
                self._sqlite_conn.execute(
                    """
                    INSERT INTO audit_logs (
                        audit_id, action, entity_type, entity_id, actor_id,
                        old_value_json, new_value_json, request_id, created_at,
                        previous_hash, entry_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        log.audit_id,
                        action.value,
                        entity_type,
                        entity_id,
                        actor_id,
                        json.dumps(old_value) if old_value else None,
                        json.dumps(new_value) if new_value else None,
                        request_id,
                        log.created_at.isoformat(),
                        log.previous_hash,
                        log.entry_hash,
                    ),
                )
                self._sqlite_conn.commit()

            self._audit_logs.append(log)

        logger.debug(f"Audit log: {action.value} {entity_type}:{entity_id}")
        return log

    def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get audit logs with filtering.

        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            from_time: Filter entries after this time
            to_time: Filter entries before this time
            limit: Maximum entries to return

        Returns:
            List of AuditLog entries
        """
        with self._lock:
            if self._sqlite_conn:
                query = """
                    SELECT audit_id, action, entity_type, entity_id, actor_id,
                           actor_type, old_value_json, new_value_json, request_id,
                           created_at, previous_hash, entry_hash
                    FROM audit_logs WHERE 1=1
                """
                params: List[Any] = []

                if entity_type:
                    query += " AND entity_type = ?"
                    params.append(entity_type)
                if entity_id:
                    query += " AND entity_id = ?"
                    params.append(entity_id)
                if from_time:
                    query += " AND created_at >= ?"
                    params.append(from_time.isoformat())
                if to_time:
                    query += " AND created_at <= ?"
                    params.append(to_time.isoformat())

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                rows = self._sqlite_conn.execute(query, params).fetchall()

                return [
                    AuditLog(
                        audit_id=row[0],
                        action=AuditAction(row[1]),
                        entity_type=row[2],
                        entity_id=row[3],
                        actor_id=row[4],
                        actor_type=row[5],
                        old_value=json.loads(row[6]) if row[6] else None,
                        new_value=json.loads(row[7]) if row[7] else None,
                        request_id=row[8],
                        created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(timezone.utc),
                        previous_hash=row[10],
                        entry_hash=row[11],
                    )
                    for row in rows
                ]

        return []

    # ============ Enhanced Query Methods ============

    def get_entry_by_chain_tx(self, chain: str, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get a ledger entry by its chain transaction hash."""
        with self._lock:
            if self._sqlite_conn:
                row = self._sqlite_conn.execute(
                    """
                    SELECT tx_id, entry_id, mandate_id, from_wallet, to_wallet,
                           amount, fee, currency, entry_type, chain, chain_tx_hash,
                           block_number, audit_anchor, status, created_at
                    FROM ledger_entries
                    WHERE chain = ? AND chain_tx_hash = ?
                    """,
                    (chain, tx_hash),
                ).fetchone()

                if row:
                    return {
                        "tx_id": row[0],
                        "entry_id": row[1],
                        "mandate_id": row[2],
                        "from_wallet": row[3],
                        "to_wallet": row[4],
                        "amount": row[5],
                        "fee": row[6],
                        "currency": row[7],
                        "entry_type": row[8],
                        "chain": row[9],
                        "chain_tx_hash": row[10],
                        "block_number": row[11],
                        "audit_anchor": row[12],
                        "status": row[13],
                        "created_at": row[14],
                    }

        return None

    def get_entries_for_reconciliation(
        self,
        chain: Optional[str] = None,
        from_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get entries that need reconciliation with blockchain.

        Returns entries with chain references that can be verified.
        """
        with self._lock:
            if self._sqlite_conn:
                query = """
                    SELECT tx_id, entry_id, from_wallet, to_wallet, amount,
                           currency, chain, chain_tx_hash, block_number,
                           audit_anchor, status, created_at
                    FROM ledger_entries
                    WHERE chain_tx_hash IS NOT NULL
                    AND status = 'confirmed'
                """
                params: List[Any] = []

                if chain:
                    query += " AND chain = ?"
                    params.append(chain)
                if from_time:
                    query += " AND created_at >= ?"
                    params.append(from_time.isoformat())

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                rows = self._sqlite_conn.execute(query, params).fetchall()

                return [
                    {
                        "tx_id": row[0],
                        "entry_id": row[1],
                        "from_wallet": row[2],
                        "to_wallet": row[3],
                        "amount": row[4],
                        "currency": row[5],
                        "chain": row[6],
                        "chain_tx_hash": row[7],
                        "block_number": row[8],
                        "audit_anchor": row[9],
                        "status": row[10],
                        "created_at": row[11],
                    }
                    for row in rows
                ]

        return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get ledger statistics."""
        with self._lock:
            if self._sqlite_conn:
                stats = {}

                # Entry counts
                row = self._sqlite_conn.execute(
                    "SELECT COUNT(*), COUNT(DISTINCT from_wallet), COUNT(DISTINCT to_wallet) FROM ledger_entries"
                ).fetchone()
                stats["total_entries"] = row[0]
                stats["unique_senders"] = row[1]
                stats["unique_recipients"] = row[2]

                # Volume by currency
                rows = self._sqlite_conn.execute(
                    """
                    SELECT currency, SUM(CAST(amount AS NUMERIC)), COUNT(*)
                    FROM ledger_entries
                    WHERE status = 'confirmed'
                    GROUP BY currency
                    """
                ).fetchall()
                stats["volume_by_currency"] = {
                    row[0]: {"total": row[1], "count": row[2]}
                    for row in rows
                }

                # Reconciliation stats
                row = self._sqlite_conn.execute(
                    "SELECT COUNT(*) FROM pending_reconciliation WHERE resolved = 0"
                ).fetchone()
                stats["pending_reconciliation"] = row[0]

                # Snapshot count
                row = self._sqlite_conn.execute(
                    "SELECT COUNT(*) FROM balance_snapshots"
                ).fetchone()
                stats["snapshot_count"] = row[0]

                return stats

        return {}
