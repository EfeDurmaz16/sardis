"""Tests for the real StripeSPTAdapter and the stripe-spt webhook router.

HTTP calls are intercepted at the transport layer using httpx.MockTransport,
which ships with httpx and requires no additional dependencies.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_v2_core.credential_store import CredentialEncryption
from sardis_v2_core.delegated_adapters.stripe_spt import StripeSPTAdapter
from sardis_v2_core.delegated_credential import (
    CredentialClass,
    CredentialNetwork,
    CredentialScope,
    CredentialStatus,
    DelegatedCredential,
)
from sardis_v2_core.delegated_executor import DelegatedPaymentRequest

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _fernet_key() -> bytes:
    return Fernet.generate_key()


def _make_encryption() -> CredentialEncryption:
    return CredentialEncryption(key=_fernet_key())


def _make_active_credential(
    encryption: CredentialEncryption | None = None,
    token: bytes = b"pm_test_abc123",
) -> DelegatedCredential:
    enc = encryption or _make_encryption()
    encrypted = enc.encrypt_for_class(token, CredentialClass.OPAQUE_DELEGATED_TOKEN)
    return DelegatedCredential(
        org_id="org_test",
        agent_id="agent_test",
        network=CredentialNetwork.STRIPE_SPT,
        status=CredentialStatus.ACTIVE,
        credential_class=CredentialClass.OPAQUE_DELEGATED_TOKEN,
        token_reference="tok_ref_pm_test_abc123",
        token_encrypted=encrypted,
        scope=CredentialScope(max_per_tx=Decimal("1000")),
        consent_id="dcns_test",
    ), enc


def _make_request(amount: Decimal = Decimal("50")) -> DelegatedPaymentRequest:
    return DelegatedPaymentRequest(
        credential_reference="tok_ref_pm_test_abc123",
        consent_reference="dcns_test",
        merchant_binding="merch_acme",
        amount=amount,
        currency="USD",
    )


def _stripe_pi_response(
    pi_id: str = "pi_test_001",
    status: str = "succeeded",
    amount: int = 5000,
    currency: str = "usd",
) -> dict[str, Any]:
    return {
        "id": pi_id,
        "object": "payment_intent",
        "amount": amount,
        "currency": currency,
        "status": status,
        "fee": 0,
        "authorization_id": f"auth_{pi_id}",
    }


def _mock_transport(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Build an httpx.MockTransport that returns each response in order."""
    it = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        return next(it)

    return httpx.MockTransport(handler)


def _stripe_sig_header(payload: bytes, secret: str) -> str:
    """Construct a valid Stripe-Signature header."""
    ts = str(int(time.time()))
    signed = f"{ts}.{payload.decode('utf-8')}"
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


# ---------------------------------------------------------------------------
# StripeSPTAdapter.execute() tests
# ---------------------------------------------------------------------------

class TestStripeSPTAdapterExecute:

    @pytest.mark.asyncio
    async def test_execute_success(self):
        enc = _make_encryption()
        cred, enc = _make_active_credential(encryption=enc)
        request = _make_request()

        stripe_response = httpx.Response(
            200,
            json=_stripe_pi_response(pi_id="pi_abc001", status="succeeded", amount=5000),
        )

        adapter = StripeSPTAdapter(
            api_key="sk_test_fake_000000",
            encryption=enc,
            base_url="https://api.stripe.com",
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.post.return_value = stripe_response

            result = await adapter.execute(request, cred)

        assert result.success is True
        assert result.network == "stripe_spt"
        assert result.reference_id == "pi_abc001"
        assert result.amount == Decimal("50")
        assert result.currency == "USD"
        assert result.settlement_status == "instant"

    @pytest.mark.asyncio
    async def test_execute_stripe_api_error(self):
        enc = _make_encryption()
        cred, enc = _make_active_credential(encryption=enc)
        request = _make_request()

        stripe_error_response = httpx.Response(
            402,
            json={
                "error": {
                    "code": "card_declined",
                    "message": "Your card was declined.",
                }
            },
        )

        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000", encryption=enc)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.post.return_value = stripe_error_response

            result = await adapter.execute(request, cred)

        assert result.success is False
        assert "card_declined" in result.error or "402" in result.error
        assert result.network == "stripe_spt"

    @pytest.mark.asyncio
    async def test_execute_decryption_failure(self):
        # Credential encrypted with a different key — decryption must fail
        enc_a = _make_encryption()
        enc_b = _make_encryption()
        cred, _ = _make_active_credential(encryption=enc_a)

        # Adapter uses enc_b, which cannot decrypt the token from enc_a
        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000", encryption=enc_b)
        request = _make_request()

        result = await adapter.execute(request, cred)

        assert result.success is False
        assert "Credential decryption failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_http_connection_error(self):
        enc = _make_encryption()
        cred, enc = _make_active_credential(encryption=enc)
        request = _make_request()

        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000", encryption=enc)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")

            result = await adapter.execute(request, cred)

        assert result.success is False
        assert "HTTP error" in result.error

    @pytest.mark.asyncio
    async def test_execute_pending_status_returns_pending_settlement(self):
        enc = _make_encryption()
        cred, enc = _make_active_credential(encryption=enc)
        request = _make_request()

        stripe_response = httpx.Response(
            200,
            json=_stripe_pi_response(pi_id="pi_pending_001", status="requires_capture"),
        )

        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000", encryption=enc)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.post.return_value = stripe_response

            result = await adapter.execute(request, cred)

        assert result.success is False
        assert result.settlement_status == "pending"


# ---------------------------------------------------------------------------
# StripeSPTAdapter.provision_credential() tests
# ---------------------------------------------------------------------------

class TestStripeSPTAdapterProvision:

    @pytest.mark.asyncio
    async def test_provision_credential_success(self):
        enc = _make_encryption()
        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000", encryption=enc)

        stripe_response = httpx.Response(
            200,
            json={
                "id": "pm_test_provisioned_001",
                "object": "payment_method",
                "type": "card",
            },
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.post.return_value = stripe_response

            cred = await adapter.provision_credential(
                org_id="org_1",
                agent_id="agent_1",
                scope=CredentialScope(max_per_tx=Decimal("200")),
                encryption=enc,
                customer_id="cus_test_123",
            )

        assert cred.network == CredentialNetwork.STRIPE_SPT
        assert cred.status == CredentialStatus.ACTIVE
        assert cred.credential_class == CredentialClass.OPAQUE_DELEGATED_TOKEN
        assert "pm_test_provisioned_001" in cred.token_reference
        assert cred.provider_metadata["payment_method_id"] == "pm_test_provisioned_001"
        assert cred.provider_metadata["customer_id"] == "cus_test_123"
        assert cred.scope.max_per_tx == Decimal("200")
        # Token must actually be encrypted (not plaintext)
        decrypted = enc.decrypt_for_class(cred.token_encrypted, CredentialClass.OPAQUE_DELEGATED_TOKEN)
        assert decrypted == b"pm_test_provisioned_001"

    @pytest.mark.asyncio
    async def test_provision_credential_api_error_raises(self):
        enc = _make_encryption()
        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000", encryption=enc)

        stripe_error = httpx.Response(
            400,
            json={"error": {"code": "invalid_request", "message": "Invalid API key."}},
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.post.return_value = stripe_error

            with pytest.raises(RuntimeError, match="Stripe SPT provision failed"):
                await adapter.provision_credential(
                    org_id="org_1",
                    agent_id="agent_1",
                    scope=CredentialScope(),
                )

    @pytest.mark.asyncio
    async def test_provision_credential_http_error_raises(self):
        enc = _make_encryption()
        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000", encryption=enc)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.post.side_effect = httpx.ConnectTimeout("Timed out")

            with pytest.raises(RuntimeError, match="Stripe SPT provision HTTP error"):
                await adapter.provision_credential(
                    org_id="org_1",
                    agent_id="agent_1",
                    scope=CredentialScope(),
                )


# ---------------------------------------------------------------------------
# StripeSPTAdapter.check_health() tests
# ---------------------------------------------------------------------------

class TestStripeSPTAdapterCheckHealth:

    @pytest.mark.asyncio
    async def test_check_health_returns_true_on_200(self):
        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000")

        healthy_response = httpx.Response(200, json={"object": "list", "data": []})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.get.return_value = healthy_response

            assert await adapter.check_health() is True

    @pytest.mark.asyncio
    async def test_check_health_returns_false_on_401(self):
        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000")

        auth_error = httpx.Response(
            401,
            json={"error": {"code": "invalid_api_key", "message": "No such API key."}},
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.get.return_value = auth_error

            assert await adapter.check_health() is False

    @pytest.mark.asyncio
    async def test_check_health_returns_false_without_api_key(self):
        adapter = StripeSPTAdapter(api_key="")
        # No HTTP call should be made when there is no key
        assert await adapter.check_health() is False

    @pytest.mark.asyncio
    async def test_check_health_returns_false_on_http_error(self):
        adapter = StripeSPTAdapter(api_key="sk_test_fake_000000")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_client.get.side_effect = httpx.ConnectError("Network unreachable")

            assert await adapter.check_health() is False


# ---------------------------------------------------------------------------
# Webhook handler endpoint tests
# ---------------------------------------------------------------------------

def _build_spt_test_app(webhook_secret: str) -> TestClient:
    """Build a minimal FastAPI app with the SPT webhook router."""
    from sardis_api.routers.stripe_spt_webhooks import router

    app = FastAPI()
    app.include_router(router)

    os.environ["STRIPE_SPT_WEBHOOK_SECRET"] = webhook_secret
    return TestClient(app)


class TestStripeSPTWebhookHandler:

    _SECRET = "whsec_test_spt_fake_000000"  # noqa: S105

    def setup_method(self):
        os.environ["STRIPE_SPT_WEBHOOK_SECRET"] = self._SECRET

    def teardown_method(self):
        os.environ.pop("STRIPE_SPT_WEBHOOK_SECRET", None)

    def _client(self) -> TestClient:
        from sardis_api.routers.stripe_spt_webhooks import router
        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    def _post(
        self,
        client: TestClient,
        event_type: str,
        pi_id: str = "pi_test_wh_001",
        signature: str | None = None,
    ) -> Any:
        payload_dict = {
            "id": f"evt_{pi_id}",
            "type": event_type,
            "data": {
                "object": {
                    "id": pi_id,
                    "amount": 10000,
                    "currency": "usd",
                    "status": "succeeded" if event_type == "payment_intent.succeeded" else "failed",
                    "last_payment_error": (
                        {"code": "card_declined", "message": "Declined."} if "failed" in event_type else None
                    ),
                }
            },
        }
        payload_bytes = json.dumps(payload_dict).encode()
        sig = signature or _stripe_sig_header(payload_bytes, self._SECRET)

        return client.post(
            "/stripe-spt/webhooks",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": sig,
            },
        )

    def test_payment_intent_succeeded_returns_200(self):
        client = self._client()
        resp = self._post(client, "payment_intent.succeeded")
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    def test_payment_intent_payment_failed_returns_200(self):
        client = self._client()
        resp = self._post(client, "payment_intent.payment_failed")
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    def test_unhandled_event_type_still_returns_200(self):
        client = self._client()
        resp = self._post(client, "some_other_event.happened")
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    def test_missing_signature_returns_400(self):
        from sardis_api.routers.stripe_spt_webhooks import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        payload = json.dumps({"id": "evt_1", "type": "payment_intent.succeeded"}).encode()
        resp = client.post(
            "/stripe-spt/webhooks",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert "Missing signature" in resp.json()["detail"]

    def test_invalid_signature_returns_400(self):
        client = self._client()
        resp = self._post(client, "payment_intent.succeeded", signature="t=1234,v1=badsig")
        assert resp.status_code == 400
        assert "Invalid signature" in resp.json()["detail"]

    def test_missing_webhook_secret_returns_500(self):
        os.environ.pop("STRIPE_SPT_WEBHOOK_SECRET", None)
        from sardis_api.routers.stripe_spt_webhooks import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        payload = json.dumps({"id": "evt_1", "type": "payment_intent.succeeded"}).encode()
        resp = client.post(
            "/stripe-spt/webhooks",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=1234,v1=fakesig",
            },
        )
        assert resp.status_code == 500

    def test_malformed_json_returns_400(self):
        client = self._client()
        payload_bytes = b"not valid json {"
        sig = _stripe_sig_header(payload_bytes, self._SECRET)
        resp = client.post(
            "/stripe-spt/webhooks",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": sig,
            },
        )
        assert resp.status_code == 400
        assert "Invalid JSON" in resp.json()["detail"]
