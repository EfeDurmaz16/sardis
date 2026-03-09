"""Tests for Visa TAP adapter and webhook handler."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from decimal import Decimal

import pytest
from sardis_v2_core.credential_store import CredentialEncryption
from sardis_v2_core.delegated_adapters.visa_tap import (
    MockVisaTAPAdapter,
    VisaTAPAdapter,
    verify_visa_tap_signature,
)
from sardis_v2_core.delegated_credential import (
    CredentialClass,
    CredentialNetwork,
    CredentialScope,
    CredentialStatus,
    DelegatedCredential,
)
from sardis_v2_core.delegated_executor import DelegatedPaymentRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fernet_key() -> bytes:
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


def _make_encryption() -> CredentialEncryption:
    return CredentialEncryption(key=_fernet_key())


def _make_active_visa_credential(
    consent_id: str = "dcns_visa_test",
    scope: CredentialScope | None = None,
) -> DelegatedCredential:
    return DelegatedCredential(
        org_id="org_1",
        agent_id="agent_1",
        network=CredentialNetwork.VISA_TAP,
        status=CredentialStatus.ACTIVE,
        credential_class=CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
        token_reference="tok_ref_visa_test",
        token_encrypted=b"enc_visa_test_payload",
        scope=scope or CredentialScope(),
        consent_id=consent_id,
        provider_metadata={
            "trid": "TRID_TEST",
            "dpan_ref": "dpan_test_ref",
            "par": "PAR_TEST_123",
        },
    )


def _make_visa_request(amount: Decimal = Decimal("75")) -> DelegatedPaymentRequest:
    return DelegatedPaymentRequest(
        credential_reference="tok_ref_visa_test",
        consent_reference="dcns_visa_test",
        merchant_binding="merch_visa_1",
        amount=amount,
        currency="USD",
    )


# ---------------------------------------------------------------------------
# MockVisaTAPAdapter tests
# ---------------------------------------------------------------------------


class TestMockVisaTAPAdapter:

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        adapter = MockVisaTAPAdapter()
        cred = _make_active_visa_credential()
        request = _make_visa_request()
        result = await adapter.execute(request, cred)
        assert result.success is True
        assert result.network == "visa_tap"
        assert result.amount == Decimal("75")
        assert result.reference_id.startswith("visa_mock_")
        assert result.authorization_id.startswith("auth_visa_mock_")

    @pytest.mark.asyncio
    async def test_failure_on_inactive_credential(self):
        adapter = MockVisaTAPAdapter()
        cred = DelegatedCredential(
            status=CredentialStatus.REVOKED,
            network=CredentialNetwork.VISA_TAP,
            token_reference="tok",
            token_encrypted=b"enc",
            consent_id="dcns_visa_test",
        )
        request = _make_visa_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "not active" in result.error

    @pytest.mark.asyncio
    async def test_failure_on_suspended_credential(self):
        adapter = MockVisaTAPAdapter()
        cred = DelegatedCredential(
            status=CredentialStatus.SUSPENDED,
            network=CredentialNetwork.VISA_TAP,
            token_reference="tok",
            token_encrypted=b"enc",
            consent_id="dcns_visa_test",
        )
        request = _make_visa_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "not active" in result.error

    @pytest.mark.asyncio
    async def test_configured_failure(self):
        adapter = MockVisaTAPAdapter(should_fail=True)
        cred = _make_active_visa_credential()
        request = _make_visa_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "Mock failure" in result.error
        assert result.reference_id.startswith("visa_mock_fail_")

    @pytest.mark.asyncio
    async def test_check_health(self):
        adapter = MockVisaTAPAdapter()
        assert await adapter.check_health() is True

    @pytest.mark.asyncio
    async def test_check_health_always_true_regardless_of_fail_flag(self):
        adapter = MockVisaTAPAdapter(should_fail=True)
        assert await adapter.check_health() is True

    @pytest.mark.asyncio
    async def test_estimate_fee(self):
        adapter = MockVisaTAPAdapter()
        fee = await adapter.estimate_fee(Decimal("100"), "USD")
        assert fee == Decimal("2.0")

    @pytest.mark.asyncio
    async def test_estimate_fee_proportional(self):
        adapter = MockVisaTAPAdapter()
        fee_small = await adapter.estimate_fee(Decimal("50"), "USD")
        fee_large = await adapter.estimate_fee(Decimal("200"), "USD")
        assert fee_small == Decimal("1.0")
        assert fee_large == Decimal("4.0")

    @pytest.mark.asyncio
    async def test_provision_credential(self):
        adapter = MockVisaTAPAdapter()
        enc = _make_encryption()
        cred = await adapter.provision_credential(
            org_id="org_1",
            agent_id="agent_1",
            scope=CredentialScope(max_per_tx=Decimal("300")),
            encryption=enc,
        )
        assert cred.network == CredentialNetwork.VISA_TAP
        assert cred.status == CredentialStatus.ACTIVE
        assert cred.credential_class == CredentialClass.REHYDRATABLE_EXECUTION_TOKEN
        assert cred.scope.max_per_tx == Decimal("300")
        # Was actually encrypted (not the placeholder)
        assert cred.token_encrypted != b"mock_encrypted"
        # Provider metadata must contain PAR and TRID
        assert "par" in cred.provider_metadata
        assert "trid" in cred.provider_metadata
        assert "dpan_ref" in cred.provider_metadata
        assert cred.provider_metadata.get("mock") is True

    @pytest.mark.asyncio
    async def test_provision_credential_without_encryption(self):
        adapter = MockVisaTAPAdapter()
        cred = await adapter.provision_credential(
            org_id="org_2",
            agent_id="agent_2",
            scope=CredentialScope(),
        )
        assert cred.network == CredentialNetwork.VISA_TAP
        assert cred.token_encrypted == b"mock_encrypted"

    @pytest.mark.asyncio
    async def test_network_property(self):
        adapter = MockVisaTAPAdapter()
        assert adapter.network == CredentialNetwork.VISA_TAP

    @pytest.mark.asyncio
    async def test_fee_in_result(self):
        adapter = MockVisaTAPAdapter()
        cred = _make_active_visa_credential()
        request = _make_visa_request(amount=Decimal("100"))
        result = await adapter.execute(request, cred)
        assert result.success is True
        assert result.fee == Decimal("2.0")  # 2% of 100


# ---------------------------------------------------------------------------
# VisaTAPAdapter (real) tests
# ---------------------------------------------------------------------------


class TestVisaTAPAdapter:

    def test_network_property(self):
        adapter = VisaTAPAdapter()
        assert adapter.network == CredentialNetwork.VISA_TAP

    @pytest.mark.asyncio
    async def test_check_health_false_without_config(self):
        adapter = VisaTAPAdapter()
        assert await adapter.check_health() is False

    @pytest.mark.asyncio
    async def test_check_health_false_missing_certificate(self):
        adapter = VisaTAPAdapter(api_key="test_key", certificate_path="")
        assert await adapter.check_health() is False

    @pytest.mark.asyncio
    async def test_check_health_false_missing_api_key(self):
        adapter = VisaTAPAdapter(api_key="", certificate_path="/path/to/cert.pem")
        assert await adapter.check_health() is False

    @pytest.mark.asyncio
    async def test_check_health_true_with_both_configured(self):
        adapter = VisaTAPAdapter(
            api_key="test_api_key",
            certificate_path="/path/to/cert.pem",
        )
        assert await adapter.check_health() is True

    @pytest.mark.asyncio
    async def test_estimate_fee(self):
        adapter = VisaTAPAdapter()
        fee = await adapter.estimate_fee(Decimal("100"), "USD")
        assert fee == Decimal("2.0")

    @pytest.mark.asyncio
    async def test_execute_raises_not_implemented_on_decrypt_success(self):
        """Real adapter raises NotImplementedError once decryption succeeds."""
        enc = _make_encryption()
        adapter = VisaTAPAdapter(
            api_key="test_key",
            certificate_path="/cert.pem",
            trid="TRID_TEST",
            encryption=enc,
        )
        token_bytes = b"dpan_test_value"
        encrypted = enc.encrypt_for_class(
            token_bytes, CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
        )
        cred = DelegatedCredential(
            org_id="org_1",
            agent_id="agent_1",
            network=CredentialNetwork.VISA_TAP,
            status=CredentialStatus.ACTIVE,
            credential_class=CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
            token_reference="tok_ref_real",
            token_encrypted=encrypted,
            consent_id="dcns_real",
        )
        request = _make_visa_request()
        with pytest.raises(NotImplementedError, match="MockVisaTAPAdapter"):
            await adapter.execute(request, cred)

    @pytest.mark.asyncio
    async def test_execute_returns_error_on_decryption_failure(self):
        """Real adapter returns DelegatedPaymentResult with error when decryption fails."""
        enc = _make_encryption()
        adapter = VisaTAPAdapter(
            api_key="test_key",
            certificate_path="/cert.pem",
            encryption=enc,
        )
        cred = DelegatedCredential(
            org_id="org_1",
            agent_id="agent_1",
            network=CredentialNetwork.VISA_TAP,
            status=CredentialStatus.ACTIVE,
            credential_class=CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
            token_reference="tok_ref_bad",
            token_encrypted=b"this_is_not_valid_fernet_ciphertext",
            consent_id="dcns_real",
        )
        request = _make_visa_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "decryption" in result.error.lower()

    @pytest.mark.asyncio
    async def test_provision_raises_not_implemented(self):
        adapter = VisaTAPAdapter(api_key="k", certificate_path="/c.pem", trid="TRID")
        with pytest.raises(NotImplementedError, match="MockVisaTAPAdapter"):
            await adapter.provision_credential(
                org_id="org_1",
                agent_id="agent_1",
                scope=CredentialScope(),
            )

    def test_default_base_url_sandbox(self):
        adapter = VisaTAPAdapter(environment="sandbox")
        assert "sandbox" in adapter._base_url

    def test_default_base_url_production(self):
        adapter = VisaTAPAdapter(environment="production")
        assert "sandbox" not in adapter._base_url

    def test_custom_base_url_overrides_environment(self):
        adapter = VisaTAPAdapter(
            environment="sandbox",
            base_url="https://custom.visa.example.com",
        )
        assert adapter._base_url == "https://custom.visa.example.com"

    def test_translate_to_visa_shape(self):
        """_translate_to_visa produces the correct Visa Token Service payload."""
        enc = _make_encryption()
        adapter = VisaTAPAdapter(trid="TRID_123", encryption=enc)
        request = _make_visa_request(amount=Decimal("50.00"))
        cred = _make_active_visa_credential()
        payload = adapter._translate_to_visa(request, b"dpan_value", cred)
        assert payload["trid"] == "TRID_123"
        assert payload["dpan"] == "dpan_value"
        assert payload["amount"]["value"] == "5000"
        assert payload["amount"]["currency"] == "USD"
        assert payload["paymentAccountReference"] == "PAR_TEST_123"

    def test_translate_from_visa_approved(self):
        raw = {
            "responseCode": "00",
            "transactionId": "txn_123",
            "authorizationCode": "AUTH_ABC",
            "amount": {"value": 5000, "currency": "USD"},
        }
        result = VisaTAPAdapter._translate_from_visa(raw)
        assert result.success is True
        assert result.network == "visa_tap"
        assert result.reference_id == "txn_123"
        assert result.authorization_id == "AUTH_ABC"
        assert result.amount == Decimal("50")
        assert result.currency == "USD"

    def test_translate_from_visa_declined(self):
        raw = {
            "responseCode": "51",
            "transactionId": "txn_declined",
            "amount": {"value": 2000, "currency": "EUR"},
        }
        result = VisaTAPAdapter._translate_from_visa(raw)
        assert result.success is False
        assert result.settlement_status == "pending"


# ---------------------------------------------------------------------------
# verify_visa_tap_signature tests
# ---------------------------------------------------------------------------


class TestVerifyVisaTapSignature:

    def _make_sig(self, secret: str, payload: bytes) -> str:
        return hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256,
        ).hexdigest()

    def test_valid_signature(self):
        secret = "test_webhook_secret"
        payload = b'{"type": "token.suspended"}'
        sig = self._make_sig(secret, payload)
        assert verify_visa_tap_signature(payload, sig, secret) is True

    def test_invalid_signature(self):
        secret = "test_webhook_secret"
        payload = b'{"type": "token.suspended"}'
        assert verify_visa_tap_signature(payload, "bad_signature", secret) is False

    def test_wrong_secret(self):
        payload = b'{"type": "token.suspended"}'
        sig = self._make_sig("correct_secret", payload)
        assert verify_visa_tap_signature(payload, sig, "wrong_secret") is False

    def test_signature_with_leading_trailing_whitespace(self):
        secret = "test_webhook_secret"
        payload = b'{"type": "token.expired"}'
        sig = "  " + self._make_sig(secret, payload) + "  "
        assert verify_visa_tap_signature(payload, sig, secret) is True


# ---------------------------------------------------------------------------
# Visa TAP webhook handler endpoint tests
# ---------------------------------------------------------------------------


class TestVisaTapWebhookEndpoint:
    """Integration-style tests using FastAPI TestClient via httpx + ASGI."""

    def _build_client(self, secret: str):
        """Build an httpx AsyncClient against a minimal FastAPI app."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from sardis_api.routers.visa_tap_webhooks import router

        app = FastAPI()
        app.include_router(router)
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    def _make_signature(self, secret: str, payload: bytes) -> str:
        return hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256,
        ).hexdigest()

    @pytest.mark.asyncio
    async def test_valid_token_lifecycle_event(self, monkeypatch):
        secret = "visa_test_secret"
        monkeypatch.setenv("VISA_TAP_WEBHOOK_SECRET", secret)

        payload = json.dumps({
            "type": "token.suspended",
            "eventId": "evt_visa_001",
            "data": {"tokenId": "tok_visa_abc123"},
        }).encode()
        sig = self._make_signature(secret, payload)

        async with self._build_client(secret) as client:
            resp = await client.post(
                "/visa-tap/webhooks",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Visa-Signature": sig,
                },
            )
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    @pytest.mark.asyncio
    async def test_valid_authorization_event(self, monkeypatch):
        secret = "visa_test_secret"
        monkeypatch.setenv("VISA_TAP_WEBHOOK_SECRET", secret)

        payload = json.dumps({
            "type": "authorization.approved",
            "eventId": "evt_visa_002",
            "data": {
                "transactionId": "txn_abc",
                "responseCode": "00",
            },
        }).encode()
        sig = self._make_signature(secret, payload)

        async with self._build_client(secret) as client:
            resp = await client.post(
                "/visa-tap/webhooks",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Visa-Signature": sig,
                },
            )
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    @pytest.mark.asyncio
    async def test_unknown_event_type_still_returns_200(self, monkeypatch):
        secret = "visa_test_secret"
        monkeypatch.setenv("VISA_TAP_WEBHOOK_SECRET", secret)

        payload = json.dumps({
            "type": "unknown.future_event",
            "eventId": "evt_visa_003",
            "data": {},
        }).encode()
        sig = self._make_signature(secret, payload)

        async with self._build_client(secret) as client:
            resp = await client.post(
                "/visa-tap/webhooks",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Visa-Signature": sig,
                },
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_signature_header_returns_400(self, monkeypatch):
        secret = "visa_test_secret"
        monkeypatch.setenv("VISA_TAP_WEBHOOK_SECRET", secret)

        payload = json.dumps({"type": "token.expired"}).encode()

        async with self._build_client(secret) as client:
            resp = await client.post(
                "/visa-tap/webhooks",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_400(self, monkeypatch):
        secret = "visa_test_secret"
        monkeypatch.setenv("VISA_TAP_WEBHOOK_SECRET", secret)

        payload = json.dumps({"type": "token.deactivated"}).encode()

        async with self._build_client(secret) as client:
            resp = await client.post(
                "/visa-tap/webhooks",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Visa-Signature": "completely_wrong_signature",
                },
            )
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_missing_webhook_secret_env_returns_500(self, monkeypatch):
        monkeypatch.delenv("VISA_TAP_WEBHOOK_SECRET", raising=False)

        payload = json.dumps({"type": "token.expired"}).encode()

        async with self._build_client("") as client:
            resp = await client.post(
                "/visa-tap/webhooks",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Visa-Signature": "any_sig",
                },
            )
        assert resp.status_code == 500
