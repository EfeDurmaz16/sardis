"""Tests for sardis_sdk.bulk."""

from __future__ import annotations

import asyncio

import pytest

from sardis_sdk.bulk import (
    AsyncBulkExecutor,
    BulkConfig,
    OperationStatus,
    SyncBulkExecutor,
    bulk_execute_async,
    bulk_execute_sync,
)


class TestBulkConfig:
    def test_defaults(self):
        cfg = BulkConfig()
        assert cfg.batch_size > 0
        assert cfg.max_concurrency > 0
        assert cfg.stop_on_error is False
        assert cfg.retry_failed is True

    def test_custom(self):
        cfg = BulkConfig(batch_size=5, max_concurrency=2, stop_on_error=True, retry_failed=False, max_retries=0)
        assert cfg.batch_size == 5
        assert cfg.max_concurrency == 2
        assert cfg.stop_on_error is True
        assert cfg.retry_failed is False
        assert cfg.max_retries == 0


class TestAsyncBulkExecutor:
    @pytest.mark.asyncio
    async def test_all_success(self):
        async def op(x: int) -> int:
            return x * 2

        result = await AsyncBulkExecutor(op).execute([1, 2, 3])
        assert result.summary.total == 3
        assert result.summary.successful == 3
        assert result.outputs == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_stop_on_error_skips_rest(self):
        async def op(x: int) -> int:
            if x == 2:
                raise ValueError("boom")
            return x

        # Use multiple batches so items after the failing batch are skipped.
        cfg = BulkConfig(batch_size=2, max_concurrency=1, stop_on_error=True, retry_failed=False)
        result = await AsyncBulkExecutor(op, config=cfg).execute([0, 1, 2, 3, 4])

        assert result.summary.failed == 1
        assert any(r.status == OperationStatus.SKIPPED for r in result.results)

    @pytest.mark.asyncio
    async def test_respects_max_concurrency(self):
        current = 0
        max_seen = 0
        lock = asyncio.Lock()

        async def op(x: int) -> int:
            nonlocal current, max_seen
            async with lock:
                current += 1
                max_seen = max(max_seen, current)
            await asyncio.sleep(0.02)
            async with lock:
                current -= 1
            return x

        cfg = BulkConfig(batch_size=50, max_concurrency=3, retry_failed=False)
        await AsyncBulkExecutor(op, config=cfg).execute(list(range(20)))
        assert max_seen <= 3


class TestSyncBulkExecutor:
    def test_sync_success(self):
        def op(x: int) -> int:
            return x + 1

        result = SyncBulkExecutor(op).execute([1, 2, 3])
        assert result.outputs == [2, 3, 4]
        assert result.summary.successful == 3


class TestConvenience:
    @pytest.mark.asyncio
    async def test_bulk_execute_async(self):
        async def op(x: str) -> str:
            return x.upper()

        result = await bulk_execute_async(op, ["a", "b"])
        assert result.outputs == ["A", "B"]

    def test_bulk_execute_sync(self):
        def op(x: str) -> str:
            return x.upper()

        result = bulk_execute_sync(op, ["a", "b"])
        assert result.outputs == ["A", "B"]
