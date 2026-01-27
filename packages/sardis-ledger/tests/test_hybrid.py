"""
Tests for hybrid ledger (PostgreSQL + immudb).

These tests require a running immudb instance.
Start with: docker-compose -f docker-compose.immudb.yml up -d

Run with: pytest tests/test_hybrid.py -v
"""
import asyncio
from decimal import Decimal
import pytest

# Skip all tests if immudb-py is not installed
pytest.importorskip("immudb")

from sardis_ledger.hybrid import (
    HybridConfig,
    HybridLedger,
    HybridReceipt,
    ConsistencyReport,
    create_hybrid_ledger,
)
from sardis_ledger.models import LedgerEntryType
from sardis_ledger.immutable import VerificationStatus


pytestmark = pytest.mark.immudb


@pytest.fixture
def config():
    """Test configuration."""
    return HybridConfig(
        enable_postgresql=True,
        enable_immudb=True,
        immudb_host="localhost",
        immudb_port=3322,
        immudb_user="immudb",
        immudb_password="immudb",
        immudb_database="sardis_hybrid_test",
        require_dual_write=True,
        async_immudb_write=False,
    )


@pytest.fixture
async def hybrid_ledger(config):
    """Connected hybrid ledger instance."""
    ledger = HybridLedger(config)
    try:
        await ledger.connect()
        yield ledger
    finally:
        await ledger.disconnect()


@pytest.mark.asyncio
class TestHybridLedger:
    """Integration tests for HybridLedger."""

    async def test_connect_disconnect(self, config):
        """Test connection lifecycle."""
        ledger = HybridLedger(config)

        await ledger.connect()
        assert ledger._connected
        assert ledger._pg_engine is not None
        assert ledger._immudb_trail is not None

        await ledger.disconnect()
        assert not ledger._connected

    async def test_create_entry(self, hybrid_ledger):
        """Test creating an entry in both stores."""
        receipt = await hybrid_ledger.create_entry(
            account_id="acc_hybrid_test",
            amount=Decimal("100.00"),
            entry_type=LedgerEntryType.CREDIT,
            currency="USDC",
            actor_id="test_user",
        )

        assert isinstance(receipt, HybridReceipt)
        assert receipt.entry_id
        assert receipt.pg_entry_id
        assert receipt.consistent
        assert receipt.immudb_receipt is not None
        assert receipt.immudb_receipt.merkle_proof is not None

    async def test_create_entry_with_chain_data(self, hybrid_ledger):
        """Test creating an entry with on-chain data."""
        receipt = await hybrid_ledger.create_entry(
            account_id="acc_chain_test",
            amount=Decimal("250.50"),
            entry_type=LedgerEntryType.CREDIT,
            currency="USDC",
            chain="base",
            chain_tx_hash="0x123abc456def",
            block_number=12345678,
            actor_id="test_user",
        )

        assert receipt.consistent

        # Verify entry was stored correctly
        pg_entry = hybrid_ledger._pg_engine.get_entry(receipt.pg_entry_id)
        assert pg_entry is not None
        assert pg_entry.chain == "base"
        assert pg_entry.chain_tx_hash == "0x123abc456def"

    async def test_verify_entry(self, hybrid_ledger):
        """Test verifying an entry across both stores."""
        # Create entry
        receipt = await hybrid_ledger.create_entry(
            account_id="acc_verify_test",
            amount=Decimal("75.00"),
            entry_type=LedgerEntryType.DEBIT,
            currency="USDC",
            actor_id="test_user",
        )

        # Verify
        result = await hybrid_ledger.verify_entry(receipt.entry_id)

        assert result.status == VerificationStatus.VERIFIED
        assert result.immudb_verified
        assert result.merkle_verified

    async def test_get_balance(self, hybrid_ledger):
        """Test getting balance from PostgreSQL."""
        account = "acc_balance_test"

        # Create some entries
        await hybrid_ledger.create_entry(
            account_id=account,
            amount=Decimal("1000.00"),
            entry_type=LedgerEntryType.CREDIT,
            actor_id="test",
        )
        await hybrid_ledger.create_entry(
            account_id=account,
            amount=Decimal("250.00"),
            entry_type=LedgerEntryType.DEBIT,
            actor_id="test",
        )

        balance = hybrid_ledger.get_balance(account)
        assert balance == Decimal("750.000000000000000000")

    async def test_get_entries(self, hybrid_ledger):
        """Test getting entries from PostgreSQL."""
        account = "acc_entries_test"

        # Create entries
        for i in range(5):
            await hybrid_ledger.create_entry(
                account_id=account,
                amount=Decimal(f"{(i + 1) * 10}.00"),
                entry_type=LedgerEntryType.CREDIT,
                actor_id="test",
            )

        entries = hybrid_ledger.get_entries(account, limit=10)
        assert len(entries) >= 5

    async def test_get_audit_proof(self, hybrid_ledger):
        """Test generating comprehensive audit proof."""
        receipt = await hybrid_ledger.create_entry(
            account_id="acc_proof_test",
            amount=Decimal("500.00"),
            entry_type=LedgerEntryType.CREDIT,
            currency="USDC",
            actor_id="test_user",
        )

        proof = await hybrid_ledger.get_audit_proof(receipt.entry_id)

        assert proof["version"] == "1.0"
        assert "stores" in proof
        assert "postgresql" in proof["stores"]
        assert "immudb" in proof["stores"]
        assert "consistency" in proof

    async def test_check_consistency(self, hybrid_ledger):
        """Test consistency checking between stores."""
        # Create some entries
        for i in range(10):
            await hybrid_ledger.create_entry(
                account_id=f"acc_consistency_{i}",
                amount=Decimal("100.00"),
                entry_type=LedgerEntryType.CREDIT,
                actor_id="test",
            )

        report = await hybrid_ledger.check_consistency(sample_size=5)

        assert isinstance(report, ConsistencyReport)
        assert report.total_checked <= 10
        assert report.is_consistent

    async def test_health_check(self, hybrid_ledger):
        """Test health check."""
        health = await hybrid_ledger.health_check()

        assert health["status"] == "healthy"
        assert "stores" in health
        assert "postgresql" in health["stores"]
        assert "immudb" in health["stores"]


@pytest.mark.asyncio
class TestHybridLedgerPGOnly:
    """Tests with only PostgreSQL enabled."""

    async def test_pg_only_mode(self):
        """Test running with only PostgreSQL."""
        config = HybridConfig(
            enable_postgresql=True,
            enable_immudb=False,
            require_dual_write=False,
        )
        ledger = HybridLedger(config)

        await ledger.connect()

        receipt = await ledger.create_entry(
            account_id="acc_pg_only",
            amount=Decimal("100.00"),
            entry_type=LedgerEntryType.CREDIT,
            actor_id="test",
        )

        assert receipt.pg_entry_id
        assert receipt.immudb_receipt is None

        await ledger.disconnect()


@pytest.mark.asyncio
class TestCreateHybridLedger:
    """Test factory function."""

    async def test_create_with_defaults(self):
        """Test creating hybrid ledger with defaults."""
        ledger = create_hybrid_ledger()

        assert ledger.config.immudb_host == "localhost"
        assert ledger.config.enable_postgresql
        assert ledger.config.enable_immudb

    async def test_create_with_anchoring(self):
        """Test creating hybrid ledger with anchoring."""
        ledger = create_hybrid_ledger(
            enable_anchoring=True,
            anchor_chain="base",
        )

        assert ledger.config.enable_anchoring
        assert ledger.config.anchor_chain == "base"
