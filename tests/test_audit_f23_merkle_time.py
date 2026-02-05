"""Tests for F23: Deterministic Merkle timestamps."""
import pytest
import time
from pathlib import Path
from datetime import datetime, timezone


def test_merkle_receipt_uses_chain_timestamp():
    """Merkle receipt should use chain receipt timestamp when available."""
    from sardis_ledger.records import LedgerStore, ChainReceipt
    from sardis_v2_core.mandates import PaymentMandate, VCProof

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = LedgerStore(f"sqlite:///{db_path}")

        # Create test mandate
        proof = VCProof(
            verification_method="test#key-1",
            created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            proof_value="test_proof",
        )

        mandate = PaymentMandate(
            mandate_id="test_mandate_merkle",
            mandate_type="payment",
            issuer="wallet:test",
            subject="agent:test",
            expires_at=int(time.time()) + 300,
            nonce="test_nonce",
            proof=proof,
            domain="test.network",
            purpose="test",
            chain="base",
            token="USDC",
            amount_minor=1_000_000,
            destination="0xdestination",
            audit_hash="test_hash",
            wallet_id="test_wallet",
        )

        # Create receipt with explicit timestamp
        chain_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        receipt = ChainReceipt(
            tx_hash="0xtesthash",
            chain="base",
            block_number=12345,
            audit_anchor="test_anchor",
            timestamp=chain_timestamp,
        )

        # Create Merkle receipt
        merkle_receipt = store.create_receipt(mandate, receipt)

        # Verify the receipt uses the chain timestamp
        assert merkle_receipt["timestamp"] == chain_timestamp.isoformat()


def test_merkle_receipt_deterministic_with_same_inputs():
    """Two receipts with identical inputs should produce identical Merkle roots."""
    from sardis_ledger.records import LedgerStore, ChainReceipt
    from sardis_v2_core.mandates import PaymentMandate, VCProof

    import tempfile

    # Create first ledger
    with tempfile.TemporaryDirectory() as tmpdir1:
        db_path1 = Path(tmpdir1) / "test1.db"
        store1 = LedgerStore(f"sqlite:///{db_path1}")

        proof = VCProof(
            verification_method="test#key-1",
            created="2024-01-15T10:00:00Z",
            proof_value="test_proof",
        )

        mandate1 = PaymentMandate(
            mandate_id="test_mandate_deterministic",
            mandate_type="payment",
            issuer="wallet:test",
            subject="agent:test",
            expires_at=int(time.time()) + 300,
            nonce="test_nonce",
            proof=proof,
            domain="test.network",
            purpose="test",
            chain="base",
            token="USDC",
            amount_minor=1_000_000,
            destination="0xdestination",
            audit_hash="test_hash",
            wallet_id="test_wallet",
        )

        # Use fixed timestamp for determinism
        chain_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        receipt1 = ChainReceipt(
            tx_hash="0xsametxhash",
            chain="base",
            block_number=12345,
            audit_anchor="same_anchor",
            timestamp=chain_timestamp,
        )

        merkle_receipt1 = store1.create_receipt(mandate1, receipt1)

    # Create second ledger with same inputs
    with tempfile.TemporaryDirectory() as tmpdir2:
        db_path2 = Path(tmpdir2) / "test2.db"
        store2 = LedgerStore(f"sqlite:///{db_path2}")

        mandate2 = PaymentMandate(
            mandate_id="test_mandate_deterministic",
            mandate_type="payment",
            issuer="wallet:test",
            subject="agent:test",
            expires_at=int(time.time()) + 300,
            nonce="test_nonce",
            proof=proof,
            domain="test.network",
            purpose="test",
            chain="base",
            token="USDC",
            amount_minor=1_000_000,
            destination="0xdestination",
            audit_hash="test_hash",
            wallet_id="test_wallet",
        )

        receipt2 = ChainReceipt(
            tx_hash="0xsametxhash",
            chain="base",
            block_number=12345,
            audit_anchor="same_anchor",
            timestamp=chain_timestamp,  # Same timestamp
        )

        merkle_receipt2 = store2.create_receipt(mandate2, receipt2)

        # Both should produce the same leaf hash and merkle root
        assert merkle_receipt1["merkle_proof"]["leaf"] == merkle_receipt2["merkle_proof"]["leaf"]
        assert merkle_receipt1["timestamp"] == merkle_receipt2["timestamp"]


def test_merkle_receipt_without_chain_timestamp_fallback():
    """Merkle receipt should fall back gracefully when chain timestamp is not available."""
    from sardis_ledger.records import LedgerStore, ChainReceipt
    from sardis_v2_core.mandates import PaymentMandate, VCProof

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = LedgerStore(f"sqlite:///{db_path}")

        proof = VCProof(
            verification_method="test#key-1",
            created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            proof_value="test_proof",
        )

        mandate = PaymentMandate(
            mandate_id="test_mandate_fallback",
            mandate_type="payment",
            issuer="wallet:test",
            subject="agent:test",
            expires_at=int(time.time()) + 300,
            nonce="test_nonce",
            proof=proof,
            domain="test.network",
            purpose="test",
            chain="base",
            token="USDC",
            amount_minor=1_000_000,
            destination="0xdestination",
            audit_hash="test_hash",
            wallet_id="test_wallet",
        )

        # Create receipt WITHOUT timestamp
        receipt = ChainReceipt(
            tx_hash="0xtesthash",
            chain="base",
            block_number=12345,
            audit_anchor="test_anchor",
            timestamp=None,  # No timestamp provided
        )

        # Should still create receipt successfully
        merkle_receipt = store.create_receipt(mandate, receipt)
        assert merkle_receipt is not None
        assert "timestamp" in merkle_receipt
        assert "merkle_root" in merkle_receipt
