"""Tests for FingerprintJS device intelligence provider.

Covers issue #133. All API calls are mocked.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from sardis_guardrails.fingerprint import (
    API_REGIONS,
    BotResult,
    DeviceIntelligence,
    DeviceRisk,
    FingerprintError,
    FingerprintProvider,
    TamperingResult,
    VPNResult,
    get_fingerprint_provider,
)


# ============ Mock API Responses ============

CLEAN_EVENT = {
    "products": {
        "identification": {
            "data": {
                "requestId": "req_clean",
                "visitorId": "visitor_abc",
                "visitorFound": True,
                "confidence": {"score": 0.995},
                "incognito": False,
                "ip": "1.2.3.4",
                "ipLocation": {
                    "country": {"code": "US", "name": "United States"},
                    "city": {"name": "San Francisco"},
                    "timezone": "America/Los_Angeles",
                },
                "firstSeenAt": {"global": "2025-01-01T00:00:00Z"},
                "lastSeenAt": {"global": "2026-03-11T00:00:00Z"},
            }
        },
        "botd": {
            "data": {"bot": {"result": "notDetected", "type": ""}}
        },
        "vpn": {
            "data": {
                "result": False,
                "methods": {
                    "publicVPN": False,
                    "relay": False,
                    "timezoneMismatch": False,
                },
            }
        },
        "tampering": {
            "data": {
                "result": False,
                "anomalyScore": 0.0,
                "antiDetectBrowser": False,
            }
        },
        "ipBlocklist": {"data": {"result": False}},
        "virtualMachine": {"data": {"result": False}},
        "suspectScore": {"data": {"result": 5}},
        "velocity": {"data": {}},
    }
}

BAD_BOT_EVENT = {
    "products": {
        "identification": {
            "data": {
                "requestId": "req_bot",
                "visitorId": "",
                "visitorFound": False,
                "confidence": {"score": 0.0},
                "incognito": False,
                "ip": "5.6.7.8",
                "ipLocation": {},
            }
        },
        "botd": {
            "data": {"bot": {"result": "bad", "type": "headlessChrome"}}
        },
        "vpn": {"data": {"result": False, "methods": {}}},
        "tampering": {"data": {"result": False}},
        "ipBlocklist": {"data": {"result": False}},
        "virtualMachine": {"data": {"result": False}},
        "suspectScore": {"data": {"result": 90}},
    }
}

SUSPICIOUS_EVENT = {
    "products": {
        "identification": {
            "data": {
                "requestId": "req_sus",
                "visitorId": "visitor_sus",
                "visitorFound": True,
                "confidence": {"score": 0.85},
                "incognito": True,
                "ip": "10.20.30.40",
                "ipLocation": {
                    "country": {"code": "RU"},
                    "city": {"name": "Moscow"},
                    "timezone": "Europe/Moscow",
                },
            }
        },
        "botd": {
            "data": {"bot": {"result": "notDetected"}}
        },
        "vpn": {
            "data": {
                "result": True,
                "methods": {
                    "publicVPN": True,
                    "relay": False,
                    "timezoneMismatch": True,
                },
            }
        },
        "tampering": {
            "data": {
                "result": True,
                "anomalyScore": 0.8,
                "antiDetectBrowser": True,
            }
        },
        "ipBlocklist": {"data": {"result": True}},
        "virtualMachine": {"data": {"result": True}},
        "suspectScore": {"data": {"result": 75}},
    }
}


def _mock_get_response(json_data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=json_data,
        request=httpx.Request("GET", "https://api.fpjs.io/events/test"),
    )


# ============ Provider Initialization Tests ============

class TestProviderInit:
    def test_defaults(self):
        provider = FingerprintProvider(api_key="test-key")
        assert provider._base_url == API_REGIONS["us"]
        assert provider.is_configured is True

    def test_eu_region(self):
        provider = FingerprintProvider(api_key="key", region="eu")
        assert provider._base_url == API_REGIONS["eu"]

    def test_ap_region(self):
        provider = FingerprintProvider(api_key="key", region="ap")
        assert provider._base_url == API_REGIONS["ap"]

    def test_not_configured(self):
        provider = FingerprintProvider(api_key="")
        assert provider.is_configured is False

    def test_env_var_config(self):
        with patch.dict("os.environ", {
            "FINGERPRINT_API_KEY": "env-key",
            "FINGERPRINT_REGION": "eu",
        }):
            provider = FingerprintProvider()
            assert provider.is_configured is True
            assert provider._base_url == API_REGIONS["eu"]

    def test_headers(self):
        provider = FingerprintProvider(api_key="my-secret-key")
        headers = provider._headers()
        assert headers["Auth-API-Key"] == "my-secret-key"


# ============ Device Intelligence Parsing Tests ============

class TestCleanEvent:
    @pytest.mark.asyncio
    async def test_clean_device(self):
        provider = FingerprintProvider(api_key="test")
        mock_resp = _mock_get_response(CLEAN_EVENT)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.get_device_intelligence("req_clean")

        assert isinstance(result, DeviceIntelligence)
        assert result.visitor_id == "visitor_abc"
        assert result.visitor_found is True
        assert result.confidence_score == 0.995
        assert result.bot_result == BotResult.NOT_DETECTED
        assert result.is_bot is False
        assert result.vpn.detected is False
        assert result.tampering.detected is False
        assert result.ip_blocklisted is False
        assert result.incognito is False
        assert result.suspect_score == 5
        assert result.country == "US"
        assert result.city == "San Francisco"
        assert result.ip_address == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_clean_risk_level(self):
        provider = FingerprintProvider(api_key="test")
        mock_resp = _mock_get_response(CLEAN_EVENT)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.get_device_intelligence("req_clean")

        assert result.risk_level == DeviceRisk.CLEAN
        assert result.is_suspicious is False
        assert result.risk_score < 0.1


class TestBadBotEvent:
    @pytest.mark.asyncio
    async def test_bot_detection(self):
        provider = FingerprintProvider(api_key="test")
        mock_resp = _mock_get_response(BAD_BOT_EVENT)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.get_device_intelligence("req_bot")

        assert result.bot_result == BotResult.BAD
        assert result.bot_type == "headlessChrome"
        assert result.is_bot is True
        assert result.is_suspicious is True
        assert result.risk_level == DeviceRisk.CRITICAL
        assert result.risk_score >= 0.4


class TestSuspiciousEvent:
    @pytest.mark.asyncio
    async def test_suspicious_signals(self):
        provider = FingerprintProvider(api_key="test")
        mock_resp = _mock_get_response(SUSPICIOUS_EVENT)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.get_device_intelligence("req_sus")

        assert result.vpn.detected is True
        assert result.vpn.public_vpn is True
        assert result.vpn.timezone_mismatch is True
        assert result.tampering.detected is True
        assert result.tampering.anti_detect_browser is True
        assert result.tampering.anomaly_score == 0.8
        assert result.ip_blocklisted is True
        assert result.virtual_machine is True
        assert result.incognito is True
        assert result.suspect_score == 75

    @pytest.mark.asyncio
    async def test_suspicious_risk(self):
        provider = FingerprintProvider(api_key="test")
        mock_resp = _mock_get_response(SUSPICIOUS_EVENT)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.get_device_intelligence("req_sus")

        assert result.is_suspicious is True
        assert result.risk_level == DeviceRisk.HIGH
        assert result.risk_score >= 0.5


# ============ Error Handling Tests ============

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_no_api_key_raises(self):
        provider = FingerprintProvider(api_key="")
        with pytest.raises(FingerprintError, match="not configured"):
            await provider.get_device_intelligence("req_123")

    @pytest.mark.asyncio
    async def test_api_error_raises(self):
        provider = FingerprintProvider(api_key="test")
        error_resp = httpx.Response(
            status_code=403,
            json={"error": "Forbidden"},
            request=httpx.Request("GET", "https://api.fpjs.io/events/req_123"),
        )

        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "Forbidden", request=error_resp.request, response=error_resp
            ),
        ):
            with pytest.raises(FingerprintError, match="403"):
                await provider.get_device_intelligence("req_123")

    @pytest.mark.asyncio
    async def test_connection_error_raises(self):
        provider = FingerprintProvider(api_key="test")

        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("timeout"),
        ):
            with pytest.raises(FingerprintError, match="failed"):
                await provider.get_device_intelligence("req_123")


# ============ Visitor History Tests ============

class TestVisitorHistory:
    @pytest.mark.asyncio
    async def test_get_history(self):
        provider = FingerprintProvider(api_key="test")
        history_resp = {
            "visitorId": "visitor_abc",
            "visits": [
                {"requestId": "req_1", "timestamp": 1700000000},
                {"requestId": "req_2", "timestamp": 1700000100},
            ],
        }
        mock_resp = _mock_get_response(history_resp)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            visits = await provider.get_visitor_history("visitor_abc", limit=2)

        assert len(visits) == 2

    @pytest.mark.asyncio
    async def test_no_api_key_raises(self):
        provider = FingerprintProvider(api_key="")
        with pytest.raises(FingerprintError):
            await provider.get_visitor_history("visitor_abc")


# ============ Health Check Tests ============

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self):
        provider = FingerprintProvider(api_key="test")
        mock_resp = httpx.Response(
            404, json={},
            request=httpx.Request("GET", "https://api.fpjs.io/events/health_check_probe"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_unreachable(self):
        provider = FingerprintProvider(api_key="test")
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("refused"),
        ):
            assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_no_key(self):
        provider = FingerprintProvider(api_key="")
        assert await provider.health_check() is False


# ============ DeviceIntelligence Property Tests ============

class TestDeviceIntelligenceProperties:
    def test_is_bot(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v", bot_result=BotResult.BAD
        )
        assert di.is_bot is True

    def test_is_not_bot(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v", bot_result=BotResult.GOOD
        )
        assert di.is_bot is False

    def test_risk_level_critical(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v", bot_result=BotResult.BAD
        )
        assert di.risk_level == DeviceRisk.CRITICAL

    def test_risk_level_high(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v", ip_blocklisted=True
        )
        assert di.risk_level == DeviceRisk.HIGH

    def test_risk_level_medium_vpn(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v",
            vpn=VPNResult(detected=True),
        )
        assert di.risk_level == DeviceRisk.MEDIUM

    def test_risk_level_low_incognito(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v", incognito=True
        )
        assert di.risk_level == DeviceRisk.LOW

    def test_risk_level_clean(self):
        di = DeviceIntelligence(request_id="r", visitor_id="v")
        assert di.risk_level == DeviceRisk.CLEAN

    def test_risk_score_composes(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v",
            bot_result=BotResult.BAD,
            vpn=VPNResult(detected=True),
            tampering=TamperingResult(detected=True),
            ip_blocklisted=True,
        )
        assert di.risk_score >= 0.7
        assert di.risk_score <= 1.0

    def test_suspect_score_high(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v", suspect_score=85
        )
        assert di.risk_level == DeviceRisk.CRITICAL

    def test_is_suspicious_suspect_score(self):
        di = DeviceIntelligence(
            request_id="r", visitor_id="v", suspect_score=60
        )
        assert di.is_suspicious is True


# ============ Singleton Tests ============

class TestSingleton:
    def test_get_fingerprint_provider(self):
        import sardis_guardrails.fingerprint as fp_mod
        fp_mod._provider = None  # Reset

        p1 = get_fingerprint_provider()
        p2 = get_fingerprint_provider()
        assert p1 is p2

        fp_mod._provider = None  # Cleanup


# ============ Module Export Tests ============

class TestModuleExports:
    def test_from_guardrails(self):
        from sardis_guardrails import (
            BotResult,
            DeviceIntelligence,
            DeviceRisk,
            FingerprintError,
            FingerprintProvider,
            get_fingerprint_provider,
        )
        assert all([
            BotResult, DeviceIntelligence, DeviceRisk,
            FingerprintError, FingerprintProvider, get_fingerprint_provider,
        ])
