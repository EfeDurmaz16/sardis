"""Tests for trust-gated payment execution, spending limits, and RFC 9421 signing."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_v2_core.kya_trust_scoring import (
    TRUST_TIER_LIMITS,
    KYALevel,
    TrustScore,
    TrustScorer,
    TrustSignal,
    TrustTier,
)

# ============ Trust-Gated ControlPlane Tests ============


def _make_intent(agent_id="agent_001", amount="100.00", fides_did=None):
    from sardis_v2_core.execution_intent import ExecutionIntent, IntentSource

    intent = ExecutionIntent(
        source=IntentSource.A2A,
        agent_id=agent_id,
        amount=Decimal(amount),
        currency="USDC",
        chain="base",
    )
    if fides_did:
        intent.metadata["fides_did"] = fides_did
    return intent


@pytest.mark.asyncio
async def test_low_trust_blocks_high_amount():
    """Trust score 0.2 with $500 payment -> denied."""
    from sardis_v2_core.control_plane import ControlPlane

    mock_scorer = AsyncMock()
    mock_scorer.calculate_trust = AsyncMock(return_value=TrustScore(
        agent_id="agent_001",
        overall=0.2,
        tier=TrustTier.UNTRUSTED,
        max_per_tx=Decimal("10"),
        max_per_day=Decimal("25"),
    ))

    mock_config = MagicMock()
    mock_config.min_trust_for_payment = 0.3

    plane = ControlPlane(
        trust_scorer=mock_scorer,
        fides_config=mock_config,
    )

    intent = _make_intent(amount="500.00", fides_did="did:fides:untrusted")
    result = await plane.submit(intent)

    assert result.success is False
    assert "trust_score_insufficient" in result.error
    assert result.data["trust_score"] == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_high_trust_passes():
    """Trust score 0.9 passes the trust gate."""
    from sardis_v2_core.control_plane import ControlPlane

    mock_scorer = AsyncMock()
    mock_scorer.calculate_trust = AsyncMock(return_value=TrustScore(
        agent_id="agent_001",
        overall=0.9,
        tier=TrustTier.SOVEREIGN,
        max_per_tx=Decimal("50000"),
        max_per_day=Decimal("100000"),
    ))

    mock_config = MagicMock()
    mock_config.min_trust_for_payment = 0.3

    # Mock chain executor to avoid actual execution
    mock_chain = AsyncMock()
    mock_chain.execute = AsyncMock(return_value={"tx_hash": "0xabc"})

    plane = ControlPlane(
        trust_scorer=mock_scorer,
        fides_config=mock_config,
        chain_executor=mock_chain,
    )

    intent = _make_intent(amount="100.00", fides_did="did:fides:trusted")
    result = await plane.submit(intent)

    # Trust gate passes — should reach execution
    assert result.success is True or "trust_score_insufficient" not in (result.error or "")


@pytest.mark.asyncio
async def test_no_fides_did_skips_trust_gate():
    """Intent without fides_did in metadata skips the trust gate."""
    from sardis_v2_core.control_plane import ControlPlane

    mock_scorer = AsyncMock()
    mock_config = MagicMock()
    mock_config.min_trust_for_payment = 0.3

    mock_chain = AsyncMock()
    mock_chain.execute = AsyncMock(return_value={"tx_hash": "0xdef"})

    plane = ControlPlane(
        trust_scorer=mock_scorer,
        fides_config=mock_config,
        chain_executor=mock_chain,
    )

    intent = _make_intent(amount="100.00")  # No fides_did
    result = await plane.submit(intent)

    # Should not call trust scorer
    mock_scorer.calculate_trust.assert_not_called()


# ============ Dynamic Spending Limits Tests ============


def test_trust_overrides_kya_when_stricter():
    """Trust score LOW overrides policy limits when stricter."""
    from sardis_v2_core.spending_policy import SpendingPolicy, TrustLevel, create_default_policy

    # Create MEDIUM trust policy ($500/tx)
    policy = create_default_policy("agent_001", TrustLevel.MEDIUM)

    # With trust_score_override=0.25 (UNTRUSTED tier, $10/tx max),
    # effective limit should be min($500, $10) = $10
    mock_wallet = MagicMock()

    result = asyncio.get_event_loop().run_until_complete(
        policy.evaluate(
            mock_wallet,
            Decimal("15.00"),
            Decimal("0"),
            chain="base",
            token="USDC",
            trust_score_override=0.25,
        )
    )

    assert result[0] is False
    assert result[1] == "per_transaction_limit"


def test_high_trust_gets_full_limits():
    """SOVEREIGN trust gets configured limits (no additional restriction)."""
    from sardis_v2_core.spending_policy import SpendingPolicy, TrustLevel, create_default_policy

    policy = create_default_policy("agent_001", TrustLevel.HIGH)

    mock_wallet = MagicMock()

    # $4000 is within HIGH tier ($5000/tx) and SOVEREIGN trust ($50000/tx)
    result = asyncio.get_event_loop().run_until_complete(
        policy.evaluate(
            mock_wallet,
            Decimal("4000.00"),
            Decimal("0"),
            chain="base",
            token="USDC",
            trust_score_override=0.95,  # SOVEREIGN
        )
    )

    assert result[0] is True
    assert result[1] == "OK"


def test_trust_override_none_uses_configured():
    """No trust_score_override uses configured policy limits only."""
    from sardis_v2_core.spending_policy import TrustLevel, create_default_policy

    policy = create_default_policy("agent_001", TrustLevel.LOW)
    mock_wallet = MagicMock()

    # $45 is within LOW tier ($50/tx)
    result = asyncio.get_event_loop().run_until_complete(
        policy.evaluate(
            mock_wallet,
            Decimal("45.00"),
            Decimal("0"),
            chain="base",
            token="USDC",
            trust_score_override=None,
        )
    )

    assert result[0] is True


# ============ RFC 9421 Signing Tests ============


def test_rfc9421_sign_verify_roundtrip():
    """Sign a request and verify it passes."""
    try:
        from nacl.signing import SigningKey
    except ImportError:
        pytest.skip("PyNaCl not installed")

    from sardis_protocol.fides_signing import sign_request, verify_request

    signing_key = SigningKey.generate()
    private_key = signing_key.encode()
    public_key = signing_key.verify_key.encode()
    keyid = "did:fides:test-signer"

    method = "POST"
    url = "https://api.sardis.sh/api/v2/pay"
    headers = {"content-type": "application/json"}
    body = '{"amount": "100.00", "currency": "USDC"}'

    sig_headers = sign_request(
        method=method,
        url=url,
        headers=headers,
        body=body,
        private_key=private_key,
        keyid=keyid,
    )

    assert "Content-Digest" in sig_headers
    assert "Signature-Input" in sig_headers
    assert "Signature" in sig_headers
    assert sig_headers["Content-Digest"].startswith("sha-256=:")
    assert sig_headers["Signature"].startswith("sig1=:")

    # Verify
    all_headers = {**headers, **sig_headers}
    result = verify_request(
        method=method,
        url=url,
        headers=all_headers,
        body=body,
        public_key=public_key,
    )

    assert result.valid is True
    assert result.keyid == keyid


def test_invalid_rfc9421_signature_rejected():
    """Forged signature is rejected."""
    try:
        from nacl.signing import SigningKey
    except ImportError:
        pytest.skip("PyNaCl not installed")

    from sardis_protocol.fides_signing import sign_request, verify_request

    signer = SigningKey.generate()
    attacker = SigningKey.generate()
    keyid = "did:fides:signer"

    method = "POST"
    url = "https://api.sardis.sh/api/v2/pay"
    headers = {"content-type": "application/json"}
    body = '{"amount": "100.00"}'

    sig_headers = sign_request(
        method=method, url=url, headers=headers, body=body,
        private_key=signer.encode(), keyid=keyid,
    )

    # Verify with attacker's public key (should fail)
    all_headers = {**headers, **sig_headers}
    result = verify_request(
        method=method, url=url, headers=all_headers, body=body,
        public_key=attacker.verify_key.encode(),  # Wrong key!
    )

    assert result.valid is False
    assert "verification failed" in (result.error or "").lower()


def test_rfc9421_tampered_body_rejected():
    """Tampered body fails content digest check."""
    try:
        from nacl.signing import SigningKey
    except ImportError:
        pytest.skip("PyNaCl not installed")

    from sardis_protocol.fides_signing import sign_request, verify_request

    signer = SigningKey.generate()
    keyid = "did:fides:signer"

    method = "POST"
    url = "https://api.sardis.sh/api/v2/pay"
    headers = {"content-type": "application/json"}
    body = '{"amount": "100.00"}'

    sig_headers = sign_request(
        method=method, url=url, headers=headers, body=body,
        private_key=signer.encode(), keyid=keyid,
    )

    # Tamper with body
    tampered_body = '{"amount": "999999.00"}'
    all_headers = {**headers, **sig_headers}
    result = verify_request(
        method=method, url=url, headers=all_headers, body=tampered_body,
        public_key=signer.verify_key.encode(),
    )

    assert result.valid is False
    assert "Digest mismatch" in (result.error or "")


def test_rfc9421_missing_content_digest_rejected():
    """A stripped Content-Digest header must invalidate the signature."""
    try:
        from nacl.signing import SigningKey
    except ImportError:
        pytest.skip("PyNaCl not installed")

    from sardis_protocol.fides_signing import sign_request, verify_request

    signer = SigningKey.generate()
    method = "POST"
    url = "https://api.sardis.sh/api/v2/pay"
    headers = {"content-type": "application/json"}
    body = '{"amount": "100.00"}'

    sig_headers = sign_request(
        method=method,
        url=url,
        headers=headers,
        body=body,
        private_key=signer.encode(),
        keyid="did:fides:signer",
    )
    sig_headers.pop("Content-Digest")

    result = verify_request(
        method=method,
        url=url,
        headers={**headers, **sig_headers},
        body=body,
        public_key=signer.verify_key.encode(),
    )

    assert result.valid is False
    assert "Content-Digest" in (result.error or "")


def test_rfc9421_missing_headers():
    """Missing signature headers returns invalid."""
    try:
        from nacl.signing import SigningKey
    except ImportError:
        pytest.skip("PyNaCl not installed")

    from sardis_protocol.fides_signing import verify_request

    signer = SigningKey.generate()

    result = verify_request(
        method="POST",
        url="https://example.com/api",
        headers={"content-type": "application/json"},
        body="{}",
        public_key=signer.verify_key.encode(),
    )

    assert result.valid is False
    assert "Missing" in (result.error or "")
