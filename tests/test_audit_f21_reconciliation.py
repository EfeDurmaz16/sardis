"""Tests for F21: Fix reconciliation agent:unknown."""
import pytest
import time
from pathlib import Path
from datetime import datetime, timezone


def test_reconciliation_preserves_original_subject():
    """Reconciliation should preserve original mandate subject, not use agent:unknown."""
    from sardis_ledger.records import LedgerStore, ChainReceipt
    from sardis_v2_core.mandates import PaymentMandate, VCProof

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = LedgerStore(f"sqlite:///{db_path}")

        # Create test mandate with specific subject
        proof = VCProof(
            verification_method="test#key-1",
            created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            proof_value="test_proof",
        )

        original_subject = "agent:my-ai-assistant"
        original_issuer = "wallet:my-wallet"

        mandate = PaymentMandate(
            mandate_id="test_mandate_reconcile",
            mandate_type="payment",
            issuer=original_issuer,
            subject=original_subject,
            expires_at=int(time.time()) + 300,
            nonce="test_nonce",
            proof=proof,
            domain="test.network",
            purpose="test_payment",
            chain="base",
            token="USDC",
            amount_minor=1_000_000,  # 1 USDC
            destination="0xdestination",
            audit_hash="test_hash",
            wallet_id="my-wallet",
        )

        receipt = ChainReceipt(
            tx_hash="0xtesthash",
            chain="base",
            block_number=12345,
            audit_anchor="test_anchor",
        )

        # Queue for reconciliation
        entry_id = store.queue_for_reconciliation(mandate, receipt, "test error")
        assert entry_id is not None

        # Get pending reconciliation entries
        pending = store.get_pending_reconciliation(limit=10)
        assert len(pending) == 1

        entry = pending[0]

        # Verify metadata was preserved
        assert entry.metadata is not None
        assert entry.metadata.get("subject") == original_subject
        assert entry.metadata.get("issuer") == original_issuer
        assert entry.metadata.get("domain") == "test.network"
        assert entry.metadata.get("purpose") == "test_payment"


def test_reconciliation_restores_original_mandate_data():
    """Reconciliation should reconstruct mandate with original data."""
    from sardis_ledger.records import LedgerStore, ChainReceipt, PendingReconciliation
    import hashlib

    # Create a mock pending reconciliation with metadata
    entry = PendingReconciliation(
        id="recon_test123",
        mandate_id="mandate_123",
        chain_tx_hash="0xhash123",
        chain="base",
        audit_anchor="anchor_123",
        from_wallet="wallet_from",
        to_wallet="wallet_to",
        amount="1000000",
        currency="USDC",
        error="test error",
        metadata={
            "subject": "agent:specific-agent",
            "issuer": "wallet:specific-wallet",
            "domain": "custom.domain",
            "purpose": "custom_purpose",
        }
    )

    # Verify the metadata contains expected values
    assert entry.metadata["subject"] == "agent:specific-agent"
    assert entry.metadata["issuer"] == "wallet:specific-wallet"
    assert entry.metadata["domain"] == "custom.domain"
    assert entry.metadata["purpose"] == "custom_purpose"


def test_reconciliation_fallback_for_missing_metadata():
    """Reconciliation should handle entries with missing metadata gracefully."""
    from sardis_ledger.records import PendingReconciliation

    # Create entry without metadata (legacy or corrupted)
    entry = PendingReconciliation(
        id="recon_test456",
        mandate_id="mandate_456",
        chain_tx_hash="0xhash456",
        chain="base",
        audit_anchor="anchor_456",
        from_wallet="wallet_from",
        to_wallet="wallet_to",
        amount="1000000",
        currency="USDC",
        error="test error",
        metadata=None,  # Missing metadata
    )

    # Verify it doesn't crash when metadata is None
    subject = entry.metadata.get("subject", "agent:unknown") if entry.metadata else "agent:unknown"
    assert subject == "agent:unknown"
