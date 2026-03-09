"""Tests for FIDES Trust Graph adapter, DID Bridge, and TrustScorer integration."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_v2_core.did_bridge import DIDBridge, DIDRegistrationError
from sardis_v2_core.fides_did import generate_did
from sardis_v2_core.fides_trust_adapter import FidesAttestation, FidesTrustGraphAdapter
from sardis_v2_core.trust_graph import TrustPathNode, TrustPathResult

# ============ FidesTrustGraphAdapter Tests ============


@pytest.fixture
def adapter():
    return FidesTrustGraphAdapter(trust_url="http://fides-test:3200", timeout_seconds=2)


@pytest.mark.asyncio
async def test_adapter_get_trust_score(adapter):
    """Mock httpx, verify FIDES HTTP response -> float score."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "found": True,
        "cumulativeTrust": 0.72,
        "hops": 2,
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    adapter._client = mock_client

    score = await adapter.get_trust_score("did:fides:platform", "did:fides:agent1")

    assert score == pytest.approx(0.72)
    mock_client.get.assert_called_once_with("/v1/trust/did:fides:platform/did:fides:agent1")


@pytest.mark.asyncio
async def test_adapter_get_trust_score_self(adapter):
    """Same DID returns 1.0 without HTTP call."""
    score = await adapter.get_trust_score("did:fides:a", "did:fides:a")
    assert score == 1.0


@pytest.mark.asyncio
async def test_adapter_find_path(adapter):
    """Mock httpx, verify response -> TrustPathResult."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "found": True,
        "path": [
            {"did": "did:fides:a", "trustLevel": 100},
            {"did": "did:fides:b", "trustLevel": 75},
            {"did": "did:fides:c", "trustLevel": 50},
        ],
        "cumulativeTrust": 0.65,
        "hops": 2,
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    adapter._client = mock_client

    result = await adapter.find_path("did:fides:a", "did:fides:c")

    assert result.found is True
    assert result.hops == 2
    assert result.cumulative_trust == pytest.approx(0.65)
    assert len(result.path) == 3
    assert result.path[0].did == "did:fides:a"


@pytest.mark.asyncio
async def test_adapter_find_path_not_found(adapter):
    """No path returns empty TrustPathResult."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"found": False}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    adapter._client = mock_client

    result = await adapter.find_path("did:fides:a", "did:fides:z")

    assert result.found is False
    assert result.hops == 0
    assert result.cumulative_trust == 0.0


@pytest.mark.asyncio
async def test_adapter_fides_unavailable_returns_zero(adapter):
    """Timeout/connection error returns 0.0 (graceful degradation)."""
    import httpx

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("connection timed out"))
    mock_client.is_closed = False
    adapter._client = mock_client

    score = await adapter.get_trust_score("did:fides:a", "did:fides:b")
    assert score == 0.0

    result = await adapter.find_path("did:fides:a", "did:fides:b")
    assert result.found is False


@pytest.mark.asyncio
async def test_submit_attestation(adapter):
    """Mock httpx, verify attestation payload format."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"attestationId": "att_123"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    adapter._client = mock_client

    result = await adapter.submit_attestation(
        issuer_did="did:fides:issuer",
        subject_did="did:fides:subject",
        trust_level=75,
        signature="deadbeef",
        payload={"context": "test"},
    )

    assert result.success is True
    assert result.attestation_id == "att_123"

    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/v1/trust"
    body = call_args[1]["json"]
    assert body["issuerDid"] == "did:fides:issuer"
    assert body["subjectDid"] == "did:fides:subject"
    assert body["trustLevel"] == 75


# ============ DIDBridge Tests ============


@pytest.fixture
def bridge():
    return DIDBridge()


def test_did_bridge_register_and_resolve(bridge):
    """Round-trip: register + resolve both directions."""
    fides_did = generate_did(b"\x01" * 32)
    with patch.object(DIDBridge, "verify_ownership", return_value=True):
        mapping = bridge.register_fides_did(
            agent_id="agent_001",
            fides_did=fides_did,
            signature="sig_hex",
            public_key="pk_hex",
        )

    assert mapping.agent_id == "agent_001"
    assert mapping.fides_did == fides_did
    assert mapping.verified_at is not None

    # Forward lookup
    assert bridge.resolve_to_fides("agent_001") == fides_did

    # Reverse lookup
    assert bridge.resolve_to_sardis(fides_did) == "agent_001"


def test_did_bridge_invalid_format(bridge):
    """Non-did:fides: prefix raises error."""
    with pytest.raises(DIDRegistrationError, match="Invalid FIDES DID format"):
        bridge.register_fides_did(
            agent_id="agent_001",
            fides_did="did:web:example.com",
            signature="sig",
            public_key="pk",
        )


def test_did_bridge_duplicate_did(bridge):
    """Same FIDES DID to different agent raises error."""
    fides_did = generate_did(b"\x02" * 32)
    with patch.object(DIDBridge, "verify_ownership", return_value=True):
        bridge.register_fides_did("agent_001", fides_did, "sig", "pk")

    with pytest.raises(DIDRegistrationError, match="already registered"):
        with patch.object(DIDBridge, "verify_ownership", return_value=True):
            bridge.register_fides_did("agent_002", fides_did, "sig", "pk")


def test_did_bridge_bad_signature(bridge):
    """Bad signature raises DIDRegistrationError."""
    fides_did = generate_did(b"\x03" * 32)
    with pytest.raises(DIDRegistrationError, match="signature verification failed"):
        bridge.register_fides_did(
            agent_id="agent_001",
            fides_did=fides_did,
            signature="bad",
            public_key="bad",
        )


def test_did_bridge_verify_ownership_with_nacl():
    """Ed25519 signature verification (requires PyNaCl)."""
    try:
        from nacl.signing import SigningKey
    except ImportError:
        pytest.skip("PyNaCl not installed")

    signing_key = SigningKey.generate()
    public_key_hex = signing_key.verify_key.encode().hex()
    fides_did = generate_did(signing_key.verify_key.encode())

    agent_id = "agent_test"
    signature = signing_key.sign(agent_id.encode()).signature.hex()

    result = DIDBridge.verify_ownership(
        agent_id=agent_id,
        fides_did=fides_did,
        signature=signature,
        public_key=public_key_hex,
    )
    assert result is True


def test_did_bridge_verify_ownership_wrong_signature():
    """Wrong signature fails verification."""
    fides_did = generate_did(b"\x04" * 32)
    result = DIDBridge.verify_ownership(
        agent_id="agent_test",
        fides_did=fides_did,
        signature="0" * 128,
        public_key=(b"\x04" * 32).hex(),
    )
    assert result is False


def test_did_bridge_verify_ownership_rejects_did_public_key_mismatch():
    """A valid signature is not enough if the DID encodes a different public key."""
    try:
        from nacl.signing import SigningKey
    except ImportError:
        pytest.skip("PyNaCl not installed")

    signing_key = SigningKey.generate()
    mismatched_did = generate_did(b"\x07" * 32)
    signature = signing_key.sign(b"agent_test").signature.hex()

    result = DIDBridge.verify_ownership(
        agent_id="agent_test",
        fides_did=mismatched_did,
        signature=signature,
        public_key=signing_key.verify_key.encode().hex(),
    )
    assert result is False


def test_did_bridge_reregistration_replaces_reverse_mapping(bridge):
    """Re-registering an agent with a new DID should drop stale reverse lookups."""
    did_one = generate_did(b"\x05" * 32)
    did_two = generate_did(b"\x06" * 32)

    with patch.object(DIDBridge, "verify_ownership", return_value=True):
        bridge.register_fides_did("agent_001", did_one, "sig", "pk")
        bridge.register_fides_did("agent_001", did_two, "sig", "pk")

    assert bridge.resolve_to_fides("agent_001") == did_two
    assert bridge.resolve_to_sardis(did_one) is None
    assert bridge.resolve_to_sardis(did_two) == "agent_001"


# ============ TrustScorer + FidesTrustGraphAdapter Integration ============


@pytest.mark.asyncio
async def test_trust_scorer_with_fides_adapter():
    """Full TrustScorer with FidesTrustGraphAdapter: transitive_trust uses real score."""
    adapter = FidesTrustGraphAdapter(trust_url="http://test:3200")

    # Mock the HTTP client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "found": True,
        "cumulativeTrust": 0.85,
        "hops": 1,
        "path": [
            {"did": "did:fides:sardis-platform", "trustLevel": 100},
            {"did": "did:fides:agent1", "trustLevel": 85},
        ],
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    adapter._client = mock_client

    # Mock Redis cache to avoid dependency
    with patch("sardis_v2_core.kya_trust_scoring.TrustScorer.__init__", return_value=None) as mock_init:
        from sardis_v2_core.kya_trust_scoring import (
            DEFAULT_WEIGHTS,
            TRUST_TIER_LIMITS,
            KYALevel,
            TrustScorer,
            TrustTier,
        )

        scorer = TrustScorer.__new__(TrustScorer)
        scorer._weights = DEFAULT_WEIGHTS.copy()
        scorer._cache_ttl = 300
        scorer._trust_graph = adapter
        scorer._platform_did = "did:fides:sardis-platform"

        # Create a mock cache store
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        scorer._cache_store = mock_cache

        score = await scorer.calculate_trust(
            agent_id="agent_test",
            kya_level=KYALevel.VERIFIED,
            agent_did="did:fides:agent1",
            use_cache=False,
        )

    # The transitive_trust signal should use the FIDES score (0.85) not the default 0.5
    transitive = next(s for s in score.signals if s.name == "transitive_trust")
    assert transitive.score == pytest.approx(0.85)
    assert transitive.details["path_found"] is True
    assert transitive.details["hops"] == 1


@pytest.mark.asyncio
async def test_trust_scorer_fides_unavailable_fallback():
    """When FIDES is unavailable, transitive_trust falls back to 0.5."""
    import httpx

    adapter = FidesTrustGraphAdapter(trust_url="http://test:3200")

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("down"))
    mock_client.is_closed = False
    adapter._client = mock_client

    with patch("sardis_v2_core.kya_trust_scoring.TrustScorer.__init__", return_value=None):
        from sardis_v2_core.kya_trust_scoring import (
            DEFAULT_WEIGHTS,
            KYALevel,
            TrustScorer,
        )

        scorer = TrustScorer.__new__(TrustScorer)
        scorer._weights = DEFAULT_WEIGHTS.copy()
        scorer._cache_ttl = 300
        scorer._trust_graph = adapter
        scorer._platform_did = "did:fides:sardis-platform"

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        scorer._cache_store = mock_cache

        score = await scorer.calculate_trust(
            agent_id="agent_test",
            kya_level=KYALevel.NONE,
            agent_did="did:fides:agent1",
            use_cache=False,
        )

    transitive = next(s for s in score.signals if s.name == "transitive_trust")
    # Should gracefully degrade to 0.5 (not crash)
    assert transitive.score == pytest.approx(0.5)
    assert transitive.details.get("reason") == "fides_unavailable"
