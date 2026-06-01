"""Tests for x402 facilitator API router."""
from __future__ import annotations

import base64
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.routes.protocol.x402 import router


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v2/x402")
    return app


def _make_challenge_header(**overrides):
    """Generate a valid base64-encoded challenge header."""
    from sardis.protocol.x402 import generate_challenge, serialize_challenge_header
    challenge_resp = generate_challenge(
        resource_uri=overrides.get("resource_uri", "https://api.example.com/data"),
        amount=overrides.get("amount", "1000000"),
        currency=overrides.get("currency", "USDC"),
        payee_address=overrides.get("payee_address", "0x" + "a" * 40),
        network=overrides.get("network", "base"),
        ttl_seconds=overrides.get("ttl_seconds", 300),
    )
    challenge = challenge_resp.challenge
    header = serialize_challenge_header(challenge)
    return header, challenge


def test_challenge_generation():
    """POST /challenges generates a valid challenge."""
    app = _create_test_app()
    client = TestClient(app)

    response = client.post("/api/v2/x402/challenges", json={
        "resource_uri": "https://api.example.com/data",
        "amount": "1000000",
        "currency": "USDC",
        "network": "base",
        "payee_address": "0x" + "a" * 40,
        "ttl_seconds": 300,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "1000000"
    assert body["currency"] == "USDC"
    assert body["network"] == "base"
    assert "payment_id" in body
    assert "nonce" in body
    assert "challenge_header" in body

    # Verify the challenge_header is valid base64
    decoded = json.loads(base64.b64decode(body["challenge_header"]))
    assert decoded["payment_id"] == body["payment_id"]


def _signed_authorization(challenge, *, value=None, network=None):
    """Produce a real EIP-3009 signed authorization + payer for a challenge.

    Returns (payer_address, authorization_dict, signature_hex).
    """
    from eth_account import Account
    from eth_account.messages import encode_typed_data

    from sardis.protocol.x402_erc3009 import (
        TRANSFER_WITH_AUTHORIZATION_TYPE,
        resolve_eip712_domain,
    )

    acct = Account.create()
    nonce_hex = "0x" + "11" * 32
    amount = value if value is not None else int(challenge.amount)
    domain = resolve_eip712_domain(network or challenge.network)
    message = {
        "from": acct.address,
        "to": challenge.payee_address,
        "value": amount,
        "validAfter": 0,
        "validBefore": 9999999999,
        "nonce": bytes.fromhex(nonce_hex[2:]),
    }
    signable = encode_typed_data(
        domain,
        {"TransferWithAuthorization": TRANSFER_WITH_AUTHORIZATION_TYPE},
        message,
    )
    signed = acct.sign_message(signable)
    auth = {
        "from": acct.address,
        "to": challenge.payee_address,
        "value": str(amount),
        "validAfter": 0,
        "validBefore": 9999999999,
        "nonce": nonce_hex,
    }
    return acct.address, auth, "0x" + signed.signature.hex()


def test_verify_accepts_valid_eip3009_signature():
    """POST /verify accepts a payload with a real, valid EIP-3009 signature."""
    app = _create_test_app()
    client = TestClient(app)

    header, challenge = _make_challenge_header()
    payer, auth, signature = _signed_authorization(challenge)

    response = client.post("/api/v2/x402/verify", json={
        "payment_id": challenge.payment_id,
        "payer_address": payer,
        "amount": challenge.amount,
        "nonce": challenge.nonce,
        "signature": signature,
        "authorization": auth,
        "challenge_header": header,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["payment_id"] == challenge.payment_id
    assert body["accepted"] is True, body


def test_verify_rejects_unsigned_payload():
    """A payload with a junk signature and no authorization is REJECTED.

    This is the core fail-closed guarantee: x402 /verify must never accept an
    unverified payment proof. (Was previously 'accepted without sig'.)
    """
    app = _create_test_app()
    client = TestClient(app)

    header, challenge = _make_challenge_header()

    response = client.post("/api/v2/x402/verify", json={
        "payment_id": challenge.payment_id,
        "payer_address": "0x" + "c" * 40,
        "amount": challenge.amount,
        "nonce": challenge.nonce,
        "signature": "test_signature",
        "challenge_header": header,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert "authorization_missing" in body["reason"] or "signature" in body["reason"]


def test_verify_rejects_forged_signature():
    """A valid authorization signed by a DIFFERENT key (forged) is REJECTED."""
    app = _create_test_app()
    client = TestClient(app)

    header, challenge = _make_challenge_header()
    payer, auth, _good_sig = _signed_authorization(challenge)

    # Attacker keeps the victim's authorization/payer but supplies a signature
    # from their own (different) challenge — recovery will not match payer.
    _other_header, other_challenge = _make_challenge_header()
    _attacker, _attacker_auth, attacker_sig = _signed_authorization(other_challenge)

    response = client.post("/api/v2/x402/verify", json={
        "payment_id": challenge.payment_id,
        "payer_address": payer,
        "amount": challenge.amount,
        "nonce": challenge.nonce,
        "signature": attacker_sig,
        "authorization": auth,
        "challenge_header": header,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert "signature_invalid" in body["reason"]


def test_verify_rejects_authorization_amount_tamper():
    """An authorization whose value != challenge amount is REJECTED."""
    app = _create_test_app()
    client = TestClient(app)

    header, challenge = _make_challenge_header()
    # Sign for a different (smaller) value than the challenge demands.
    payer, auth, signature = _signed_authorization(challenge, value=1)

    response = client.post("/api/v2/x402/verify", json={
        "payment_id": challenge.payment_id,
        "payer_address": payer,
        "amount": challenge.amount,
        "nonce": challenge.nonce,
        "signature": signature,
        "authorization": auth,
        "challenge_header": header,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert "value_mismatch" in body["reason"]


def test_dry_run_returns_preview():
    """POST /dry-run returns simulation results."""
    app = _create_test_app()
    client = TestClient(app)

    header, challenge = _make_challenge_header()

    response = client.post("/api/v2/x402/dry-run", json={
        "payment_id": challenge.payment_id,
        "payer_address": "0x" + "c" * 40,
        "amount": challenge.amount,
        "nonce": challenge.nonce,
        "challenge_header": header,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["payment_id"] == challenge.payment_id
    assert "would_succeed" in body


def test_verify_invalid_challenge_header():
    """Invalid challenge_header returns not accepted."""
    app = _create_test_app()
    client = TestClient(app)

    response = client.post("/api/v2/x402/verify", json={
        "payment_id": "x402_bad",
        "payer_address": "0x" + "c" * 40,
        "amount": "1000000",
        "nonce": "bad_nonce",
        "signature": "bad_sig",
        "challenge_header": "not_valid_base64!!!",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert "invalid_challenge" in body["reason"]
