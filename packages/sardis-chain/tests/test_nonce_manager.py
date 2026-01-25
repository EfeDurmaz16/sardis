"""
Comprehensive tests for sardis_chain.nonce_manager module.

Tests cover:
- NonceManager initialization and configuration
- Nonce acquisition and reservation
- Pending transaction tracking
- Stuck transaction detection
- Transaction receipt verification
- Nonce release and recovery
- Concurrent access handling
- Error cases (conflicts, timeouts)
"""
from __future__ import annotations

import asyncio
import pytest
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from dataclasses import dataclass

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_chain.nonce_manager import (
    NonceManager,
    TransactionReceiptStatus,
    ReceiptValidation,
    PendingTransaction,
    NonceConflictError,
    StuckTransactionError,
    TransactionFailedError,
    get_nonce_manager,
)
from sardis_chain.config import NonceManagerConfig, get_config


class TestTransactionReceiptStatus:
    """Tests for TransactionReceiptStatus enum."""

    def test_status_values(self):
        """Should have correct status values."""
        assert TransactionReceiptStatus.SUCCESS.value == "success"
        assert TransactionReceiptStatus.FAILED.value == "failed"
        assert TransactionReceiptStatus.PENDING.value == "pending"
        assert TransactionReceiptStatus.NOT_FOUND.value == "not_found"
        assert TransactionReceiptStatus.REPLACED.value == "replaced"


class TestReceiptValidation:
    """Tests for ReceiptValidation class."""

    def test_successful_validation(self):
        """Should create successful validation result."""
        validation = ReceiptValidation(
            status=TransactionReceiptStatus.SUCCESS,
            tx_hash="0x123",
            block_number=12345,
            gas_used=21000,
            effective_gas_price=50_000_000_000,
        )

        assert validation.is_successful is True
        assert validation.is_final is True

    def test_failed_validation(self):
        """Should create failed validation result."""
        validation = ReceiptValidation(
            status=TransactionReceiptStatus.FAILED,
            tx_hash="0x456",
            revert_reason="execution reverted",
        )

        assert validation.is_successful is False
        assert validation.is_final is True

    def test_pending_validation(self):
        """Should create pending validation result."""
        validation = ReceiptValidation(
            status=TransactionReceiptStatus.PENDING,
            tx_hash="0x789",
        )

        assert validation.is_successful is False
        assert validation.is_final is False


class TestPendingTransaction:
    """Tests for PendingTransaction class."""

    def test_create_pending_transaction(self):
        """Should create pending transaction."""
        pending = PendingTransaction(
            tx_hash="0xabc",
            nonce=5,
            address="0x1234567890123456789012345678901234567890",
            chain="ethereum",
            submitted_at=datetime.now(timezone.utc),
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash123",
        )

        assert pending.tx_hash == "0xabc"
        assert pending.nonce == 5
        assert pending.check_count == 0

    def test_is_stuck_within_timeout(self):
        """Should not be stuck within timeout."""
        pending = PendingTransaction(
            tx_hash="0xdef",
            nonce=10,
            address="0x1234567890123456789012345678901234567890",
            chain="ethereum",
            submitted_at=datetime.now(timezone.utc),
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash456",
        )

        assert pending.is_stuck(timeout_seconds=300) is False

    def test_is_stuck_after_timeout(self):
        """Should be stuck after timeout."""
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        pending = PendingTransaction(
            tx_hash="0xghi",
            nonce=15,
            address="0x1234567890123456789012345678901234567890",
            chain="ethereum",
            submitted_at=old_time,
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash789",
        )

        assert pending.is_stuck(timeout_seconds=300) is True  # 5 min timeout


class TestNonceManager:
    """Tests for NonceManager class."""

    @pytest.fixture
    def manager(self):
        """Create NonceManager instance."""
        config = NonceManagerConfig(
            cache_ttl_seconds=60,
            stuck_tx_timeout_seconds=120,
            replacement_gas_bump_percent=10,
        )
        return NonceManager(config)

    @pytest.fixture
    def mock_rpc_client(self):
        """Create mock RPC client."""
        client = AsyncMock()
        client.get_nonce = AsyncMock(return_value=0)
        client.get_transaction_receipt = AsyncMock(return_value=None)
        client.get_transaction = AsyncMock(return_value=None)
        client.get_block_number = AsyncMock(return_value=12345)
        client.get_gas_price = AsyncMock(return_value=50_000_000_000)
        client.get_max_priority_fee = AsyncMock(return_value=2_000_000_000)
        return client

    @pytest.mark.asyncio
    async def test_get_nonce_first_call(self, manager, mock_rpc_client):
        """Should fetch nonce from RPC on first call."""
        mock_rpc_client.get_nonce.return_value = 5

        nonce = await manager.get_nonce(
            "0x1234567890123456789012345678901234567890",
            mock_rpc_client
        )

        assert nonce == 5
        mock_rpc_client.get_nonce.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_nonce_cached(self, manager, mock_rpc_client):
        """Should use cached nonce on subsequent calls."""
        mock_rpc_client.get_nonce.return_value = 5
        address = "0x1234567890123456789012345678901234567890"

        # First call
        await manager.get_nonce(address, mock_rpc_client)
        # Second call
        await manager.get_nonce(address, mock_rpc_client)

        # Should only call RPC once (cached)
        assert mock_rpc_client.get_nonce.call_count == 1

    @pytest.mark.asyncio
    async def test_get_nonce_force_refresh(self, manager, mock_rpc_client):
        """Should refresh from RPC when forced."""
        mock_rpc_client.get_nonce.return_value = 5
        address = "0x1234567890123456789012345678901234567890"

        await manager.get_nonce(address, mock_rpc_client)
        mock_rpc_client.get_nonce.return_value = 10

        nonce = await manager.get_nonce(address, mock_rpc_client, force_refresh=True)

        assert nonce == 10
        assert mock_rpc_client.get_nonce.call_count == 2

    @pytest.mark.asyncio
    async def test_reserve_nonce(self, manager, mock_rpc_client):
        """Should reserve and increment nonce."""
        mock_rpc_client.get_nonce.return_value = 5
        address = "0x1234567890123456789012345678901234567890"

        nonce1 = await manager.reserve_nonce(address, mock_rpc_client)
        nonce2 = await manager.reserve_nonce(address, mock_rpc_client)

        assert nonce1 == 5
        assert nonce2 == 6

    @pytest.mark.asyncio
    async def test_reserve_nonce_conflict(self, manager, mock_rpc_client):
        """Should raise conflict if nonce already used."""
        mock_rpc_client.get_nonce.return_value = 5
        address = "0x1234567890123456789012345678901234567890"

        # Reserve nonce 5
        await manager.reserve_nonce(address, mock_rpc_client)

        # Register a pending transaction for nonce 5
        manager.register_pending_transaction(
            tx_hash="0xexisting",
            address=address,
            nonce=5,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash",
        )

        # Reset cached nonce to try to get 5 again
        manager._nonces[address.lower()] = 5

        # Should raise conflict
        with pytest.raises(NonceConflictError) as exc_info:
            await manager.reserve_nonce(address, mock_rpc_client)

        assert exc_info.value.nonce == 5

    def test_register_pending_transaction(self, manager):
        """Should register pending transaction."""
        address = "0x1234567890123456789012345678901234567890"

        manager.register_pending_transaction(
            tx_hash="0xtx123",
            address=address,
            nonce=10,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash123",
        )

        assert "0xtx123" in manager._pending_txs
        assert manager.get_pending_count(address) == 1

    @pytest.mark.asyncio
    async def test_verify_receipt_success(self, manager, mock_rpc_client):
        """Should verify successful receipt."""
        mock_rpc_client.get_transaction_receipt.return_value = {
            "status": "0x1",
            "blockNumber": "0x1234",
            "gasUsed": "0x5208",
            "effectiveGasPrice": "0xba43b7400",
            "logs": [],
        }

        validation = await manager.verify_receipt("0xtx456", mock_rpc_client)

        assert validation.status == TransactionReceiptStatus.SUCCESS
        assert validation.is_successful is True
        assert validation.block_number == 0x1234

    @pytest.mark.asyncio
    async def test_verify_receipt_failed(self, manager, mock_rpc_client):
        """Should verify failed receipt."""
        mock_rpc_client.get_transaction_receipt.return_value = {
            "status": "0x0",
            "blockNumber": "0x1234",
            "gasUsed": "0x5208",
            "effectiveGasPrice": "0xba43b7400",
            "logs": [],
        }
        mock_rpc_client.get_transaction.return_value = {
            "from": "0x123",
            "to": "0x456",
            "input": "0x",
            "value": "0x0",
            "gas": "0x5208",
            "blockNumber": "0x1234",
        }
        mock_rpc_client.eth_call = AsyncMock(side_effect=Exception("execution reverted"))

        validation = await manager.verify_receipt("0xtx789", mock_rpc_client)

        assert validation.status == TransactionReceiptStatus.FAILED
        assert validation.is_successful is False

    @pytest.mark.asyncio
    async def test_verify_receipt_pending(self, manager, mock_rpc_client):
        """Should handle pending (no receipt) case."""
        mock_rpc_client.get_transaction_receipt.return_value = None

        validation = await manager.verify_receipt("0xtxpending", mock_rpc_client)

        assert validation.status == TransactionReceiptStatus.PENDING

    @pytest.mark.asyncio
    async def test_wait_for_receipt_success(self, manager, mock_rpc_client):
        """Should wait for and return receipt."""
        call_count = 0

        async def mock_get_receipt(tx_hash):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return None  # Pending
            return {
                "status": "0x1",
                "blockNumber": "0x1234",
                "gasUsed": "0x5208",
                "effectiveGasPrice": "0xba43b7400",
                "logs": [],
            }

        mock_rpc_client.get_transaction_receipt = mock_get_receipt

        validation = await manager.wait_for_receipt(
            "0xtxwait",
            mock_rpc_client,
            timeout_seconds=10,
            poll_interval=0.1,
        )

        assert validation.is_successful is True
        assert call_count >= 3

    @pytest.mark.asyncio
    async def test_wait_for_receipt_timeout(self, manager, mock_rpc_client):
        """Should raise timeout error."""
        mock_rpc_client.get_transaction_receipt.return_value = None  # Always pending

        with pytest.raises(TimeoutError):
            await manager.wait_for_receipt(
                "0xtxtimeout",
                mock_rpc_client,
                timeout_seconds=0.5,
                poll_interval=0.1,
            )

    @pytest.mark.asyncio
    async def test_wait_for_receipt_failed_tx(self, manager, mock_rpc_client):
        """Should raise TransactionFailedError for failed tx."""
        mock_rpc_client.get_transaction_receipt.return_value = {
            "status": "0x0",
            "blockNumber": "0x1234",
            "gasUsed": "0x5208",
            "logs": [],
        }
        mock_rpc_client.get_transaction.return_value = None

        with pytest.raises(TransactionFailedError) as exc_info:
            await manager.wait_for_receipt(
                "0xtxfailed",
                mock_rpc_client,
                timeout_seconds=10,
                poll_interval=0.1,
            )

        assert exc_info.value.tx_hash == "0xtxfailed"

    @pytest.mark.asyncio
    async def test_get_stuck_transactions(self, manager):
        """Should return stuck transactions."""
        address = "0x1234567890123456789012345678901234567890"
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Register old pending transaction
        manager._pending_txs["0xstuck"] = PendingTransaction(
            tx_hash="0xstuck",
            nonce=5,
            address=address.lower(),
            chain="ethereum",
            submitted_at=old_time,
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash",
        )
        manager._address_pending[address.lower()] = {"0xstuck"}

        stuck = await manager.get_stuck_transactions()

        assert len(stuck) == 1
        assert stuck[0].tx_hash == "0xstuck"

    @pytest.mark.asyncio
    async def test_calculate_replacement_gas(self, manager, mock_rpc_client):
        """Should calculate bumped gas prices."""
        original = PendingTransaction(
            tx_hash="0xoriginal",
            nonce=5,
            address="0x123",
            chain="ethereum",
            submitted_at=datetime.now(timezone.utc),
            gas_price=50_000_000_000,  # 50 gwei
            priority_fee=2_000_000_000,  # 2 gwei
            data_hash="hash",
        )

        mock_rpc_client.get_gas_price.return_value = 40_000_000_000
        mock_rpc_client.get_max_priority_fee.return_value = 1_500_000_000

        max_fee, priority_fee = await manager.calculate_replacement_gas(
            original, mock_rpc_client
        )

        # Should be at least 10% higher
        assert max_fee >= original.gas_price * 1.1
        assert priority_fee >= original.priority_fee * 1.1

    @pytest.mark.asyncio
    async def test_release_nonce(self, manager, mock_rpc_client):
        """Should release reserved nonce."""
        address = "0x1234567890123456789012345678901234567890"
        mock_rpc_client.get_nonce.return_value = 5

        # Reserve and register
        nonce = await manager.reserve_nonce(address, mock_rpc_client)
        manager.register_pending_transaction(
            tx_hash="0xtx",
            address=address,
            nonce=nonce,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash",
        )

        # Release
        await manager.release_nonce(address, nonce)

        # Nonce cache should be cleared
        assert address.lower() not in manager._nonces
        assert "0xtx" not in manager._pending_txs

    @pytest.mark.asyncio
    async def test_sync_with_chain(self, manager, mock_rpc_client):
        """Should sync nonce with chain."""
        address = "0x1234567890123456789012345678901234567890"
        mock_rpc_client.get_nonce.return_value = 100

        nonce = await manager.sync_with_chain(address, mock_rpc_client)

        assert nonce == 100

    def test_get_pending_count(self, manager):
        """Should return correct pending count."""
        address = "0x1234567890123456789012345678901234567890"

        assert manager.get_pending_count(address) == 0

        manager.register_pending_transaction(
            tx_hash="0xtx1",
            address=address,
            nonce=1,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash1",
        )
        manager.register_pending_transaction(
            tx_hash="0xtx2",
            address=address,
            nonce=2,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash2",
        )

        assert manager.get_pending_count(address) == 2

    def test_get_all_pending(self, manager):
        """Should return all pending transactions."""
        manager.register_pending_transaction(
            tx_hash="0xtx1",
            address="0xaddr1",
            nonce=1,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash1",
        )
        manager.register_pending_transaction(
            tx_hash="0xtx2",
            address="0xaddr2",
            nonce=2,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash2",
        )

        all_pending = manager.get_all_pending()
        assert len(all_pending) == 2

        # Filter by address
        addr1_pending = manager.get_all_pending("0xaddr1")
        assert len(addr1_pending) == 1

    def test_clear_pending(self, manager):
        """Should clear pending transactions."""
        address = "0x1234567890123456789012345678901234567890"

        manager.register_pending_transaction(
            tx_hash="0xtx1",
            address=address,
            nonce=1,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash1",
        )

        count = manager.clear_pending(address)

        assert count == 1
        assert manager.get_pending_count(address) == 0

    def test_clear_all_pending(self, manager):
        """Should clear all pending transactions."""
        manager.register_pending_transaction(
            tx_hash="0xtx1",
            address="0xaddr1",
            nonce=1,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash1",
        )
        manager.register_pending_transaction(
            tx_hash="0xtx2",
            address="0xaddr2",
            nonce=2,
            chain="ethereum",
            gas_price=50_000_000_000,
            priority_fee=2_000_000_000,
            data_hash="hash2",
        )

        count = manager.clear_pending()  # Clear all

        assert count == 2


class TestNonceManagerConcurrency:
    """Concurrency tests for NonceManager."""

    @pytest.mark.asyncio
    async def test_concurrent_nonce_reservation(self):
        """Should handle concurrent nonce reservations."""
        manager = NonceManager()
        address = "0x1234567890123456789012345678901234567890"

        mock_rpc = AsyncMock()
        mock_rpc.get_nonce = AsyncMock(return_value=0)

        # Concurrent reservations
        async def reserve():
            return await manager.reserve_nonce(address, mock_rpc)

        results = await asyncio.gather(*[reserve() for _ in range(10)])

        # All nonces should be unique
        assert len(set(results)) == 10
        assert sorted(results) == list(range(10))


class TestGetNonceManager:
    """Tests for get_nonce_manager function."""

    def test_returns_singleton(self):
        """Should return same instance."""
        # Reset global
        import sardis_chain.nonce_manager as nm_module
        nm_module._nonce_manager = None

        manager1 = get_nonce_manager()
        manager2 = get_nonce_manager()

        assert manager1 is manager2


class TestNonceConflictError:
    """Tests for NonceConflictError exception."""

    def test_error_message(self):
        """Should have descriptive error message."""
        error = NonceConflictError(
            address="0x123",
            nonce=5,
            existing_tx="0xexisting",
        )

        assert "nonce" in str(error).lower() or "5" in str(error)
        assert error.nonce == 5
        assert error.existing_tx == "0xexisting"


class TestTransactionFailedError:
    """Tests for TransactionFailedError exception."""

    def test_error_with_revert_reason(self):
        """Should include revert reason."""
        error = TransactionFailedError(
            tx_hash="0xfailed",
            revert_reason="execution reverted: insufficient balance",
        )

        assert "0xfailed" in str(error)
        assert "insufficient balance" in str(error)

    def test_error_without_revert_reason(self):
        """Should work without revert reason."""
        error = TransactionFailedError(tx_hash="0xfailed2")

        assert "0xfailed2" in str(error)
