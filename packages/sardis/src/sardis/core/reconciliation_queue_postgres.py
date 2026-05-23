"""PostgreSQL-backed reconciliation queue.

Persistent replacement for InMemoryReconciliationQueue.  Ensures that
failed ledger appends and spend-state reconciliation entries survive
process restarts.

Implements the ReconciliationQueuePort protocol from orchestrator.py
with async methods backed by asyncpg.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .orchestrator import ReconciliationEntry

logger = logging.getLogger(__name__)


class PostgresReconciliationQueue:
    """Postgres-backed reconciliation queue.

    Each entry is stored as a row in the ``reconciliation_queue`` table
    (see migration 057).  The ``payload_json`` column holds the full
    serialised :class:`ReconciliationEntry` so that no information is
    lost across restarts.

    The ``entry_type`` column stores the mandate_id for quick lookups,
    matching the in-memory implementation's dict-key semantics.
    """

    MAX_RETRIES = 5

    def __init__(self, pool: Any) -> None:
        """Initialise with an asyncpg connection pool."""
        self._pool = pool

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _entry_to_payload(entry: ReconciliationEntry) -> dict[str, Any]:
        """Serialise a ReconciliationEntry to a JSON-safe dict."""
        return {
            "mandate_id": entry.mandate_id,
            "chain_tx_hash": entry.chain_tx_hash,
            "chain": entry.chain,
            "audit_anchor": entry.audit_anchor,
            "payment_mandate": str(entry.payment_mandate),
            "chain_receipt": str(entry.chain_receipt),
            "error": entry.error,
            "created_at": entry.created_at.isoformat(),
            "retry_count": entry.retry_count,
            "last_retry": entry.last_retry.isoformat() if entry.last_retry else None,
            "resolved": entry.resolved,
        }

    @staticmethod
    def _row_to_entry(row: Any) -> ReconciliationEntry:
        """Deserialise a database row back to a ReconciliationEntry."""
        payload = row["payload_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)

        created_at = payload.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = row["created_at"] if "created_at" in row else datetime.now(UTC)

        last_retry = payload.get("last_retry")
        if isinstance(last_retry, str):
            last_retry = datetime.fromisoformat(last_retry)

        return ReconciliationEntry(
            mandate_id=payload["mandate_id"],
            chain_tx_hash=payload["chain_tx_hash"],
            chain=payload["chain"],
            audit_anchor=payload["audit_anchor"],
            payment_mandate=payload.get("payment_mandate"),
            chain_receipt=payload.get("chain_receipt"),
            error=payload["error"],
            created_at=created_at,
            retry_count=row["retry_count"],
            last_retry=last_retry,
            resolved=(row["status"] == "resolved"),
        )

    # ------------------------------------------------------------------
    # ReconciliationQueuePort interface (async)
    # ------------------------------------------------------------------

    async def enqueue(self, entry: ReconciliationEntry) -> str:
        """Insert a new reconciliation entry and return its mandate_id."""
        payload = self._entry_to_payload(entry)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO reconciliation_queue (entry_type, payload_json, status, retry_count)
                VALUES ($1, $2::jsonb, 'pending', $3)
                """,
                entry.mandate_id,
                json.dumps(payload),
                entry.retry_count,
            )
        logger.warning(
            "Ledger append queued for reconciliation (postgres): "
            "mandate_id=%s, tx_hash=%s, error=%s",
            entry.mandate_id,
            entry.chain_tx_hash,
            entry.error,
        )
        return entry.mandate_id

    async def get_pending(self, limit: int = 100) -> list[ReconciliationEntry]:
        """Return pending entries ordered by creation time."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, entry_type, payload_json, status, retry_count, created_at, processed_at
                FROM reconciliation_queue
                WHERE status = 'pending' AND retry_count < $1
                ORDER BY created_at
                LIMIT $2
                """,
                self.MAX_RETRIES,
                limit,
            )
        return [self._row_to_entry(row) for row in rows]

    async def mark_resolved(self, mandate_id: str) -> bool:
        """Mark the entry for *mandate_id* as resolved."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE reconciliation_queue
                SET status = 'resolved', processed_at = now()
                WHERE entry_type = $1 AND status IN ('pending', 'processing')
                """,
                mandate_id,
            )
        updated = self._rows_affected(result)
        if updated:
            logger.info("Reconciliation resolved (postgres): mandate_id=%s", mandate_id)
        return updated > 0

    async def increment_retry(self, mandate_id: str) -> bool:
        """Increment the retry counter for the given mandate_id."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE reconciliation_queue
                SET retry_count = retry_count + 1
                WHERE entry_type = $1 AND status IN ('pending', 'processing')
                """,
                mandate_id,
            )
        return self._rows_affected(result) > 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rows_affected(result: str) -> int:
        """Parse asyncpg command-tag (e.g. ``UPDATE 1``) to an int count."""
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError, AttributeError):
            return 0
