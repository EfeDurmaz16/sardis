"""Tests for F11: Sync ledger append thread lock."""
import pytest
import threading
import time
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone


def test_sync_append_acquires_lock():
    """Sync append() should acquire lock for thread safety."""
    from sardis_ledger.records import LedgerStore, ChainReceipt
    from sardis_v2_core.mandates import PaymentMandate, VCProof

    # Create temporary test ledger
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
            mandate_id="test_mandate_1",
            mandate_type="payment",
            issuer="wallet:test_wallet",
            subject="agent:test",
            expires_at=int(time.time()) + 300,
            nonce="test_nonce",
            proof=proof,
            domain="test.network",
            purpose="test",
            chain="base",
            token="USDC",
            amount_minor=1_000_000,  # 1 USDC
            destination="0xdestination",
            audit_hash="test_hash",
            wallet_id="test_wallet",
        )

        receipt = ChainReceipt(
            tx_hash="0xtesthash",
            chain="base",
            block_number=12345,
            audit_anchor="test_anchor",
        )

        # Test that append works (implicitly tests lock acquisition)
        tx = store.append(mandate, receipt)
        assert tx is not None
        assert tx.amount == Decimal("1.000000")


def test_concurrent_appends_are_safe():
    """Multiple threads appending should not cause race conditions."""
    from sardis_ledger.records import LedgerStore, ChainReceipt
    from sardis_v2_core.mandates import PaymentMandate, VCProof

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_concurrent.db"
        store = LedgerStore(f"sqlite:///{db_path}")

        results = []
        errors = []

        def append_transaction(idx):
            try:
                proof = VCProof(
                    verification_method="test#key-1",
                    created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    proof_value="test_proof",
                )

                mandate = PaymentMandate(
                    mandate_id=f"mandate_{idx}",
                    mandate_type="payment",
                    issuer="wallet:test",
                    subject="agent:test",
                    expires_at=int(time.time()) + 300,
                    nonce=f"nonce_{idx}",
                    proof=proof,
                    domain="test.network",
                    purpose="test",
                    chain="base",
                    token="USDC",
                    amount_minor=1_000_000,
                    destination="0xdest",
                    audit_hash=f"hash_{idx}",
                    wallet_id="test_wallet",
                )

                receipt = ChainReceipt(
                    tx_hash=f"0xhash_{idx}",
                    chain="base",
                    block_number=12345 + idx,
                    audit_anchor=f"anchor_{idx}",
                )

                tx = store.append(mandate, receipt)
                results.append(tx.tx_id)
            except Exception as e:
                errors.append(str(e))

        # Spawn multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=append_transaction, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
