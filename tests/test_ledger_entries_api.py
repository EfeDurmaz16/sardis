"""Tests for /api/v2/ledger/entries endpoints."""
from __future__ import annotations

import time
import hashlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.routers.ledger import router as ledger_router, get_deps, LedgerDependencies
from sardis_ledger.records import LedgerStore, ChainReceipt
from sardis_v2_core.mandates import PaymentMandate, VCProof


@pytest.fixture
def app_with_ledger() -> FastAPI:
    ledger = LedgerStore(dsn="memory://")

    now = int(time.time())
    proof = VCProof(
        verification_method="wallet:wallet_1#key-1",
        created="2026-01-01T00:00:00Z",
        proof_value="test",
    )
    mandate = PaymentMandate(
        mandate_id="mnd_test",
        mandate_type="payment",
        issuer="wallet:wallet_1",
        subject="agent_1",
        expires_at=now + 300,
        nonce="nonce",
        proof=proof,
        domain="sardis.network",
        purpose="checkout",
        chain="base_sepolia",
        token="USDC",
        amount_minor=10_00,
        destination="0xabc",
        audit_hash=hashlib.sha256(b"test").hexdigest(),
        wallet_id="wallet_1",
        merchant_domain="openai.com",
    )
    receipt = ChainReceipt(
        tx_hash="0xdeadbeef",
        chain="base_sepolia",
        block_number=1,
        audit_anchor="merkle::abc123",
    )
    ledger.append(mandate, receipt)
    ledger.create_receipt(mandate, receipt)

    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: LedgerDependencies(ledger=ledger)
    app.include_router(ledger_router, prefix="/api/v2/ledger")
    return app


def test_list_entries_filters_by_wallet(app_with_ledger: FastAPI) -> None:
    client = TestClient(app_with_ledger)
    resp = client.get("/api/v2/ledger/entries", params={"wallet_id": "wallet_1", "limit": 50, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert len(data["entries"]) == 1
    assert data["entries"][0]["from_wallet"] == "wallet_1"


def test_get_entry_and_verify(app_with_ledger: FastAPI) -> None:
    client = TestClient(app_with_ledger)
    entries = client.get("/api/v2/ledger/entries").json()["entries"]
    tx_id = entries[0]["tx_id"]

    resp = client.get(f"/api/v2/ledger/entries/{tx_id}")
    assert resp.status_code == 200
    entry = resp.json()
    assert entry["tx_id"] == tx_id

    verify = client.get(f"/api/v2/ledger/entries/{tx_id}/verify")
    assert verify.status_code == 200
    payload = verify.json()
    assert payload["valid"] is True
    assert payload["anchor"] == "merkle::abc123"
    assert payload["receipt_id"].startswith("rct_")
    assert payload["merkle_root"]
    assert payload["current_root"]
    assert payload["is_current_root"] is True
    assert payload["checks"]["proof_present"] is True
    assert payload["checks"]["leaf_matches_payload"] is True
    assert payload["checks"]["root_matches_chain_step"] is True
