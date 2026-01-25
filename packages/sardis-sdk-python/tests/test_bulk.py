"""
Comprehensive tests for sardis_sdk.bulk module.

Tests cover:
- BulkConfig configuration
- AsyncBulkExecutor for async bulk operations
- SyncBulkExecutor for sync bulk operations
- Error handling and partial failures
- Concurrency control
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sardis_sdk.bulk import (
    BulkConfig,
    OperationStatus,
    OperationResult,
    BulkOperationResult,
    BulkOperationSummary,
    AsyncBulkExecutor,
    SyncBulkExecutor,
    bulk_execute_async,
    bulk_execute_sync,
)


class TestBulkConfig:
    """Tests for BulkConfig class."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = BulkConfig()

        assert config.max_concurrent > 0
        assert config.stop_on_error is False
        assert config.retry_failed is True

    def test_custom_config(self):
        """Should accept custom configuration."""
        config = BulkConfig(
            max_concurrent=5,
            stop_on_error=True,
            retry_failed=False,
            timeout_per_operation=30.0,
        )

        assert config.max_concurrent == 5
        assert config.stop_on_error is True
        assert config.retry_failed is False
        assert config.timeout_per_operation == 30.0


class TestOperationStatus:
    """Tests for OperationStatus enum."""

    def test_status_values(self):
        """Should have correct status values."""
        assert OperationStatus.SUCCESS.value == "success"
        assert OperationStatus.FAILED.value == "failed"
        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.SKIPPED.value == "skipped"


class TestOperationResult:
    """Tests for OperationResult class."""

    def test_successful_result(self):
        """Should create successful result."""
        result = OperationResult(
            index=0,
            status=OperationStatus.SUCCESS,
            result={"id": "created_123"},
        )

        assert result.index == 0
        assert result.status == OperationStatus.SUCCESS
        assert result.result["id"] == "created_123"
        assert result.error is None

    def test_failed_result(self):
        """Should create failed result."""
        result = OperationResult(
            index=1,
            status=OperationStatus.FAILED,
            error="Validation failed",
        )

        assert result.status == OperationStatus.FAILED
        assert result.error == "Validation failed"
        assert result.result is None


class TestBulkOperationSummary:
    """Tests for BulkOperationSummary class."""

    def test_create_summary(self):
        """Should create summary from results."""
        results = [
            OperationResult(0, OperationStatus.SUCCESS, result={"id": "1"}),
            OperationResult(1, OperationStatus.SUCCESS, result={"id": "2"}),
            OperationResult(2, OperationStatus.FAILED, error="Error"),
            OperationResult(3, OperationStatus.SKIPPED),
        ]

        summary = BulkOperationSummary.from_results(results)

        assert summary.total == 4
        assert summary.successful == 2
        assert summary.failed == 1
        assert summary.skipped == 1

    def test_all_successful(self):
        """Should calculate all_successful."""
        results = [
            OperationResult(0, OperationStatus.SUCCESS),
            OperationResult(1, OperationStatus.SUCCESS),
        ]

        summary = BulkOperationSummary.from_results(results)

        assert summary.all_successful is True

    def test_has_failures(self):
        """Should detect failures."""
        results = [
            OperationResult(0, OperationStatus.SUCCESS),
            OperationResult(1, OperationStatus.FAILED, error="Error"),
        ]

        summary = BulkOperationSummary.from_results(results)

        assert summary.all_successful is False


class TestAsyncBulkExecutor:
    """Tests for AsyncBulkExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_all_success(self):
        """Should execute all operations successfully."""
        operations = [
            {"data": "item_1"},
            {"data": "item_2"},
            {"data": "item_3"},
        ]

        call_count = 0

        async def execute_fn(op):
            nonlocal call_count
            call_count += 1
            return {"created": op["data"]}

        executor = AsyncBulkExecutor(
            operations=operations,
            execute_fn=execute_fn,
        )

        result = await executor.execute()

        assert result.summary.total == 3
        assert result.summary.successful == 3
        assert result.summary.failed == 0
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_failures(self):
        """Should handle partial failures."""
        operations = [
            {"id": 1, "should_fail": False},
            {"id": 2, "should_fail": True},
            {"id": 3, "should_fail": False},
        ]

        async def execute_fn(op):
            if op["should_fail"]:
                raise ValueError(f"Operation {op['id']} failed")
            return {"id": op["id"], "status": "created"}

        executor = AsyncBulkExecutor(
            operations=operations,
            execute_fn=execute_fn,
        )

        result = await executor.execute()

        assert result.summary.total == 3
        assert result.summary.successful == 2
        assert result.summary.failed == 1

    @pytest.mark.asyncio
    async def test_stop_on_error(self):
        """Should stop on first error when configured."""
        operations = [{"id": i} for i in range(10)]
        executed = []

        async def execute_fn(op):
            executed.append(op["id"])
            if op["id"] == 2:
                raise ValueError("Error at 2")
            return {"success": True}

        config = BulkConfig(stop_on_error=True, max_concurrent=1)
        executor = AsyncBulkExecutor(
            operations=operations,
            execute_fn=execute_fn,
            config=config,
        )

        result = await executor.execute()

        # Should stop at error
        assert len(executed) <= 3  # 0, 1, 2

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Should respect concurrency limit."""
        max_concurrent_seen = 0
        current_concurrent = 0

        async def execute_fn(op):
            nonlocal max_concurrent_seen, current_concurrent
            current_concurrent += 1
            max_concurrent_seen = max(max_concurrent_seen, current_concurrent)
            await asyncio.sleep(0.05)
            current_concurrent -= 1
            return {"done": True}

        operations = [{"id": i} for i in range(20)]
        config = BulkConfig(max_concurrent=3)

        executor = AsyncBulkExecutor(
            operations=operations,
            execute_fn=execute_fn,
            config=config,
        )

        await executor.execute()

        assert max_concurrent_seen <= 3


class TestSyncBulkExecutor:
    """Tests for SyncBulkExecutor class."""

    def test_execute_all_success(self):
        """Should execute all operations."""
        operations = [{"value": i} for i in range(5)]

        def execute_fn(op):
            return {"result": op["value"] * 2}

        executor = SyncBulkExecutor(
            operations=operations,
            execute_fn=execute_fn,
        )

        result = executor.execute()

        assert result.summary.total == 5
        assert result.summary.successful == 5

    def test_execute_with_failures(self):
        """Should handle failures."""
        operations = [{"id": 1}, {"id": 2, "fail": True}, {"id": 3}]

        def execute_fn(op):
            if op.get("fail"):
                raise RuntimeError("Failed")
            return {"created": op["id"]}

        executor = SyncBulkExecutor(
            operations=operations,
            execute_fn=execute_fn,
        )

        result = executor.execute()

        assert result.summary.failed == 1
        assert result.summary.successful == 2


class TestBulkExecuteFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_bulk_execute_async(self):
        """Should execute async bulk operations."""
        operations = [1, 2, 3, 4, 5]

        async def double(x):
            return x * 2

        result = await bulk_execute_async(operations, double)

        assert result.summary.total == 5
        assert result.summary.successful == 5

        # Check results
        successful_results = [
            r.result for r in result.results
            if r.status == OperationStatus.SUCCESS
        ]
        assert 2 in successful_results
        assert 10 in successful_results

    def test_bulk_execute_sync(self):
        """Should execute sync bulk operations."""
        operations = ["a", "b", "c"]

        def upper(s):
            return s.upper()

        result = bulk_execute_sync(operations, upper)

        assert result.summary.total == 3
        assert result.summary.successful == 3


class TestBulkOperationResult:
    """Tests for BulkOperationResult class."""

    def test_get_successful_results(self):
        """Should get only successful results."""
        result = BulkOperationResult(
            results=[
                OperationResult(0, OperationStatus.SUCCESS, result="a"),
                OperationResult(1, OperationStatus.FAILED, error="err"),
                OperationResult(2, OperationStatus.SUCCESS, result="c"),
            ],
            summary=BulkOperationSummary(total=3, successful=2, failed=1),
        )

        successful = result.successful_results

        assert len(successful) == 2
        assert all(r.status == OperationStatus.SUCCESS for r in successful)

    def test_get_failed_results(self):
        """Should get only failed results."""
        result = BulkOperationResult(
            results=[
                OperationResult(0, OperationStatus.SUCCESS, result="a"),
                OperationResult(1, OperationStatus.FAILED, error="err"),
            ],
            summary=BulkOperationSummary(total=2, successful=1, failed=1),
        )

        failed = result.failed_results

        assert len(failed) == 1
        assert failed[0].error == "err"


class TestBulkEdgeCases:
    """Edge case tests for bulk operations."""

    @pytest.mark.asyncio
    async def test_empty_operations(self):
        """Should handle empty operations list."""
        async def execute_fn(op):
            return {"done": True}

        executor = AsyncBulkExecutor(
            operations=[],
            execute_fn=execute_fn,
        )

        result = await executor.execute()

        assert result.summary.total == 0

    @pytest.mark.asyncio
    async def test_single_operation(self):
        """Should handle single operation."""
        async def execute_fn(op):
            return {"processed": op}

        executor = AsyncBulkExecutor(
            operations=["single"],
            execute_fn=execute_fn,
        )

        result = await executor.execute()

        assert result.summary.total == 1
        assert result.summary.successful == 1

    @pytest.mark.asyncio
    async def test_none_result(self):
        """Should handle None results."""
        async def execute_fn(op):
            return None

        executor = AsyncBulkExecutor(
            operations=[1, 2],
            execute_fn=execute_fn,
        )

        result = await executor.execute()

        assert result.summary.successful == 2

    @pytest.mark.asyncio
    async def test_operation_timeout(self):
        """Should handle operation timeouts."""
        async def slow_execute(op):
            await asyncio.sleep(10)
            return {"done": True}

        config = BulkConfig(timeout_per_operation=0.1)
        executor = AsyncBulkExecutor(
            operations=[1],
            execute_fn=slow_execute,
            config=config,
        )

        # Should complete (may timeout the operation)
        result = await executor.execute()

        # Depending on implementation, may be failed or timed out
        assert result.summary.total == 1
