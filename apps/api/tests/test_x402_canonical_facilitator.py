"""Conformance tests for the canonical x402 v1 facilitator endpoints.

Exercises the real canonical wire format end-to-end against the EIP-3009 /
EIP-712 verifier:
- POST /verify with {x402Version, paymentPayload, paymentRequirements}
  → {isValid, payer, invalidReason?}
- GET /supported → {kinds:[...]}
plus bad-case rejections expressed in the canonical wire format (forged sig,
tampered amount, recipient mismatch, wrong network, expired, unsupported scheme).
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.routes.protocol.x402 import router

NETWORK = "base-sepolia"  # canonical id; Sardis "base_sepolia"
SARDIS_NETWORK = "base_sepolia"


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v2/x402")
    return app


def _domain():
    from sardis.protocol.x402_erc3009 import resolve_eip712_domain

    return resolve_eip712_domain(SARDIS_NETWORK)


def _sign_authorization(*, to, value, valid_after=0, valid_before=9999999999, signer=None):
    """Produce (payer_address, authorization_dict, signature_hex) for the canonical wire."""
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    from sardis.protocol.x402_erc3009 import TRANSFER_WITH_AUTHORIZATION_TYPE

    acct = signer or Account.create()
    nonce_hex = "0x" + "22" * 32
    message = {
        "from": acct.address,
        "to": to,
        "value": int(value),
        "validAfter": valid_after,
        "validBefore": valid_before,
        "nonce": bytes.fromhex(nonce_hex[2:]),
    }
    signable = encode_typed_data(
        _domain(),
        {"TransferWithAuthorization": TRANSFER_WITH_AUTHORIZATION_TYPE},
        message,
    )
    signed = acct.sign_message(signable)
    auth = {
        "from": acct.address,
        "to": to,
        "value": str(value),
        "validAfter": str(valid_after),
        "validBefore": str(valid_before),
        "nonce": nonce_hex,
    }
    return acct.address, auth, "0x" + signed.signature.hex()


def _requirements(*, pay_to, max_amount, network=NETWORK, asset=None, extra=None):
    return {
        "scheme": "exact",
        "network": network,
        "maxAmountRequired": str(max_amount),
        "asset": asset or "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        "payTo": pay_to,
        "resource": "https://api.example.com/premium-data",
        "description": "Access to premium market data",
        "maxTimeoutSeconds": 60,
        "mimeType": "application/json",
        "outputSchema": None,
        "extra": extra if extra is not None else {"name": "USDC", "version": "2"},
    }


def _payload(*, network=NETWORK, signature, authorization):
    return {
        "x402Version": 1,
        "scheme": "exact",
        "network": network,
        "payload": {"signature": signature, "authorization": authorization},
    }


def _verify(client, payload, requirements):
    return client.post(
        "/api/v2/x402/verify",
        json={"x402Version": 1, "paymentPayload": payload, "paymentRequirements": requirements},
    )


# --- GET /supported --------------------------------------------------------

def test_supported_returns_canonical_kinds():
    client = TestClient(_create_test_app())
    resp = client.get("/api/v2/x402/supported")
    assert resp.status_code == 200
    body = resp.json()
    assert "kinds" in body
    nets = {k["network"] for k in body["kinds"]}
    assert "base" in nets and "base-sepolia" in nets
    for k in body["kinds"]:
        assert k["x402Version"] == 1
        assert k["scheme"] == "exact"


# --- Happy path ------------------------------------------------------------

def test_canonical_verify_accepts_valid_signature():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    payer, auth, sig = _sign_authorization(to=pay_to, value=10000)
    resp = _verify(
        client,
        _payload(signature=sig, authorization=auth),
        _requirements(pay_to=pay_to, max_amount=10000),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["isValid"] is True, body
    assert body["payer"].lower() == payer.lower()
    assert body.get("invalidReason") is None


# --- Bad-case rejections (canonical wire) ----------------------------------

def test_canonical_verify_rejects_forged_signature():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    payer, auth, _good = _sign_authorization(to=pay_to, value=10000)
    # Attacker signs a DIFFERENT authorization; splice their sig onto victim auth.
    _att_payer, _att_auth, attacker_sig = _sign_authorization(to=pay_to, value=10000)
    resp = _verify(
        client,
        _payload(signature=attacker_sig, authorization=auth),
        _requirements(pay_to=pay_to, max_amount=10000),
    )
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_exact_evm_payload_signature"


def test_canonical_verify_rejects_amount_tamper():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    # Signed value=1, but requirements demand 10000.
    _payer, auth, sig = _sign_authorization(to=pay_to, value=1)
    resp = _verify(
        client,
        _payload(signature=sig, authorization=auth),
        _requirements(pay_to=pay_to, max_amount=10000),
    )
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_exact_evm_payload_authorization_value"


def test_canonical_verify_rejects_recipient_mismatch():
    client = TestClient(_create_test_app())
    signed_to = "0x" + "b" * 40
    required_to = "0x" + "a" * 40
    _payer, auth, sig = _sign_authorization(to=signed_to, value=10000)
    resp = _verify(
        client,
        _payload(signature=sig, authorization=auth),
        _requirements(pay_to=required_to, max_amount=10000),
    )
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_exact_evm_payload_recipient_mismatch"


def test_canonical_verify_rejects_expired_authorization():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    # validBefore in the past → expired.
    _payer, auth, sig = _sign_authorization(
        to=pay_to, value=10000, valid_after=0, valid_before=1
    )
    resp = _verify(
        client,
        _payload(signature=sig, authorization=auth),
        _requirements(pay_to=pay_to, max_amount=10000),
    )
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_exact_evm_payload_authorization_valid_before"


def test_canonical_verify_rejects_not_yet_valid():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    # validAfter far in the future → not yet valid.
    _payer, auth, sig = _sign_authorization(
        to=pay_to, value=10000, valid_after=9999999990, valid_before=9999999999
    )
    resp = _verify(
        client,
        _payload(signature=sig, authorization=auth),
        _requirements(pay_to=pay_to, max_amount=10000),
    )
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_exact_evm_payload_authorization_valid_after"


def test_canonical_verify_rejects_network_mismatch_between_payload_and_requirements():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    _payer, auth, sig = _sign_authorization(to=pay_to, value=10000)
    payload = _payload(network="base", signature=sig, authorization=auth)
    requirements = _requirements(pay_to=pay_to, max_amount=10000, network="base-sepolia")
    resp = _verify(client, payload, requirements)
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_network"


def test_canonical_verify_rejects_unknown_network():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    _payer, auth, sig = _sign_authorization(to=pay_to, value=10000)
    payload = _payload(network="solana", signature=sig, authorization=auth)
    requirements = _requirements(pay_to=pay_to, max_amount=10000, network="solana")
    resp = _verify(client, payload, requirements)
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_network"


def test_canonical_verify_rejects_unsupported_scheme():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    _payer, auth, sig = _sign_authorization(to=pay_to, value=10000)
    payload = {
        "x402Version": 1,
        "scheme": "permit2",
        "network": NETWORK,
        "payload": {"signature": sig, "authorization": auth},
    }
    requirements = _requirements(pay_to=pay_to, max_amount=10000)
    resp = _verify(client, payload, requirements)
    body = resp.json()
    assert body["isValid"] is False
    # Decode of the payload rejects an unsupported scheme before verify runs.
    assert body["invalidReason"] == "unsupported_scheme"


def test_canonical_verify_rejects_tampered_extra_domain():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    _payer, auth, sig = _sign_authorization(to=pay_to, value=10000)
    # Attacker-supplied EIP-712 domain in extra that does NOT match Sardis's
    # hardcoded USDC domain for base-sepolia ("USDC","2").
    requirements = _requirements(
        pay_to=pay_to, max_amount=10000, extra={"name": "Evil Token", "version": "9"}
    )
    resp = _verify(client, _payload(signature=sig, authorization=auth), requirements)
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_payment_requirements"


def test_canonical_verify_rejects_wrong_x402_version():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    _payer, auth, sig = _sign_authorization(to=pay_to, value=10000)
    payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": NETWORK,
        "payload": {"signature": sig, "authorization": auth},
    }
    resp = _verify(client, payload, _requirements(pay_to=pay_to, max_amount=10000))
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_x402_version"


def test_canonical_verify_rejects_malformed_requirements():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    _payer, auth, sig = _sign_authorization(to=pay_to, value=10000)
    resp = client.post(
        "/api/v2/x402/verify",
        json={
            "x402Version": 1,
            "paymentPayload": _payload(signature=sig, authorization=auth),
            "paymentRequirements": {"scheme": "exact"},  # missing required fields
        },
    )
    body = resp.json()
    assert body["isValid"] is False
    assert body["invalidReason"] == "invalid_payment_requirements"


# --- Settle re-verifies (fail-closed before any broadcast) -----------------

def test_canonical_settle_rejects_forged_before_broadcast():
    client = TestClient(_create_test_app())
    pay_to = "0x" + "a" * 40
    _payer, auth, _good = _sign_authorization(to=pay_to, value=10000)
    _a, _aa, attacker_sig = _sign_authorization(to=pay_to, value=10000)
    resp = client.post(
        "/api/v2/x402/settle",
        json={
            "x402Version": 1,
            "paymentPayload": _payload(signature=attacker_sig, authorization=auth),
            "paymentRequirements": _requirements(pay_to=pay_to, max_amount=10000),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["transaction"] == ""
    assert body["errorReason"] == "invalid_exact_evm_payload_signature"
