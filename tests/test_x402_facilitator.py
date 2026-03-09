"""Tests for x402 facilitator API router."""
from __future__ import annotations

import base64
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_api.routers.x402 import router


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v2/x402")
    return app


def _make_challenge_header(**overrides):
    """Generate a valid base64-encoded challenge header."""
    from sardis_protocol.x402 import generate_challenge, serialize_challenge_header
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


def test_verify_endpoint():
    """POST /verify accepts a valid payload."""
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
    assert body["payment_id"] == challenge.payment_id
    # Without signature verification, should still be accepted
    assert "accepted" in body


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
