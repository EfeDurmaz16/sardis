"""
Comprehensive tests for sardis_checkout.idempotency module.

Tests cover:
- IdempotencyStore implementations
- IdempotencyManager behavior
- Concurrent request handling
- Key conflict detection
- Expiration handling
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import json

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_checkout.idempotency import (
    IdempotencyError,
    IdempotencyKeyConflict,
    IdempotencyOperationInProgress,
    IdempotencyStore,
    InMemoryIdempotencyStore,
    IdempotencyManager,
)
from sardis_checkout.models import IdempotencyRecord


class TestIdempotencyError:
    """Tests for IdempotencyError exception."""

    def test_base_error(self):
        """Should create base idempotency error."""
        error = IdempotencyError("Something went wrong")
        assert str(error) == "Something went wrong"


class TestIdempotencyKeyConflict:
    """Tests for IdempotencyKeyConflict exception."""

    def test_conflict_error(self):
        """Should create key conflict error."""
        error = IdempotencyKeyConflict("Key reused with different params")
        assert "different params" in str(error).lower() or "key" in str(error).lower()


class TestIdempotencyOperationInProgress:
    """Tests for IdempotencyOperationInProgress exception."""

    def test_in_progress_error(self):
        """Should create in-progress error."""
        error = IdempotencyOperationInProgress("Operation already running")
        assert isinstance(error, IdempotencyError)


class TestInMemoryIdempotencyStore:
    """Tests for InMemoryIdempotencyStore class."""

    @pytest.fixture
    def store(self):
        """Create in-memory store."""
        return InMemoryIdempotencyStore()

    @pytest.fixture
    def sample_record(self):
        """Create sample idempotency record."""
        return IdempotencyRecord(
            idempotency_key="test_key_123",
            operation="create_checkout",
            request_hash="abc123",
            status="completed",
            response_code=200,
            response_body=json.dumps({"id": "checkout_456"}),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

    @pytest.mark.asyncio
    async def test_create_record(self, store, sample_record):
        """Should create new record."""
        success = await store.create(sample_record)
        assert success is True

    @pytest.mark.asyncio
    async def test_get_record(self, store, sample_record):
        """Should retrieve created record."""
        await store.create(sample_record)

        record = await store.get(sample_record.idempotency_key)

        assert record is not None
        assert record.idempotency_key == sample_record.idempotency_key

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        """Should return None for nonexistent key."""
        record = await store.get("nonexistent_key")
        assert record is None

    @pytest.mark.asyncio
    async def test_create_duplicate(self, store, sample_record):
        """Should return False for duplicate key."""
        await store.create(sample_record)

        # Try to create again
        success = await store.create(sample_record)
        assert success is False

    @pytest.mark.asyncio
    async def test_update_record(self, store, sample_record):
        """Should update existing record."""
        await store.create(sample_record)

        sample_record.status = "failed"
        sample_record.response_code = 500

        success = await store.update(sample_record)
        assert success is True

        updated = await store.get(sample_record.idempotency_key)
        assert updated.status == "failed"
        assert updated.response_code == 500

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, store, sample_record):
        """Should return False for updating nonexistent record."""
        success = await store.update(sample_record)
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_record(self, store, sample_record):
        """Should delete record."""
        await store.create(sample_record)

        success = await store.delete(sample_record.idempotency_key)
        assert success is True

        # Should not exist anymore
        record = await store.get(sample_record.idempotency_key)
        assert record is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store):
        """Should return False for deleting nonexistent record."""
        success = await store.delete("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, store):
        """Should cleanup expired records."""
        # Create expired record
        expired = IdempotencyRecord(
            idempotency_key="expired_key",
            operation="test",
            request_hash="hash",
            status="completed",
            response_code=200,
            response_body="{}",
            created_at=datetime.utcnow() - timedelta(hours=48),
            expires_at=datetime.utcnow() - timedelta(hours=24),
        )
        await store.create(expired)

        # Create valid record
        valid = IdempotencyRecord(
            idempotency_key="valid_key",
            operation="test",
            request_hash="hash",
            status="completed",
            response_code=200,
            response_body="{}",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        await store.create(valid)

        count = await store.cleanup_expired()

        assert count == 1
        assert await store.get("expired_key") is None
        assert await store.get("valid_key") is not None

    @pytest.mark.asyncio
    async def test_get_expired_returns_none(self, store):
        """Should return None for expired records."""
        expired = IdempotencyRecord(
            idempotency_key="auto_expire",
            operation="test",
            request_hash="hash",
            status="completed",
            response_code=200,
            response_body="{}",
            created_at=datetime.utcnow() - timedelta(hours=48),
            expires_at=datetime.utcnow() - timedelta(seconds=1),
        )
        store._records[expired.idempotency_key] = expired

        record = await store.get(expired.idempotency_key)
        assert record is None


class TestIdempotencyManager:
    """Tests for IdempotencyManager class."""

    @pytest.fixture
    def manager(self):
        """Create idempotency manager."""
        store = InMemoryIdempotencyStore()
        return IdempotencyManager(
            store=store,
            default_ttl_hours=24,
            lock_timeout_seconds=60,
        )

    @pytest.mark.asyncio
    async def test_execute_idempotent_first_time(self, manager):
        """Should execute operation on first request."""
        execute_count = 0

        async def operation():
            nonlocal execute_count
            execute_count += 1
            return {"result": "success"}

        result = await manager.execute_idempotent(
            idempotency_key="first_key",
            operation="test_op",
            request_data={"param": "value"},
            execute_fn=operation,
        )

        assert result == {"result": "success"}
        assert execute_count == 1

    @pytest.mark.asyncio
    async def test_execute_idempotent_replay(self, manager):
        """Should replay result for duplicate request."""
        execute_count = 0

        async def operation():
            nonlocal execute_count
            execute_count += 1
            return {"result": "success", "count": execute_count}

        # First execution
        result1 = await manager.execute_idempotent(
            idempotency_key="replay_key",
            operation="test_op",
            request_data={"param": "value"},
            execute_fn=operation,
        )

        # Second execution with same key
        result2 = await manager.execute_idempotent(
            idempotency_key="replay_key",
            operation="test_op",
            request_data={"param": "value"},
            execute_fn=operation,
        )

        # Should only execute once
        assert execute_count == 1
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_different_keys_execute_separately(self, manager):
        """Should execute separately for different keys."""
        execute_count = 0

        async def operation():
            nonlocal execute_count
            execute_count += 1
            return {"count": execute_count}

        result1 = await manager.execute_idempotent(
            idempotency_key="key_1",
            operation="test_op",
            request_data={},
            execute_fn=operation,
        )

        result2 = await manager.execute_idempotent(
            idempotency_key="key_2",
            operation="test_op",
            request_data={},
            execute_fn=operation,
        )

        assert execute_count == 2
        assert result1["count"] == 1
        assert result2["count"] == 2

    @pytest.mark.asyncio
    async def test_key_conflict_on_different_params(self, manager):
        """Should detect key conflict when params differ."""
        async def operation():
            return {"result": "success"}

        # First execution
        await manager.execute_idempotent(
            idempotency_key="conflict_key",
            operation="test_op",
            request_data={"param": "value1"},
            execute_fn=operation,
        )

        # Second execution with different params should conflict
        with pytest.raises(IdempotencyKeyConflict):
            await manager.execute_idempotent(
                idempotency_key="conflict_key",
                operation="test_op",
                request_data={"param": "value2"},  # Different!
                execute_fn=operation,
            )

    @pytest.mark.asyncio
    async def test_failed_operation_allows_retry(self, manager):
        """Should allow retry after failed operation."""
        call_count = 0

        async def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Temporary failure")
            return {"result": "success"}

        # First call fails
        try:
            await manager.execute_idempotent(
                idempotency_key="retry_key",
                operation="test_op",
                request_data={},
                execute_fn=failing_then_succeeding,
            )
        except ValueError:
            pass

        # Retry should succeed
        result = await manager.execute_idempotent(
            idempotency_key="retry_key",
            operation="test_op",
            request_data={},
            execute_fn=failing_then_succeeding,
        )

        assert result == {"result": "success"}


class TestIdempotencyConcurrency:
    """Concurrency tests for idempotency."""

    @pytest.mark.asyncio
    async def test_concurrent_same_key(self):
        """Should handle concurrent requests with same key."""
        store = InMemoryIdempotencyStore()
        manager = IdempotencyManager(store=store)

        execute_count = 0
        execute_lock = asyncio.Lock()

        async def slow_operation():
            nonlocal execute_count
            async with execute_lock:
                execute_count += 1
            await asyncio.sleep(0.1)
            return {"result": "done"}

        # Start multiple concurrent requests
        tasks = [
            manager.execute_idempotent(
                idempotency_key="concurrent_key",
                operation="test",
                request_data={},
                execute_fn=slow_operation,
            )
            for _ in range(5)
        ]

        # Note: Some may fail with IdempotencyOperationInProgress
        # depending on implementation
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one should succeed
        successes = [r for r in results if not isinstance(r, Exception)]
        assert len(successes) >= 1


class TestIdempotencyEdgeCases:
    """Edge case tests for idempotency."""

    @pytest.mark.asyncio
    async def test_empty_request_data(self):
        """Should handle empty request data."""
        store = InMemoryIdempotencyStore()
        manager = IdempotencyManager(store=store)

        result = await manager.execute_idempotent(
            idempotency_key="empty_data",
            operation="test",
            request_data={},
            execute_fn=lambda: {"result": "ok"},
        )

        assert result["result"] == "ok"

    @pytest.mark.asyncio
    async def test_none_result(self):
        """Should handle None result from operation."""
        store = InMemoryIdempotencyStore()
        manager = IdempotencyManager(store=store)

        result = await manager.execute_idempotent(
            idempotency_key="none_result",
            operation="test",
            request_data={},
            execute_fn=lambda: None,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_complex_result(self):
        """Should handle complex result objects."""
        store = InMemoryIdempotencyStore()
        manager = IdempotencyManager(store=store)

        complex_result = {
            "id": "123",
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "decimal": "100.50",
        }

        result = await manager.execute_idempotent(
            idempotency_key="complex_result",
            operation="test",
            request_data={},
            execute_fn=lambda: complex_result,
        )

        assert result == complex_result
