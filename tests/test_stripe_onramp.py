"""Tests for Stripe Crypto Onramp integration.

Covers:
1. POST /api/v2/onramp/stripe/session — session creation
2. GET /api/v2/onramp/stripe/link/{wallet_id} — hosted link generation
3. POST /api/v2/webhooks/stripe-onramp — webhook handling
4. Signature verification for webhooks
5. Error handling (missing API key, bad wallet, Stripe errors)
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import os
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from server.routes.wallets.onramp import (
    _CHAIN_TO_STRIPE_NETWORK,
    StripeOnrampLinkResponse,
    StripeOnrampSessionRequest,
    StripeOnrampSessionResponse,
    StripeOnrampWebhookEvent,
    _get_client_ip,
    _verify_stripe_onramp_signature,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test_onramp_wh_fixture"  # noqa: S105


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


def _make_onramp_event(
    session_id: str = "cos_test_abc123",
    session_status: str = "processing",
    event_type: str = "crypto.onramp_session.updated",
    wallet_address: str = "0x1234567890abcdef1234567890abcdef12345678",
) -> tuple[dict, bytes]:
    """Create a sample Stripe Crypto Onramp webhook event payload."""
    payload = {
        "id": f"evt_{session_id}",
        "type": event_type,
        "data": {
            "object": {
                "id": session_id,
                "object": "crypto.onramp_session",
                "status": session_status,
                "transaction_details": {
                    "destination_currency": "usdc",
                    "destination_network": "base",
                    "source_amount": "50.00",
                    "destination_amount": "49.85",
                    "wallet_addresses": {"base": wallet_address},
                    "transaction_id": "tx_onramp_test_123",
                },
            },
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    return payload, raw


# ---------------------------------------------------------------------------
# Signature verification tests
# ---------------------------------------------------------------------------


class TestStripeOnrampSignatureVerification:
    """Test the manual Stripe webhook signature verifier."""

    def test_valid_signature(self):
        payload = b'{"type":"crypto.onramp_session.updated"}'
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)
        assert _verify_stripe_onramp_signature(payload, sig, WEBHOOK_SECRET) is True

    def test_invalid_signature(self):
        payload = b'{"type":"crypto.onramp_session.updated"}'
        sig = _make_stripe_signature(payload, "wrong_secret")
        assert _verify_stripe_onramp_signature(payload, sig, WEBHOOK_SECRET) is False

    def test_tampered_payload(self):
        payload = b'{"type":"crypto.onramp_session.updated"}'
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)
        tampered = b'{"type":"crypto.onramp_session.updated","tampered":true}'
        assert _verify_stripe_onramp_signature(tampered, sig, WEBHOOK_SECRET) is False

    def test_missing_v1_in_header(self):
        assert _verify_stripe_onramp_signature(b"{}", "t=12345", WEBHOOK_SECRET) is False

    def test_missing_timestamp_in_header(self):
        assert _verify_stripe_onramp_signature(b"{}", "v1=abcdef", WEBHOOK_SECRET) is False

    def test_malformed_header(self):
        assert _verify_stripe_onramp_signature(b"{}", "garbage", WEBHOOK_SECRET) is False

    def test_empty_header(self):
        assert _verify_stripe_onramp_signature(b"{}", "", WEBHOOK_SECRET) is False


# ---------------------------------------------------------------------------
# Chain mapping tests
# ---------------------------------------------------------------------------


class TestChainToStripeNetwork:
    def test_base_mapping(self):
        assert _CHAIN_TO_STRIPE_NETWORK["base"] == "base"

    def test_base_sepolia_maps_to_base(self):
        assert _CHAIN_TO_STRIPE_NETWORK["base_sepolia"] == "base"

    def test_ethereum_mapping(self):
        assert _CHAIN_TO_STRIPE_NETWORK["ethereum"] == "ethereum"

    def test_polygon_mapping(self):
        assert _CHAIN_TO_STRIPE_NETWORK["polygon"] == "polygon"


# ---------------------------------------------------------------------------
# Request/Response model tests
# ---------------------------------------------------------------------------


class TestStripeOnrampModels:
    def test_session_request_defaults(self):
        req = StripeOnrampSessionRequest(wallet_id="wal_test123")
        assert req.wallet_id == "wal_test123"
        assert req.amount is None
        assert req.chain is None
        assert req.destination_currency == "usdc"
        assert req.source_currency == "usd"
        assert req.lock_wallet_address is True

    def test_session_request_custom(self):
        req = StripeOnrampSessionRequest(
            wallet_id="0x1234567890abcdef1234567890abcdef12345678",
            amount="100.00",
            chain="ethereum",
            destination_currency="eth",
            source_currency="eur",
            lock_wallet_address=False,
        )
        assert req.amount == "100.00"
        assert req.chain == "ethereum"
        assert req.destination_currency == "eth"
        assert req.lock_wallet_address is False

    def test_session_response(self):
        resp = StripeOnrampSessionResponse(
            session_id="cos_test",
            client_secret="cos_cs_test",
            redirect_url="https://crypto.link.com?session_hash=abc",
            status="initialized",
            wallet_address="0x1234",
            destination_network="base",
            created_at="2026-03-29T00:00:00+00:00",
        )
        assert resp.session_id == "cos_test"
        assert resp.client_secret == "cos_cs_test"

    def test_link_response(self):
        resp = StripeOnrampLinkResponse(
            url="https://crypto.link.com?destination_currency=usdc",
            wallet_address="0x1234",
            destination_network="base",
        )
        assert "crypto.link.com" in resp.url

    def test_webhook_event_model(self):
        event = StripeOnrampWebhookEvent(
            session_id="cos_test",
            status="fulfillment_complete",
            wallet_address="0x1234",
            destination_currency="usdc",
            destination_network="base",
            source_amount="50.00",
            destination_amount="49.85",
            transaction_id="tx_123",
            received_at=datetime.now(UTC).isoformat(),
        )
        assert event.status == "fulfillment_complete"
        assert event.transaction_id == "tx_123"


# ---------------------------------------------------------------------------
# Client IP extraction test
# ---------------------------------------------------------------------------


class TestGetClientIp:
    def test_from_x_forwarded_for(self):
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.client = MagicMock(host="127.0.0.1")
        assert _get_client_ip(request) == "1.2.3.4"

    def test_from_client_host(self):
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="10.0.0.1")
        assert _get_client_ip(request) == "10.0.0.1"

    def test_no_ip_available(self):
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) is None


# ---------------------------------------------------------------------------
# Integration tests using FastAPI TestClient
# ---------------------------------------------------------------------------

# These tests require the full app to be importable. They are skipped if
# dependencies are not available (e.g. in a minimal CI environment).

try:
    from fastapi.testclient import TestClient
    from server.main import create_app

    _APP_AVAILABLE = True
except Exception:
    _APP_AVAILABLE = False


@pytest.mark.skipif(not _APP_AVAILABLE, reason="Full app not importable")
class TestStripeOnrampEndpoints:
    """Integration tests against the real FastAPI router."""

    @pytest.fixture(autouse=True)
    def _setup_client(self):
        self.app = create_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_stripe_session_endpoint_exists(self):
        """POST /onramp/stripe/session should be a registered route."""
        # In test/dev mode with SARDIS_ALLOW_ANON=1, auth may pass
        # so we may get 404 (wallet not found) or 503 (Stripe not configured)
        # instead of 401/403. Either way, the endpoint exists.
        resp = self.client.post(
            "/api/v2/onramp/stripe/session",
            json={"wallet_id": "wal_test"},
        )
        # Should not be 405 (Method Not Allowed) or 422 only on missing body
        assert resp.status_code != 405

    def test_stripe_link_endpoint_exists(self):
        """GET /onramp/stripe/link/{wallet_id} should be a registered route."""
        resp = self.client.get("/api/v2/onramp/stripe/link/wal_test")
        assert resp.status_code != 405

    def test_stripe_onramp_webhook_no_signature_with_secret(self):
        """Webhook should reject requests without Stripe-Signature when secret is set."""
        _, payload = _make_onramp_event()
        with patch.dict(os.environ, {"STRIPE_ONRAMP_WEBHOOK_SECRET": WEBHOOK_SECRET}):
            resp = self.client.post(
                "/api/v2/webhooks/stripe-onramp",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 400

    def test_stripe_onramp_webhook_invalid_signature(self):
        """Webhook should reject requests with invalid signatures."""
        _, payload = _make_onramp_event()
        with patch.dict(os.environ, {"STRIPE_ONRAMP_WEBHOOK_SECRET": WEBHOOK_SECRET}):
            resp = self.client.post(
                "/api/v2/webhooks/stripe-onramp",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "t=123,v1=invalid",
                },
            )
        assert resp.status_code == 400

    def test_stripe_onramp_webhook_valid_signature(self):
        """Webhook should accept and process events with valid signatures."""
        _, payload = _make_onramp_event(session_status="processing")
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)

        # Ensure Stripe SDK import fails so we test our manual verifier
        with (
            patch.dict(os.environ, {"STRIPE_ONRAMP_WEBHOOK_SECRET": WEBHOOK_SECRET}),
            patch.dict("sys.modules", {"stripe": None}),
        ):
            resp = self.client.post(
                "/api/v2/webhooks/stripe-onramp",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": sig,
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["received"] is True
        assert body["processed"] is True
        assert body["status"] == "processing"

    def test_stripe_onramp_webhook_ignores_unrelated_events(self):
        """Webhook should accept but not process non-onramp events."""
        payload_dict = {
            "id": "evt_unrelated",
            "type": "payment_intent.succeeded",
            "data": {"object": {}},
        }
        payload = json.dumps(payload_dict).encode("utf-8")
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)

        with (
            patch.dict(os.environ, {"STRIPE_ONRAMP_WEBHOOK_SECRET": WEBHOOK_SECRET}),
            patch.dict("sys.modules", {"stripe": None}),
        ):
            resp = self.client.post(
                "/api/v2/webhooks/stripe-onramp",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": sig,
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["processed"] is False

    def test_stripe_onramp_webhook_dev_mode_no_secret(self):
        """In dev mode, webhook should accept events without a secret."""
        _, payload = _make_onramp_event(session_status="fulfillment_complete")

        env_overrides = {
            "SARDIS_ENVIRONMENT": "dev",
        }
        # Remove any webhook secret
        env_copy = os.environ.copy()
        env_copy.pop("STRIPE_ONRAMP_WEBHOOK_SECRET", None)
        env_copy.pop("STRIPE_WEBHOOK_SECRET", None)
        env_copy.update(env_overrides)

        with patch.dict(os.environ, env_copy, clear=True):
            resp = self.client.post(
                "/api/v2/webhooks/stripe-onramp",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["received"] is True
        assert body["status"] == "fulfillment_complete"

    def test_stripe_onramp_webhook_fulfillment_complete(self):
        """Verify fulfillment_complete events are processed correctly."""
        _, payload = _make_onramp_event(
            session_id="cos_fulfilled",
            session_status="fulfillment_complete",
            wallet_address="0xDeaDbEeF00000000000000000000000000000001",
        )
        sig = _make_stripe_signature(payload, WEBHOOK_SECRET)

        with (
            patch.dict(os.environ, {"STRIPE_ONRAMP_WEBHOOK_SECRET": WEBHOOK_SECRET}),
            patch.dict("sys.modules", {"stripe": None}),
        ):
            resp = self.client.post(
                "/api/v2/webhooks/stripe-onramp",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": sig,
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "cos_fulfilled"
        assert body["status"] == "fulfillment_complete"


# ---------------------------------------------------------------------------
# Unit tests for _create_stripe_onramp_session (mocked httpx)
# ---------------------------------------------------------------------------


class TestCreateStripeOnrampSession:
    """Test the internal Stripe API caller with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_success(self):
        from server.routes.wallets.onramp import _create_stripe_onramp_session

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "cos_test_123",
            "client_secret": "cos_cs_test_secret",
            "redirect_url": "https://crypto.link.com?session_hash=abc",
            "status": "initialized",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.dict(os.environ, {"STRIPE_SECRET_KEY": "test_fixture_key"}),
            patch("server.routes.wallets.onramp.httpx.AsyncClient", return_value=mock_client),
        ):
            result = await _create_stripe_onramp_session(
                wallet_address="0x1234567890abcdef1234567890abcdef12345678",
                chain="base",
                amount="50.00",
                destination_currency="usdc",
                source_currency="usd",
                lock_wallet_address=True,
                customer_ip="1.2.3.4",
            )

        assert result["id"] == "cos_test_123"
        assert result["client_secret"] == "cos_cs_test_secret"

        # Verify the POST call was made correctly
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://api.stripe.com/v1/crypto/onramp_sessions"
        form_data = call_args[1]["data"]
        assert form_data["wallet_addresses[ethereum]"] == "0x1234567890abcdef1234567890abcdef12345678"
        assert form_data["destination_currencies[0]"] == "usdc"
        # base + ethereum both included (sorted)
        assert "base" in [form_data.get(f"destination_networks[{i}]") for i in range(3)]
        assert form_data["source_amount"] == "50.00"
        assert form_data["source_currency"] == "usd"
        assert form_data["lock_wallet_address"] == "true"
        assert form_data["customer_ip_address"] == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_no_api_key_raises_503(self):
        from server.routes.wallets.onramp import _create_stripe_onramp_session

        env_copy = os.environ.copy()
        env_copy.pop("STRIPE_SECRET_KEY", None)
        env_copy.pop("STRIPE_API_KEY", None)

        with patch.dict(os.environ, env_copy, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                await _create_stripe_onramp_session(
                    wallet_address="0x1234",
                    chain="base",
                    amount=None,
                    destination_currency="usdc",
                    source_currency="usd",
                    lock_wallet_address=True,
                    customer_ip=None,
                )
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_stripe_error_raises_502(self):
        from server.routes.wallets.onramp import _create_stripe_onramp_session

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error":{"message":"Invalid request"}}'
        mock_response.json.return_value = {"error": {"message": "Invalid request"}}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.dict(os.environ, {"STRIPE_SECRET_KEY": "test_fixture_key"}),
            patch("server.routes.wallets.onramp.httpx.AsyncClient", return_value=mock_client),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await _create_stripe_onramp_session(
                    wallet_address="0x1234",
                    chain="base",
                    amount="50.00",
                    destination_currency="usdc",
                    source_currency="usd",
                    lock_wallet_address=True,
                    customer_ip=None,
                )
        assert exc_info.value.status_code == 502
        assert "Invalid request" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_evm_addresses_populated(self):
        """All common EVM chain addresses should be set to the same address."""
        from server.routes.wallets.onramp import _create_stripe_onramp_session

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "cos_test", "status": "initialized"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        wallet = "0xAABBCCDDEEFF00112233445566778899AABBCCDD"

        with (
            patch.dict(os.environ, {"STRIPE_SECRET_KEY": "test_fixture_key"}),
            patch("server.routes.wallets.onramp.httpx.AsyncClient", return_value=mock_client),
        ):
            await _create_stripe_onramp_session(
                wallet_address=wallet,
                chain="base",
                amount=None,
                destination_currency="usdc",
                source_currency="usd",
                lock_wallet_address=False,
                customer_ip=None,
            )

        form_data = mock_client.post.call_args[1]["data"]
        # Stripe uses "ethereum" key for all EVM chains (Base, Polygon, etc.)
        assert form_data["wallet_addresses[ethereum]"] == wallet

    @pytest.mark.asyncio
    async def test_no_amount_omits_source_amount(self):
        """When amount is None, source_amount should not be in the request."""
        from server.routes.wallets.onramp import _create_stripe_onramp_session

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "cos_test", "status": "initialized"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.dict(os.environ, {"STRIPE_SECRET_KEY": "test_fixture_key"}),
            patch("server.routes.wallets.onramp.httpx.AsyncClient", return_value=mock_client),
        ):
            await _create_stripe_onramp_session(
                wallet_address="0x1234",
                chain="base",
                amount=None,
                destination_currency="usdc",
                source_currency="usd",
                lock_wallet_address=True,
                customer_ip=None,
            )

        form_data = mock_client.post.call_args[1]["data"]
        assert "source_amount" not in form_data


# ---------------------------------------------------------------------------
# Hosted link URL construction tests
# ---------------------------------------------------------------------------


class TestStripeOnrampLinkUrl:
    """Test that the hosted link URL is constructed correctly."""

    @pytest.mark.asyncio
    async def test_link_url_contains_expected_params(self):
        """The URL should contain destination_currency, network, and wallet."""
        from server.routes.wallets.onramp import get_stripe_onramp_link

        # Mock the wallet resolution and auth
        wallet_addr = "0xAABBCCDDEEFF00112233445566778899AABBCCDD"
        mock_principal = MagicMock()

        with patch("server.routes.wallets.onramp._resolve_wallet_address", return_value=wallet_addr):
            resp = await get_stripe_onramp_link(
                wallet_id="wal_test",
                chain="base",
                destination_currency="usdc",
                source_currency="usd",
                amount="100",
                principal=mock_principal,
            )

        assert "crypto.link.com" in resp.url
        assert "destination_currency=usdc" in resp.url
        assert "destination_network=base" in resp.url
        assert "source_amount=100" in resp.url
        assert wallet_addr in resp.url

    @pytest.mark.asyncio
    async def test_link_url_no_amount(self):
        """When amount is None, source_amount should not be in the URL."""
        from server.routes.wallets.onramp import get_stripe_onramp_link

        wallet_addr = "0x1234567890abcdef1234567890abcdef12345678"
        mock_principal = MagicMock()

        with patch("server.routes.wallets.onramp._resolve_wallet_address", return_value=wallet_addr):
            resp = await get_stripe_onramp_link(
                wallet_id="wal_test",
                chain="ethereum",
                destination_currency="eth",
                source_currency="usd",
                amount=None,
                principal=mock_principal,
            )

        assert "source_amount" not in resp.url
        assert "destination_network=ethereum" in resp.url
        assert resp.destination_network == "ethereum"

    @pytest.mark.asyncio
    async def test_link_wallet_not_found(self):
        """Should raise 404 if wallet cannot be resolved."""
        from server.routes.wallets.onramp import get_stripe_onramp_link

        mock_principal = MagicMock()

        with patch(
            "server.routes.wallets.onramp._resolve_wallet_address",
            side_effect=ValueError("Wallet wal_bad not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_stripe_onramp_link(
                    wallet_id="wal_bad",
                    principal=mock_principal,
                )
        assert exc_info.value.status_code == 404


# Import HTTPException at module level for the test assertions
from fastapi import HTTPException
