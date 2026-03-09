"""Tests for FIDES Identity API endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_v2_core.did_bridge import DIDBridge, DIDMapping
from sardis_v2_core.trust_graph import TrustPathNode, TrustPathResult


@pytest.fixture
def app():
    """Create test FastAPI app with fides_identity router."""
    from sardis_api.routers.fides_identity import router

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v2")

    # Override auth dependency to bypass authentication
    from sardis_api.authz import Principal, require_principal
    test_app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="test_org",
        scopes=["*"],
    )

    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset module-level singletons between tests."""
    import sardis_api.routers.fides_identity as mod
    mod._did_bridge = None
    mod._fides_adapter = None
    mod._agit_engine = None
    mod._trust_scorer = None
    yield
    mod._did_bridge = None
    mod._fides_adapter = None
    mod._agit_engine = None
    mod._trust_scorer = None


def test_register_fides_did(client):
    """Links FIDES DID to agent via API."""
    from datetime import UTC, datetime

    mock_bridge = MagicMock(spec=DIDBridge)
    mock_bridge.register_fides_did.return_value = DIDMapping(
        agent_id="agent_001",
        fides_did="did:fides:abc123",
        public_key_hex="deadbeef",
        verified_at=datetime(2026, 1, 1, tzinfo=UTC),
        verification_signature="sig_hex",
    )

    with patch("sardis_api.routers.fides_identity._get_did_bridge", return_value=mock_bridge):
        resp = client.post(
            "/api/v2/agents/agent_001/fides/register",
            json={
                "fides_did": "did:fides:abc123",
                "signature": "sig_hex",
                "public_key": "deadbeef",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "agent_001"
    assert data["fides_did"] == "did:fides:abc123"
    assert data["verified_at"] is not None


def test_register_fides_did_invalid(client):
    """Invalid DID registration returns 400."""
    from sardis_v2_core.did_bridge import DIDRegistrationError

    mock_bridge = MagicMock(spec=DIDBridge)
    mock_bridge.register_fides_did.side_effect = DIDRegistrationError("Invalid format")

    with patch("sardis_api.routers.fides_identity._get_did_bridge", return_value=mock_bridge):
        resp = client.post(
            "/api/v2/agents/agent_001/fides/register",
            json={
                "fides_did": "bad_format",
                "signature": "sig",
                "public_key": "pk",
            },
        )

    assert resp.status_code == 400


def test_get_fides_identity(client):
    """Get linked FIDES identity."""
    from datetime import UTC, datetime

    mock_bridge = MagicMock(spec=DIDBridge)
    mock_bridge.get_mapping.return_value = DIDMapping(
        agent_id="agent_001",
        fides_did="did:fides:abc",
        public_key_hex="pk_hex",
        verified_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    with patch("sardis_api.routers.fides_identity._get_did_bridge", return_value=mock_bridge):
        resp = client.get("/api/v2/agents/agent_001/fides/identity")

    assert resp.status_code == 200
    data = resp.json()
    assert data["fides_did"] == "did:fides:abc"
    assert data["verified_at"] is not None


def test_get_fides_identity_not_linked(client):
    """Agent without FIDES DID returns null fields."""
    mock_bridge = MagicMock(spec=DIDBridge)
    mock_bridge.get_mapping.return_value = None

    with patch("sardis_api.routers.fides_identity._get_did_bridge", return_value=mock_bridge):
        resp = client.get("/api/v2/agents/agent_001/fides/identity")

    assert resp.status_code == 200
    data = resp.json()
    assert data["fides_did"] is None


def test_get_trust_score_with_fides(client):
    """Returns trust score computed via FIDES adapter."""
    from decimal import Decimal

    from sardis_v2_core.kya_trust_scoring import TrustScore, TrustSignal, TrustTier

    mock_scorer = AsyncMock()
    mock_scorer.calculate_trust = AsyncMock(return_value=TrustScore(
        agent_id="agent_001",
        overall=0.72,
        tier=TrustTier.HIGH,
        max_per_tx=Decimal("5000"),
        max_per_day=Decimal("10000"),
        signals=[
            TrustSignal(name="transitive_trust", score=0.85, weight=0.15),
        ],
    ))

    mock_bridge = MagicMock(spec=DIDBridge)
    mock_bridge.resolve_to_fides.return_value = "did:fides:agent_001"

    with patch("sardis_api.routers.fides_identity._get_trust_scorer", return_value=mock_scorer), \
         patch("sardis_api.routers.fides_identity._get_did_bridge", return_value=mock_bridge):
        resp = client.get("/api/v2/agents/agent_001/trust-score")

    assert resp.status_code == 200
    data = resp.json()
    assert data["overall"] == pytest.approx(0.72, abs=0.001)
    assert data["tier"] == "high"


def test_trust_path_query(client):
    """Finds trust path between agents."""
    mock_bridge = MagicMock(spec=DIDBridge)
    mock_bridge.resolve_to_fides.return_value = "did:fides:agent_001"

    mock_adapter = AsyncMock()
    mock_adapter.find_path = AsyncMock(return_value=TrustPathResult(
        from_did="did:fides:agent_001",
        to_did="did:fides:target",
        found=True,
        path=[
            TrustPathNode(did="did:fides:agent_001", trust_level=100),
            TrustPathNode(did="did:fides:target", trust_level=75),
        ],
        cumulative_trust=0.75,
        hops=1,
    ))

    with patch("sardis_api.routers.fides_identity._get_did_bridge", return_value=mock_bridge), \
         patch("sardis_api.routers.fides_identity._get_fides_adapter", return_value=mock_adapter):
        resp = client.get("/api/v2/agents/agent_001/trust-path/did:fides:target")

    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["hops"] == 1
    assert data["cumulative_trust"] == pytest.approx(0.75, abs=0.001)


def test_trust_path_no_fides_did(client):
    """Agent without FIDES DID returns 404."""
    mock_bridge = MagicMock(spec=DIDBridge)
    mock_bridge.resolve_to_fides.return_value = None

    with patch("sardis_api.routers.fides_identity._get_did_bridge", return_value=mock_bridge):
        resp = client.get("/api/v2/agents/agent_001/trust-path/did:fides:target")

    assert resp.status_code == 404


def test_policy_history_endpoint(client):
    """Returns AGIT commit log."""
    from sardis_v2_core.agit_policy_engine import AgitPolicyEngine

    mock_engine = MagicMock(spec=AgitPolicyEngine)
    mock_engine.get_chain_history.return_value = [
        {"commit_hash": "abc123", "created_at": "2026-01-01T00:00:00", "signed": False, "signer_did": None},
        {"commit_hash": "def456", "created_at": "2026-01-02T00:00:00", "signed": True, "signer_did": "did:fides:signer"},
    ]

    with patch("sardis_api.routers.fides_identity._get_agit_engine", return_value=mock_engine):
        resp = client.get("/api/v2/agents/agent_001/policy-history")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["commits"][0]["commit_hash"] == "abc123"


def test_policy_chain_verify_endpoint(client):
    """Returns chain integrity status."""
    from sardis_v2_core.agit_policy_engine import AgitPolicyEngine, PolicyChainVerification

    mock_engine = MagicMock(spec=AgitPolicyEngine)
    mock_engine.verify_policy_chain.return_value = PolicyChainVerification(
        valid=True,
        chain_length=5,
    )

    with patch("sardis_api.routers.fides_identity._get_agit_engine", return_value=mock_engine):
        resp = client.post("/api/v2/agents/agent_001/policy-history/verify")

    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["chain_length"] == 5
