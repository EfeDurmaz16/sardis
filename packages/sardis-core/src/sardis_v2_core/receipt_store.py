"""Persistent store for execution receipts.

Supports in-memory (dev) and PostgreSQL (prod) implementations.
Receipts are immutable once stored — write-once, read-many.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

from .execution_receipt import ExecutionReceipt

logger = logging.getLogger(__name__)


class ReceiptStore(Protocol):
    """Interface for receipt persistence."""

    async def save(self, receipt: ExecutionReceipt) -> None: ...
    async def get(self, receipt_id: str) -> ExecutionReceipt | None: ...
    async def get_by_tx_hash(self, tx_hash: str) -> ExecutionReceipt | None: ...
    async def list_by_agent(self, agent_id: str, limit: int = 50) -> list[ExecutionReceipt]: ...
    async def list_by_org(self, org_id: str, limit: int = 50) -> list[ExecutionReceipt]: ...
    async def verify(self, receipt_id: str) -> bool: ...


class InMemoryReceiptStore:
    """In-memory receipt store for development and testing."""

    def __init__(self) -> None:
        self._receipts: dict[str, ExecutionReceipt] = {}
        self._by_tx_hash: dict[str, str] = {}  # tx_hash -> receipt_id

    async def save(self, receipt: ExecutionReceipt) -> None:
        if receipt.receipt_id in self._receipts:
            raise ValueError(f"Receipt already exists: {receipt.receipt_id}")
        self._receipts[receipt.receipt_id] = receipt
        if receipt.tx_hash:
            self._by_tx_hash[receipt.tx_hash] = receipt.receipt_id
        logger.info("Receipt saved: %s", receipt.receipt_id)

    async def get(self, receipt_id: str) -> ExecutionReceipt | None:
        return self._receipts.get(receipt_id)

    async def get_by_tx_hash(self, tx_hash: str) -> ExecutionReceipt | None:
        receipt_id = self._by_tx_hash.get(tx_hash)
        if receipt_id:
            return self._receipts.get(receipt_id)
        return None

    async def list_by_agent(self, agent_id: str, limit: int = 50) -> list[ExecutionReceipt]:
        results = [r for r in self._receipts.values() if r.agent_id == agent_id]
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]

    async def list_by_org(self, org_id: str, limit: int = 50) -> list[ExecutionReceipt]:
        results = [r for r in self._receipts.values() if r.org_id == org_id]
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]

    async def verify(self, receipt_id: str) -> bool:
        receipt = self._receipts.get(receipt_id)
        if not receipt:
            return False
        return receipt.verify()


class PostgresReceiptStore:
    """PostgreSQL-backed receipt store for production use.

    Requires an asyncpg connection pool passed at construction time.
    """

    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def save(self, receipt: ExecutionReceipt) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO execution_receipts
                   (receipt_id, timestamp_, intent_hash, policy_snapshot_hash,
                    compliance_result_hash, tx_hash, chain, ledger_entry_id,
                    ledger_tx_id, org_id, agent_id, amount, currency, signature)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                """,
                receipt.receipt_id, receipt.timestamp, receipt.intent_hash,
                receipt.policy_snapshot_hash, receipt.compliance_result_hash,
                receipt.tx_hash, receipt.chain, receipt.ledger_entry_id,
                receipt.ledger_tx_id, receipt.org_id, receipt.agent_id,
                receipt.amount, receipt.currency, receipt.signature,
            )
        logger.info("Receipt persisted: %s", receipt.receipt_id)

    async def get(self, receipt_id: str) -> ExecutionReceipt | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM execution_receipts WHERE receipt_id = $1",
                receipt_id,
            )
        return _row_to_receipt(row) if row else None

    async def get_by_tx_hash(self, tx_hash: str) -> ExecutionReceipt | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM execution_receipts WHERE tx_hash = $1",
                tx_hash,
            )
        return _row_to_receipt(row) if row else None

    async def list_by_agent(self, agent_id: str, limit: int = 50) -> list[ExecutionReceipt]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM execution_receipts WHERE agent_id = $1 ORDER BY timestamp_ DESC LIMIT $2",
                agent_id, limit,
            )
        return [_row_to_receipt(r) for r in rows]

    async def list_by_org(self, org_id: str, limit: int = 50) -> list[ExecutionReceipt]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM execution_receipts WHERE org_id = $1 ORDER BY timestamp_ DESC LIMIT $2",
                org_id, limit,
            )
        return [_row_to_receipt(r) for r in rows]

    async def verify(self, receipt_id: str) -> bool:
        receipt = await self.get(receipt_id)
        if not receipt:
            return False
        return receipt.verify()


def _row_to_receipt(row: Any) -> ExecutionReceipt:
    """Convert a database row to ExecutionReceipt."""
    return ExecutionReceipt(
        receipt_id=row["receipt_id"],
        timestamp=row["timestamp_"],
        intent_hash=row["intent_hash"],
        policy_snapshot_hash=row["policy_snapshot_hash"],
        compliance_result_hash=row["compliance_result_hash"],
        tx_hash=row["tx_hash"],
        chain=row["chain"],
        ledger_entry_id=row["ledger_entry_id"] or "",
        ledger_tx_id=row["ledger_tx_id"] or "",
        org_id=row["org_id"],
        agent_id=row["agent_id"],
        amount=row["amount"],
        currency=row["currency"],
        signature=row["signature"],
    )
