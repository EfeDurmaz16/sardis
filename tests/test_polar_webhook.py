"""Tests for Polar webhook endpoint with signature enforcement.

Covers:
- Valid signature → processes event
- Missing signature header → 401
- Invalid signature → 401
- Adapter not configured → 503
- subscription.created event → calls handle_webhook_event
- subscription.canceled event → calls handle_webhook_event
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure package sources are on sys.path
_root = Path(__file__).parent.parent
_pkgs = _root / "packages"
for _pkg in ("sardis-core", "api"):
    _p = _pkgs / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from server.routes.providers.polar_webhook import router as polar_router

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WEBHOOK_SECRET = "test-polar-signing-key-for-unit-tests"  # noqa: S105

_SUBSCRIPTION_CREATED_PAYLOAD = {
    "type": "subscription.created",
    "data": {
        "id": "sub_polar_123",
        "status": "active",
        "metadata": {"org_id": "org_456", "plan": "starter"},
    },
}

_SUBSCRIPTION_CANCELED_PAYLOAD = {
    "type": "subscription.canceled",
    "data": {
        "id": "sub_polar_123",
        "status": "canceled",
        "metadata": {"org_id": "org_456", "plan": "starter"},
    },
}

_ORDER_CREATED_PAYLOAD = {
    "type": "order.created",
    "data": {
        "id": "ord_polar_789",
        "amount": 2999,
        "currency": "usd",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sign(secret: str, body: bytes) -> str:
    """Produce the expected HMAC-SHA256 signature for a webhook payload."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _build_app() -> FastAPI:
    """Create a minimal app with the polar webhook router."""
    app = FastAPI()
    app.include_router(polar_router, prefix="/api/v2/billing")
    return app


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_adapter(*, is_configured: bool = True, verify_result: bool = True):
    """Create a mock PolarBillingAdapter."""
    adapter = MagicMock()
    adapter.is_configured = is_configured
    adapter.verify_webhook.return_value = verify_result
    adapter.handle_webhook_event = AsyncMock()
    return adapter


# ---------------------------------------------------------------------------
# Tests: Signature Enforcement
# ---------------------------------------------------------------------------


class TestPolarWebhookSignatureEnforcement:
    """Webhook must enforce signature validation."""

    def test_missing_signature_returns_401(self):
        """Request without webhook-signature header must be rejected."""
        adapter = _mock_adapter(is_configured=True)

        with patch(
            "server.billing.polar_adapter.PolarBillingAdapter",
            return_value=adapter,
        ):
            app = _build_app()
            client = TestClient(app)
            body = json.dumps(_SUBSCRIPTION_CREATED_PAYLOAD)

            resp = client.post(
                "/api/v2/billing/polar-webhook",
                content=body,
                headers={"content-type": "application/json"},
            )

        assert resp.status_code == 401
        assert "missing" in resp.json()["detail"].lower()

    def test_invalid_signature_returns_401(self):
        """Request with wrong webhook-signature must be rejected."""
        adapter = _mock_adapter(is_configured=True, verify_result=False)

        with patch(
            "server.billing.polar_adapter.PolarBillingAdapter",
            return_value=adapter,
        ):
            app = _build_app()
            client = TestClient(app)
            body = json.dumps(_SUBSCRIPTION_CREATED_PAYLOAD)

            resp = client.post(
                "/api/v2/billing/polar-webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "webhook-signature": "bad-sig",
                },
            )

        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: Adapter Not Configured
# ---------------------------------------------------------------------------


class TestPolarWebhookAdapterNotConfigured:
    """When adapter is not configured, return 503."""

    def test_unconfigured_adapter_returns_503(self):
        """If PolarBillingAdapter.is_configured is False → 503."""
        adapter = _mock_adapter(is_configured=False)

        with patch(
            "server.billing.polar_adapter.PolarBillingAdapter",
            return_value=adapter,
        ):
            app = _build_app()
            client = TestClient(app)
            body = json.dumps(_SUBSCRIPTION_CREATED_PAYLOAD)

            resp = client.post(
                "/api/v2/billing/polar-webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "webhook-signature": "any-sig",
                },
            )

        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: Event Processing
# ---------------------------------------------------------------------------


class TestPolarWebhookEventProcessing:
    """Verify that valid events are processed via handle_webhook_event."""

    def test_subscription_created_processed(self):
        """subscription.created event → handle_webhook_event called."""
        adapter = _mock_adapter(is_configured=True, verify_result=True)

        with patch(
            "server.billing.polar_adapter.PolarBillingAdapter",
            return_value=adapter,
        ):
            app = _build_app()
            client = TestClient(app)
            body = json.dumps(_SUBSCRIPTION_CREATED_PAYLOAD).encode()
            sig = "valid-sig"  # verify_webhook is mocked to return True

            resp = client.post(
                "/api/v2/billing/polar-webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "webhook-signature": sig,
                },
            )

        assert resp.status_code == 200
        assert resp.json()["received"] is True
        adapter.handle_webhook_event.assert_awaited_once_with(
            "subscription.created",
            _SUBSCRIPTION_CREATED_PAYLOAD["data"],
        )

    def test_subscription_canceled_processed(self):
        """subscription.canceled event → handle_webhook_event called."""
        adapter = _mock_adapter(is_configured=True, verify_result=True)

        with patch(
            "server.billing.polar_adapter.PolarBillingAdapter",
            return_value=adapter,
        ):
            app = _build_app()
            client = TestClient(app)
            body = json.dumps(_SUBSCRIPTION_CANCELED_PAYLOAD).encode()

            resp = client.post(
                "/api/v2/billing/polar-webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "webhook-signature": "sig",
                },
            )

        assert resp.status_code == 200
        adapter.handle_webhook_event.assert_awaited_once_with(
            "subscription.canceled",
            _SUBSCRIPTION_CANCELED_PAYLOAD["data"],
        )

    def test_order_created_processed(self):
        """order.created event → handle_webhook_event called."""
        adapter = _mock_adapter(is_configured=True, verify_result=True)

        with patch(
            "server.billing.polar_adapter.PolarBillingAdapter",
            return_value=adapter,
        ):
            app = _build_app()
            client = TestClient(app)
            body = json.dumps(_ORDER_CREATED_PAYLOAD).encode()

            resp = client.post(
                "/api/v2/billing/polar-webhook",
                content=body,
                headers={
                    "content-type": "application/json",
                    "webhook-signature": "sig",
                },
            )

        assert resp.status_code == 200
        adapter.handle_webhook_event.assert_awaited_once()
        call_args = adapter.handle_webhook_event.call_args
        assert call_args[0][0] == "order.created"

    def test_invalid_json_returns_400(self):
        """Non-JSON body with valid signature → 400."""
        adapter = _mock_adapter(is_configured=True, verify_result=True)

        with patch(
            "server.billing.polar_adapter.PolarBillingAdapter",
            return_value=adapter,
        ):
            app = _build_app()
            client = TestClient(app)

            resp = client.post(
                "/api/v2/billing/polar-webhook",
                content=b"not json at all {{{",
                headers={
                    "content-type": "application/json",
                    "webhook-signature": "sig",
                },
            )

        assert resp.status_code == 400
        assert "invalid json" in resp.json()["detail"].lower()
