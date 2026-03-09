"""Tests for PostgreSQL-backed reconciliation queue.

Verifies that PostgresReconciliationQueue correctly persists, retrieves,
resolves, and retries reconciliation entries using a mock asyncpg pool.

TDD-flagged: InMemoryReconciliationQueue loses all pending entries on
restart.  Any payment where ledger append fails after chain execution
will lose its reconciliation state.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis_v2_core.orchestrator import ReconciliationEntry
from sardis_v2_core.reconciliation_queue_postgres import PostgresReconciliationQueue


# ── Helpers ──────────────────────────────────────────────────────────


def _make_entry(
    mandate_id: str = "mdt_test_001",
    chain_tx_hash: str = "0xabc123",
    chain: str = "base",
    error: str = "ledger append timeout",
    retry_count: int = 0,
) -> ReconciliationEntry:
    """Build a sample ReconciliationEntry."""
    return ReconciliationEntry(
        mandate_id=mandate_id,
        chain_tx_hash=chain_tx_hash,
        chain=chain,
        audit_anchor="anchor_001",
        payment_mandate="<mandate>",
        chain_receipt="<receipt>",
        error=error,
        created_at=datetime.now(UTC),
        retry_count=retry_count,
        last_retry=None,
        resolved=False,
    )


def _make_row(entry: ReconciliationEntry, *, status: str = "pending") -> dict[str, Any]:
    """Build a mock database row dict from a ReconciliationEntry."""
    payload = PostgresReconciliationQueue._entry_to_payload(entry)
    return {
        "id": 1,
        "entry_type": entry.mandate_id,
        "payload_json": payload,
        "status": status,
        "retry_count": entry.retry_count,
        "created_at": entry.created_at,
        "processed_at": None,
    }


class _FakeRow(dict):
    """A dict subclass that also supports attribute-style access via keys()."""

    def keys(self):
        return super().keys()


def _make_mock_pool(
    *,
    fetch_rows: list[dict] | None = None,
    execute_result: str = "UPDATE 1",
) -> AsyncMock:
    """Build a mock asyncpg pool with acquire() -> connection context manager.

    Args:
        fetch_rows: Rows to return from conn.fetch().
        execute_result: String to return from conn.execute() (asyncpg command tag).
    """
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=execute_result)

    rows = [_FakeRow(r) for r in (fetch_rows or [])]
    conn.fetch = AsyncMock(return_value=rows)

    # Make conn usable as an async context manager
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=ctx)

    return pool


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enqueue_inserts_row():
    """enqueue() should INSERT a row and return the mandate_id."""
    pool = _make_mock_pool()
    queue = PostgresReconciliationQueue(pool)
    entry = _make_entry()

    result = await queue.enqueue(entry)

    assert result == "mdt_test_001"

    # Verify execute was called with INSERT
    conn = pool.acquire().__aenter__.return_value
    conn.execute.assert_awaited_once()
    call_args = conn.execute.call_args
    sql = call_args[0][0]
    assert "INSERT INTO reconciliation_queue" in sql
    # Verify the mandate_id is passed as entry_type
    assert call_args[0][1] == "mdt_test_001"
    # Verify the payload JSON is valid
    payload = json.loads(call_args[0][2])
    assert payload["mandate_id"] == "mdt_test_001"
    assert payload["chain_tx_hash"] == "0xabc123"
    assert payload["chain"] == "base"
    assert payload["error"] == "ledger append timeout"


@pytest.mark.asyncio
async def test_get_pending_returns_entries():
    """get_pending() should SELECT pending entries ordered by created_at."""
    entry = _make_entry()
    rows = [_make_row(entry)]
    pool = _make_mock_pool(fetch_rows=rows)
    queue = PostgresReconciliationQueue(pool)

    pending = await queue.get_pending()

    assert len(pending) == 1
    assert pending[0].mandate_id == "mdt_test_001"
    assert pending[0].chain_tx_hash == "0xabc123"
    assert pending[0].chain == "base"
    assert pending[0].error == "ledger append timeout"
    assert pending[0].resolved is False

    # Verify SELECT was called
    conn = pool.acquire().__aenter__.return_value
    conn.fetch.assert_awaited_once()
    sql = conn.fetch.call_args[0][0]
    assert "WHERE status = 'pending'" in sql
    assert "ORDER BY created_at" in sql


@pytest.mark.asyncio
async def test_get_pending_respects_limit():
    """get_pending(limit=N) should pass the limit to the query."""
    pool = _make_mock_pool(fetch_rows=[])
    queue = PostgresReconciliationQueue(pool)

    await queue.get_pending(limit=10)

    conn = pool.acquire().__aenter__.return_value
    # The limit parameter should be the second positional arg
    call_args = conn.fetch.call_args[0]
    assert call_args[2] == 10  # $2 = limit


@pytest.mark.asyncio
async def test_get_pending_excludes_max_retries():
    """get_pending() should filter out entries with retry_count >= MAX_RETRIES."""
    pool = _make_mock_pool(fetch_rows=[])
    queue = PostgresReconciliationQueue(pool)

    await queue.get_pending()

    conn = pool.acquire().__aenter__.return_value
    sql = conn.fetch.call_args[0][0]
    assert "retry_count" in sql
    # First positional param ($1) should be MAX_RETRIES
    assert conn.fetch.call_args[0][1] == PostgresReconciliationQueue.MAX_RETRIES


@pytest.mark.asyncio
async def test_mark_resolved_updates_status():
    """mark_resolved() should UPDATE status to 'resolved' and set processed_at."""
    pool = _make_mock_pool(execute_result="UPDATE 1")
    queue = PostgresReconciliationQueue(pool)

    result = await queue.mark_resolved("mdt_test_001")

    assert result is True

    conn = pool.acquire().__aenter__.return_value
    conn.execute.assert_awaited_once()
    sql = conn.execute.call_args[0][0]
    assert "SET status = 'resolved'" in sql
    assert "processed_at = now()" in sql
    assert conn.execute.call_args[0][1] == "mdt_test_001"


@pytest.mark.asyncio
async def test_mark_resolved_returns_false_when_not_found():
    """mark_resolved() should return False when no rows match."""
    pool = _make_mock_pool(execute_result="UPDATE 0")
    queue = PostgresReconciliationQueue(pool)

    result = await queue.mark_resolved("mdt_nonexistent")

    assert result is False


@pytest.mark.asyncio
async def test_increment_retry_increments_count():
    """increment_retry() should UPDATE retry_count = retry_count + 1."""
    pool = _make_mock_pool(execute_result="UPDATE 1")
    queue = PostgresReconciliationQueue(pool)

    result = await queue.increment_retry("mdt_test_001")

    assert result is True

    conn = pool.acquire().__aenter__.return_value
    conn.execute.assert_awaited_once()
    sql = conn.execute.call_args[0][0]
    assert "retry_count = retry_count + 1" in sql
    assert conn.execute.call_args[0][1] == "mdt_test_001"


@pytest.mark.asyncio
async def test_increment_retry_returns_false_when_not_found():
    """increment_retry() should return False when no rows match."""
    pool = _make_mock_pool(execute_result="UPDATE 0")
    queue = PostgresReconciliationQueue(pool)

    result = await queue.increment_retry("mdt_nonexistent")

    assert result is False


@pytest.mark.asyncio
async def test_entry_serialisation_roundtrip():
    """ReconciliationEntry should survive serialise -> deserialise roundtrip."""
    entry = _make_entry()
    row = _FakeRow(_make_row(entry))

    restored = PostgresReconciliationQueue._row_to_entry(row)

    assert restored.mandate_id == entry.mandate_id
    assert restored.chain_tx_hash == entry.chain_tx_hash
    assert restored.chain == entry.chain
    assert restored.audit_anchor == entry.audit_anchor
    assert restored.error == entry.error
    assert restored.retry_count == entry.retry_count
    assert restored.resolved is False
