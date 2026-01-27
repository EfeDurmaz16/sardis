"""
Tests for immutable audit trail using immudb.

These tests require a running immudb instance.
Start with: docker-compose -f docker-compose.immudb.yml up -d

Run with: pytest tests/test_immutable.py -v
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import pytest

# Skip all tests if immudb-py is not installed
pytest.importorskip("immudb")

from sardis_ledger.immutable import (
    AuditEntry,
    ImmutableAuditTrail,
    ImmutableConfig,
    ImmutableReceipt,
    MerkleProof,
    VerificationResult,
    VerificationStatus,
    create_audit_trail,
)
from sardis_ledger.models import LedgerEntry, LedgerEntryType


# Mark all tests as requiring immudb
pytestmark = pytest.mark.immudb


@pytest.fixture
def config():
    """Test configuration."""
    return ImmutableConfig(
        immudb_host="localhost",
        immudb_port=3322,
        immudb_user="immudb",
        immudb_password="immudb",
        immudb_database="sardis_test",
    )


@pytest.fixture
async def audit_trail(config):
    """Connected audit trail instance."""
    trail = ImmutableAuditTrail(config)
    try:
        await trail.connect()
        yield trail
    finally:
        await trail.disconnect()


class TestAuditEntry:
    """Tests for AuditEntry model."""

    def test_create_entry(self):
        """Test creating an audit entry."""
        entry = AuditEntry(
            tx_id="tx_123",
            account_id="acc_456",
            entry_type="credit",
            amount="100.50",
            currency="USDC",
        )

        assert entry.entry_id.startswith("iae_")
        assert entry.tx_id == "tx_123"
        assert entry.amount == "100.50"

    def test_compute_hash(self):
        """Test hash computation is deterministic."""
        entry = AuditEntry(
            entry_id="iae_test123",
            tx_id="tx_123",
            account_id="acc_456",
            entry_type="credit",
            amount="100.50",
            currency="USDC",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        hash1 = entry.compute_hash()
        hash2 = entry.compute_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_to_json_from_json(self):
        """Test JSON serialization round-trip."""
        original = AuditEntry(
            tx_id="tx_123",
            account_id="acc_456",
            entry_type="credit",
            amount="100.50",
            currency="USDC",
            chain="base",
            chain_tx_hash="0x123abc",
        )
        original.entry_hash = original.compute_hash()

        json_str = original.to_json()
        restored = AuditEntry.from_json(json_str)

        assert restored.tx_id == original.tx_id
        assert restored.amount == original.amount
        assert restored.chain_tx_hash == original.chain_tx_hash
        assert restored.entry_hash == original.entry_hash

    def test_from_ledger_entry(self):
        """Test creating audit entry from LedgerEntry."""
        ledger_entry = LedgerEntry(
            tx_id="tx_789",
            account_id="acc_123",
            entry_type=LedgerEntryType.CREDIT,
            amount=Decimal("250.00"),
            fee=Decimal("0.50"),
            currency="USDC",
            chain="base",
            chain_tx_hash="0xdef456",
        )

        audit_entry = AuditEntry.from_ledger_entry(
            ledger_entry,
            actor_id="user_001",
            request_id="req_abc",
        )

        assert audit_entry.ledger_entry_id == ledger_entry.entry_id
        assert audit_entry.amount == "250.000000000000000000"
        assert audit_entry.entry_type == "credit"
        assert audit_entry.actor_id == "user_001"
        assert audit_entry.entry_hash is not None


class TestMerkleProof:
    """Tests for MerkleProof model."""

    def test_create_proof(self):
        """Test creating a Merkle proof."""
        proof = MerkleProof(
            entry_id="iae_test",
            tx_id=42,
            leaf_hash="abc123",
            root_hash="def456",
            proof_nodes=["node1", "node2"],
            tree_size=100,
        )

        assert proof.tx_id == 42
        assert len(proof.proof_nodes) == 2

    def test_to_dict_from_dict(self):
        """Test dictionary serialization."""
        original = MerkleProof(
            entry_id="iae_test",
            tx_id=42,
            leaf_hash="abc123",
            root_hash="def456",
            proof_nodes=["node1", "node2"],
            tree_size=100,
        )

        data = original.to_dict()
        restored = MerkleProof.from_dict(data)

        assert restored.tx_id == original.tx_id
        assert restored.root_hash == original.root_hash


@pytest.mark.asyncio
class TestImmutableAuditTrail:
    """Integration tests for ImmutableAuditTrail (requires running immudb)."""

    async def test_connect_disconnect(self, config):
        """Test connection lifecycle."""
        trail = ImmutableAuditTrail(config)

        await trail.connect()
        assert trail._connected

        await trail.disconnect()
        assert not trail._connected

    async def test_append_entry(self, audit_trail):
        """Test appending an entry."""
        entry = AuditEntry(
            tx_id="tx_test_append",
            account_id="acc_test",
            entry_type="credit",
            amount="100.00",
            currency="USDC",
        )
        entry.entry_hash = entry.compute_hash()

        receipt = await audit_trail.append(entry, actor_id="test_user")

        assert isinstance(receipt, ImmutableReceipt)
        assert receipt.entry_id == entry.entry_id
        assert receipt.immudb_tx_id > 0
        assert receipt.merkle_proof is not None
        assert receipt.merkle_proof.root_hash

    async def test_get_entry(self, audit_trail):
        """Test retrieving an entry."""
        # Create entry
        original = AuditEntry(
            tx_id="tx_test_get",
            account_id="acc_test",
            entry_type="debit",
            amount="50.00",
            currency="USDC",
        )
        original.entry_hash = original.compute_hash()

        await audit_trail.append(original)

        # Retrieve entry
        retrieved = await audit_trail.get(original.entry_id)

        assert retrieved is not None
        assert retrieved.tx_id == original.tx_id
        assert retrieved.amount == original.amount

    async def test_get_nonexistent_entry(self, audit_trail):
        """Test retrieving a non-existent entry."""
        result = await audit_trail.get("iae_nonexistent_12345")
        assert result is None

    async def test_verify_entry(self, audit_trail):
        """Test verifying an entry."""
        entry = AuditEntry(
            tx_id="tx_test_verify",
            account_id="acc_test",
            entry_type="credit",
            amount="75.00",
            currency="USDC",
        )
        entry.entry_hash = entry.compute_hash()

        await audit_trail.append(entry)

        result = await audit_trail.verify(entry.entry_id)

        assert isinstance(result, VerificationResult)
        assert result.status == VerificationStatus.VERIFIED
        assert result.immudb_verified
        assert result.merkle_verified

    async def test_verify_nonexistent_entry(self, audit_trail):
        """Test verifying a non-existent entry."""
        result = await audit_trail.verify("iae_nonexistent_xyz")

        assert result.status == VerificationStatus.NOT_FOUND

    async def test_get_audit_proof(self, audit_trail):
        """Test generating audit proof."""
        entry = AuditEntry(
            tx_id="tx_test_proof",
            account_id="acc_test",
            entry_type="transfer",
            amount="200.00",
            currency="USDC",
        )
        entry.entry_hash = entry.compute_hash()

        await audit_trail.append(entry)

        proof = await audit_trail.get_audit_proof(entry.entry_id)

        assert proof["version"] == "1.0"
        assert proof["entry"]["entry_id"] == entry.entry_id
        assert proof["merkle_proof"]["root_hash"]
        assert proof["verification"]["verified"]

    async def test_get_state(self, audit_trail):
        """Test getting database state."""
        state = await audit_trail.get_state()

        assert "tx_id" in state
        assert state["tx_id"] >= 0

    async def test_health_check(self, audit_trail):
        """Test health check."""
        health = await audit_trail.health_check()

        assert health["status"] == "healthy"
        assert health["connected"]


@pytest.mark.asyncio
class TestCreateAuditTrail:
    """Test factory function."""

    async def test_create_with_defaults(self):
        """Test creating audit trail with defaults."""
        trail = create_audit_trail()

        assert trail.config.immudb_host == "localhost"
        assert trail.config.immudb_port == 3322

    async def test_create_with_custom_config(self):
        """Test creating audit trail with custom config."""
        trail = create_audit_trail(
            immudb_host="immudb.example.com",
            immudb_port=3323,
            immudb_database="custom_db",
        )

        assert trail.config.immudb_host == "immudb.example.com"
        assert trail.config.immudb_port == 3323
        assert trail.config.immudb_database == "custom_db"


# Pytest configuration
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "immudb: tests that require a running immudb instance"
    )
