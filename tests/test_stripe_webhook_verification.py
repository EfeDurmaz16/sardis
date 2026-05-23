"""Tests for Stripe webhook signature verification in checkout connector.

Verifies that:
1. Valid signatures are accepted
2. Invalid signatures are rejected with ValueError
3. Missing webhook secret in production raises RuntimeError
4. Missing webhook secret in dev logs warning but proceeds
5. Replay attacks (old timestamps) are rejected
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import os
import time
from unittest.mock import AsyncMock, patch

import pytest

# Import the connector
from sardis.checkout.connectors.stripe import StripeConnector


def _make_stripe_signature(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Generate a valid Stripe webhook signature for testing."""
    ts = timestamp or int(time.time())
    signed_payload = f"{ts}.{payload.decode('utf-8')}"
    sig = hmac_mod.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={ts},v1={sig}"


def _make_event_payload(event_type: str = "checkout.session.completed") -> tuple[dict, bytes]:
    """Create a sample Stripe webhook event payload."""
    payload = {
        "type": event_type,
        "data": {
            "object": {
                "id": "cs_test_abc123",
                "payment_status": "paid",
                "amount_total": 5000,
                "currency": "usd",
                "metadata": {"agent_id": "agent_test", "wallet_id": "wal_test"},
            },
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    return payload, raw


WEBHOOK_SECRET = "test_wh_test_fixture_not_real"  # noqa: S105 — test fixture


class TestStripeWebhookVerification:
    """Test the Stripe webhook signature verification."""

    @pytest.fixture
    def connector(self):
        return StripeConnector(
            api_key="test_fixture_not_real",
            webhook_secret=WEBHOOK_SECRET,
        )

    @pytest.fixture
    def connector_no_secret(self):
        return StripeConnector(api_key="test_fixture_not_real", webhook_secret=None)

    @pytest.mark.asyncio
    async def test_valid_signature_accepted(self, connector):
        """A correctly signed webhook payload should be processed successfully."""
        payload, raw = _make_event_payload()
        sig = _make_stripe_signature(raw, WEBHOOK_SECRET)
        headers = {"stripe-signature": sig}

        result = await connector.handle_webhook(payload, headers, raw_payload=raw)

        assert result["event_type"] == "checkout.session.completed"
        assert result["session_id"] == "cs_test_abc123"
        assert result["payment_status"] == "paid"
        assert result["amount"] == 50.0  # 5000 cents -> $50

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, connector):
        """An incorrectly signed payload should raise ValueError."""
        payload, raw = _make_event_payload()
        # Sign with wrong secret
        bad_sig = _make_stripe_signature(raw, "test_wh_wrong_fixture")
        headers = {"stripe-signature": bad_sig}

        with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
            await connector.handle_webhook(payload, headers, raw_payload=raw)

    @pytest.mark.asyncio
    async def test_tampered_payload_rejected(self, connector):
        """A payload that was modified after signing should be rejected."""
        payload, raw = _make_event_payload()
        sig = _make_stripe_signature(raw, WEBHOOK_SECRET)
        headers = {"stripe-signature": sig}

        # Tamper with the raw payload after signing
        tampered = raw.replace(b"paid", b"free")

        with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
            await connector.handle_webhook(payload, headers, raw_payload=tampered)

    @pytest.mark.asyncio
    async def test_replay_attack_rejected(self, connector):
        """A signature with an old timestamp (>5 min) should be rejected."""
        payload, raw = _make_event_payload()
        old_timestamp = int(time.time()) - 600  # 10 minutes ago
        sig = _make_stripe_signature(raw, WEBHOOK_SECRET, timestamp=old_timestamp)
        headers = {"stripe-signature": sig}

        with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
            await connector.handle_webhook(payload, headers, raw_payload=raw)

    @pytest.mark.asyncio
    async def test_missing_secret_production_raises(self, connector_no_secret):
        """Missing webhook secret in production must raise RuntimeError."""
        payload, raw = _make_event_payload()
        headers = {"stripe-signature": "t=123,v1=abc"}

        with patch.dict(os.environ, {"SARDIS_ENV": "production"}):
            with pytest.raises(RuntimeError, match="SARDIS_STRIPE_WEBHOOK_SECRET is not configured"):
                await connector_no_secret.handle_webhook(payload, headers, raw_payload=raw)

    @pytest.mark.asyncio
    async def test_missing_secret_dev_warns_and_proceeds(self, connector_no_secret):
        """Missing webhook secret in dev should log warning but process the event."""
        payload, raw = _make_event_payload()
        headers = {"stripe-signature": "t=123,v1=abc"}

        with patch.dict(os.environ, {"SARDIS_ENV": "dev"}, clear=False):
            # Remove SARDIS_STRIPE_WEBHOOK_SECRET if present
            env = os.environ.copy()
            env.pop("SARDIS_STRIPE_WEBHOOK_SECRET", None)
            with patch.dict(os.environ, env, clear=True):
                result = await connector_no_secret.handle_webhook(payload, headers, raw_payload=raw)

        assert result["event_type"] == "checkout.session.completed"

    @pytest.mark.asyncio
    async def test_no_signature_no_secret_dev(self, connector_no_secret):
        """No signature and no secret in dev should proceed (for testing convenience)."""
        payload, raw = _make_event_payload()
        headers = {}  # No stripe-signature header

        with patch.dict(os.environ, {"SARDIS_ENV": "dev"}, clear=False):
            env = os.environ.copy()
            env.pop("SARDIS_STRIPE_WEBHOOK_SECRET", None)
            with patch.dict(os.environ, env, clear=True):
                result = await connector_no_secret.handle_webhook(payload, headers, raw_payload=raw)

        assert result["event_type"] == "checkout.session.completed"

    @pytest.mark.asyncio
    async def test_verify_webhook_method(self, connector):
        """The verify_webhook method should correctly validate signatures."""
        payload, raw = _make_event_payload()
        sig = _make_stripe_signature(raw, WEBHOOK_SECRET)

        assert await connector.verify_webhook(raw, sig) is True

    @pytest.mark.asyncio
    async def test_verify_webhook_invalid(self, connector):
        """The verify_webhook method should reject bad signatures."""
        payload, raw = _make_event_payload()
        bad_sig = _make_stripe_signature(raw, "test_wh_other_fixture")

        assert await connector.verify_webhook(raw, bad_sig) is False

    @pytest.mark.asyncio
    async def test_verify_webhook_no_secret(self, connector_no_secret):
        """verify_webhook should return False when no secret is configured."""
        payload, raw = _make_event_payload()
        sig = _make_stripe_signature(raw, "test_wh_anything")

        assert await connector_no_secret.verify_webhook(raw, sig) is False

    @pytest.mark.asyncio
    async def test_malformed_signature_rejected(self, connector):
        """A malformed signature header should be rejected."""
        payload, raw = _make_event_payload()
        headers = {"stripe-signature": "not_a_valid_signature"}

        with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
            await connector.handle_webhook(payload, headers, raw_payload=raw)
