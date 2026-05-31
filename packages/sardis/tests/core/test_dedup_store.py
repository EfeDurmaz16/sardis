"""Tests for durable deduplication store.

Verifies that both InMemoryDedupStore and RedisDedupStore correctly
block duplicate mandates and allow new ones.

TDD-flagged: Process-local dedup in orchestrator.py:440 means duplicate
mandates sent to different instances can result in double payments.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from sardis.core.dedup_store import InMemoryDedupStore, RedisDedupStore

# ── Fixtures ────────────────────────────────────────────────────────


SAMPLE_RESULT = {
    "mandate_id": "mdt_test_001",
    "ledger_tx_id": "ltx_001",
    "chain_tx_hash": "0xabc123",
    "chain": "base",
    "status": "submitted",
}


def _make_mock_redis(*, existing: dict[str, str] | None = None) -> AsyncMock:
    """Build a mock async Redis client.

    Args:
        existing: Pre-populated key/value pairs (simulates keys already set).
    """
    store: dict[str, str] = dict(existing or {})

    client = AsyncMock()

    async def _get(key: str) -> str | None:
        return store.get(key)

    async def _set(key: str, value: str, *, ex: int | None = None) -> None:
        store[key] = value

    client.get = AsyncMock(side_effect=_get)
    client.set = AsyncMock(side_effect=_set)

    return client


# ── InMemoryDedupStore tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_in_memory_dedup_allows_new():
    """First call with a new mandate_id returns None (not a duplicate)."""
    store = InMemoryDedupStore()
    result = await store.check_and_set("mdt_new", SAMPLE_RESULT)
    assert result is None


@pytest.mark.asyncio
async def test_in_memory_dedup_blocks_duplicate():
    """Second call with the same mandate_id returns the first result."""
    store = InMemoryDedupStore()

    first = await store.check_and_set("mdt_dup", SAMPLE_RESULT)
    assert first is None  # stored successfully

    second = await store.check_and_set("mdt_dup", {"should": "be_ignored"})
    assert second == SAMPLE_RESULT  # returns the originally stored result


@pytest.mark.asyncio
async def test_in_memory_dedup_different_ids_independent():
    """Different mandate IDs do not interfere with each other."""
    store = InMemoryDedupStore()

    r1 = await store.check_and_set("mdt_a", {"id": "a"})
    r2 = await store.check_and_set("mdt_b", {"id": "b"})

    assert r1 is None
    assert r2 is None


@pytest.mark.asyncio
async def test_in_memory_check_returns_existing():
    """check() returns stored result without modifying state."""
    store = InMemoryDedupStore()

    assert await store.check("mdt_x") is None
    await store.check_and_set("mdt_x", SAMPLE_RESULT)
    assert await store.check("mdt_x") == SAMPLE_RESULT


# ── RedisDedupStore tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_redis_dedup_allows_new():
    """First call stores the result in Redis with TTL and returns None."""
    redis = _make_mock_redis()
    store = RedisDedupStore(redis, ttl_seconds=3600)

    result = await store.check_and_set("mdt_new", SAMPLE_RESULT)

    assert result is None
    # Verify Redis set was called with the correct key and TTL
    redis.set.assert_awaited_once()
    call_args = redis.set.call_args
    assert call_args[0][0] == "sardis:dedup:mdt_new"
    assert json.loads(call_args[0][1]) == SAMPLE_RESULT
    assert call_args[1]["ex"] == 3600


@pytest.mark.asyncio
async def test_redis_dedup_blocks_duplicate():
    """When key already exists in Redis, returns the stored result."""
    pre_existing = {
        "sardis:dedup:mdt_dup": json.dumps(SAMPLE_RESULT),
    }
    redis = _make_mock_redis(existing=pre_existing)
    store = RedisDedupStore(redis, ttl_seconds=86_400)

    result = await store.check_and_set("mdt_dup", {"should": "be_ignored"})

    assert result == SAMPLE_RESULT
    # set should NOT have been called since it was a duplicate
    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_dedup_check_only():
    """check() reads without writing."""
    pre_existing = {
        "sardis:dedup:mdt_exist": json.dumps(SAMPLE_RESULT),
    }
    redis = _make_mock_redis(existing=pre_existing)
    store = RedisDedupStore(redis, ttl_seconds=86_400)

    # Existing key returns result
    assert await store.check("mdt_exist") == SAMPLE_RESULT
    # Non-existing key returns None
    assert await store.check("mdt_missing") is None
    # set should never have been called
    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_dedup_raises_on_connection_failure():
    """Fail-closed: Redis errors propagate so orchestrator can reject."""
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=ConnectionError("redis down"))

    store = RedisDedupStore(redis, ttl_seconds=86_400)

    with pytest.raises(ConnectionError, match="redis down"):
        await store.check_and_set("mdt_fail", SAMPLE_RESULT)


@pytest.mark.asyncio
async def test_redis_dedup_check_raises_on_connection_failure():
    """Fail-closed: Redis errors on check() also propagate."""
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=ConnectionError("redis down"))

    store = RedisDedupStore(redis, ttl_seconds=86_400)

    with pytest.raises(ConnectionError, match="redis down"):
        await store.check("mdt_fail")


@pytest.mark.asyncio
async def test_redis_dedup_uses_default_ttl():
    """Default TTL is 86400 seconds (24 hours)."""
    redis = _make_mock_redis()
    store = RedisDedupStore(redis)

    await store.check_and_set("mdt_ttl", SAMPLE_RESULT)

    call_args = redis.set.call_args
    assert call_args[1]["ex"] == 86_400


# ── P1-4: PaymentResult rehydration ─────────────────────────────────


@pytest.mark.asyncio
async def test_redis_dedup_rehydrates_payment_result_not_str():
    """P1-4: a stored PaymentResult must come back as a PaymentResult, not a str.

    RedisDedupStore JSON-serialised with default=str, so a hit returned a raw
    string and A2A callers crashed on result.chain_tx_hash. Both stores must be
    interchangeable: check()/check_and_set() rehydrate into a PaymentResult.
    """
    from sardis.core.orchestrator import PaymentResult

    result = PaymentResult(
        mandate_id="mdt_pr_001",
        ledger_tx_id="ltx_pr_001",
        chain_tx_hash="0xdeadbeef",
        chain="base",
        audit_anchor="0x" + "00" * 32,
        status="submitted",
    )

    redis = _make_mock_redis()
    store = RedisDedupStore(redis, ttl_seconds=3600)

    # First store (no duplicate yet).
    assert await store.check_and_set("mdt_pr_001", result) is None

    # A subsequent check must return an equivalent PaymentResult object.
    hit = await store.check("mdt_pr_001")
    assert isinstance(hit, PaymentResult)
    assert hit.chain_tx_hash == "0xdeadbeef"
    assert hit.mandate_id == "mdt_pr_001"
    assert hit.chain == "base"

    # check_and_set on the duplicate also rehydrates.
    dup = await store.check_and_set("mdt_pr_001", result)
    assert isinstance(dup, PaymentResult)
    assert dup.chain_tx_hash == "0xdeadbeef"


@pytest.mark.asyncio
async def test_in_memory_dedup_returns_payment_result():
    """InMemoryDedupStore returns the same PaymentResult object (interchangeable)."""
    from sardis.core.orchestrator import PaymentResult

    result = PaymentResult(
        mandate_id="mdt_pr_002",
        ledger_tx_id="ltx_pr_002",
        chain_tx_hash="0xfeed",
        chain="base",
        audit_anchor="0x" + "00" * 32,
    )
    store = InMemoryDedupStore()
    assert await store.check_and_set("mdt_pr_002", result) is None
    hit = await store.check("mdt_pr_002")
    assert isinstance(hit, PaymentResult)
    assert hit.chain_tx_hash == "0xfeed"


# ── P1-5: atomic reserve (SET NX) ───────────────────────────────────


@pytest.mark.asyncio
async def test_in_memory_reserve_is_atomic():
    """First reserve of a key returns True; a concurrent second returns False."""
    store = InMemoryDedupStore()
    assert await store.reserve("mdt_resv") is True
    assert await store.reserve("mdt_resv") is False
    # A different key is independent.
    assert await store.reserve("mdt_other") is True


@pytest.mark.asyncio
async def test_redis_reserve_uses_set_nx():
    """Redis reserve uses SET NX so only one worker wins the reservation."""
    reserved: dict[str, str] = {}
    redis = AsyncMock()

    async def _set(key, value, *, nx=False, ex=None):
        if nx and key in reserved:
            return None  # redis returns None when NX fails
        reserved[key] = value
        return True

    redis.set = AsyncMock(side_effect=_set)
    store = RedisDedupStore(redis, ttl_seconds=3600)

    assert await store.reserve("mdt_nx") is True
    assert await store.reserve("mdt_nx") is False
    # NX flag must have been passed.
    assert redis.set.await_args_list[0].kwargs.get("nx") is True
