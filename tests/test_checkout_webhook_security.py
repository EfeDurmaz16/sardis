from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_server.routes.commerce.checkout import (
    CheckoutDependencies,
    get_deps,
    public_router,
)


class _DummyConnector:
    def __init__(self, valid_signature: str = "valid_sig"):
        self.valid_signature = valid_signature
        self.calls: list[tuple[bytes, str]] = []

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        self.calls.append((payload, signature))
        return signature == self.valid_signature


class _DummyOrchestrator:
    def __init__(self):
        self.connectors: dict[str, _DummyConnector] = {}

    async def handle_webhook(self, psp: str, payload: dict, headers: dict) -> dict:
        return {"status": "ok", "psp": psp, "payload": payload, "has_headers": bool(headers)}


@pytest.fixture
def checkout_app():
    app = FastAPI()
    orchestrator = _DummyOrchestrator()
    deps = CheckoutDependencies(wallet_repo=MagicMock(), orchestrator=orchestrator)
    app.dependency_overrides[get_deps] = lambda: deps
    app.include_router(public_router, prefix="/api/v2/checkout")
    return app, orchestrator


def test_checkout_webhook_rejects_unknown_psp(checkout_app):
    app, _ = checkout_app
    client = TestClient(app)
    resp = client.post("/api/v2/checkout/webhooks/unknown", json={"id": "evt_1"})
    assert resp.status_code == 400
    assert "not configured" in resp.json()["detail"]


def test_checkout_webhook_rejects_missing_stripe_signature(checkout_app):
    app, orchestrator = checkout_app
    orchestrator.connectors["stripe"] = _DummyConnector()
    client = TestClient(app)
    resp = client.post("/api/v2/checkout/webhooks/stripe", json={"id": "evt_1"})
    assert resp.status_code == 401
    assert "Missing stripe-signature header" in resp.json()["detail"]


def test_checkout_webhook_rejects_invalid_stripe_signature(checkout_app):
    app, orchestrator = checkout_app
    orchestrator.connectors["stripe"] = _DummyConnector(valid_signature="good")
    client = TestClient(app)
    resp = client.post(
        "/api/v2/checkout/webhooks/stripe",
        content=json.dumps({"id": "evt_1"}),
        headers={"content-type": "application/json", "stripe-signature": "bad"},
    )
    assert resp.status_code == 401
    assert "Invalid webhook signature" in resp.json()["detail"]


def test_checkout_webhook_accepts_valid_stripe_signature(checkout_app):
    app, orchestrator = checkout_app
    connector = _DummyConnector(valid_signature="good")
    orchestrator.connectors["stripe"] = connector
    client = TestClient(app)
    resp = client.post(
        "/api/v2/checkout/webhooks/stripe",
        content=json.dumps({"id": "evt_1", "type": "checkout.session.completed"}),
        headers={"content-type": "application/json", "stripe-signature": "good"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert connector.calls and connector.calls[0][1] == "good"


def test_checkout_webhook_rejects_missing_nonstripe_signature(checkout_app):
    app, orchestrator = checkout_app
    orchestrator.connectors["paypal"] = _DummyConnector()
    client = TestClient(app)
    resp = client.post("/api/v2/checkout/webhooks/paypal", json={"id": "evt_1"})
    assert resp.status_code == 401
    assert "Missing x-paypal-signature header" in resp.json()["detail"]


def test_checkout_webhook_accepts_valid_nonstripe_signature(checkout_app):
    app, orchestrator = checkout_app
    connector = _DummyConnector(valid_signature="ok_sig")
    orchestrator.connectors["paypal"] = connector
    client = TestClient(app)
    resp = client.post(
        "/api/v2/checkout/webhooks/paypal",
        content=json.dumps({"id": "evt_2", "type": "payment.completed"}),
        headers={"content-type": "application/json", "x-paypal-signature": "ok_sig"},
    )
    assert resp.status_code == 200
    assert resp.json()["psp"] == "paypal"
    assert connector.calls and connector.calls[0][1] == "ok_sig"
