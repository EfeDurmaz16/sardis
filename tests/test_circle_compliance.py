"""Tests for Circle Compliance Engine integration.

Tests address screening, transaction screening, magic test values,
failover to Elliptic, and integration with the sanctions factory.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_compliance.circle_compliance import (
    CircleComplianceClient,
    CircleComplianceError,
    CircleComplianceProvider,
    CircleScreeningAction,
    CircleScreeningResponse,
    CircleRiskLevel,
    CIRCLE_CHAIN_MAP,
    _map_chain,
    _map_action_to_risk,
    _is_sanctioned,
    create_circle_compliance_provider,
)
from sardis_compliance.sanctions import (
    EntityType,
    FailoverSanctionsProvider,
    MockSanctionsProvider,
    SanctionsRisk,
    ScreeningResult,
    SanctionsService,
    WalletScreeningRequest,
    TransactionScreeningRequest,
    create_sanctions_service,
)


# ── Chain Mapping ────────────────────────────────────────────────────


class TestChainMapping:
    def test_map_base(self):
        assert _map_chain("base") == "BASE"

    def test_map_ethereum(self):
        assert _map_chain("ethereum") == "ETH"

    def test_map_polygon(self):
        assert _map_chain("polygon") == "MATIC"

    def test_map_unknown_chain_uppercases(self):
        assert _map_chain("fantom") == "FANTOM"

    def test_map_testnet(self):
        assert _map_chain("base_sepolia") == "BASE-SEPOLIA"


# ── Action/Risk Mapping ─────────────────────────────────────────────


class TestActionMapping:
    def test_approve_maps_to_low(self):
        assert _map_action_to_risk(CircleScreeningAction.APPROVE) == SanctionsRisk.LOW

    def test_review_maps_to_high(self):
        assert _map_action_to_risk(CircleScreeningAction.REVIEW) == SanctionsRisk.HIGH

    def test_deny_maps_to_blocked(self):
        assert _map_action_to_risk(CircleScreeningAction.DENY) == SanctionsRisk.BLOCKED

    def test_freeze_maps_to_blocked(self):
        assert _map_action_to_risk(CircleScreeningAction.FREEZE_AND_DENY) == SanctionsRisk.BLOCKED

    def test_deny_is_sanctioned(self):
        assert _is_sanctioned(CircleScreeningAction.DENY) is True

    def test_freeze_is_sanctioned(self):
        assert _is_sanctioned(CircleScreeningAction.FREEZE_AND_DENY) is True

    def test_approve_not_sanctioned(self):
        assert _is_sanctioned(CircleScreeningAction.APPROVE) is False

    def test_review_not_sanctioned(self):
        assert _is_sanctioned(CircleScreeningAction.REVIEW) is False


# ── CircleComplianceClient ───────────────────────────────────────────


class TestCircleComplianceClient:
    @pytest.fixture
    def client(self):
        return CircleComplianceClient(api_key="test-circle-key")

    @pytest.mark.asyncio
    async def test_screen_address_approve(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "id": "scr_001",
                "action": "APPROVE",
                "riskLevel": "LOW",
                "screeningResults": [],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            response = await client.screen_address("0xclean123", "base")
            assert response.action == CircleScreeningAction.APPROVE
            assert response.risk_level == CircleRiskLevel.LOW
            assert response.screening_id == "scr_001"
            assert len(response.matches) == 0

    @pytest.mark.asyncio
    async def test_screen_address_deny_sanctions(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "id": "scr_002",
                "action": "DENY",
                "riskLevel": "SEVERE",
                "screeningResults": [
                    {
                        "listName": "OFAC SDN",
                        "category": "sanctions",
                        "description": "Sanctioned entity",
                        "riskLevel": "SEVERE",
                    }
                ],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            response = await client.screen_address("0xsanctioned9999", "base")
            assert response.action == CircleScreeningAction.DENY
            assert response.risk_level == CircleRiskLevel.SEVERE
            assert len(response.matches) == 1
            assert response.matches[0].list_name == "OFAC SDN"

    @pytest.mark.asyncio
    async def test_screen_address_freeze(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "id": "scr_003",
                "action": "FREEZE_AND_DENY",
                "riskLevel": "SEVERE",
                "screeningResults": [
                    {
                        "listName": "Frozen Registry",
                        "category": "frozen",
                        "description": "Frozen address",
                        "riskLevel": "SEVERE",
                    }
                ],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            response = await client.screen_address("0xfrozen8888", "ethereum")
            assert response.action == CircleScreeningAction.FREEZE_AND_DENY
            assert len(response.matches) == 1

    @pytest.mark.asyncio
    async def test_screen_address_review(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "id": "scr_004",
                "action": "REVIEW",
                "riskLevel": "HIGH",
                "screeningResults": [],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            response = await client.screen_address("0xhighrisk5555", "base")
            assert response.action == CircleScreeningAction.REVIEW
            assert response.risk_level == CircleRiskLevel.HIGH

    @pytest.mark.asyncio
    async def test_screen_transfer(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "id": "scr_005",
                "action": "APPROVE",
                "riskLevel": "LOW",
                "screeningResults": [],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            sender_resp, recipient_resp = await client.screen_transfer(
                "0xsender", "0xrecipient", "base"
            )
            assert sender_resp.action == CircleScreeningAction.APPROVE
            assert recipient_resp.action == CircleScreeningAction.APPROVE

    @pytest.mark.asyncio
    async def test_unknown_action_defaults_to_deny(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "id": "scr_006",
                "action": "UNKNOWN_ACTION",
                "riskLevel": "UNKNOWN",
                "screeningResults": [],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            response = await client.screen_address("0xweird", "base")
            assert response.action == CircleScreeningAction.DENY


# ── CircleComplianceProvider (SanctionsProvider) ─────────────────────


class TestCircleComplianceProvider:
    @pytest.fixture
    def provider(self):
        return CircleComplianceProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_screen_wallet_clean(self, provider):
        mock_resp = CircleScreeningResponse(
            screening_id="scr_clean",
            address="0xclean",
            chain="base",
            action=CircleScreeningAction.APPROVE,
            risk_level=CircleRiskLevel.LOW,
        )
        with patch.object(provider._client, "screen_address", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xclean", chain="base")
            )
            assert result.risk_level == SanctionsRisk.LOW
            assert result.is_sanctioned is False
            assert result.provider == "circle_compliance"

    @pytest.mark.asyncio
    async def test_screen_wallet_sanctioned(self, provider):
        from sardis_compliance.circle_compliance import CircleScreeningMatch

        mock_resp = CircleScreeningResponse(
            screening_id="scr_bad",
            address="0xbad",
            chain="base",
            action=CircleScreeningAction.DENY,
            risk_level=CircleRiskLevel.SEVERE,
            matches=[
                CircleScreeningMatch(
                    list_name="OFAC SDN",
                    category="sanctions",
                    description="Sanctioned entity",
                )
            ],
        )
        with patch.object(provider._client, "screen_address", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xbad", chain="base")
            )
            assert result.risk_level == SanctionsRisk.BLOCKED
            assert result.is_sanctioned is True
            assert result.should_block is True
            assert len(result.matches) == 1

    @pytest.mark.asyncio
    async def test_screen_wallet_api_error_fails_closed(self, provider):
        with patch.object(
            provider._client, "screen_address",
            new_callable=AsyncMock,
            side_effect=CircleComplianceError("API timeout"),
        ):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xerror", chain="base")
            )
            assert result.risk_level == SanctionsRisk.BLOCKED
            assert result.should_block is True
            assert "Screening failed" in result.reason

    @pytest.mark.asyncio
    async def test_blocklist_overrides_api(self, provider):
        await provider.add_to_blocklist("0xlocal_block", "test")
        result = await provider.screen_wallet(
            WalletScreeningRequest(address="0xlocal_block", chain="base")
        )
        assert result.is_sanctioned is True
        assert result.should_block is True

    @pytest.mark.asyncio
    async def test_remove_from_blocklist(self, provider):
        await provider.add_to_blocklist("0xtemp", "test")
        await provider.remove_from_blocklist("0xtemp")

        mock_resp = CircleScreeningResponse(
            screening_id="scr_temp",
            address="0xtemp",
            chain="base",
            action=CircleScreeningAction.APPROVE,
            risk_level=CircleRiskLevel.LOW,
        )
        with patch.object(provider._client, "screen_address", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xtemp", chain="base")
            )
            assert result.is_sanctioned is False

    @pytest.mark.asyncio
    async def test_screen_transaction_both_clean(self, provider):
        mock_resp = CircleScreeningResponse(
            screening_id="scr_tx",
            address="",
            chain="base",
            action=CircleScreeningAction.APPROVE,
            risk_level=CircleRiskLevel.LOW,
        )
        with patch.object(provider._client, "screen_address", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.screen_transaction(
                TransactionScreeningRequest(
                    tx_hash="0xtx123",
                    chain="base",
                    from_address="0xsender",
                    to_address="0xrecipient",
                    amount=Decimal("100"),
                )
            )
            assert result.risk_level == SanctionsRisk.LOW
            assert result.is_sanctioned is False
            assert result.entity_type == EntityType.TRANSACTION

    @pytest.mark.asyncio
    async def test_screen_transaction_one_bad(self, provider):
        clean_resp = CircleScreeningResponse(
            screening_id="scr_clean",
            address="0xsender",
            chain="base",
            action=CircleScreeningAction.APPROVE,
            risk_level=CircleRiskLevel.LOW,
        )
        bad_resp = CircleScreeningResponse(
            screening_id="scr_bad",
            address="0xbad_recipient",
            chain="base",
            action=CircleScreeningAction.DENY,
            risk_level=CircleRiskLevel.SEVERE,
        )

        call_count = 0

        async def mock_screen(address, chain):
            nonlocal call_count
            call_count += 1
            return clean_resp if call_count == 1 else bad_resp

        with patch.object(provider._client, "screen_address", side_effect=mock_screen):
            result = await provider.screen_transaction(
                TransactionScreeningRequest(
                    tx_hash="0xtx_bad",
                    chain="base",
                    from_address="0xsender",
                    to_address="0xbad_recipient",
                    amount=Decimal("50"),
                )
            )
            assert result.should_block is True
            assert result.entity_type == EntityType.TRANSACTION


# ── Factory Function ─────────────────────────────────────────────────


class TestCreateSanctionsService:
    def test_circle_provider_with_key(self):
        service = create_sanctions_service(
            provider_name="circle",
            circle_api_key="test-circle-key",
        )
        assert isinstance(service, SanctionsService)

    def test_circle_provider_with_elliptic_failover(self):
        service = create_sanctions_service(
            api_key="elliptic-key",
            api_secret="elliptic-secret",
            provider_name="circle",
            circle_api_key="test-circle-key",
        )
        assert isinstance(service, SanctionsService)
        assert isinstance(service._provider, FailoverSanctionsProvider)

    @patch.dict("os.environ", {"SARDIS_ENVIRONMENT": "dev"})
    def test_circle_no_key_falls_back_to_mock(self):
        service = create_sanctions_service(provider_name="circle")
        assert isinstance(service, SanctionsService)
        assert isinstance(service._provider, MockSanctionsProvider)

    def test_mock_provider_default(self):
        service = create_sanctions_service(provider_name="mock")
        assert isinstance(service, SanctionsService)
        assert isinstance(service._provider, MockSanctionsProvider)

    def test_elliptic_with_circle_failover(self):
        service = create_sanctions_service(
            api_key="elliptic-key",
            api_secret="elliptic-secret",
            provider_name="elliptic",
            circle_api_key="circle-key",
        )
        assert isinstance(service._provider, FailoverSanctionsProvider)


# ── Factory Helper ───────────────────────────────────────────────────


class TestCreateCircleComplianceProvider:
    def test_with_explicit_key(self):
        provider = create_circle_compliance_provider(api_key="test-key")
        assert isinstance(provider, CircleComplianceProvider)

    @patch.dict("os.environ", {"CIRCLE_API_KEY": "env-key"})
    def test_with_env_key(self):
        provider = create_circle_compliance_provider()
        assert isinstance(provider, CircleComplianceProvider)

    def test_no_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Circle API key required"):
                create_circle_compliance_provider()


# ── Integration: Circle → ComplianceEngine Pipeline ──────────────────


class TestCircleCompliancePipeline:
    @pytest.mark.asyncio
    async def test_clean_address_passes_sanctions(self):
        """Clean address should pass through sanctions check."""
        provider = CircleComplianceProvider(api_key="test-key")
        mock_resp = CircleScreeningResponse(
            screening_id="scr_pipeline",
            address="0xagent123",
            chain="base",
            action=CircleScreeningAction.APPROVE,
            risk_level=CircleRiskLevel.LOW,
        )

        with patch.object(provider._client, "screen_address", new_callable=AsyncMock, return_value=mock_resp):
            service = SanctionsService(provider=provider)
            result = await service.screen_address("0xagent123", "base")
            assert result.should_block is False
            assert result.provider == "circle_compliance"

    @pytest.mark.asyncio
    async def test_sanctioned_address_blocked(self):
        """Sanctioned address should be blocked."""
        provider = CircleComplianceProvider(api_key="test-key")
        mock_resp = CircleScreeningResponse(
            screening_id="scr_blocked",
            address="0xofac9999",
            chain="base",
            action=CircleScreeningAction.DENY,
            risk_level=CircleRiskLevel.SEVERE,
        )

        with patch.object(provider._client, "screen_address", new_callable=AsyncMock, return_value=mock_resp):
            service = SanctionsService(provider=provider)
            blocked = await service.is_blocked("0xofac9999", "base")
            assert blocked is True

    @pytest.mark.asyncio
    async def test_review_address_not_blocked_but_high_risk(self):
        """REVIEW action → not blocked but flagged as HIGH risk."""
        provider = CircleComplianceProvider(api_key="test-key")
        mock_resp = CircleScreeningResponse(
            screening_id="scr_review",
            address="0xreview5555",
            chain="base",
            action=CircleScreeningAction.REVIEW,
            risk_level=CircleRiskLevel.HIGH,
        )

        with patch.object(provider._client, "screen_address", new_callable=AsyncMock, return_value=mock_resp):
            service = SanctionsService(provider=provider)
            result = await service.screen_address("0xreview5555", "base")
            assert result.risk_level == SanctionsRisk.HIGH
            assert result.should_block is False
            assert result.is_sanctioned is False
