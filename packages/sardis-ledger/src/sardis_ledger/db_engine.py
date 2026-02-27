"""PostgreSQL-backed ledger engine.

Replaces the in-memory dicts in ``LedgerEngine`` with queries against
``ledger_entries_v2``, ``balance_snapshots``, ``ledger_batches``,
and ``ledger_audit_log`` tables.

Uses PostgreSQL advisory locks instead of ``threading.RLock``.

Pattern follows ``policy_store_postgres.py`` and ``db_balance.py``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .models import (
    AuditAction,
    AuditLog,
    BalanceSnapshot,
    BatchTransaction,
    LedgerEntry,
    LedgerEntryStatus,
    LedgerEntryType,
    to_ledger_decimal,
    validate_amount,
)
from .engine import (
    BatchProcessingError,
    InsufficientBalanceError,
    LedgerError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _advisory_lock_key(account_id: str) -> int:
    """Deterministic 63-bit hash for pg_advisory_lock."""
    h = hashlib.sha256(account_id.encode()).digest()
    return int.from_bytes(h[:8], "big") & 0x7FFFFFFFFFFFFFFF


class PostgresLedgerEngine:
    """
    Production ledger engine backed by PostgreSQL.

    Uses ``ledger_entries`` and ``audit_log`` tables from the existing
    schema.  Row-level concurrency is handled via PostgreSQL advisory
    locks instead of in-process threading locks.
    """

    def __init__(self, dsn: str, enable_audit: bool = True) -> None:
        self._dsn = dsn
        self.enable_audit = enable_audit
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    # ------------------------------------------------------------------
    # Advisory locking
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def _advisory_lock(self, conn, account_id: str):
        """Acquire and release a PostgreSQL advisory lock."""
        key = _advisory_lock_key(account_id)
        await conn.execute("SELECT pg_advisory_lock($1)", key)
        try:
            yield
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", key)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def _generate_tx_id(self) -> str:
        return f"tx_{uuid.uuid4().hex[:20]}"

    async def get_balance(
        self,
        account_id: str,
        currency: str = "USDC",
        at_time: Optional[datetime] = None,
    ) -> Decimal:
        """Get account balance by aggregating ledger entries."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if at_time is None:
                row = await conn.fetchrow(
                    """
                    SELECT
                        COALESCE(SUM(
                            CASE WHEN entry_type IN ('credit', 'refund') THEN amount
                                 WHEN entry_type IN ('debit', 'fee') THEN -amount
                                 ELSE 0
                            END
                        ), 0) AS balance
                    FROM ledger_entries_v2
                    WHERE account_id = $1 AND currency = $2
                      AND status = 'confirmed'
                    """,
                    account_id,
                    currency,
                )
            else:
                row = await conn.fetchrow(
                    """
                    SELECT
                        COALESCE(SUM(
                            CASE WHEN entry_type IN ('credit', 'refund') THEN amount
                                 WHEN entry_type IN ('debit', 'fee') THEN -amount
                                 ELSE 0
                            END
                        ), 0) AS balance
                    FROM ledger_entries_v2
                    WHERE account_id = $1 AND currency = $2
                      AND status = 'confirmed'
                      AND created_at <= $3
                    """,
                    account_id,
                    currency,
                    at_time,
                )
            return to_ledger_decimal(row["balance"]) if row else Decimal("0")

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
        audit_anchor: Optional[str] = None,
        fee: Decimal = Decimal("0"),
        metadata: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> LedgerEntry:
        """Create a ledger entry with advisory lock concurrency."""
        amount = to_ledger_decimal(amount)
        fee = to_ledger_decimal(fee)
        validate_amount(amount, allow_zero=False)

        if not account_id:
            raise ValidationError("account_id", account_id, "Account ID is required")

        entry_id = f"le_{uuid.uuid4().hex[:20]}"
        final_tx_id = tx_id or self._generate_tx_id()
        now = datetime.now(timezone.utc)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                async with self._advisory_lock(conn, account_id):
                    # Balance check for debits
                    if entry_type in (LedgerEntryType.DEBIT, LedgerEntryType.FEE):
                        current = await self._get_balance_in_tx(conn, account_id, currency)
                        required = amount + fee
                        if current < required:
                            raise InsufficientBalanceError(account_id, required, current)

                    # Calculate running balance
                    current = await self._get_balance_in_tx(conn, account_id, currency)
                    if entry_type in (LedgerEntryType.CREDIT, LedgerEntryType.REFUND):
                        running = current + amount
                    elif entry_type in (LedgerEntryType.DEBIT, LedgerEntryType.FEE):
                        running = current - amount - fee
                    else:
                        running = current

                    # Insert
                    await conn.execute(
                        """
                        INSERT INTO ledger_entries_v2
                            (entry_id, tx_id, account_id, entry_type, amount, fee,
                             running_balance, currency, chain, chain_tx_hash,
                             block_number, audit_anchor, status, confirmed_at,
                             metadata, created_at)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                        """,
                        entry_id,
                        final_tx_id,
                        account_id,
                        entry_type.value,
                        float(amount),
                        float(fee),
                        float(running),
                        currency,
                        chain,
                        chain_tx_hash,
                        block_number,
                        audit_anchor,
                        LedgerEntryStatus.CONFIRMED.value,
                        now,
                        json.dumps(metadata or {}),
                        now,
                    )

                    # Audit log
                    if self.enable_audit:
                        await self._add_audit_log(
                            conn,
                            action=AuditAction.CREATE,
                            entity_type="ledger_entry",
                            entity_id=entry_id,
                            actor_id=actor_id,
                        )

        entry = LedgerEntry(
            entry_id=entry_id,
            tx_id=final_tx_id,
            account_id=account_id,
            entry_type=entry_type,
            amount=amount,
            fee=fee,
            running_balance=running,
            currency=currency,
            chain=chain,
            chain_tx_hash=chain_tx_hash,
            block_number=block_number,
            audit_anchor=audit_anchor,
            status=LedgerEntryStatus.CONFIRMED,
            confirmed_at=now,
            created_at=now,
            metadata=metadata or {},
        )

        logger.info(
            "Created ledger entry (DB): %s, account=%s, type=%s, amount=%s, balance=%s",
            entry_id,
            account_id,
            entry_type.value,
            amount,
            running,
        )
        return entry

    async def _get_balance_in_tx(
        self, conn, account_id: str, currency: str
    ) -> Decimal:
        """Get balance within an existing transaction/connection."""
        row = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(
                CASE WHEN entry_type IN ('credit', 'refund') THEN amount
                     WHEN entry_type IN ('debit', 'fee') THEN -amount
                     ELSE 0
                END
            ), 0) AS balance
            FROM ledger_entries_v2
            WHERE account_id = $1 AND currency = $2 AND status = 'confirmed'
            """,
            account_id,
            currency,
        )
        return to_ledger_decimal(row["balance"]) if row else Decimal("0")

    async def get_entry(self, entry_id: str) -> Optional[LedgerEntry]:
        """Get a ledger entry by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ledger_entries_v2 WHERE entry_id = $1",
                entry_id,
            )
            if not row:
                return None
            return self._row_to_entry(row)

    async def get_entries(
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
        """Get ledger entries with filtering."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = "SELECT * FROM ledger_entries_v2 WHERE account_id = $1"
            params: list = [account_id]
            idx = 2

            if currency:
                query += f" AND currency = ${idx}"
                params.append(currency)
                idx += 1
            if entry_type:
                query += f" AND entry_type = ${idx}"
                params.append(entry_type.value)
                idx += 1
            if status:
                query += f" AND status = ${idx}"
                params.append(status.value)
                idx += 1
            if from_time:
                query += f" AND created_at >= ${idx}"
                params.append(from_time)
                idx += 1
            if to_time:
                query += f" AND created_at <= ${idx}"
                params.append(to_time)
                idx += 1

            query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
            params.extend([limit, offset])

            rows = await conn.fetch(query, *params)
            return [self._row_to_entry(r) for r in rows]

    async def rollback_entry(
        self,
        entry_id: str,
        reason: str,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> LedgerEntry:
        """Rollback a ledger entry by creating a reversal."""
        original = await self.get_entry(entry_id)
        if not original:
            raise LedgerError(f"Entry not found: {entry_id}", code="ENTRY_NOT_FOUND")
        if original.status == LedgerEntryStatus.REVERSED:
            raise LedgerError(f"Already reversed: {entry_id}", code="ALREADY_REVERSED")

        # Create reversal entry
        reversal = await self.create_entry(
            account_id=original.account_id,
            amount=original.amount,
            entry_type=LedgerEntryType.REVERSAL,
            currency=original.currency,
            tx_id=f"rev_{original.tx_id}",
            chain=original.chain,
            audit_anchor=original.audit_anchor,
            metadata={
                "original_entry_id": original.entry_id,
                "reversal_reason": reason,
                "original_type": original.entry_type.value,
            },
            actor_id=actor_id,
            request_id=request_id,
        )

        # Mark original as reversed
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE ledger_entries_v2 SET status = $2 WHERE entry_id = $1",
                entry_id,
                LedgerEntryStatus.REVERSED.value,
            )

        return reversal

    async def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        actor_id: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs from DB."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = "SELECT * FROM ledger_audit_log WHERE 1=1"
            params: list = []
            idx = 1

            if entity_type:
                query += f" AND entity_type = ${idx}"
                params.append(entity_type)
                idx += 1
            if entity_id:
                query += f" AND entity_id = ${idx}"
                params.append(entity_id)
                idx += 1
            if action:
                query += f" AND action = ${idx}"
                params.append(action.value)
                idx += 1
            if actor_id:
                query += f" AND actor_id = ${idx}"
                params.append(actor_id)
                idx += 1
            if from_time:
                query += f" AND created_at >= ${idx}"
                params.append(from_time)
                idx += 1
            if to_time:
                query += f" AND created_at <= ${idx}"
                params.append(to_time)
                idx += 1

            query += f" ORDER BY created_at DESC LIMIT ${idx}"
            params.append(limit)

            rows = await conn.fetch(query, *params)
            return [
                AuditLog(
                    audit_id=r["audit_id"],
                    action=AuditAction(r["action"]),
                    entity_type=r["entity_type"],
                    entity_id=r["entity_id"],
                    actor_id=r["actor_id"],
                    actor_type=r.get("actor_type"),
                    old_value=json.loads(r["old_value"]) if r["old_value"] else None,
                    new_value=json.loads(r["new_value"]) if r["new_value"] else None,
                    request_id=r.get("request_id"),
                    previous_hash=r["previous_hash"],
                    entry_hash=r["entry_hash"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    async def create_batch(
        self,
        entries: Sequence[Dict[str, Any]],
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> BatchTransaction:
        """Create and process a batch of entries atomically."""
        batch_id = f"batch_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Acquire advisory locks on all accounts in sorted order
                accounts = sorted({spec["account_id"] for spec in entries})
                for acct in accounts:
                    key = _advisory_lock_key(acct)
                    await conn.execute("SELECT pg_advisory_xact_lock($1)", key)

                await conn.execute(
                    "INSERT INTO ledger_batches (batch_id, status, created_at) VALUES ($1, $2, $3)",
                    batch_id,
                    LedgerEntryStatus.PENDING.value,
                    now,
                )

                created: List[LedgerEntry] = []
                for i, spec in enumerate(entries):
                    entry_type = spec.get("entry_type")
                    if isinstance(entry_type, str):
                        entry_type = LedgerEntryType(entry_type)

                    entry = await self.create_entry(
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
                    )
                    created.append(entry)

                    await conn.execute(
                        "INSERT INTO ledger_batch_entries (batch_id, entry_id, entry_index) VALUES ($1, $2, $3)",
                        batch_id,
                        entry.entry_id,
                        i,
                    )

                completed_at = datetime.now(timezone.utc)
                await conn.execute(
                    "UPDATE ledger_batches SET status = $1, completed_at = $2 WHERE batch_id = $3",
                    LedgerEntryStatus.CONFIRMED.value,
                    completed_at,
                    batch_id,
                )

                if self.enable_audit:
                    await self._add_audit_log(
                        conn,
                        action=AuditAction.CREATE,
                        entity_type="batch",
                        entity_id=batch_id,
                        actor_id=actor_id,
                    )

        batch = BatchTransaction(
            batch_id=batch_id,
            entries=created,
            status=LedgerEntryStatus.CONFIRMED,
            created_at=now,
            completed_at=completed_at,
        )
        logger.info("Batch completed (DB): %s, entries=%d", batch_id, len(created))
        return batch

    async def rollback_batch(
        self,
        batch_id: str,
        reason: str,
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> BatchTransaction:
        """Rollback an entire batch."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ledger_batches WHERE batch_id = $1", batch_id
            )
            if not row:
                raise LedgerError(f"Batch not found: {batch_id}", code="BATCH_NOT_FOUND")
            if row["is_rolled_back"]:
                raise LedgerError(f"Batch already rolled back: {batch_id}", code="ALREADY_ROLLED_BACK")

            entry_rows = await conn.fetch(
                """
                SELECT e.* FROM ledger_entries_v2 e
                JOIN ledger_batch_entries be ON e.entry_id = be.entry_id
                WHERE be.batch_id = $1
                ORDER BY be.entry_index DESC
                """,
                batch_id,
            )
            entries = [self._row_to_entry(r) for r in entry_rows]

            for entry in entries:
                if entry.status != LedgerEntryStatus.REVERSED:
                    await self.rollback_entry(
                        entry.entry_id,
                        f"Batch rollback: {reason}",
                        actor_id,
                        request_id,
                    )

            now = datetime.now(timezone.utc)
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE ledger_batches
                    SET is_rolled_back = TRUE, rollback_reason = $1, rollback_at = $2
                    WHERE batch_id = $3
                    """,
                    reason,
                    now,
                    batch_id,
                )
                if self.enable_audit:
                    await self._add_audit_log(
                        conn,
                        action=AuditAction.ROLLBACK,
                        entity_type="batch",
                        entity_id=batch_id,
                        actor_id=actor_id,
                    )

        batch = BatchTransaction(
            batch_id=batch_id,
            entries=entries,
            status=LedgerEntryStatus(row["status"]),
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            is_rolled_back=True,
            rollback_reason=reason,
            rollback_at=now,
        )
        logger.info("Rolled back batch (DB): %s, entries=%d", batch_id, len(entries))
        return batch

    async def get_batch(self, batch_id: str) -> Optional[BatchTransaction]:
        """Get a batch by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ledger_batches WHERE batch_id = $1", batch_id
            )
            if not row:
                return None
            entry_rows = await conn.fetch(
                """
                SELECT e.* FROM ledger_entries_v2 e
                JOIN ledger_batch_entries be ON e.entry_id = be.entry_id
                WHERE be.batch_id = $1
                ORDER BY be.entry_index ASC
                """,
                batch_id,
            )
            return BatchTransaction(
                batch_id=batch_id,
                entries=[self._row_to_entry(r) for r in entry_rows],
                status=LedgerEntryStatus(row["status"]),
                created_at=row["created_at"],
                completed_at=row["completed_at"],
                is_rolled_back=row["is_rolled_back"],
                rollback_reason=row["rollback_reason"],
                rollback_at=row["rollback_at"],
            )

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    async def get_snapshots(
        self,
        account_id: str,
        currency: str = "USDC",
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> List[BalanceSnapshot]:
        """Get balance snapshots for an account."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = "SELECT * FROM balance_snapshots WHERE account_id = $1 AND currency = $2"
            params: list = [account_id, currency]
            idx = 3
            if from_time:
                query += f" AND snapshot_at >= ${idx}"
                params.append(from_time)
                idx += 1
            if to_time:
                query += f" AND snapshot_at <= ${idx}"
                params.append(to_time)
                idx += 1
            query += " ORDER BY snapshot_at ASC"
            rows = await conn.fetch(query, *params)
            return [
                BalanceSnapshot(
                    snapshot_id=r["snapshot_id"],
                    account_id=r["account_id"],
                    currency=r["currency"],
                    balance=to_ledger_decimal(r["balance"]),
                    last_entry_id=r["last_entry_id"] or "",
                    last_entry_created_at=r["last_entry_created_at"],
                    entry_count=r["entry_count"],
                    snapshot_at=r["snapshot_at"],
                    merkle_root=r.get("merkle_root"),
                )
                for r in rows
            ]

    # ------------------------------------------------------------------
    # Audit chain verification
    # ------------------------------------------------------------------

    async def verify_audit_chain(self) -> Tuple[bool, Optional[str]]:
        """Verify integrity of audit log hash chain."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM ledger_audit_log ORDER BY created_at ASC"
            )
            if not rows:
                return True, None

            for i, row in enumerate(rows):
                expected_prev = rows[i - 1]["entry_hash"] if i > 0 else None
                if row["previous_hash"] != expected_prev:
                    return False, f"Hash chain broken at audit log {row['audit_id']}"

                data = json.dumps(
                    {
                        "audit_id": row["audit_id"],
                        "action": row["action"],
                        "entity_type": row["entity_type"],
                        "entity_id": row["entity_id"],
                        "actor_id": row["actor_id"],
                        "created_at": row["created_at"].isoformat(),
                        "previous_hash": row["previous_hash"] or "",
                    },
                    sort_keys=True,
                )
                computed = hashlib.sha256(data.encode()).hexdigest()
                if row["entry_hash"] != computed:
                    return False, f"Hash mismatch at audit log {row['audit_id']}"

            return True, None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _add_audit_log(
        self,
        conn,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[str] = None,
    ) -> None:
        """Insert hash-chained audit log entry into ledger_audit_log."""
        audit_id = f"aud_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)

        # Get previous hash for chain
        prev = await conn.fetchval(
            "SELECT entry_hash FROM ledger_audit_log ORDER BY created_at DESC LIMIT 1"
        )

        data = json.dumps(
            {
                "audit_id": audit_id,
                "action": action.value,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "actor_id": actor_id,
                "created_at": now.isoformat(),
                "previous_hash": prev or "",
            },
            sort_keys=True,
        )
        entry_hash = hashlib.sha256(data.encode()).hexdigest()

        await conn.execute(
            """
            INSERT INTO ledger_audit_log
                (audit_id, action, entity_type, entity_id, actor_id,
                 previous_hash, entry_hash, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            audit_id,
            action.value,
            entity_type,
            entity_id,
            actor_id or "system",
            prev,
            entry_hash,
            now,
        )

    def _row_to_entry(self, row) -> LedgerEntry:
        """Convert a DB row to LedgerEntry."""
        meta = row.get("metadata")
        if isinstance(meta, str):
            meta = json.loads(meta)

        return LedgerEntry(
            entry_id=row["entry_id"],
            tx_id=row["tx_id"],
            account_id=row["account_id"],
            entry_type=LedgerEntryType(row["entry_type"]),
            amount=to_ledger_decimal(row["amount"]),
            fee=to_ledger_decimal(row.get("fee", 0)),
            running_balance=to_ledger_decimal(row.get("running_balance", 0)),
            currency=row["currency"],
            chain=row.get("chain"),
            chain_tx_hash=row.get("chain_tx_hash"),
            block_number=row.get("block_number"),
            audit_anchor=row.get("audit_anchor"),
            status=LedgerEntryStatus(row["status"]),
            confirmed_at=row.get("confirmed_at"),
            created_at=row["created_at"],
            metadata=meta if isinstance(meta, dict) else {},
        )

    async def close(self) -> None:
        # Pool lifecycle managed by Database.close() at app shutdown
        pass
