import os
import sqlite3
import tempfile

from sardis_protocol.storage import SqliteReplayCache, MandateArchive
from sardis_v2_core.mandates import MandateChain, IntentMandate, CartMandate, PaymentMandate, VCProof


def _sqlite_dsn(tmp_path: str) -> str:
    return f"sqlite:///{tmp_path}"


def test_sqlite_replay_cache_persists_entries():
    with tempfile.TemporaryDirectory() as tmp:
        dsn = _sqlite_dsn(os.path.join(tmp, "cache.db"))
        cache = SqliteReplayCache(dsn)
        assert cache.check_and_store("mandate-1", 9999999999)
        assert not cache.check_and_store("mandate-1", 9999999999)
        # Re-open to ensure persistence
        cache2 = SqliteReplayCache(dsn)
        assert not cache2.check_and_store("mandate-1", 9999999999)


def test_mandate_archive_persists_chain():
    with tempfile.TemporaryDirectory() as tmp:
        dsn = _sqlite_dsn(os.path.join(tmp, "mandates.db"))
        archive = MandateArchive(dsn)
        proof = VCProof(
            type="DataIntegrityProof",
            verification_method="did:agent#ed25519:stub",
            created="2024-01-01T00:00:00Z",
            proof_value="c2lnbg==",
        )
        chain = MandateChain(
            intent=IntentMandate(
                mandate_id="intent-1",
                mandate_type="intent",
                issuer="sardis",
                subject="agent",
                expires_at=9999999999,
                nonce="intent",
                proof=proof,
                domain="merchant.example",
                purpose="intent",
                scope=["digital"],
                requested_amount=100_00,
            ),
            cart=CartMandate(
                mandate_id="cart-1",
                mandate_type="cart",
                issuer="sardis",
                subject="agent",
                expires_at=9999999999,
                nonce="cart",
                proof=proof,
                domain="merchant.example",
                purpose="cart",
                line_items=[{"sku": "sku", "description": "item", "amount_minor": 100_00}],
                merchant_domain="merchant.example",
                currency="USD",
                subtotal_minor=100_00,
                taxes_minor=0,
            ),
            payment=PaymentMandate(
                mandate_id="payment-1",
                mandate_type="payment",
                issuer="sardis",
                subject="agent",
                expires_at=9999999999,
                nonce="pay",
                proof=proof,
                domain="merchant.example",
                purpose="checkout",
                chain="base",
                token="USDC",
                amount_minor=100_00,
                destination="0xmerchant",
                audit_hash="audit",
            ),
        )
        archive.store(chain)
        # ensure row exists
        with sqlite3.connect(os.path.join(tmp, "mandates.db")) as conn:
            row = conn.execute("SELECT mandate_id FROM mandate_chains WHERE mandate_id = ?", ("payment-1",)).fetchone()
            assert row is not None
