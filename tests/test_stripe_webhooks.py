"""Tests for Stripe inbound webhook router (Treasury & Issuing events).

Covers:
- Valid webhook with correct signature -> processes event
- Missing signature header -> 400
- Invalid signature -> 400
- Unknown event type -> ignored, returns 200
- Malformed JSON body -> 400
- Treasury event routing
- Issuing event routing
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import server.routes.providers.stripe_webhooks as stripe_webhooks
from server.routes.providers.stripe_webhooks import (
    ISSUING_EVENTS,
    TREASURY_EVENTS,
    StripeWebhookDeps,
    router,
    verify_stripe_signature,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stripe_signature(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Construct a valid Stripe-Signature header value."""
    ts = timestamp or int(time.time())
    signed_payload = f"{ts}.{payload.decode('utf-8')}"
    sig = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={ts},v1={sig}"


def _stripe_event(event_type: str = "treasury.received_credit", event_id: str = "evt_test_001") -> dict:
    return {
        "id": event_id,
        "type": event_type,
        "data": {
            "object": {
                "id": "obj_123",
                "amount": 10000,
                "currency": "usd",
            },
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test_webhook_signing_secret_for_unit_tests"


@pytest.fixture(autouse=True)
def _set_webhook_secret(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)


@pytest.fixture
def mock_treasury_provider():
    provider = AsyncMock()
    provider.handle_webhook = AsyncMock(return_value=None)
    return provider


@pytest.fixture
def mock_issuing_provider():
    provider = AsyncMock()
    provider.handle_authorization_webhook = AsyncMock(return_value={"approved": True})
    return provider


@pytest.fixture
def deps(mock_treasury_provider, mock_issuing_provider):
    return StripeWebhookDeps(
        treasury_provider=mock_treasury_provider,
        issuing_provider=mock_issuing_provider,
    )


@pytest.fixture
def app(deps):
    """Create a minimal FastAPI app with the stripe webhook router."""
    app = FastAPI()

    # Override the dependency so it returns our mocked deps
    def override_get_deps():
        return deps

    original_get_deps = stripe_webhooks.get_deps
    stripe_webhooks.get_deps = override_get_deps
    app.dependency_overrides[original_get_deps] = override_get_deps

    app.include_router(router)
    yield app

    # Restore
    stripe_webhooks.get_deps = original_get_deps
    app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests for verify_stripe_signature
# ---------------------------------------------------------------------------


class TestVerifyStripeSignature:
    def test_valid_signature_returns_true(self):
        payload = b'{"type": "test"}'
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)
        assert verify_stripe_signature(payload, sig, WEBHOOK_SECRET) is True

    def test_invalid_signature_returns_false(self):
        payload = b'{"type": "test"}'
        sig = _make_stripe_signature(payload, "wrong_secret")
        assert verify_stripe_signature(payload, sig, WEBHOOK_SECRET) is False

    def test_missing_v1_returns_false(self):
        sig = "t=12345"
        assert verify_stripe_signature(b"payload", sig, WEBHOOK_SECRET) is False

    def test_missing_timestamp_returns_false(self):
        sig = "v1=abcdef1234567890"
        assert verify_stripe_signature(b"payload", sig, WEBHOOK_SECRET) is False

    def test_malformed_header_returns_false(self):
        assert verify_stripe_signature(b"payload", "garbage", WEBHOOK_SECRET) is False

    def test_empty_string_returns_false(self):
        assert verify_stripe_signature(b"payload", "", WEBHOOK_SECRET) is False


# ---------------------------------------------------------------------------
# Endpoint tests — using manual verification (no stripe SDK)
# ---------------------------------------------------------------------------


class TestStripeWebhookEndpoint:
    """Tests that exercise the webhook endpoint with manual HMAC verification.

    We patch 'import stripe' to raise ImportError so the endpoint
    falls through to manual verify_stripe_signature.
    """

    def _post_webhook(self, client, event: dict, signature: str | None = None):
        """POST to /stripe/webhooks with proper content type."""
        payload = json.dumps(event).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if signature is not None:
            headers["Stripe-Signature"] = signature
        return client.post("/stripe/webhooks", content=payload, headers=headers)

    @patch.dict("sys.modules", {"stripe": None})
    def test_missing_signature_returns_400(self, client):
        event = _stripe_event()
        resp = self._post_webhook(client, event, signature=None)
        assert resp.status_code == 400
        assert "Missing signature" in resp.json()["detail"]

    @patch.dict("sys.modules", {"stripe": None})
    def test_invalid_signature_returns_400(self, client):
        event = _stripe_event()
        resp = self._post_webhook(client, event, signature="t=123,v1=bad_sig")
        assert resp.status_code == 400
        assert "Invalid signature" in resp.json()["detail"]

    @patch.dict("sys.modules", {"stripe": None})
    def test_valid_treasury_event_processed(self, client, mock_treasury_provider):
        event = _stripe_event("treasury.received_credit")
        payload = json.dumps(event).encode("utf-8")
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)
        resp = self._post_webhook(client, event, signature=sig)
        assert resp.status_code == 200
        assert resp.json() == {"received": True}
        mock_treasury_provider.handle_webhook.assert_awaited_once_with(
            "treasury.received_credit",
            event["data"]["object"],
        )

    @patch.dict("sys.modules", {"stripe": None})
    def test_valid_issuing_transaction_event_returns_200(self, client, mock_issuing_provider):
        event = _stripe_event("issuing_transaction.created")
        payload = json.dumps(event).encode("utf-8")
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)
        resp = self._post_webhook(client, event, signature=sig)
        assert resp.status_code == 200
        assert resp.json() == {"received": True}
        # Informational issuing events are just logged, no handler call
        mock_issuing_provider.handle_webhook.assert_not_awaited()

    @patch.dict("sys.modules", {"stripe": None})
    def test_unknown_event_type_returns_200(self, client):
        event = _stripe_event("some.unknown.event")
        payload = json.dumps(event).encode("utf-8")
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)
        resp = self._post_webhook(client, event, signature=sig)
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    @patch.dict("sys.modules", {"stripe": None})
    def test_malformed_json_returns_400(self, client):
        payload = b"not valid json {{{{"
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)
        headers = {
            "Content-Type": "application/json",
            "Stripe-Signature": sig,
        }
        resp = client.post("/stripe/webhooks", content=payload, headers=headers)
        assert resp.status_code == 400
        assert "Invalid JSON" in resp.json()["detail"]

    @patch.dict("sys.modules", {"stripe": None})
    def test_handler_error_still_returns_200(self, client, mock_treasury_provider):
        """Even if the handler raises, we return 200 to avoid Stripe retries."""
        mock_treasury_provider.handle_webhook.side_effect = RuntimeError("DB down")
        event = _stripe_event("treasury.received_credit")
        payload = json.dumps(event).encode("utf-8")
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)
        resp = self._post_webhook(client, event, signature=sig)
        assert resp.status_code == 200

    def test_missing_webhook_secret_env_returns_500(self, client, monkeypatch):
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        event = _stripe_event()
        resp = self._post_webhook(client, event, signature="t=1,v1=x")
        assert resp.status_code == 500
        assert "not configured" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Stripe SDK path tests
# ---------------------------------------------------------------------------


_has_stripe = False
try:
    import stripe as _stripe_mod  # noqa: F401
    _has_stripe = True
except ImportError:
    pass


@pytest.mark.skipif(not _has_stripe, reason="stripe SDK not installed")
class TestStripeWebhookWithSDK:
    """Tests exercising the stripe SDK code path (construct_event)."""

    def _post_webhook(self, client, event: dict, signature: str | None = None):
        payload = json.dumps(event).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if signature is not None:
            headers["Stripe-Signature"] = signature
        return client.post("/stripe/webhooks", content=payload, headers=headers)

    def test_sdk_valid_event(self, client, mock_treasury_provider):
        event = _stripe_event("treasury.outbound_payment.posted")
        mock_construct = MagicMock(return_value=event)

        with patch("stripe.Webhook.construct_event", mock_construct):
            payload = json.dumps(event).encode("utf-8")
            sig = "t=123,v1=whatever"
            resp = self._post_webhook(client, event, signature=sig)

        assert resp.status_code == 200
        mock_treasury_provider.handle_webhook.assert_awaited_once()

    def test_sdk_signature_verification_error(self, client):
        import stripe
        event = _stripe_event()

        mock_construct = MagicMock(side_effect=stripe.error.SignatureVerificationError("bad sig", "header"))

        with patch("stripe.Webhook.construct_event", mock_construct):
            resp = self._post_webhook(client, event, signature="t=1,v1=bad")

        assert resp.status_code == 400
        assert "Invalid signature" in resp.json()["detail"]

    def test_sdk_generic_exception(self, client):
        mock_construct = MagicMock(side_effect=Exception("unexpected"))

        with patch("stripe.Webhook.construct_event", mock_construct):
            event = _stripe_event()
            resp = self._post_webhook(client, event, signature="t=1,v1=x")

        assert resp.status_code == 400
        assert "Invalid event" in resp.json()["detail"]
