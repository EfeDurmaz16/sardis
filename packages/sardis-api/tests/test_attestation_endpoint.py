"""Tests for the attestation envelope model and API endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_v2_core.attestation_envelope import (
    AttestationEnvelope,
    build_attestation_envelope,
    verify_attestation_signature,
)

from sardis_api.authz import Principal, require_principal
from sardis_api.routers.attestation import router


# ── Helpers ────────────────────────────────────────────────────────────


def _admin_principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _admin_principal
    app.include_router(router, prefix="/api/v2")
    return app


class _FakeConn:
    """Minimal mock for an asyncpg connection."""

    def __init__(self, rows):
        self._rows = list(rows)
        self._call = 0

    async def fetchrow(self, *args, **kwargs):
        if self._call < len(self._rows):
            row = self._rows[self._call]
            self._call += 1
            return row
        return None


class _FakePool:
    """Minimal mock for an asyncpg pool with async context manager acquire()."""

    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return self

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _mock_pool(*rows):
    """Build a fake pool whose connection returns the given rows in order."""
    conn = _FakeConn(rows)
    return _FakePool(conn)


_POOL_PATCH = "sardis_v2_core.database.Database.get_pool"


# ── E1: Attestation Envelope Model ────────────────────────────────────


def test_build_attestation_unsigned():
    """Build an envelope without a signing key — signature must be empty."""
    envelope = build_attestation_envelope(
        mandate_id="mnd_abc123",
        agent_did="did:sardis:agent_42",
        policy_rules=["per_tx_limit", "scope_check"],
        evidence=["hash_abc", "hash_def"],
        verification_report={
            "mandate_chain_valid": True,
            "policy_compliance": "pass",
            "kya_score": 0.85,
            "provenance": "turnkey_mpc",
        },
    )

    assert isinstance(envelope, AttestationEnvelope)
    assert envelope.attestation_id.startswith("att_")
    assert envelope.timestamp  # ISO 8601 string
    assert envelope.agent_did == "did:sardis:agent_42"
    assert envelope.mandate_id == "mnd_abc123"
    assert envelope.policy_rules_applied == ["per_tx_limit", "scope_check"]
    assert envelope.evidence_chain == ["hash_abc", "hash_def"]
    assert envelope.verification_report["policy_compliance"] == "pass"
    assert envelope.signature == ""


def test_build_attestation_signed():
    """Build an envelope with an Ed25519 signing key — signature must verify."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    pub_bytes = private_key.public_key().public_bytes_raw()

    envelope = build_attestation_envelope(
        mandate_id="mnd_signed",
        agent_did="did:sardis:agent_99",
        policy_rules=["total_limit"],
        evidence=["merkle::abcdef"],
        signing_key=seed,
    )

    assert envelope.signature != ""
    assert len(envelope.signature) > 10  # base64-encoded Ed25519 sig

    # Verify the signature round-trips
    assert verify_attestation_signature(envelope, pub_bytes) is True

    # Tamper detection
    envelope.mandate_id = "mnd_tampered"
    assert verify_attestation_signature(envelope, pub_bytes) is False


def test_build_attestation_to_dict():
    """to_dict() returns all expected fields."""
    envelope = build_attestation_envelope(
        mandate_id="mnd_dict",
        agent_did="did:sardis:agent_1",
        policy_rules=["check_a"],
        evidence=["ev_1"],
    )
    d = envelope.to_dict()
    expected_keys = {
        "attestation_id",
        "timestamp",
        "agent_did",
        "mandate_id",
        "policy_rules_applied",
        "evidence_chain",
        "ap2_mandate_ref",
        "verification_report",
        "signature",
    }
    assert set(d.keys()) == expected_keys


def test_verify_unsigned_returns_false():
    """verify_attestation_signature returns False for unsigned envelopes."""
    envelope = build_attestation_envelope(
        mandate_id="mnd_unsigned",
        agent_did="did:sardis:agent_0",
        policy_rules=[],
        evidence=[],
    )
    assert verify_attestation_signature(envelope, b"\x00" * 32) is False


# ── E2: Endpoint Tests ────────────────────────────────────────────────


def test_attestation_endpoint_returns_envelope():
    """Mocked payment + decision — endpoint must return valid envelope JSON."""
    payment_row = {
        "entry_id": "pay_001",
        "wallet_id": "wal_1",
        "entry_type": "payment",
        "amount": 50.0,
        "currency": "USDC",
        "chain": "base",
        "chain_tx_hash": "0xtx1",
        "status": "confirmed",
        "created_at": "2026-01-01T00:00:00Z",
        "agent_id": "agent_42",
    }
    decision_row = {
        "id": "pdec_abc",
        "verdict": "allow",
        "steps_json": '[{"rule": "per_tx_limit"}, {"rule": "scope_check"}]',
        "evidence_hash": "sha256_abc",
    }

    pool = _mock_pool(payment_row, decision_row)
    app = _build_app()
    client = TestClient(app)

    with patch(_POOL_PATCH, new=AsyncMock(return_value=pool)):
        resp = client.get("/api/v2/payments/pay_001/attestation")

    assert resp.status_code == 200
    body = resp.json()
    assert body["attestation_id"].startswith("att_")
    assert body["mandate_id"] == "pay_001"
    assert body["agent_did"] == "did:sardis:agent_42"
    assert "per_tx_limit" in body["policy_rules_applied"]
    assert "scope_check" in body["policy_rules_applied"]
    assert body["verification_report"]["mandate_chain_valid"] is True
    assert body["verification_report"]["policy_compliance"] == "pass"
    assert body["verification_report"]["provenance"] == "turnkey_mpc"


def test_attestation_endpoint_404_not_found():
    """Unknown payment returns 404."""
    pool = _mock_pool(None, None)
    app = _build_app()
    client = TestClient(app)

    with patch(_POOL_PATCH, new=AsyncMock(return_value=pool)):
        resp = client.get("/api/v2/payments/pay_unknown/attestation")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_attestation_endpoint_404_no_decision():
    """Payment exists but no policy decision — returns 404."""
    payment_row = {
        "entry_id": "pay_002",
        "wallet_id": "wal_2",
        "entry_type": "payment",
        "amount": 25.0,
        "currency": "USDC",
        "chain": "base",
        "chain_tx_hash": "0xtx2",
        "status": "confirmed",
        "created_at": "2026-01-01T00:00:00Z",
        "agent_id": "agent_99",
    }
    pool = _mock_pool(payment_row, None)
    app = _build_app()
    client = TestClient(app)

    with patch(_POOL_PATCH, new=AsyncMock(return_value=pool)):
        resp = client.get("/api/v2/payments/pay_002/attestation")

    assert resp.status_code == 404
    assert "attestation" in resp.json()["detail"].lower()
