"""Tests for OpenSanctions screening provider.

Covers issue #136. All API calls are mocked.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from sardis_compliance.providers.opensanctions import (
    DEFAULT_API_URL,
    DEFAULT_MATCH_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    OpenSanctionsProvider,
    _risk_severity,
    _score_to_risk,
)
from sardis_compliance.sanctions import (
    EntityType,
    SanctionsRisk,
    TransactionScreeningRequest,
    WalletScreeningRequest,
    create_sanctions_service,
)

# Test addresses
CLEAN_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"
SANCTIONED_ADDRESS = "0xd882cfc20f52f2599d84b8e8d58c7fb62cfe344b"  # Known Lazarus Group

# Mock API responses
CLEAN_MATCH_RESPONSE = {
    "responses": {
        "wallet": {
            "query": {},
            "results": [],
            "total": {"value": 0},
        }
    }
}

SANCTIONED_MATCH_RESPONSE = {
    "responses": {
        "wallet": {
            "query": {},
            "results": [
                {
                    "id": "NK-os-lazarus-wallet-1",
                    "schema": "CryptoWallet",
                    "caption": "Lazarus Group Wallet",
                    "score": 0.95,
                    "datasets": ["us_ofac_sdn"],
                    "properties": {
                        "publicKey": [SANCTIONED_ADDRESS],
                        "currency": ["ETH"],
                        "holder": ["NK-Lazarus-Group"],
                        "name": ["Lazarus Group Wallet"],
                    },
                }
            ],
            "total": {"value": 1},
        }
    }
}

LOW_CONFIDENCE_MATCH_RESPONSE = {
    "responses": {
        "wallet": {
            "query": {},
            "results": [
                {
                    "id": "NK-os-partial-1",
                    "schema": "CryptoWallet",
                    "caption": "Partial Match Wallet",
                    "score": 0.72,
                    "datasets": ["eu_fsf"],
                    "properties": {
                        "publicKey": ["0xsimilar123"],
                        "currency": ["ETH"],
                    },
                }
            ],
            "total": {"value": 1},
        }
    }
}

ENTITY_MATCH_RESPONSE = {
    "responses": {
        "entity": {
            "query": {},
            "results": [
                {
                    "id": "NK-os-entity-1",
                    "schema": "Person",
                    "caption": "Kim Jong Un",
                    "score": 0.88,
                    "datasets": ["un_sc_sanctions"],
                    "properties": {
                        "name": ["Kim Jong Un"],
                        "nationality": ["kp"],
                    },
                }
            ],
            "total": {"value": 1},
        }
    }
}


def _mock_post_response(json_data: dict, status: int = 200) -> httpx.Response:
    """Create a mock httpx Response."""
    return httpx.Response(
        status_code=status,
        json=json_data,
        request=httpx.Request("POST", "https://api.opensanctions.org/match/default"),
    )


def _mock_get_response(json_data: dict, status: int = 200) -> httpx.Response:
    """Create a mock httpx GET Response."""
    return httpx.Response(
        status_code=status,
        json=json_data,
        request=httpx.Request("GET", "https://api.opensanctions.org/search/default"),
    )


# ============ Score Mapping Tests ============

class TestScoreToRisk:
    def test_high_score_blocked(self):
        assert _score_to_risk(0.95) == SanctionsRisk.BLOCKED

    def test_threshold_score_severe(self):
        assert _score_to_risk(0.7) == SanctionsRisk.SEVERE

    def test_medium_score(self):
        assert _score_to_risk(0.5) == SanctionsRisk.HIGH

    def test_low_score_medium(self):
        assert _score_to_risk(0.3) == SanctionsRisk.MEDIUM

    def test_very_low_score(self):
        assert _score_to_risk(0.1) == SanctionsRisk.LOW


class TestRiskSeverity:
    def test_ordering(self):
        assert _risk_severity(SanctionsRisk.LOW) < _risk_severity(SanctionsRisk.MEDIUM)
        assert _risk_severity(SanctionsRisk.MEDIUM) < _risk_severity(SanctionsRisk.HIGH)
        assert _risk_severity(SanctionsRisk.HIGH) < _risk_severity(SanctionsRisk.SEVERE)
        assert _risk_severity(SanctionsRisk.SEVERE) < _risk_severity(SanctionsRisk.BLOCKED)


# ============ Provider Initialization Tests ============

class TestProviderInit:
    def test_defaults(self):
        provider = OpenSanctionsProvider()
        assert provider._api_url == DEFAULT_API_URL
        assert provider._dataset == "default"
        assert provider._threshold == DEFAULT_MATCH_THRESHOLD

    def test_custom_config(self):
        provider = OpenSanctionsProvider(
            api_url="http://localhost:8000",
            api_key="test-key",
            dataset="sanctions",
            match_threshold=0.8,
        )
        assert provider._api_url == "http://localhost:8000"
        assert provider._api_key == "test-key"
        assert provider._dataset == "sanctions"
        assert provider._threshold == 0.8

    def test_strips_trailing_slash(self):
        provider = OpenSanctionsProvider(api_url="http://localhost:8000/")
        assert provider._api_url == "http://localhost:8000"

    def test_env_var_config(self):
        with patch.dict("os.environ", {
            "OPENSANCTIONS_API_URL": "http://yente:8000",
            "OPENSANCTIONS_API_KEY": "env-key",
            "OPENSANCTIONS_DATASET": "sanctions",
            "OPENSANCTIONS_THRESHOLD": "0.85",
        }):
            provider = OpenSanctionsProvider()
            assert provider._api_url == "http://yente:8000"
            assert provider._api_key == "env-key"
            assert provider._dataset == "sanctions"
            assert provider._threshold == 0.85

    def test_headers_with_api_key(self):
        provider = OpenSanctionsProvider(api_key="my-key")
        headers = provider._headers()
        assert headers["Authorization"] == "ApiKey my-key"

    def test_headers_without_api_key(self):
        provider = OpenSanctionsProvider(api_key="")
        headers = provider._headers()
        assert "Authorization" not in headers


# ============ Wallet Screening Tests ============

class TestWalletScreening:
    @pytest.mark.asyncio
    async def test_clean_address(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        mock_resp = _mock_post_response(CLEAN_MATCH_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address=CLEAN_ADDRESS)
            )

        assert result.is_sanctioned is False
        assert result.risk_level == SanctionsRisk.LOW
        assert result.provider == "opensanctions"
        assert len(result.matches) == 0

    @pytest.mark.asyncio
    async def test_sanctioned_address(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        mock_resp = _mock_post_response(SANCTIONED_MATCH_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address=SANCTIONED_ADDRESS)
            )

        assert result.is_sanctioned is True
        assert result.risk_level == SanctionsRisk.BLOCKED
        assert result.should_block is True
        assert len(result.matches) == 1
        assert result.matches[0]["caption"] == "Lazarus Group Wallet"
        assert "us_ofac_sdn" in result.matches[0]["datasets"]
        assert "Lazarus Group Wallet" in result.reason

    @pytest.mark.asyncio
    async def test_low_confidence_match(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        mock_resp = _mock_post_response(LOW_CONFIDENCE_MATCH_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address="0xsomething")
            )

        # Score 0.72 is above threshold but below HIGH_CONFIDENCE
        assert result.is_sanctioned is False  # Not high enough confidence
        assert result.risk_level == SanctionsRisk.SEVERE  # But still severe risk
        assert result.should_block is False  # Not auto-blocked, needs review

    @pytest.mark.asyncio
    async def test_api_error_fails_closed(self):
        provider = OpenSanctionsProvider(api_url="http://mock")

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address=CLEAN_ADDRESS)
            )

        # Fail-closed: API error → treat as blocked
        assert result.should_block is True
        assert result.risk_level == SanctionsRisk.BLOCKED
        assert "fail-closed" in result.reason

    @pytest.mark.asyncio
    async def test_http_error_fails_closed(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        error_resp = httpx.Response(
            status_code=500,
            json={"error": "Internal server error"},
            request=httpx.Request("POST", "http://mock/match/default"),
        )

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=error_resp.request, response=error_resp
            ),
        ):
            result = await provider.screen_wallet(
                WalletScreeningRequest(address=CLEAN_ADDRESS)
            )

        assert result.should_block is True
        assert "fail-closed" in result.reason


# ============ Custom Blocklist Tests ============

class TestBlocklist:
    @pytest.mark.asyncio
    async def test_add_and_check(self):
        provider = OpenSanctionsProvider(api_url="http://mock")

        # Add to blocklist
        added = await provider.add_to_blocklist(CLEAN_ADDRESS, "Suspicious activity")
        assert added is True

        # Should be blocked without API call
        result = await provider.screen_wallet(
            WalletScreeningRequest(address=CLEAN_ADDRESS)
        )
        assert result.should_block is True
        assert "Custom blocklist" in result.reason

    @pytest.mark.asyncio
    async def test_remove_from_blocklist(self):
        provider = OpenSanctionsProvider(api_url="http://mock")

        await provider.add_to_blocklist(CLEAN_ADDRESS, "Test")
        removed = await provider.remove_from_blocklist(CLEAN_ADDRESS)
        assert removed is True

        # Verify removal of non-existent returns False
        removed2 = await provider.remove_from_blocklist("0xnonexistent")
        assert removed2 is False

    @pytest.mark.asyncio
    async def test_blocklist_case_insensitive(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        await provider.add_to_blocklist("0xABCD", "Test")

        result = await provider.screen_wallet(
            WalletScreeningRequest(address="0xabcd")
        )
        assert result.should_block is True


# ============ Transaction Screening Tests ============

class TestTransactionScreening:
    @pytest.mark.asyncio
    async def test_clean_transaction(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        mock_resp = _mock_post_response(CLEAN_MATCH_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.screen_transaction(
                TransactionScreeningRequest(
                    tx_hash="0xtx123",
                    chain="base",
                    from_address=CLEAN_ADDRESS,
                    to_address="0xrecipient",
                    amount=Decimal("100"),
                )
            )

        assert result.is_sanctioned is False
        assert result.entity_type == EntityType.TRANSACTION

    @pytest.mark.asyncio
    async def test_sanctioned_recipient(self):
        provider = OpenSanctionsProvider(api_url="http://mock")

        # First call (from_address): clean; Second call (to_address): sanctioned
        mock_clean = _mock_post_response(CLEAN_MATCH_RESPONSE)
        mock_sanctioned = _mock_post_response(SANCTIONED_MATCH_RESPONSE)

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=[mock_clean, mock_sanctioned],
        ):
            result = await provider.screen_transaction(
                TransactionScreeningRequest(
                    tx_hash="0xtx456",
                    chain="ethereum",
                    from_address=CLEAN_ADDRESS,
                    to_address=SANCTIONED_ADDRESS,
                    amount=Decimal("500"),
                )
            )

        assert result.should_block is True
        assert result.entity_type == EntityType.TRANSACTION
        assert result.entity_id == "0xtx456"

    @pytest.mark.asyncio
    async def test_transaction_api_error_fails_closed(self):
        provider = OpenSanctionsProvider(api_url="http://mock")

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("timeout"),
        ):
            result = await provider.screen_transaction(
                TransactionScreeningRequest(
                    tx_hash="0xtx789",
                    chain="base",
                    from_address=CLEAN_ADDRESS,
                    to_address="0xrecipient",
                    amount=Decimal("50"),
                )
            )

        assert result.should_block is True
        assert "fail-closed" in result.reason


# ============ Entity Matching Tests ============

class TestEntityMatching:
    @pytest.mark.asyncio
    async def test_match_person(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        mock_resp = _mock_post_response(ENTITY_MATCH_RESPONSE)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            matches = await provider.match_entity(
                name="Kim Jong Un",
                schema="Person",
                nationality="kp",
            )

        assert len(matches) == 1
        assert matches[0]["caption"] == "Kim Jong Un"
        assert matches[0]["score"] == 0.88

    @pytest.mark.asyncio
    async def test_no_entity_matches(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        empty_response = {
            "responses": {"entity": {"query": {}, "results": [], "total": {"value": 0}}}
        }
        mock_resp = _mock_post_response(empty_response)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            matches = await provider.match_entity(name="John Smith", schema="Person")

        assert len(matches) == 0


# ============ Search Tests ============

class TestSearch:
    @pytest.mark.asyncio
    async def test_text_search(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        search_response = {
            "results": [
                {"id": "NK-1", "caption": "Test Entity", "score": 0.8}
            ]
        }
        mock_resp = _mock_get_response(search_response)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            results = await provider.search("test entity")

        assert len(results) == 1
        assert results[0]["caption"] == "Test Entity"


# ============ Health Check Tests ============

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self):
        provider = OpenSanctionsProvider(api_url="http://mock")
        mock_resp = httpx.Response(
            200,
            json={"status": "ok"},
            request=httpx.Request("GET", "http://mock/healthz"),
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_unhealthy(self):
        provider = OpenSanctionsProvider(api_url="http://mock")

        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("refused"),
        ):
            assert await provider.health_check() is False


# ============ Factory Integration Tests ============

class TestFactory:
    def test_opensanctions_provider_created(self):
        with patch.dict("os.environ", {
            "SARDIS_COMPLIANCE_SCREENING_PROVIDER": "opensanctions",
            "OPENSANCTIONS_API_URL": "http://localhost:8000",
        }):
            service = create_sanctions_service()
            assert service._provider is not None
            assert isinstance(service._provider, OpenSanctionsProvider)


# ============ Module Export Tests ============

class TestModuleExports:
    def test_provider_importable_from_providers(self):
        from sardis_compliance.providers import OpenSanctionsProvider
        assert OpenSanctionsProvider is not None

    def test_provider_importable_from_compliance(self):
        from sardis_compliance import OpenSanctionsProvider
        assert OpenSanctionsProvider is not None
