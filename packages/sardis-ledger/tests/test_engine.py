"""
Comprehensive tests for sardis_ledger.engine module.

Tests cover:
- LockManager for row-level locking
- LedgerError exceptions hierarchy
- Batch transaction processing
- Optimistic concurrency control
- Transaction rollback
"""
from __future__ import annotations

import asyncio
import pytest
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_ledger.engine import (
    LedgerError,
    LockAcquisitionError,
    LockTimeoutError,
    ConcurrencyError,
    InsufficientBalanceError,
    BatchProcessingError,
    RollbackError,
    ValidationError,
    LockManager,
)


class TestLedgerError:
    """Tests for LedgerError base class."""

    def test_create_error(self):
        """Should create error with message and code."""
        error = LedgerError(
            message="Something went wrong",
            code="CUSTOM_ERROR",
            details={"field": "value"},
        )

        assert str(error) == "Something went wrong"
        assert error.code == "CUSTOM_ERROR"
        assert error.details["field"] == "value"
        assert error.timestamp is not None

    def test_to_dict(self):
        """Should convert to dictionary."""
        error = LedgerError("Test error", code="TEST")
        result = error.to_dict()

        assert result["error"] == "TEST"
        assert result["message"] == "Test error"
        assert "timestamp" in result


class TestLockAcquisitionError:
    """Tests for LockAcquisitionError."""

    def test_error_with_holder(self):
        """Should include current holder info."""
        error = LockAcquisitionError(
            resource_type="account",
            resource_id="acc_123",
            holder_id="tx_456",
        )

        assert "account" in str(error)
        assert "acc_123" in str(error)
        assert error.code == "LOCK_ACQUISITION_FAILED"
        assert error.details["current_holder"] == "tx_456"

    def test_error_without_holder(self):
        """Should work without holder info."""
        error = LockAcquisitionError(
            resource_type="entry",
            resource_id="entry_789",
        )

        assert "entry" in str(error)


class TestLockTimeoutError:
    """Tests for LockTimeoutError."""

    def test_timeout_error(self):
        """Should include timeout information."""
        error = LockTimeoutError(
            resource_type="account",
            resource_id="acc_123",
            timeout=30.0,
        )

        assert "30" in str(error) or "30.0" in str(error)
        assert error.details["timeout"] == 30.0


class TestConcurrencyError:
    """Tests for ConcurrencyError."""

    def test_concurrency_error(self):
        """Should include version information."""
        error = ConcurrencyError(
            entity_id="entity_123",
            expected_version=5,
            actual_version=7,
        )

        assert "5" in str(error)
        assert "7" in str(error)
        assert error.details["expected_version"] == 5
        assert error.details["actual_version"] == 7


class TestInsufficientBalanceError:
    """Tests for InsufficientBalanceError."""

    def test_balance_error(self):
        """Should include balance information."""
        error = InsufficientBalanceError(
            account_id="acc_123",
            required=Decimal("100"),
            available=Decimal("50"),
        )

        assert "100" in str(error)
        assert "50" in str(error)
        assert error.details["required"] == "100"
        assert error.details["available"] == "50"


class TestBatchProcessingError:
    """Tests for BatchProcessingError."""

    def test_batch_error(self):
        """Should include batch information."""
        cause = ValueError("Invalid entry")
        error = BatchProcessingError(
            batch_id="batch_123",
            failed_index=5,
            cause=cause,
        )

        assert "batch_123" in str(error)
        assert "5" in str(error)
        assert error.details["failed_index"] == 5


class TestRollbackError:
    """Tests for RollbackError."""

    def test_rollback_error(self):
        """Should include rollback information."""
        error = RollbackError(
            tx_id="tx_123",
            reason="State already committed",
        )

        assert "tx_123" in str(error)
        assert error.details["reason"] == "State already committed"


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error(self):
        """Should include validation information."""
        error = ValidationError(
            field="amount",
            value=-100,
            reason="Must be positive",
        )

        assert "amount" in str(error)
        assert error.details["value"] == "-100"


class TestLockManager:
    """Tests for LockManager class."""

    @pytest.fixture
    def lock_manager(self):
        """Create LockManager instance."""
        return LockManager()

    def test_acquire_lock(self, lock_manager):
        """Should acquire lock successfully."""
        lock = lock_manager.acquire(
            resource_type="account",
            resource_id="acc_123",
            holder_id="tx_456",
        )

        assert lock is not None
        assert lock.is_active()

    def test_acquire_lock_already_held(self, lock_manager):
        """Should raise error if lock already held."""
        # First acquisition
        lock_manager.acquire(
            resource_type="account",
            resource_id="acc_123",
            holder_id="tx_456",
        )

        # Second acquisition by different holder should fail
        with pytest.raises(LockAcquisitionError):
            lock_manager.acquire(
                resource_type="account",
                resource_id="acc_123",
                holder_id="tx_789",
                timeout=0.1,
            )

    def test_release_lock(self, lock_manager):
        """Should release lock."""
        lock = lock_manager.acquire(
            resource_type="account",
            resource_id="acc_123",
            holder_id="tx_456",
        )

        # Release the lock
        lock_manager.release(
            resource_type="account",
            resource_id="acc_123",
            holder_id="tx_456",
        )

        # Now another holder can acquire
        new_lock = lock_manager.acquire(
            resource_type="account",
            resource_id="acc_123",
            holder_id="tx_999",
        )

        assert new_lock is not None

    def test_same_holder_can_reacquire(self, lock_manager):
        """Same holder should be able to reacquire."""
        lock_manager.acquire(
            resource_type="account",
            resource_id="acc_123",
            holder_id="tx_456",
        )

        # Same holder can acquire again (reentrant)
        lock2 = lock_manager.acquire(
            resource_type="account",
            resource_id="acc_123",
            holder_id="tx_456",
        )

        assert lock2 is not None

    def test_cleanup_expired_locks(self, lock_manager):
        """Should cleanup expired locks."""
        # Set short expiry
        lock_manager.lock_expiry = timedelta(milliseconds=100)

        lock_manager.acquire(
            resource_type="account",
            resource_id="acc_expired",
            holder_id="tx_old",
        )

        # Wait for expiry
        time.sleep(0.15)

        # Force cleanup
        lock_manager._last_cleanup = datetime.now(timezone.utc) - timedelta(minutes=5)
        count = lock_manager._cleanup_expired()

        assert count >= 1

    def test_multiple_resources(self, lock_manager):
        """Should handle multiple resources."""
        lock1 = lock_manager.acquire("account", "acc_1", "holder_1")
        lock2 = lock_manager.acquire("account", "acc_2", "holder_1")
        lock3 = lock_manager.acquire("entry", "entry_1", "holder_1")

        assert lock1 is not None
        assert lock2 is not None
        assert lock3 is not None


class TestLockManagerConcurrency:
    """Concurrency tests for LockManager."""

    def test_concurrent_lock_acquisition(self):
        """Should handle concurrent lock requests."""
        manager = LockManager()
        results = []
        errors = []

        def try_acquire(holder_id):
            try:
                lock = manager.acquire(
                    resource_type="account",
                    resource_id="contested_resource",
                    holder_id=holder_id,
                    timeout=0.5,
                )
                results.append(holder_id)
            except LockAcquisitionError:
                errors.append(holder_id)

        threads = [
            threading.Thread(target=try_acquire, args=(f"holder_{i}",))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should succeed
        assert len(results) == 1
        assert len(errors) == 4


class TestLedgerEngineIntegration:
    """Integration tests for ledger engine."""

    def test_error_hierarchy(self):
        """All specific errors should be LedgerError subclasses."""
        errors = [
            LockAcquisitionError("type", "id"),
            LockTimeoutError("type", "id", 10.0),
            ConcurrencyError("id", 1, 2),
            InsufficientBalanceError("acc", Decimal("100"), Decimal("50")),
            BatchProcessingError("batch", 0, ValueError("test")),
            RollbackError("tx", "reason"),
            ValidationError("field", "value", "reason"),
        ]

        for error in errors:
            assert isinstance(error, LedgerError)
            assert hasattr(error, "code")
            assert hasattr(error, "to_dict")


class TestLedgerEdgeCases:
    """Edge case tests for ledger functionality."""

    def test_empty_resource_id(self):
        """Should handle empty resource ID."""
        manager = LockManager()

        lock = manager.acquire(
            resource_type="account",
            resource_id="",
            holder_id="holder",
        )

        assert lock is not None

    def test_special_characters_in_ids(self):
        """Should handle special characters."""
        manager = LockManager()

        lock = manager.acquire(
            resource_type="account",
            resource_id="acc_123/path?query=value",
            holder_id="holder-with-dashes",
        )

        assert lock is not None

    def test_lock_manager_key_generation(self):
        """Should generate unique keys."""
        manager = LockManager()

        key1 = manager._make_key("type1", "id1")
        key2 = manager._make_key("type2", "id1")
        key3 = manager._make_key("type1", "id2")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
