"""Tests for x402 payment middleware."""
from __future__ import annotations

import base64
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_api.middleware.x402 import (
    X402MiddlewareConfig,
    X402PaymentMiddleware,
    X402PricingRegistry,
    X402PricingRule,
)


def _create_test_app(*, enabled: bool = True, rules: dict | None = None) -> FastAPI:
    """Create a minimal FastAPI app with x402 middleware."""
    app = FastAPI()

    pricing = X402PricingRegistry()
    if rules:
        for prefix, rule in rules.items():
            pricing.add_rule(rule)

    config = X402MiddlewareConfig(
        pricing_registry=pricing,
        payee_address="0x" + "a" * 40,
        payee_wallet_id="wal_test",
        enabled=enabled,
    )
    app.add_middleware(X402PaymentMiddleware, config=config)

    @app.get("/api/v2/data")
    async def get_data():
        return {"data": "hello"}

    @app.get("/api/v2/free")
    async def get_free():
        return {"data": "free"}

    return app


def test_unprotected_path_passes_through():
    """Paths without pricing rules pass through normally."""
    rules = {
        "/api/v2/data": X402PricingRule(path_prefix="/api/v2/data", amount="1000000"),
    }
    app = _create_test_app(rules=rules)
    client = TestClient(app)

    response = client.get("/api/v2/free")
    assert response.status_code == 200
    assert response.json() == {"data": "free"}


def test_protected_path_without_payment_returns_402():
    """Protected path without PAYMENT-SIGNATURE returns 402 with challenge."""
    rules = {
        "/api/v2/data": X402PricingRule(path_prefix="/api/v2/data", amount="1000000"),
    }
    app = _create_test_app(rules=rules)
    client = TestClient(app)

    response = client.get("/api/v2/data")
    assert response.status_code == 402

    body = response.json()
    assert body["error"] == "payment_required"
    assert body["amount"] == "1000000"
    assert body["currency"] == "USDC"
    assert "PaymentRequired" in response.headers


def test_feature_flag_disabled_passes_through():
    """When disabled, all paths pass through without 402."""
    rules = {
        "/api/v2/data": X402PricingRule(path_prefix="/api/v2/data", amount="1000000"),
    }
    app = _create_test_app(enabled=False, rules=rules)
    client = TestClient(app)

    response = client.get("/api/v2/data")
    assert response.status_code == 200
    assert response.json() == {"data": "hello"}


def test_no_rules_passes_through():
    """When no rules are configured, all paths pass through."""
    app = _create_test_app(enabled=True, rules={})
    client = TestClient(app)

    response = client.get("/api/v2/data")
    assert response.status_code == 200


def test_pricing_registry_prefix_matching():
    """Pricing registry matches the most specific prefix."""
    registry = X402PricingRegistry()
    registry.add_rule(X402PricingRule(path_prefix="/api/v2/", amount="100"))
    registry.add_rule(X402PricingRule(path_prefix="/api/v2/data", amount="500"))

    rule = registry.get_rule("/api/v2/data")
    assert rule is not None
    assert rule.amount == "500"

    rule2 = registry.get_rule("/api/v2/other")
    assert rule2 is not None
    assert rule2.amount == "100"

    rule3 = registry.get_rule("/api/v3/other")
    assert rule3 is None


def test_invalid_signature_rejected():
    """Invalid PAYMENT-SIGNATURE header is rejected."""
    rules = {
        "/api/v2/data": X402PricingRule(path_prefix="/api/v2/data", amount="1000000"),
    }
    app = _create_test_app(rules=rules)
    client = TestClient(app)

    response = client.get("/api/v2/data", headers={"PAYMENT-SIGNATURE": "not-valid-base64"})
    assert response.status_code == 400
    body = response.json()
    assert "error" in body


def test_402_response_has_correct_headers():
    """Verify the 402 response includes proper x402 headers."""
    rules = {
        "/api/v2/data": X402PricingRule(
            path_prefix="/api/v2/data",
            amount="1000000",
            currency="USDC",
            network="base",
        ),
    }
    app = _create_test_app(rules=rules)
    client = TestClient(app)

    response = client.get("/api/v2/data")
    assert response.status_code == 402

    # Verify PaymentRequired header is base64-encoded JSON
    payment_required = response.headers.get("PaymentRequired", "")
    assert payment_required
    decoded = json.loads(base64.b64decode(payment_required))
    assert decoded["amount"] == "1000000"
    assert decoded["currency"] == "USDC"
    assert decoded["network"] == "base"
    assert "payment_id" in decoded
    assert "nonce" in decoded
