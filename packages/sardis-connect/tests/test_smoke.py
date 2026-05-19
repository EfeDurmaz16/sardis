"""Credential-free smoke tests for sardis-connect."""

from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal

from sardis_connect import PricedEndpoint, PricingTier, SardisConnect, UsageRecord
from sardis_connect.models import PricingModel


def test_public_import_surface_and_models() -> None:
    tier = PricingTier(
        name="pro",
        price=Decimal("0.10"),
        currency="USD",
        description="Pro tier",
    )
    endpoint = PricedEndpoint(
        path="/api/generate",
        method="POST",
        price=Decimal("0.05"),
        description="Generate text",
        tiers=[tier],
    )
    usage = UsageRecord(
        session_id="mcs_test",
        endpoint="/api/generate",
        units=1500,
        unit_price=Decimal("0.001"),
    )

    assert endpoint.pricing_model == PricingModel.PER_CALL
    assert endpoint.tiers == [tier]
    assert usage.total_charge == Decimal("1.500")


def test_manifest_includes_fixed_and_metered_endpoints() -> None:
    connect = SardisConnect(
        api_key="mch_test",
        merchant_id="merch_test",
        service_name="Test API",
        service_description="Credential-free test API",
        base_url="https://example.test",
    )
    fixed = connect.price(
        "/api/generate",
        amount="0.05",
        description="Generate text",
        category="ai",
    )
    metered = connect.meter(
        "/api/tokens",
        per_unit="0.001",
        unit="token",
        description="Token usage",
    )

    manifest = connect._get_manifest()

    assert fixed.price == Decimal("0.05")
    assert metered.pricing_model == PricingModel.PER_UNIT
    assert manifest["name"] == "Test API"
    assert manifest["base_url"] == "https://example.test"
    assert manifest["merchant_id"] == "merch_test"
    assert manifest["accepts"] == ["sardis", "x402", "mpp"]
    assert [endpoint["path"] for endpoint in manifest["endpoints"]] == [
        "/api/generate",
        "/api/tokens",
    ]
    assert manifest["endpoints"][1]["unit_name"] == "token"


def test_router_exposes_discovery_and_payment_routes() -> None:
    connect = SardisConnect(api_key="mch_test", merchant_id="merch_test")

    routes = {route.path for route in connect.router.routes}

    assert "/.well-known/sardis.json" in routes
    assert "/sardis/pay" in routes
    assert "/sardis/verify" in routes
    assert "/sardis/webhooks" in routes
    assert "/sardis/usage" in routes


def test_webhook_signature_is_fail_closed_and_verifiable() -> None:
    payload = b'{"event_type":"payment.settled"}'
    secret = "test-webhook-signing-key"
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    connect = SardisConnect(webhook_secret=secret)

    assert connect._verify_webhook(payload, f"sha256={expected}") is True
    assert connect._verify_webhook(payload, "sha256=bad") is False
    assert SardisConnect()._verify_webhook(payload, f"sha256={expected}") is False
