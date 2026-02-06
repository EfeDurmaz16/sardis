"""Comprehensive x402 challenge-response protocol conformance tests.

Tests cover:
- Challenge generation and serialization
- Payment payload verification
- ERC-3009 authorization structures
- Settlement status transitions
- v2 header construction
- Backward compatibility
"""
import base64
import json
import time
from datetime import datetime

import pytest

from sardis_protocol.x402 import (
    X402Challenge,
    X402ChallengeResponse,
    X402HeaderBuilder,
    X402PaymentPayload,
    X402VerificationResult,
    X402_PAYMENT_REQUIRED_HEADER,
    X402_PAYMENT_SIGNATURE_HEADER,
    X402_PAYMENT_RESPONSE_HEADER,
    X402_VERSION_1,
    X402_VERSION_2,
    generate_challenge,
    parse_challenge_header,
    serialize_challenge_header,
    validate_x402_version,
    verify_payment_payload,
)
from sardis_protocol.x402_erc3009 import (
    ERC3009Authorization,
    build_transfer_authorization,
    encode_authorization_params,
    validate_authorization_timing,
)
from sardis_protocol.x402_settlement import (
    InMemorySettlementStore,
    X402Settlement,
    X402SettlementStatus,
    X402Settler,
)

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.x402]


# --- Test fixtures ---


@pytest.fixture
def sample_challenge() -> X402Challenge:
    """Create a sample x402 challenge."""
    return X402Challenge(
        payment_id="x402_test123",
        resource_uri="/api/resource",
        amount="1000000",
        currency="USDC",
        payee_address="0xPayee123",
        network="base",
        token_address="0xToken456",
        expires_at=int(time.time()) + 300,
        nonce="nonce789abc",
    )


@pytest.fixture
def sample_payment_payload(sample_challenge: X402Challenge) -> X402PaymentPayload:
    """Create a sample payment payload matching the challenge."""
    return X402PaymentPayload(
        payment_id=sample_challenge.payment_id,
        payer_address="0xPayer999",
        amount=sample_challenge.amount,
        nonce=sample_challenge.nonce,
        signature="0xdeadbeef",
        authorization={
            "from": "0xPayer999",
            "to": "0xPayee123",
            "value": 1000000,
            "validAfter": int(time.time()) - 60,
            "validBefore": int(time.time()) + 300,
            "nonce": "0x" + "00" * 32,
            "v": 27,
            "r": "0x" + "11" * 32,
            "s": "0x" + "22" * 32,
        },
    )


@pytest.fixture
def sample_erc3009_auth() -> ERC3009Authorization:
    """Create a sample ERC-3009 authorization."""
    now = int(time.time())
    return ERC3009Authorization(
        from_address="0x1111111111111111111111111111111111111111",
        to_address="0x2222222222222222222222222222222222222222",
        value=1000000,
        valid_after=now - 60,
        valid_before=now + 300,
        nonce="0x" + "aa" * 32,
        v=27,
        r="0x" + "bb" * 32,
        s="0x" + "cc" * 32,
    )


# --- Test 1: Challenge generation with all required fields ---


def test_challenge_generation_has_all_required_fields():
    """Test that generate_challenge creates a complete challenge with all fields."""
    response = generate_challenge(
        resource_uri="/protected/data",
        amount="5000000",
        currency="USDC",
        payee_address="0xMerchant",
        network="polygon",
        token_address="0xUSDCToken",
        ttl_seconds=600,
    )

    assert isinstance(response, X402ChallengeResponse)
    assert response.http_status == 402
    assert response.header_value != ""

    challenge = response.challenge
    assert challenge.payment_id.startswith("x402_")
    assert challenge.resource_uri == "/protected/data"
    assert challenge.amount == "5000000"
    assert challenge.currency == "USDC"
    assert challenge.payee_address == "0xMerchant"
    assert challenge.network == "polygon"
    assert challenge.token_address == "0xUSDCToken"
    assert challenge.expires_at > int(time.time())
    assert challenge.expires_at <= int(time.time()) + 600
    assert len(challenge.nonce) == 32  # UUID hex without dashes


# --- Test 2: Challenge serialization/deserialization round-trip ---


def test_challenge_serialization_roundtrip(sample_challenge: X402Challenge):
    """Test that a challenge can be serialized and deserialized without loss."""
    serialized = serialize_challenge_header(sample_challenge)

    # Verify it's base64-encoded JSON
    assert isinstance(serialized, str)
    decoded_json = base64.b64decode(serialized).decode()
    data = json.loads(decoded_json)

    # Verify all fields present
    assert data["payment_id"] == sample_challenge.payment_id
    assert data["resource_uri"] == sample_challenge.resource_uri
    assert data["amount"] == sample_challenge.amount
    assert data["currency"] == sample_challenge.currency
    assert data["payee_address"] == sample_challenge.payee_address
    assert data["network"] == sample_challenge.network
    assert data["token_address"] == sample_challenge.token_address
    assert data["expires_at"] == sample_challenge.expires_at
    assert data["nonce"] == sample_challenge.nonce

    # Parse back
    parsed = parse_challenge_header(serialized)
    assert parsed.payment_id == sample_challenge.payment_id
    assert parsed.resource_uri == sample_challenge.resource_uri
    assert parsed.amount == sample_challenge.amount
    assert parsed.currency == sample_challenge.currency
    assert parsed.payee_address == sample_challenge.payee_address
    assert parsed.network == sample_challenge.network
    assert parsed.token_address == sample_challenge.token_address
    assert parsed.expires_at == sample_challenge.expires_at
    assert parsed.nonce == sample_challenge.nonce


# --- Test 3: Payment payload construction from challenge ---


def test_payment_payload_construction_from_challenge(sample_challenge: X402Challenge):
    """Test constructing a valid payment payload from a challenge."""
    payload = X402PaymentPayload(
        payment_id=sample_challenge.payment_id,
        payer_address="0xCustomer",
        amount=sample_challenge.amount,
        nonce=sample_challenge.nonce,
        signature="0xsignature",
        authorization={"extra": "data"},
    )

    assert payload.payment_id == sample_challenge.payment_id
    assert payload.payer_address == "0xCustomer"
    assert payload.amount == sample_challenge.amount
    assert payload.nonce == sample_challenge.nonce
    assert payload.signature == "0xsignature"
    assert payload.authorization == {"extra": "data"}


# --- Test 4: Payment payload verification (happy path) ---


def test_payment_payload_verification_success(
    sample_challenge: X402Challenge,
    sample_payment_payload: X402PaymentPayload,
):
    """Test successful verification of a valid payment payload."""
    result = verify_payment_payload(
        sample_payment_payload,
        sample_challenge,
        now=int(time.time()),
    )

    assert isinstance(result, X402VerificationResult)
    assert result.accepted is True
    assert result.reason is None
    assert result.payload == sample_payment_payload


# --- Test 5: Nonce mismatch rejection ---


def test_payment_payload_nonce_mismatch_rejected(sample_challenge: X402Challenge):
    """Test that a payload with mismatched nonce is rejected."""
    payload = X402PaymentPayload(
        payment_id=sample_challenge.payment_id,
        payer_address="0xPayer",
        amount=sample_challenge.amount,
        nonce="wrong_nonce",  # Mismatch
        signature="0xsig",
    )

    result = verify_payment_payload(payload, sample_challenge)

    assert result.accepted is False
    assert result.reason == "x402_nonce_mismatch"
    assert result.payload is None


# --- Test 6: Amount mismatch rejection ---


def test_payment_payload_amount_mismatch_rejected(sample_challenge: X402Challenge):
    """Test that a payload with mismatched amount is rejected."""
    payload = X402PaymentPayload(
        payment_id=sample_challenge.payment_id,
        payer_address="0xPayer",
        amount="999999",  # Different from challenge
        nonce=sample_challenge.nonce,
        signature="0xsig",
    )

    result = verify_payment_payload(payload, sample_challenge)

    assert result.accepted is False
    assert result.reason == "x402_amount_mismatch"
    assert result.payload is None


# --- Test 7: Expired challenge rejection ---


def test_expired_challenge_rejected(sample_challenge: X402Challenge):
    """Test that an expired challenge is rejected."""
    # Set current time to after expiration
    future_time = sample_challenge.expires_at + 10

    payload = X402PaymentPayload(
        payment_id=sample_challenge.payment_id,
        payer_address="0xPayer",
        amount=sample_challenge.amount,
        nonce=sample_challenge.nonce,
        signature="0xsig",
    )

    result = verify_payment_payload(payload, sample_challenge, now=future_time)

    assert result.accepted is False
    assert result.reason == "x402_challenge_expired"
    assert result.payload is None


# --- Test 8: ERC-3009 authorization struct construction ---


def test_erc3009_authorization_construction():
    """Test building ERC-3009 TransferWithAuthorization typed data."""
    now = int(time.time())
    auth_data = build_transfer_authorization(
        from_addr="0xAAAA",
        to_addr="0xBBBB",
        value=5000000,
        valid_after=now - 60,
        valid_before=now + 300,
        nonce="0xdeadbeef",
    )

    assert auth_data["primaryType"] == "TransferWithAuthorization"
    assert "types" in auth_data
    assert "domain" in auth_data
    assert "message" in auth_data

    message = auth_data["message"]
    assert message["from"] == "0xAAAA"
    assert message["to"] == "0xBBBB"
    assert message["value"] == "5000000"
    assert message["validAfter"] == str(now - 60)
    assert message["validBefore"] == str(now + 300)
    assert message["nonce"] == "0xdeadbeef"


# --- Test 9: ERC-3009 timing validation (valid_after <= now <= valid_before) ---


def test_erc3009_timing_validation_success(sample_erc3009_auth: ERC3009Authorization):
    """Test that valid timing passes validation."""
    now = int(time.time())
    is_valid, reason = validate_authorization_timing(sample_erc3009_auth, now=now)

    assert is_valid is True
    assert reason is None


def test_erc3009_timing_not_yet_valid():
    """Test rejection when current time is before valid_after."""
    now = int(time.time())
    auth = ERC3009Authorization(
        from_address="0x1111",
        to_address="0x2222",
        value=1000000,
        valid_after=now + 100,  # Future
        valid_before=now + 300,
        nonce="0xaa",
    )

    is_valid, reason = validate_authorization_timing(auth, now=now)

    assert is_valid is False
    assert reason == "authorization_not_yet_valid"


def test_erc3009_timing_expired():
    """Test rejection when current time is after valid_before."""
    now = int(time.time())
    auth = ERC3009Authorization(
        from_address="0x1111",
        to_address="0x2222",
        value=1000000,
        valid_after=now - 300,
        valid_before=now - 100,  # Past
        nonce="0xaa",
    )

    is_valid, reason = validate_authorization_timing(auth, now=now)

    assert is_valid is False
    assert reason == "authorization_expired"


def test_erc3009_timing_invalid_range():
    """Test rejection when valid_after >= valid_before."""
    now = int(time.time())
    auth = ERC3009Authorization(
        from_address="0x1111",
        to_address="0x2222",
        value=1000000,
        valid_after=now + 100,
        valid_before=now + 50,  # Before valid_after
        nonce="0xaa",
    )

    is_valid, reason = validate_authorization_timing(auth, now=now)

    assert is_valid is False
    assert reason == "valid_after_must_be_before_valid_before"


# --- Test 10: Verify/settle separation (verify does not settle) ---


@pytest.mark.asyncio
async def test_verify_does_not_settle(
    sample_challenge: X402Challenge,
    sample_payment_payload: X402PaymentPayload,
):
    """Test that verify() does not initiate on-chain settlement."""
    store = InMemorySettlementStore()
    settler = X402Settler(store=store, chain_executor=None)

    settlement = await settler.verify(sample_challenge, sample_payment_payload)

    # Verify creates a VERIFIED settlement but does not touch blockchain
    assert settlement.status == X402SettlementStatus.VERIFIED
    assert settlement.tx_hash is None
    assert settlement.settled_at is None
    assert settlement.error is None

    # Check it was persisted
    stored = await settler.check_settlement(sample_payment_payload.payment_id)
    assert stored is not None
    assert stored.status == X402SettlementStatus.VERIFIED


# --- Test 11: Settlement status transitions (VERIFIED -> SETTLING -> SETTLED) ---


@pytest.mark.asyncio
async def test_settlement_status_transitions(
    sample_challenge: X402Challenge,
    sample_payment_payload: X402PaymentPayload,
):
    """Test the full settlement lifecycle status transitions."""
    store = InMemorySettlementStore()

    # Mock chain executor (just needs to exist)
    class MockChainExecutor:
        pass

    settler = X402Settler(store=store, chain_executor=MockChainExecutor())

    # Step 1: Verify - should be VERIFIED
    settlement = await settler.verify(sample_challenge, sample_payment_payload)
    assert settlement.status == X402SettlementStatus.VERIFIED

    # Step 2: Settle - should transition VERIFIED -> SETTLING -> SETTLED
    final_settlement = await settler.settle(settlement)
    assert final_settlement.status == X402SettlementStatus.SETTLED
    assert final_settlement.tx_hash is not None
    assert final_settlement.settled_at is not None

    # Verify persistence
    stored = await settler.check_settlement(sample_payment_payload.payment_id)
    assert stored is not None
    assert stored.status == X402SettlementStatus.SETTLED


@pytest.mark.asyncio
async def test_cannot_settle_non_verified_settlement(sample_challenge: X402Challenge):
    """Test that settle() rejects non-VERIFIED settlements."""
    store = InMemorySettlementStore()
    settler = X402Settler(store=store, chain_executor=object())

    # Create a settlement that's already SETTLED
    settlement = X402Settlement(
        payment_id="test_settled",
        status=X402SettlementStatus.SETTLED,
        challenge=sample_challenge,
    )
    await store.save(settlement)

    # Should raise error
    with pytest.raises(ValueError, match="cannot_settle"):
        await settler.settle(settlement)


# --- Test 12: v2 header construction and parsing ---


def test_v2_payment_required_header_construction(sample_challenge: X402Challenge):
    """Test constructing the v2 PaymentRequired header."""
    headers = X402HeaderBuilder.build_payment_required_header(sample_challenge)

    assert X402_PAYMENT_REQUIRED_HEADER in headers
    assert "Content-Type" in headers
    assert headers["Content-Type"] == "application/json"

    # Verify the header value can be parsed back
    parsed = parse_challenge_header(headers[X402_PAYMENT_REQUIRED_HEADER])
    assert parsed.payment_id == sample_challenge.payment_id


def test_v2_payment_signature_header_construction(
    sample_payment_payload: X402PaymentPayload,
):
    """Test constructing and parsing the v2 PAYMENT-SIGNATURE header."""
    headers = X402HeaderBuilder.build_payment_signature_header(sample_payment_payload)

    assert X402_PAYMENT_SIGNATURE_HEADER in headers
    header_value = headers[X402_PAYMENT_SIGNATURE_HEADER]

    # Parse it back
    parsed = X402HeaderBuilder.parse_payment_signature_header(header_value)
    assert parsed.payment_id == sample_payment_payload.payment_id
    assert parsed.payer_address == sample_payment_payload.payer_address
    assert parsed.amount == sample_payment_payload.amount
    assert parsed.nonce == sample_payment_payload.nonce
    assert parsed.signature == sample_payment_payload.signature
    assert parsed.authorization == sample_payment_payload.authorization


def test_v2_payment_response_header_construction():
    """Test constructing the v2 PAYMENT-RESPONSE header."""
    settlement_data = {
        "payment_id": "x402_test",
        "status": "settled",
        "tx_hash": "0xabcdef",
    }

    headers = X402HeaderBuilder.build_payment_response_header(settlement_data)

    assert X402_PAYMENT_RESPONSE_HEADER in headers
    header_value = headers[X402_PAYMENT_RESPONSE_HEADER]

    # Parse it back
    decoded = json.loads(base64.b64decode(header_value))
    assert decoded["payment_id"] == "x402_test"
    assert decoded["status"] == "settled"
    assert decoded["tx_hash"] == "0xabcdef"


# --- Test 13: Backward compatibility with v1 schemas ---


def test_v1_version_validation():
    """Test that v1 version string is accepted."""
    is_valid, reason = validate_x402_version(X402_VERSION_1)
    assert is_valid is True
    assert reason is None


def test_v2_version_validation():
    """Test that v2 version string is accepted."""
    is_valid, reason = validate_x402_version(X402_VERSION_2)
    assert is_valid is True
    assert reason is None


def test_unsupported_version_rejected():
    """Test that unsupported version strings are rejected."""
    is_valid, reason = validate_x402_version("3.0")
    assert is_valid is False
    assert reason == "x402_version_unsupported:3.0"


def test_empty_version_accepted():
    """Test that empty version string is accepted (defaults to v1)."""
    is_valid, reason = validate_x402_version("")
    assert is_valid is True
    assert reason is None


# --- Test 14: Payment_id mismatch rejection ---


def test_payment_id_mismatch_rejected(sample_challenge: X402Challenge):
    """Test that a payload with mismatched payment_id is rejected."""
    payload = X402PaymentPayload(
        payment_id="wrong_payment_id",  # Mismatch
        payer_address="0xPayer",
        amount=sample_challenge.amount,
        nonce=sample_challenge.nonce,
        signature="0xsig",
    )

    result = verify_payment_payload(payload, sample_challenge)

    assert result.accepted is False
    assert result.reason == "x402_payment_id_mismatch"
    assert result.payload is None


# --- Test 15: ERC-3009 authorization encoding ---


def test_erc3009_authorization_encoding(sample_erc3009_auth: ERC3009Authorization):
    """Test ABI encoding of ERC-3009 authorization parameters."""
    encoded = encode_authorization_params(sample_erc3009_auth)

    # Should be 9 parameters * 32 bytes each = 288 bytes
    assert isinstance(encoded, bytes)
    assert len(encoded) == 288

    # Verify it's valid bytes (doesn't raise)
    assert encoded is not None


# --- Test 16: Settlement with verification failure ---


@pytest.mark.asyncio
async def test_verify_with_invalid_payload_creates_failed_settlement(
    sample_challenge: X402Challenge,
):
    """Test that verify() creates FAILED settlement for invalid payloads."""
    store = InMemorySettlementStore()
    settler = X402Settler(store=store)

    # Create invalid payload (wrong nonce)
    invalid_payload = X402PaymentPayload(
        payment_id=sample_challenge.payment_id,
        payer_address="0xPayer",
        amount=sample_challenge.amount,
        nonce="wrong_nonce",
        signature="0xsig",
    )

    settlement = await settler.verify(sample_challenge, invalid_payload)

    assert settlement.status == X402SettlementStatus.FAILED
    assert settlement.error == "x402_nonce_mismatch"
    assert settlement.tx_hash is None

    # Check persistence
    stored = await settler.check_settlement(sample_challenge.payment_id)
    assert stored is not None
    assert stored.status == X402SettlementStatus.FAILED


# --- Test 17: Signature verification callback ---


def test_payment_payload_signature_verification_with_callback(
    sample_challenge: X402Challenge,
):
    """Test that signature verification callback is invoked and respected."""

    def mock_verify_signature(canonical: bytes, signature: str, address: str) -> bool:
        # Mock verification - only accept specific signature
        return signature == "0xvalid_signature"

    # Valid signature
    valid_payload = X402PaymentPayload(
        payment_id=sample_challenge.payment_id,
        payer_address="0xPayer",
        amount=sample_challenge.amount,
        nonce=sample_challenge.nonce,
        signature="0xvalid_signature",
    )

    result = verify_payment_payload(
        valid_payload,
        sample_challenge,
        verify_signature_fn=mock_verify_signature,
    )
    assert result.accepted is True

    # Invalid signature
    invalid_payload = X402PaymentPayload(
        payment_id=sample_challenge.payment_id,
        payer_address="0xPayer",
        amount=sample_challenge.amount,
        nonce=sample_challenge.nonce,
        signature="0xinvalid_signature",
    )

    result = verify_payment_payload(
        invalid_payload,
        sample_challenge,
        verify_signature_fn=mock_verify_signature,
    )
    assert result.accepted is False
    assert result.reason == "x402_signature_invalid"
