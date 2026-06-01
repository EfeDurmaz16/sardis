"""Conformance tests for canonical x402 v1 on the resource-server middleware.

Verifies the middleware emits the canonical 402 ``accepts:[PaymentRequirements]``
body, reads the canonical ``X-PAYMENT`` request header, and returns the canonical
``X-PAYMENT-RESPONSE`` header. The fail-closed verification gate (EIP-3009) is
exercised end-to-end through the middleware without needing a live chain.
"""
from __future__ import annotations

import base64
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.middleware.x402 import (
    X402_X_PAYMENT_HEADER,
    X402_X_PAYMENT_RESPONSE_HEADER,
    X402MiddlewareConfig,
    X402PaymentMiddleware,
    X402PricingRegistry,
    X402PricingRule,
)

PAYEE = "0x" + "a" * 40


def _create_test_app(*, network="base-sepolia") -> FastAPI:
    app = FastAPI()
    pricing = X402PricingRegistry()
    # Use a Sardis network id on the rule (middleware maps it to canonical).
    sardis_net = "base_sepolia" if network == "base-sepolia" else network
    pricing.add_rule(
        X402PricingRule(path_prefix="/api/v2/data", amount="10000", network=sardis_net)
    )
    config = X402MiddlewareConfig(
        pricing_registry=pricing, payee_address=PAYEE, enabled=True
    )
    app.add_middleware(X402PaymentMiddleware, config=config)

    @app.get("/api/v2/data")
    async def get_data():
        return {"data": "hello"}

    return app


def test_402_body_carries_canonical_accepts():
    client = TestClient(_create_test_app())
    resp = client.get("/api/v2/data")
    assert resp.status_code == 402
    body = resp.json()
    assert body["x402Version"] == 1
    assert "accepts" in body
    accept = body["accepts"][0]
    assert accept["scheme"] == "exact"
    assert accept["network"] == "base-sepolia"
    assert accept["maxAmountRequired"] == "10000"
    assert accept["payTo"] == PAYEE
    assert accept["maxTimeoutSeconds"] >= 1
    # EIP-712 token domain advertised from Sardis's hardcoded USDC domain.
    assert accept["extra"]["name"] == "USDC"
    assert accept["extra"]["version"] == "2"


def _sign_x_payment(*, to, value, network="base-sepolia", valid_before=9999999999, signer=None):
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    from sardis.protocol.x402_canonical import (
        ExactEvmAuthorization,
        PaymentPayload,
        encode_x_payment_header,
    )
    from sardis.protocol.x402_erc3009 import (
        TRANSFER_WITH_AUTHORIZATION_TYPE,
        resolve_eip712_domain,
    )

    acct = signer or Account.create()
    nonce_hex = "0x" + "33" * 32
    domain = resolve_eip712_domain("base_sepolia")
    message = {
        "from": acct.address,
        "to": to,
        "value": int(value),
        "validAfter": 0,
        "validBefore": valid_before,
        "nonce": bytes.fromhex(nonce_hex[2:]),
    }
    signable = encode_typed_data(
        domain, {"TransferWithAuthorization": TRANSFER_WITH_AUTHORIZATION_TYPE}, message
    )
    signed = acct.sign_message(signable)
    auth = ExactEvmAuthorization(
        from_=acct.address,
        to=to,
        value=str(value),
        valid_after="0",
        valid_before=str(valid_before),
        nonce=nonce_hex,
    )
    payload = PaymentPayload(
        scheme="exact", network=network, signature="0x" + signed.signature.hex(), authorization=auth
    )
    return acct.address, encode_x_payment_header(payload)


def test_canonical_x_payment_forged_signature_rejected_with_payment_response():
    """A forged X-PAYMENT is rejected at the verify gate (before any broadcast),
    and the failure is signaled via a canonical X-PAYMENT-RESPONSE header."""
    client = TestClient(_create_test_app())

    # Sign a valid auth, then splice in a different signer's signature.
    _payer, _good_xp = _sign_x_payment(to=PAYEE, value=10000)
    # Build a forged X-PAYMENT: same authorization, attacker signature.
    from eth_account import Account

    victim = Account.create()
    attacker = Account.create()
    _v, victim_xp = _sign_x_payment(to=PAYEE, value=10000, signer=victim)
    # Decode victim payload, replace signature with attacker's over a different msg.
    from eth_account.messages import encode_typed_data
    from sardis.protocol.x402_canonical import (
        decode_x_payment_header,
        encode_x_payment_header,
    )
    from sardis.protocol.x402_erc3009 import (
        TRANSFER_WITH_AUTHORIZATION_TYPE,
        resolve_eip712_domain,
    )

    vp = decode_x_payment_header(victim_xp)
    domain = resolve_eip712_domain("base_sepolia")
    attacker_msg = {
        "from": attacker.address,
        "to": PAYEE,
        "value": 10000,
        "validAfter": 0,
        "validBefore": 9999999999,
        "nonce": bytes.fromhex(vp.authorization.nonce[2:]),
    }
    attacker_sig = attacker.sign_message(
        encode_typed_data(domain, {"TransferWithAuthorization": TRANSFER_WITH_AUTHORIZATION_TYPE}, attacker_msg)
    )
    vp.signature = "0x" + attacker_sig.signature.hex()
    forged_xp = encode_x_payment_header(vp)

    resp = client.get("/api/v2/data", headers={X402_X_PAYMENT_HEADER: forged_xp})
    assert resp.status_code == 402
    assert resp.json()["x402Version"] == 1
    # Canonical X-PAYMENT-RESPONSE header present and decodes to a failure.
    pr = resp.headers.get(X402_X_PAYMENT_RESPONSE_HEADER)
    assert pr
    decoded = json.loads(base64.b64decode(pr))
    assert decoded["success"] is False
    assert decoded["transaction"] == ""
    assert decoded["network"] == "base-sepolia"
    assert decoded["errorReason"] == "invalid_exact_evm_payload_signature"


def test_canonical_x_payment_amount_tamper_rejected():
    client = TestClient(_create_test_app())
    # Sign value=1, but the rule requires 10000.
    _payer, xp = _sign_x_payment(to=PAYEE, value=1)
    resp = client.get("/api/v2/data", headers={X402_X_PAYMENT_HEADER: xp})
    assert resp.status_code == 402
    pr = resp.headers.get(X402_X_PAYMENT_RESPONSE_HEADER)
    decoded = json.loads(base64.b64decode(pr))
    assert decoded["success"] is False
    assert decoded["errorReason"] == "invalid_exact_evm_payload_authorization_value"


def test_canonical_x_payment_malformed_header_rejected():
    client = TestClient(_create_test_app())
    resp = client.get("/api/v2/data", headers={X402_X_PAYMENT_HEADER: "not!base64!"})
    assert resp.status_code == 402
    pr = resp.headers.get(X402_X_PAYMENT_RESPONSE_HEADER)
    decoded = json.loads(base64.b64decode(pr))
    assert decoded["success"] is False
    assert decoded["errorReason"] == "invalid_payload"
