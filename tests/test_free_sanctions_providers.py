"""Tests for free sanctions screening providers (OFAC, Chainalysis Oracle, Watchman).

Covers issues #125, #126, #127.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_compliance.sanctions import (
    EntityType,
    FailoverSanctionsProvider,
    SanctionsList,
    SanctionsRisk,
    ScreeningResult,
    TransactionScreeningRequest,
    WalletScreeningRequest,
    create_sanctions_service,
)

# ---------------------------------------------------------------------------
# OFACAddressProvider
# ---------------------------------------------------------------------------


class TestOFACAddressProvider:
    """Tests for the OFAC SDN address list provider."""

    def _make_provider(self):
        from sardis_compliance.providers.ofac import OFACAddressProvider
        provider = OFACAddressProvider()
        # Pre-load known addresses for testing (bypass HTTP)
        provider._sanctioned_addresses = {
            "0xbad0000000000000000000000000000000000001",
            "0xbad0000000000000000000000000000000000002",
        }
        provider._loaded = True
        provider._last_refresh = datetime.now(UTC)
        return provider

    @pytest.mark.asyncio
    async def test_sanctioned_address_blocked(self):
        provider = self._make_provider()
        result = await provider.screen_wallet(
            WalletScreeningRequest(
                address="0xBAD0000000000000000000000000000000000001",
                chain="base",
            )
        )
        assert result.is_sanctioned is True
        assert result.risk_level == SanctionsRisk.BLOCKED
        assert result.provider == "ofac_sdn"

    @pytest.mark.asyncio
    async def test_clean_address_passes(self):
        provider = self._make_provider()
        result = await provider.screen_wallet(
            WalletScreeningRequest(
                address="0xClean000000000000000000000000000000000001",
                chain="base",
            )
        )
        assert result.is_sanctioned is False
        assert result.risk_level == SanctionsRisk.LOW

    @pytest.mark.asyncio
    async def test_custom_blocklist(self):
        provider = self._make_provider()
        await provider.add_to_blocklist("0xCustomBlocked", "test reason")
        result = await provider.screen_wallet(
            WalletScreeningRequest(address="0xCustomBlocked", chain="ethereum")
        )
        assert result.is_sanctioned is True
        assert result.risk_level == SanctionsRisk.BLOCKED

        # Remove from blocklist
        await provider.remove_from_blocklist("0xCustomBlocked")
        result2 = await provider.screen_wallet(
            WalletScreeningRequest(address="0xCustomBlocked", chain="ethereum")
        )
        assert result2.is_sanctioned is False

    @pytest.mark.asyncio
    async def test_fail_closed_when_lists_not_loaded(self):
        from sardis_compliance.providers.ofac import OFACAddressProvider
        provider = OFACAddressProvider()
        provider._loaded = False

        # Mock httpx at the point of import inside the method
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xAnything", chain="base")
            )
            assert result.risk_level == SanctionsRisk.BLOCKED
            assert result.is_sanctioned is False  # Unknown, but fail-closed

    @pytest.mark.asyncio
    async def test_transaction_screening(self):
        provider = self._make_provider()
        result = await provider.screen_transaction(
            TransactionScreeningRequest(
                tx_hash="0xtxhash123",
                chain="base",
                from_address="0xBAD0000000000000000000000000000000000001",
                to_address="0xClean000000000000000000000000000000000099",
                amount=Decimal("100"),
                token="USDC",
            )
        )
        assert result.should_block is True
        assert result.entity_type == EntityType.TRANSACTION

    @pytest.mark.asyncio
    async def test_address_count_property(self):
        provider = self._make_provider()
        assert provider.address_count == 2

    @pytest.mark.asyncio
    async def test_force_refresh(self):
        from sardis_compliance.providers.ofac import OFACAddressProvider
        provider = OFACAddressProvider()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [
            "0xNewAddr0000000000000000000000000000000001",
            "0xNewAddr0000000000000000000000000000000002",
            "0xNewAddr0000000000000000000000000000000003",
        ]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            count = await provider.force_refresh()
            # 5 lists × 3 addresses each, but identical so deduplicated to 3
            assert count == 3


# ---------------------------------------------------------------------------
# ChainalysisOracleProvider
# ---------------------------------------------------------------------------


class TestChainalysisOracleProvider:
    """Tests for the Chainalysis on-chain sanctions oracle provider."""

    def _make_provider(self, rpc_urls=None):
        from sardis_compliance.providers.chainalysis import ChainalysisOracleProvider
        return ChainalysisOracleProvider(
            rpc_urls=rpc_urls or {"base": "https://rpc.example.com"},
        )

    @pytest.mark.asyncio
    async def test_sanctioned_address(self):
        provider = self._make_provider()

        with patch.object(provider, "_check_oracle", return_value=True):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xSanctioned123", chain="base")
            )
            assert result.is_sanctioned is True
            assert result.risk_level == SanctionsRisk.BLOCKED
            assert result.provider == "chainalysis_oracle"
            assert SanctionsList.OFAC in result.lists_checked

    @pytest.mark.asyncio
    async def test_clean_address(self):
        provider = self._make_provider()

        with patch.object(provider, "_check_oracle", return_value=False):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xClean456", chain="base")
            )
            assert result.is_sanctioned is False
            assert result.risk_level == SanctionsRisk.LOW

    @pytest.mark.asyncio
    async def test_oracle_unavailable_fail_closed(self):
        provider = self._make_provider()

        with patch.object(provider, "_check_oracle", return_value=None):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xUnknown789", chain="base")
            )
            assert result.risk_level == SanctionsRisk.BLOCKED
            assert result.is_sanctioned is False
            assert "fail-closed" in result.reason

    @pytest.mark.asyncio
    async def test_custom_blocklist(self):
        provider = self._make_provider()
        await provider.add_to_blocklist("0xBlockMe", "suspicious activity")

        result = await provider.screen_wallet(
            WalletScreeningRequest(address="0xBlockMe", chain="base")
        )
        assert result.is_sanctioned is True
        assert result.risk_level == SanctionsRisk.BLOCKED

    @pytest.mark.asyncio
    async def test_transaction_screening(self):
        provider = self._make_provider()

        async def mock_oracle(address, chain):
            return address == "0xFrom"

        with patch.object(provider, "_check_oracle", side_effect=mock_oracle):
            result = await provider.screen_transaction(
                TransactionScreeningRequest(
                    tx_hash="0xtx",
                    chain="base",
                    from_address="0xFrom",
                    to_address="0xTo",
                    amount=Decimal("50"),
                )
            )
            assert result.should_block is True

    @pytest.mark.asyncio
    async def test_unsupported_chain_returns_none(self):
        provider = self._make_provider()
        result = await provider._check_oracle("0xAddr", "solana")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_rpc_url_returns_none(self):
        from sardis_compliance.providers.chainalysis import ChainalysisOracleProvider
        provider = ChainalysisOracleProvider(rpc_urls={})
        result = await provider._check_oracle("0xAddr", "base")
        assert result is None


# ---------------------------------------------------------------------------
# WatchmanProvider
# ---------------------------------------------------------------------------


class TestWatchmanProvider:
    """Tests for the Moov Watchman sanctions screening provider."""

    def _make_provider(self, base_url="http://localhost:8084"):
        from sardis_compliance.providers.watchman import WatchmanProvider
        return WatchmanProvider(base_url=base_url, min_match_score=0.85)

    @pytest.mark.asyncio
    async def test_no_matches_returns_low_risk(self):
        provider = self._make_provider()

        with patch.object(provider, "_search", return_value=[]):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xCleanAddr", chain="ethereum")
            )
            assert result.is_sanctioned is False
            assert result.risk_level == SanctionsRisk.LOW
            assert result.provider == "watchman"

    @pytest.mark.asyncio
    async def test_high_score_match_blocked(self):
        from sardis_compliance.providers.watchman import WatchmanEntityMatch
        provider = self._make_provider()

        match = WatchmanEntityMatch(
            name="Sanctioned Entity",
            entity_type="person",
            source_list="OFAC",
            source_id="SDN-12345",
            match_score=0.97,
        )
        with patch.object(provider, "_search", return_value=[match]):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xSuspicious", chain="ethereum")
            )
            assert result.is_sanctioned is True
            assert result.risk_level == SanctionsRisk.BLOCKED

    @pytest.mark.asyncio
    async def test_medium_score_not_blocked(self):
        from sardis_compliance.providers.watchman import WatchmanEntityMatch
        provider = self._make_provider()

        match = WatchmanEntityMatch(
            name="Similar Name",
            entity_type="person",
            source_list="EU",
            source_id="EU-789",
            match_score=0.86,
        )
        with patch.object(provider, "_search", return_value=[match]):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xMaybe", chain="ethereum")
            )
            assert result.is_sanctioned is False
            assert result.risk_level == SanctionsRisk.HIGH

    @pytest.mark.asyncio
    async def test_entity_screening(self):
        from sardis_compliance.providers.watchman import WatchmanEntityMatch
        provider = self._make_provider()

        match = WatchmanEntityMatch(
            name="Test Org",
            entity_type="organization",
            source_list="OFAC",
            source_id="SDN-99999",
            match_score=0.96,
        )
        with patch.object(provider, "_search", return_value=[match]):
            result = await provider.screen_entity("Test Organization", entity_type="organization")
            assert result.is_sanctioned is True
            assert result.entity_type == EntityType.ORGANIZATION

    @pytest.mark.asyncio
    async def test_custom_blocklist(self):
        provider = self._make_provider()
        await provider.add_to_blocklist("0xBlocked123", "known bad actor")

        result = await provider.screen_wallet(
            WalletScreeningRequest(address="0xBlocked123", chain="ethereum")
        )
        assert result.is_sanctioned is True
        assert result.risk_level == SanctionsRisk.BLOCKED

    @pytest.mark.asyncio
    async def test_remove_from_blocklist(self):
        provider = self._make_provider()
        await provider.add_to_blocklist("0xTemp", "temporary block")
        await provider.remove_from_blocklist("0xTemp")

        with patch.object(provider, "_search", return_value=[]):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xTemp", chain="ethereum")
            )
            assert result.is_sanctioned is False

    @pytest.mark.asyncio
    async def test_transaction_screening(self):
        from sardis_compliance.providers.watchman import WatchmanEntityMatch
        provider = self._make_provider()

        match = WatchmanEntityMatch(
            name="Bad Actor",
            entity_type="person",
            source_list="OFAC",
            source_id="SDN-1",
            match_score=0.99,
        )

        call_count = 0

        async def mock_search(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [match]  # from_address flagged
            return []  # to_address clean

        with patch.object(provider, "_search", side_effect=mock_search):
            result = await provider.screen_transaction(
                TransactionScreeningRequest(
                    tx_hash="0xtx999",
                    chain="ethereum",
                    from_address="0xBadSender",
                    to_address="0xGoodReceiver",
                    amount=Decimal("200"),
                )
            )
            assert result.should_block is True
            assert result.entity_type == EntityType.TRANSACTION

    @pytest.mark.asyncio
    async def test_risk_level_mapping(self):
        from sardis_compliance.providers.watchman import WatchmanEntityMatch
        provider = self._make_provider()

        cases = [
            (0.95, SanctionsRisk.BLOCKED),
            (0.97, SanctionsRisk.BLOCKED),
            (0.90, SanctionsRisk.SEVERE),
            (0.93, SanctionsRisk.SEVERE),
            (0.85, SanctionsRisk.HIGH),
            (0.88, SanctionsRisk.HIGH),
        ]
        for score, expected_risk in cases:
            match = WatchmanEntityMatch(
                name="Test",
                entity_type="person",
                source_list="OFAC",
                source_id="X",
                match_score=score,
            )
            risk = provider._matches_to_risk([match])
            assert risk == expected_risk, f"Score {score} should map to {expected_risk}, got {risk}"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = self._make_provider()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = self._make_provider()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_search_connect_error_returns_empty(self):
        provider = self._make_provider()
        import httpx as httpx_mod

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx_mod.ConnectError("refused"))

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            matches = await provider._search(name="Test Person")
            assert matches == []


# ---------------------------------------------------------------------------
# create_sanctions_service factory
# ---------------------------------------------------------------------------


class TestCreateSanctionsServiceFactory:
    """Tests for the factory function with new provider options."""

    def test_ofac_provider(self):
        service = create_sanctions_service(provider_name="ofac")
        from sardis_compliance.providers.ofac import OFACAddressProvider
        assert isinstance(service._provider, OFACAddressProvider)

    def test_chainalysis_provider(self):
        service = create_sanctions_service(provider_name="chainalysis")
        from sardis_compliance.providers.chainalysis import ChainalysisOracleProvider
        assert isinstance(service._provider, ChainalysisOracleProvider)

    def test_watchman_provider(self):
        service = create_sanctions_service(provider_name="watchman")
        from sardis_compliance.providers.watchman import WatchmanProvider
        assert isinstance(service._provider, WatchmanProvider)

    def test_layered_provider(self):
        service = create_sanctions_service(provider_name="layered")
        assert isinstance(service._provider, FailoverSanctionsProvider)
        assert isinstance(service._provider._fallback, FailoverSanctionsProvider)

    def test_env_var_provider(self):
        with patch.dict("os.environ", {"SARDIS_COMPLIANCE_SCREENING_PROVIDER": "ofac"}):
            service = create_sanctions_service()
            from sardis_compliance.providers.ofac import OFACAddressProvider
            assert isinstance(service._provider, OFACAddressProvider)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    """Verify new providers are accessible from top-level module."""

    def test_ofac_provider_exported(self):
        from sardis_compliance import OFACAddressProvider
        assert OFACAddressProvider is not None

    def test_chainalysis_provider_exported(self):
        from sardis_compliance import ChainalysisOracleProvider
        assert ChainalysisOracleProvider is not None

    def test_watchman_provider_exported(self):
        from sardis_compliance import WatchmanProvider
        assert WatchmanProvider is not None
