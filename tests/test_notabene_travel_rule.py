"""Tests for Notabene Travel Rule provider.

Covers issue #139. All API calls are mocked.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from sardis_compliance.providers.notabene import (
    ASSET_MAP,
    CHAIN_MAP,
    NOTABENE_API_URLS,
    AddressType,
    NotabeneError,
    NotabeneTransfer,
    NotabeneTransferStatus,
    NotabeneTravelRuleProvider,
    SafePIIMode,
    ValidationResult,
    ValidationType,
    _build_beneficiary_ivms,
    _build_originator_ivms,
    _status_to_travel_rule,
)
from sardis_compliance.travel_rule import (
    BeneficiaryInfo,
    OriginatorInfo,
    TravelRuleStatus,
    TravelRuleTransfer,
    VASPProtocol,
    create_travel_rule_service,
)


# ============ Mock API Responses ============

VALIDATE_TRAVELRULE_RESPONSE = {
    "isValid": True,
    "type": "TRAVELRULE",
    "beneficiaryAddressType": "HOSTED",
    "beneficiaryVASPdid": "did:web:notabene.id:vasp:counterparty",
    "beneficiaryVASPname": "CounterpartyVASP",
    "errors": [],
    "warnings": [],
}

VALIDATE_BELOW_THRESHOLD_RESPONSE = {
    "isValid": True,
    "type": "BELOW_THRESHOLD",
    "beneficiaryAddressType": "UNKNOWN",
    "errors": [],
    "warnings": [],
}

VALIDATE_NON_CUSTODIAL_RESPONSE = {
    "isValid": True,
    "type": "NON_CUSTODIAL",
    "beneficiaryAddressType": "UNHOSTED",
    "errors": [],
    "warnings": ["Unhosted wallet — proof of ownership recommended"],
}

TRANSFER_CREATED_RESPONSE = {
    "id": "nb_tx_abc123",
    "status": "INITIATED",
    "originatorVASPdid": "did:web:notabene.id:vasp:sardis",
    "beneficiaryVASPdid": "did:web:notabene.id:vasp:counterparty",
    "transactionRef": "tr_test123",
}

TRANSFER_AUTHORIZED_RESPONSE = {
    "id": "nb_tx_abc123",
    "status": "AUTHORIZED",
    "originatorVASPdid": "did:web:notabene.id:vasp:sardis",
    "beneficiaryVASPdid": "did:web:notabene.id:vasp:counterparty",
    "transactionRef": "tr_test123",
}

TRANSFER_REJECTED_RESPONSE = {
    "id": "nb_tx_abc123",
    "status": "REJECTED",
    "transactionRef": "tr_test123",
}

VASP_INFO_RESPONSE = {
    "did": "did:web:notabene.id:vasp:counterparty",
    "name": "CounterpartyVASP",
    "website": "https://counterparty.com",
    "pii_didkey": "did:key:z6MkhaXgBZDvotDkL5257fa...",
}

ADDRESS_DISCOVERY_RESPONSE = {
    "addressType": "HOSTED",
    "vaspDID": "did:web:notabene.id:vasp:counterparty",
    "vaspName": "CounterpartyVASP",
}


def _mock_response(json_data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=json_data,
        request=httpx.Request("POST", "https://api.notabene.dev/tf/validate"),
    )


def _make_transfer(
    transfer_id: str = "tr_test123",
    amount: str = "5000",
) -> TravelRuleTransfer:
    return TravelRuleTransfer(
        transfer_id=transfer_id,
        tx_id="tx_abc",
        amount=Decimal(amount),
        currency="USDC",
        chain="base",
        originator=OriginatorInfo(
            name="Alice Smith",
            account_id="0x1111111111111111111111111111111111111111",
            country="US",
        ),
        beneficiary=BeneficiaryInfo(
            name="Bob Jones",
            account_id="0x2222222222222222222222222222222222222222",
            vasp_id="did:web:notabene.id:vasp:counterparty",
            country="DE",
        ),
    )


# ============ Provider Initialization Tests ============

class TestProviderInit:
    def test_defaults(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="test-token",
            vasp_did="did:web:notabene.id:vasp:sardis",
        )
        assert provider.is_configured is True
        assert provider._base_url == NOTABENE_API_URLS["sandbox"]

    def test_production_environment(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok",
            vasp_did="did:web:sardis",
            environment="production",
        )
        assert provider._base_url == NOTABENE_API_URLS["production"]

    def test_not_configured_no_token(self):
        provider = NotabeneTravelRuleProvider(auth_token="", vasp_did="did:test")
        assert provider.is_configured is False

    def test_not_configured_no_vasp(self):
        provider = NotabeneTravelRuleProvider(auth_token="tok", vasp_did="")
        assert provider.is_configured is False

    def test_env_var_config(self):
        with patch.dict("os.environ", {
            "NOTABENE_AUTH_TOKEN": "env-token",
            "NOTABENE_VASP_DID": "did:web:env",
            "NOTABENE_ENVIRONMENT": "production",
        }):
            provider = NotabeneTravelRuleProvider()
            assert provider.is_configured is True
            assert provider._base_url == NOTABENE_API_URLS["production"]

    def test_headers(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="my-secret-token",
            vasp_did="did:web:sardis",
        )
        headers = provider._headers()
        assert headers["Authorization"] == "Bearer my-secret-token"
        assert headers["Content-Type"] == "application/json"

    def test_pii_mode(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok",
            vasp_did="did:web:sardis",
            pii_mode=SafePIIMode.END_TO_END,
        )
        assert provider._pii_mode == SafePIIMode.END_TO_END


# ============ Validation Tests ============

class TestValidation:
    @pytest.mark.asyncio
    async def test_validate_travel_rule_required(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        transfer = _make_transfer()
        mock_resp = _mock_response(VALIDATE_TRAVELRULE_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.validate_transfer(transfer)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.transfer_type == ValidationType.TRAVELRULE
        assert result.beneficiary_address_type == AddressType.HOSTED
        assert result.beneficiary_vasp_did == "did:web:notabene.id:vasp:counterparty"
        assert result.beneficiary_vasp_name == "CounterpartyVASP"
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_validate_below_threshold(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        transfer = _make_transfer(amount="500")
        mock_resp = _mock_response(VALIDATE_BELOW_THRESHOLD_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.validate_transfer(transfer)

        assert result.transfer_type == ValidationType.BELOW_THRESHOLD
        assert result.beneficiary_address_type == AddressType.UNKNOWN

    @pytest.mark.asyncio
    async def test_validate_non_custodial(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        transfer = _make_transfer()
        mock_resp = _mock_response(VALIDATE_NON_CUSTODIAL_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.validate_transfer(transfer)

        assert result.transfer_type == ValidationType.NON_CUSTODIAL
        assert result.beneficiary_address_type == AddressType.UNHOSTED
        assert len(result.warnings) == 1

    @pytest.mark.asyncio
    async def test_validate_not_configured_raises(self):
        provider = NotabeneTravelRuleProvider(auth_token="", vasp_did="")
        with pytest.raises(NotabeneError, match="not configured"):
            await provider.validate_transfer(_make_transfer())

    @pytest.mark.asyncio
    async def test_validate_api_error_raises(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        error_resp = httpx.Response(
            status_code=403,
            json={"error": "Forbidden"},
            request=httpx.Request("POST", "https://api.notabene.dev/tf/validate"),
        )
        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "Forbidden", request=error_resp.request, response=error_resp,
            ),
        ):
            with pytest.raises(NotabeneError, match="403"):
                await provider.validate_transfer(_make_transfer())

    @pytest.mark.asyncio
    async def test_validate_connection_error(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("timeout"),
        ):
            with pytest.raises(NotabeneError, match="failed"):
                await provider.validate_transfer(_make_transfer())


# ============ Transfer Creation Tests ============

class TestSendTransferInfo:
    @pytest.mark.asyncio
    async def test_create_transfer(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        transfer = _make_transfer()
        mock_resp = _mock_response(TRANSFER_CREATED_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            status = await provider.send_transfer_info(transfer)

        assert status == TravelRuleStatus.SENT
        assert "tr_test123" in provider._transfers
        nb_transfer = provider._transfers["tr_test123"]
        assert nb_transfer.notabene_id == "nb_tx_abc123"
        assert nb_transfer.status == NotabeneTransferStatus.INITIATED

    @pytest.mark.asyncio
    async def test_create_transfer_not_configured(self):
        provider = NotabeneTravelRuleProvider(auth_token="", vasp_did="")
        with pytest.raises(NotabeneError, match="not configured"):
            await provider.send_transfer_info(_make_transfer())

    @pytest.mark.asyncio
    async def test_create_transfer_api_error(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        error_resp = httpx.Response(
            status_code=422,
            json={"error": "Validation failed"},
            request=httpx.Request("POST", "https://api.notabene.dev/tf/entity/test/tx"),
        )
        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "Unprocessable", request=error_resp.request, response=error_resp,
            ),
        ):
            with pytest.raises(NotabeneError, match="422"):
                await provider.send_transfer_info(_make_transfer())


# ============ Status Check Tests ============

class TestCheckTransferStatus:
    @pytest.mark.asyncio
    async def test_check_authorized(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        # Seed internal state
        provider._transfers["tr_test123"] = NotabeneTransfer(
            notabene_id="nb_tx_abc123",
            local_transfer_id="tr_test123",
        )
        mock_resp = _mock_response(TRANSFER_AUTHORIZED_RESPONSE)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            status = await provider.check_transfer_status("tr_test123")

        assert status == TravelRuleStatus.CONFIRMED
        assert provider._transfers["tr_test123"].status == NotabeneTransferStatus.AUTHORIZED

    @pytest.mark.asyncio
    async def test_check_rejected(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        provider._transfers["tr_test123"] = NotabeneTransfer(
            notabene_id="nb_tx_abc123",
            local_transfer_id="tr_test123",
        )
        mock_resp = _mock_response(TRANSFER_REJECTED_RESPONSE)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            status = await provider.check_transfer_status("tr_test123")

        assert status == TravelRuleStatus.REJECTED

    @pytest.mark.asyncio
    async def test_check_unknown_transfer(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        status = await provider.check_transfer_status("tr_unknown")
        assert status == TravelRuleStatus.PENDING

    @pytest.mark.asyncio
    async def test_check_not_configured(self):
        provider = NotabeneTravelRuleProvider(auth_token="", vasp_did="")
        with pytest.raises(NotabeneError, match="not configured"):
            await provider.check_transfer_status("tr_test123")


# ============ Counterparty Discovery Tests ============

class TestCounterpartyDiscovery:
    @pytest.mark.asyncio
    async def test_discover_hosted(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        mock_resp = _mock_response(ADDRESS_DISCOVERY_RESPONSE)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.discover_counterparty(
                "0x2222222222222222222222222222222222222222",
                blockchain="BASE",
            )

        assert result["addressType"] == "HOSTED"
        assert result["vaspDID"] == "did:web:notabene.id:vasp:counterparty"

    @pytest.mark.asyncio
    async def test_discover_not_configured(self):
        provider = NotabeneTravelRuleProvider(auth_token="", vasp_did="")
        with pytest.raises(NotabeneError, match="not configured"):
            await provider.discover_counterparty("0x1234")


# ============ VASP Info Tests ============

class TestGetVaspInfo:
    @pytest.mark.asyncio
    async def test_get_vasp_info(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        mock_resp = _mock_response(VASP_INFO_RESPONSE)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.get_vasp_info("did:web:notabene.id:vasp:counterparty")

        assert result["name"] == "CounterpartyVASP"
        assert "pii_didkey" in result


# ============ Webhook Tests ============

class TestWebhookProcessing:
    def test_process_transaction_updated(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        provider._transfers["tr_test123"] = NotabeneTransfer(
            notabene_id="nb_tx_abc123",
            local_transfer_id="tr_test123",
        )

        status = provider.process_webhook_event(
            "notification.transactionUpdated",
            {"transaction": {"transactionRef": "tr_test123", "status": "AUTHORIZED"}},
        )
        assert status == TravelRuleStatus.CONFIRMED

    def test_process_halt_transaction(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        provider._transfers["tr_test123"] = NotabeneTransfer(
            notabene_id="nb_tx_abc123",
            local_transfer_id="tr_test123",
        )

        status = provider.process_webhook_event(
            "notification.haltBlockchainTransaction",
            {"transaction": {"transactionRef": "tr_test123", "status": "CANCELLED"}},
        )
        assert status == TravelRuleStatus.REJECTED

    def test_process_unknown_event(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        result = provider.process_webhook_event("notification.unknown", {})
        assert result is None

    def test_process_unknown_transfer_ref(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        result = provider.process_webhook_event(
            "notification.transactionUpdated",
            {"transaction": {"transactionRef": "tr_unknown", "status": "AUTHORIZED"}},
        )
        assert result is None

    def test_verify_webhook_no_secret(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        assert provider.verify_webhook_signature(b"payload", "v1,abc", "msg1", "12345") is False

    def test_verify_webhook_no_timestamp(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok",
            vasp_did="did:web:sardis",
            webhook_secret="secret",
        )
        assert provider.verify_webhook_signature(b"payload", "v1,abc", "msg1", None) is False


# ============ Health Check Tests ============

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        mock_resp = httpx.Response(
            200, json=[],
            request=httpx.Request("GET", "https://api.notabene.dev/tf/simple/vasps"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_unreachable(self):
        provider = NotabeneTravelRuleProvider(
            auth_token="tok", vasp_did="did:web:sardis",
        )
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("refused"),
        ):
            assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_not_configured(self):
        provider = NotabeneTravelRuleProvider(auth_token="", vasp_did="")
        assert await provider.health_check() is False


# ============ IVMS 101 Builder Tests ============

class TestIVMSBuilders:
    def test_originator_full_name(self):
        info = OriginatorInfo(
            name="Alice Marie Smith",
            account_id="0x1111",
            country="US",
            date_of_birth="1990-01-15",
            national_id="123-45-6789",
        )
        ivms = _build_originator_ivms(info)
        np = ivms["naturalPerson"]
        name = np["name"]["nameIdentifier"][0]
        assert name["primaryIdentifier"] == "Smith"
        assert name["secondaryIdentifier"] == "Alice Marie"
        assert np["geographicAddress"][0]["country"] == "US"
        assert np["dateOfBirth"] == "1990-01-15"
        assert np["nationalIdentification"]["nationalIdentifier"] == "123-45-6789"

    def test_originator_single_name(self):
        info = OriginatorInfo(name="Alice", account_id="0x1111")
        ivms = _build_originator_ivms(info)
        name = ivms["naturalPerson"]["name"]["nameIdentifier"][0]
        assert name["primaryIdentifier"] == "Alice"
        assert "secondaryIdentifier" not in name

    def test_beneficiary_full(self):
        info = BeneficiaryInfo(
            name="Bob Jones",
            account_id="0x2222",
            country="DE",
        )
        ivms = _build_beneficiary_ivms(info)
        name = ivms["naturalPerson"]["name"]["nameIdentifier"][0]
        assert name["primaryIdentifier"] == "Jones"
        assert name["secondaryIdentifier"] == "Bob"
        assert ivms["naturalPerson"]["geographicAddress"][0]["country"] == "DE"

    def test_beneficiary_minimal(self):
        info = BeneficiaryInfo(name="Bob", account_id="0x2222")
        ivms = _build_beneficiary_ivms(info)
        name = ivms["naturalPerson"]["name"]["nameIdentifier"][0]
        assert name["primaryIdentifier"] == "Bob"


# ============ Status Mapping Tests ============

class TestStatusMapping:
    def test_initiated_to_sent(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.INITIATED) == TravelRuleStatus.SENT

    def test_authorized_to_confirmed(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.AUTHORIZED) == TravelRuleStatus.CONFIRMED

    def test_settled_to_confirmed(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.SETTLED) == TravelRuleStatus.CONFIRMED

    def test_rejected_to_rejected(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.REJECTED) == TravelRuleStatus.REJECTED

    def test_cancelled_to_rejected(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.CANCELLED) == TravelRuleStatus.REJECTED

    def test_failed_to_rejected(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.FAILED) == TravelRuleStatus.REJECTED

    def test_pending_beneficiary_to_sent(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.PENDING_BENEFICIARY) == TravelRuleStatus.SENT

    def test_pending_originator_to_received(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.PENDING_ORIGINATOR) == TravelRuleStatus.RECEIVED

    def test_incomplete_to_pending(self):
        assert _status_to_travel_rule(NotabeneTransferStatus.INCOMPLETE) == TravelRuleStatus.PENDING


# ============ Constants Tests ============

class TestConstants:
    def test_asset_map(self):
        assert ASSET_MAP["USDC"] == "USDC"
        assert ASSET_MAP["ETH"] == "ETH"

    def test_chain_map(self):
        assert CHAIN_MAP["base"] == "BASE"
        assert CHAIN_MAP["ethereum"] == "ETH"
        assert CHAIN_MAP["polygon"] == "MATIC"
        assert CHAIN_MAP["arbitrum"] == "ARB"

    def test_api_urls(self):
        assert "notabene.id" in NOTABENE_API_URLS["production"]
        assert "notabene.dev" in NOTABENE_API_URLS["sandbox"]


# ============ VASPProtocol Enum Tests ============

class TestVASPProtocol:
    def test_notabene_protocol_exists(self):
        assert VASPProtocol.NOTABENE == "notabene"

    def test_all_protocols(self):
        values = {p.value for p in VASPProtocol}
        assert "notabene" in values
        assert "trisa" in values
        assert "manual" in values


# ============ Factory Integration Tests ============

class TestFactory:
    def test_manual_default(self):
        service = create_travel_rule_service()
        from sardis_compliance.travel_rule import ManualTravelRuleProvider
        assert isinstance(service._provider, ManualTravelRuleProvider)

    def test_notabene_factory(self):
        service = create_travel_rule_service(provider_name="notabene")
        assert isinstance(service._provider, NotabeneTravelRuleProvider)

    def test_env_var_factory(self):
        with patch.dict("os.environ", {"SARDIS_TRAVEL_RULE_PROVIDER": "notabene"}):
            service = create_travel_rule_service()
            assert isinstance(service._provider, NotabeneTravelRuleProvider)


# ============ Module Export Tests ============

class TestModuleExports:
    def test_from_providers(self):
        from sardis_compliance.providers import NotabeneTravelRuleProvider
        assert NotabeneTravelRuleProvider is not None

    def test_from_compliance(self):
        from sardis_compliance import NotabeneTravelRuleProvider
        assert NotabeneTravelRuleProvider is not None
