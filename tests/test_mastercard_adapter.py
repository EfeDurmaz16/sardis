"""Tests for Mastercard Agent Pay adapter and webhook handler."""
from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_v2_core.credential_store import CredentialEncryption
from sardis_v2_core.delegated_adapters.mastercard_agent_pay import (
    MastercardAgentPayAdapter,
    MockMastercardAgentPayAdapter,
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


def _make_active_credential(
    consent_id: str = "dcns_mc_test",
    scope: CredentialScope | None = None,
) -> DelegatedCredential:
    return DelegatedCredential(
        org_id="org_1",
        agent_id="agent_1",
        network=CredentialNetwork.MASTERCARD_AGENT_PAY,
        status=CredentialStatus.ACTIVE,
        credential_class=CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
        token_reference="mc_tok_ref_test",
        token_encrypted=b"enc_test_payload",
        scope=scope or CredentialScope(),
        consent_id=consent_id,
    )


def _make_request(amount: Decimal = Decimal("75")) -> DelegatedPaymentRequest:
    return DelegatedPaymentRequest(
        credential_reference="mc_tok_ref_test",
        consent_reference="dcns_mc_test",
        merchant_binding="merch_mc_1",
        amount=amount,
        currency="USD",
    )


# ---------------------------------------------------------------------------
# MockMastercardAgentPayAdapter tests
# ---------------------------------------------------------------------------

class TestMockMastercardAgentPayAdapter:

    def test_network_property(self):
        adapter = MockMastercardAgentPayAdapter()
        assert adapter.network == CredentialNetwork.MASTERCARD_AGENT_PAY

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        adapter = MockMastercardAgentPayAdapter()
        cred = _make_active_credential()
        request = _make_request()
        result = await adapter.execute(request, cred)
        assert result.success is True
        assert result.network == "mastercard_agent_pay"
        assert result.amount == Decimal("75")
        assert result.reference_id.startswith("mc_mock_")
        assert result.authorization_id.startswith("mc_auth_mock_")

    @pytest.mark.asyncio
    async def test_failure_on_inactive_credential(self):
        adapter = MockMastercardAgentPayAdapter()
        cred = DelegatedCredential(
            status=CredentialStatus.REVOKED,
            network=CredentialNetwork.MASTERCARD_AGENT_PAY,
            token_reference="mc_tok",
            token_encrypted=b"enc",
            consent_id="dcns_mc_test",
        )
        request = _make_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "not active" in result.error

    @pytest.mark.asyncio
    async def test_configured_failure(self):
        adapter = MockMastercardAgentPayAdapter(should_fail=True)
        cred = _make_active_credential()
        request = _make_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "Mock failure" in result.error
        assert result.reference_id.startswith("mc_mock_fail_")

    @pytest.mark.asyncio
    async def test_check_health(self):
        adapter = MockMastercardAgentPayAdapter()
        assert await adapter.check_health() is True

    @pytest.mark.asyncio
    async def test_estimate_fee(self):
        adapter = MockMastercardAgentPayAdapter()
        fee = await adapter.estimate_fee(Decimal("100"), "USD")
        assert fee == Decimal("2.2")

    @pytest.mark.asyncio
    async def test_provision_credential(self):
        adapter = MockMastercardAgentPayAdapter()
        enc = _make_encryption()
        cred = await adapter.provision_credential(
            org_id="org_1",
            agent_id="agent_1",
            scope=CredentialScope(max_per_tx=Decimal("300")),
            encryption=enc,
        )
        assert cred.network == CredentialNetwork.MASTERCARD_AGENT_PAY
        assert cred.status == CredentialStatus.ACTIVE
        assert cred.credential_class == CredentialClass.REHYDRATABLE_EXECUTION_TOKEN
        assert cred.scope.max_per_tx == Decimal("300")
        assert cred.token_encrypted != b"mock_encrypted"  # was actually encrypted
        assert "token_unique_reference" in cred.provider_metadata
        assert "payment_account_reference" in cred.provider_metadata
        assert cred.provider_metadata["mock"] is True

    @pytest.mark.asyncio
    async def test_provision_credential_without_encryption(self):
        adapter = MockMastercardAgentPayAdapter()
        cred = await adapter.provision_credential(
            org_id="org_2",
            agent_id="agent_2",
            scope=CredentialScope(),
        )
        assert cred.token_encrypted == b"mock_encrypted"
        assert cred.network == CredentialNetwork.MASTERCARD_AGENT_PAY

    @pytest.mark.asyncio
    async def test_fee_scales_with_amount(self):
        adapter = MockMastercardAgentPayAdapter()
        small_fee = await adapter.estimate_fee(Decimal("10"), "USD")
        large_fee = await adapter.estimate_fee(Decimal("1000"), "USD")
        assert small_fee == Decimal("0.22")
        assert large_fee == Decimal("22.0")

    @pytest.mark.asyncio
    async def test_raw_response_shape(self):
        adapter = MockMastercardAgentPayAdapter()
        cred = _make_active_credential()
        request = _make_request(amount=Decimal("50"))
        result = await adapter.execute(request, cred)
        raw = result.raw_response
        assert raw["status"] == "APPROVED"
        assert raw["transactionAmount"]["value"] == "5000"
        assert raw["transactionAmount"]["currency"] == "USD"


# ---------------------------------------------------------------------------
# MastercardAgentPayAdapter (real) tests
# ---------------------------------------------------------------------------

class TestMastercardAgentPayAdapter:

    def test_network_property(self):
        adapter = MastercardAgentPayAdapter(consumer_key="ck_test")
        assert adapter.network == CredentialNetwork.MASTERCARD_AGENT_PAY

    @pytest.mark.asyncio
    async def test_check_health_configured(self):
        adapter = MastercardAgentPayAdapter(
            consumer_key="ck_test",
            p12_certificate_path="/path/to/cert.p12",
        )
        assert await adapter.check_health() is True

    @pytest.mark.asyncio
    async def test_check_health_missing_consumer_key(self):
        adapter = MastercardAgentPayAdapter(p12_certificate_path="/path/to/cert.p12")
        assert await adapter.check_health() is False

    @pytest.mark.asyncio
    async def test_check_health_missing_p12(self):
        adapter = MastercardAgentPayAdapter(consumer_key="ck_test")
        assert await adapter.check_health() is False

    @pytest.mark.asyncio
    async def test_check_health_unconfigured(self):
        adapter = MastercardAgentPayAdapter()
        assert await adapter.check_health() is False

    @pytest.mark.asyncio
    async def test_estimate_fee(self):
        adapter = MastercardAgentPayAdapter(consumer_key="ck_test")
        fee = await adapter.estimate_fee(Decimal("200"), "USD")
        assert fee == Decimal("4.4")

    @pytest.mark.asyncio
    async def test_execute_decryption_failure_returns_error(self):
        """execute() returns a failure result when credential decryption fails."""
        enc = _make_encryption()
        adapter = MastercardAgentPayAdapter(
            consumer_key="ck_test",
            encryption=enc,
        )
        cred = _make_active_credential()
        # token_encrypted is raw bytes (not valid Fernet ciphertext) — will fail decryption
        request = _make_request()
        result = await adapter.execute(request, cred)
        assert result.success is False
        assert "Credential decryption failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_raises_not_implemented_after_decrypt(self):
        """execute() raises NotImplementedError when credential decrypts successfully."""
        enc = _make_encryption()
        token = b"mc_tur_test_token"
        encrypted = enc.encrypt_with_envelope(token)
        cred = DelegatedCredential(
            org_id="org_1",
            agent_id="agent_1",
            network=CredentialNetwork.MASTERCARD_AGENT_PAY,
            status=CredentialStatus.ACTIVE,
            credential_class=CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
            token_reference="mc_tok_ref_test",
            token_encrypted=encrypted,
            consent_id="dcns_test",
        )
        adapter = MastercardAgentPayAdapter(consumer_key="ck_test", encryption=enc)
        request = _make_request()
        with pytest.raises(NotImplementedError, match="MDES Agent Pay API not yet available"):
            await adapter.execute(request, cred)

    @pytest.mark.asyncio
    async def test_provision_raises_not_implemented(self):
        adapter = MastercardAgentPayAdapter(consumer_key="ck_test")
        with pytest.raises(NotImplementedError, match="MDES tokenization API not yet available"):
            await adapter.provision_credential(
                org_id="org_1",
                agent_id="agent_1",
                scope=CredentialScope(),
            )

    def test_translate_to_mastercard_shape(self):
        """_translate_to_mastercard() produces the expected MDES request shape."""
        adapter = MastercardAgentPayAdapter(consumer_key="ck_test")
        request = DelegatedPaymentRequest(
            idempotency_key="dpay_idempotency_key_123",
            merchant_binding="merch_mc_1",
            amount=Decimal("99.50"),
            currency="USD",
        )
        token = b"mc_tur_abc123"
        result = adapter._translate_to_mastercard(request, token)
        assert result["requestId"] == "dpay_idempotency_key_123"
        assert result["tokenUniqueReference"] == "mc_tur_abc123"
        assert result["transactionAmount"]["value"] == "9950"
        assert result["transactionAmount"]["currency"] == "USD"
        assert result["merchantIdentifier"] == "merch_mc_1"
        assert result["channel"] == "AGENT_PAY"

    def test_translate_from_mastercard_approved(self):
        """_translate_from_mastercard() maps APPROVED status correctly."""
        response = {
            "transactionId": "txn_mc_001",
            "status": "APPROVED",
            "transactionAmount": {"value": "5000", "currency": "USD"},
            "authorizationCode": "auth_mc_001",
        }
        result = MastercardAgentPayAdapter._translate_from_mastercard(response)
        assert result.success is True
        assert result.network == "mastercard_agent_pay"
        assert result.reference_id == "txn_mc_001"
        assert result.amount == Decimal("50")
        assert result.currency == "USD"
        assert result.authorization_id == "auth_mc_001"
        assert result.settlement_status == "pending"

    def test_translate_from_mastercard_declined(self):
        """_translate_from_mastercard() maps non-APPROVED status as failure."""
        response = {
            "transactionId": "txn_mc_002",
            "status": "DECLINED",
            "transactionAmount": {"value": "2000", "currency": "EUR"},
            "authorizationCode": "",
        }
        result = MastercardAgentPayAdapter._translate_from_mastercard(response)
        assert result.success is False
        assert result.settlement_status == "failed"


# ---------------------------------------------------------------------------
# Webhook handler tests
# ---------------------------------------------------------------------------

def _compute_sig(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


class TestMastercardWebhookHandler:

    @pytest.mark.asyncio
    async def test_webhook_returns_200_no_secret_configured(self, test_client):
        """When MASTERCARD_WEBHOOK_SECRET is not set, webhook still returns 200."""
        payload = json.dumps({
            "type": "TOKEN_ACTIVE",
            "id": "evt_mc_001",
            "data": {"tokenUniqueReference": "mc_tur_test"},
        }).encode()

        response = await test_client.post(
            "/mastercard/webhooks",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert response.json() == {"received": True}

    @pytest.mark.asyncio
    async def test_webhook_valid_signature(self, test_client, monkeypatch):
        """Valid HMAC signature passes verification."""
        secret = "test_mc_webhook_secret"
        monkeypatch.setenv("MASTERCARD_WEBHOOK_SECRET", secret)

        payload = json.dumps({
            "type": "AUTHORIZATION_APPROVED",
            "id": "evt_mc_002",
            "data": {
                "transactionId": "txn_mc_auth_001",
                "authorizationCode": "AUTH123",
            },
        }).encode()
        sig = _compute_sig(secret, payload)

        response = await test_client.post(
            "/mastercard/webhooks",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Mastercard-Signature": sig,
            },
        )
        assert response.status_code == 200
        assert response.json() == {"received": True}

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_rejected(self, test_client, monkeypatch):
        """Invalid HMAC signature returns 400."""
        secret = "test_mc_webhook_secret"
        monkeypatch.setenv("MASTERCARD_WEBHOOK_SECRET", secret)

        payload = json.dumps({"type": "TOKEN_SUSPENDED", "id": "evt_mc_003"}).encode()

        response = await test_client.post(
            "/mastercard/webhooks",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Mastercard-Signature": "invalid_signature_hex",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_missing_signature_when_secret_configured(self, test_client, monkeypatch):
        """Missing signature header returns 400 when secret is configured."""
        monkeypatch.setenv("MASTERCARD_WEBHOOK_SECRET", "test_mc_webhook_secret")

        payload = json.dumps({"type": "TOKEN_DELETED", "id": "evt_mc_004"}).encode()

        response = await test_client.post(
            "/mastercard/webhooks",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_token_lifecycle_event(self, test_client):
        """Token lifecycle events are handled and return 200."""
        for event_type in ["TOKEN_CREATED", "TOKEN_ACTIVE", "TOKEN_SUSPENDED",
                           "TOKEN_DELETED", "TOKEN_EXPIRED"]:
            payload = json.dumps({
                "type": event_type,
                "id": f"evt_mc_{event_type.lower()}",
                "data": {"tokenUniqueReference": "mc_tur_abc"},
            }).encode()

            response = await test_client.post(
                "/mastercard/webhooks",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 200, f"Failed for event_type={event_type}"

    @pytest.mark.asyncio
    async def test_webhook_authorization_events(self, test_client):
        """Authorization result events are handled and return 200."""
        for event_type in ["AUTHORIZATION_APPROVED", "AUTHORIZATION_DECLINED",
                           "AUTHORIZATION_REVERSED"]:
            payload = json.dumps({
                "type": event_type,
                "id": f"evt_mc_{event_type.lower()}",
                "data": {
                    "transactionId": "txn_mc_001",
                    "authorizationCode": "CODE123",
                },
            }).encode()

            response = await test_client.post(
                "/mastercard/webhooks",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 200, f"Failed for event_type={event_type}"

    @pytest.mark.asyncio
    async def test_webhook_unknown_event_type_still_200(self, test_client):
        """Unknown event types are silently ignored and return 200."""
        payload = json.dumps({
            "type": "UNKNOWN_FUTURE_EVENT",
            "id": "evt_mc_unknown",
        }).encode()

        response = await test_client.post(
            "/mastercard/webhooks",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_invalid_json_returns_400(self, test_client):
        """Malformed JSON payload returns 400."""
        response = await test_client.post(
            "/mastercard/webhooks",
            content=b"not valid json {{{",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
