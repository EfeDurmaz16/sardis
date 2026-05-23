"""FingerprintJS device intelligence provider.

Integrates Fingerprint.com Server API for device fingerprinting, bot detection,
and Smart Signals (VPN, tampering, suspect score) in payment fraud prevention.

Architecture:
    [Checkout UI] → JS Agent → requestId
    [Backend]     → GET /events/{requestId} → Smart Signals → risk scoring

Server API: https://dev.fingerprint.com/docs/server-api
Python SDK: fingerprint-pro-server-api-sdk (optional, httpx fallback)

Issue: #133
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# API regions
API_REGIONS = {
    "us": "https://api.fpjs.io",
    "eu": "https://eu.api.fpjs.io",
    "ap": "https://ap.api.fpjs.io",
}

DEFAULT_REGION = "us"


class BotResult(str, Enum):
    """Bot detection result from Fingerprint."""
    NOT_DETECTED = "notDetected"
    GOOD = "good"  # Known crawler (Googlebot, etc.)
    BAD = "bad"  # Headless browser, Selenium, Puppeteer


class DeviceRisk(str, Enum):
    """Device risk level derived from Smart Signals."""
    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VPNResult:
    """VPN detection result."""
    detected: bool = False
    public_vpn: bool = False
    relay: bool = False
    timezone_mismatch: bool = False
    methods: dict[str, bool] = field(default_factory=dict)


@dataclass
class TamperingResult:
    """Browser tampering detection result."""
    detected: bool = False
    anomaly_score: float = 0.0
    anti_detect_browser: bool = False


@dataclass
class DeviceIntelligence:
    """Complete device intelligence from Fingerprint Smart Signals.

    This is the primary result object containing all signals from
    a single identification event.
    """
    request_id: str
    visitor_id: str
    visitor_found: bool = False
    confidence_score: float = 0.0

    # Bot detection
    bot_result: BotResult = BotResult.NOT_DETECTED
    bot_type: str = ""

    # Smart Signals
    vpn: VPNResult = field(default_factory=VPNResult)
    tampering: TamperingResult = field(default_factory=TamperingResult)
    incognito: bool = False
    virtual_machine: bool = False
    ip_blocklisted: bool = False
    suspect_score: int = 0  # 0-100 weighted risk score

    # IP & Geo
    ip_address: str = ""
    country: str = ""
    city: str = ""
    timezone: str = ""

    # Velocity
    velocity: dict[str, Any] = field(default_factory=dict)

    # Timestamps
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    identified_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Raw response for debugging
    raw_products: dict[str, Any] = field(default_factory=dict)

    @property
    def is_bot(self) -> bool:
        """Whether a bad bot was detected."""
        return self.bot_result == BotResult.BAD

    @property
    def is_suspicious(self) -> bool:
        """Whether device shows any suspicious signals."""
        return (
            self.is_bot
            or self.vpn.detected
            or self.tampering.detected
            or self.ip_blocklisted
            or self.virtual_machine
            or self.suspect_score > 50
        )

    @property
    def risk_level(self) -> DeviceRisk:
        """Derive overall risk from signal combination."""
        if self.is_bot or self.suspect_score >= 80:
            return DeviceRisk.CRITICAL
        if self.ip_blocklisted or self.tampering.anti_detect_browser:
            return DeviceRisk.HIGH
        if self.vpn.detected or self.suspect_score >= 50:
            return DeviceRisk.MEDIUM
        if self.incognito or self.virtual_machine or self.suspect_score >= 20:
            return DeviceRisk.LOW
        return DeviceRisk.CLEAN

    @property
    def risk_score(self) -> float:
        """Normalized risk score 0.0-1.0 for integration with AnomalyEngine."""
        score = 0.0
        if self.is_bot:
            score += 0.40
        if self.vpn.detected:
            score += 0.15
        if self.tampering.detected:
            score += 0.15
        if self.ip_blocklisted:
            score += 0.10
        if self.virtual_machine:
            score += 0.05
        if self.incognito:
            score += 0.05
        # Add normalized suspect score (0-100 → 0-0.10)
        score += min(self.suspect_score / 100, 1.0) * 0.10
        return min(score, 1.0)


class FingerprintProvider:
    """Fingerprint.com Server API client for device intelligence.

    Fetches identification events and Smart Signals to assess device risk.
    Designed to integrate with the Sardis guardrails pipeline.

    Configuration via environment variables:
        FINGERPRINT_API_KEY     — Server API secret key
        FINGERPRINT_REGION      — API region: "us", "eu", or "ap" (default: "us")

    Usage:
        provider = FingerprintProvider()
        result = await provider.get_device_intelligence(request_id)
        if result.is_suspicious:
            # Flag for review or block
    """

    def __init__(
        self,
        api_key: str | None = None,
        region: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key or os.getenv("FINGERPRINT_API_KEY", "")
        region_name = region or os.getenv("FINGERPRINT_REGION", DEFAULT_REGION)
        self._base_url = API_REGIONS.get(region_name, API_REGIONS[DEFAULT_REGION])
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Whether the provider has valid API credentials."""
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        """Build request headers (API v3)."""
        return {
            "Auth-API-Key": self._api_key,
            "Accept": "application/json",
        }

    async def get_device_intelligence(
        self, request_id: str
    ) -> DeviceIntelligence:
        """Fetch full identification event with Smart Signals.

        Args:
            request_id: The requestId returned by the JS agent.

        Returns:
            DeviceIntelligence with all signals parsed.

        Raises:
            FingerprintError: On API errors or missing configuration.
        """
        if not self._api_key:
            raise FingerprintError("FINGERPRINT_API_KEY not configured")

        url = f"{self._base_url}/events/{request_id}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise FingerprintError(
                f"Fingerprint API error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise FingerprintError(f"Fingerprint API request failed: {e}") from e

        return self._parse_event(request_id, data)

    async def get_visitor_history(
        self,
        visitor_id: str,
        limit: int = 10,
        linked_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch visit history for a visitor.

        Args:
            visitor_id: The stable visitorId.
            limit: Max visits to return.
            linked_id: Filter by linked ID.

        Returns:
            List of visit records.
        """
        if not self._api_key:
            raise FingerprintError("FINGERPRINT_API_KEY not configured")

        url = f"{self._base_url}/visitors/{visitor_id}"
        params: dict[str, Any] = {"limit": limit}
        if linked_id:
            params["linked_id"] = linked_id

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                url, headers=self._headers(), params=params
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("visits", [])

    async def health_check(self) -> bool:
        """Check if the Fingerprint API is reachable."""
        if not self._api_key:
            return False
        try:
            # Use a dummy request ID — will return 404 but proves connectivity
            url = f"{self._base_url}/events/health_check_probe"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=self._headers())
                # 404 means API is reachable, just no such event
                return resp.status_code in (200, 404, 403)
        except Exception:
            return False

    # ---- Parsing ----

    def _parse_event(
        self, request_id: str, data: dict[str, Any]
    ) -> DeviceIntelligence:
        """Parse a /events/{requestId} response into DeviceIntelligence."""
        products = data.get("products", {})

        # Identification
        ident = products.get("identification", {}).get("data", {})
        visitor_id = ident.get("visitorId", "")
        visitor_found = ident.get("visitorFound", False)
        confidence = ident.get("confidence", {}).get("score", 0.0)
        incognito = ident.get("incognito", False)
        ip_address = ident.get("ip", "")

        # IP location
        ip_loc = ident.get("ipLocation", {})
        country = ip_loc.get("country", {}).get("code", "")
        city = ip_loc.get("city", {}).get("name", "")
        timezone = ip_loc.get("timezone", "")

        first_seen = ident.get("firstSeenAt", {}).get("global")
        last_seen = ident.get("lastSeenAt", {}).get("global")

        # Bot detection
        botd = products.get("botd", {}).get("data", {})
        bot_info = botd.get("bot", {})
        bot_result_str = bot_info.get("result", "notDetected")
        try:
            bot_result = BotResult(bot_result_str)
        except ValueError:
            bot_result = BotResult.NOT_DETECTED
        bot_type = bot_info.get("type", "")

        # VPN detection
        vpn_data = products.get("vpn", {}).get("data", {})
        vpn_result = VPNResult(
            detected=vpn_data.get("result", False),
            public_vpn=vpn_data.get("methods", {}).get("publicVPN", False),
            relay=vpn_data.get("methods", {}).get("relay", False),
            timezone_mismatch=vpn_data.get("methods", {}).get(
                "timezoneMismatch", False
            ),
            methods=vpn_data.get("methods", {}),
        )

        # Tampering
        tamper_data = products.get("tampering", {}).get("data", {})
        tampering = TamperingResult(
            detected=tamper_data.get("result", False),
            anomaly_score=tamper_data.get("anomalyScore", 0.0),
            anti_detect_browser=tamper_data.get("antiDetectBrowser", False),
        )

        # IP blocklist
        ip_bl = products.get("ipBlocklist", {}).get("data", {})
        ip_blocklisted = ip_bl.get("result", False)

        # Virtual machine
        vm_data = products.get("virtualMachine", {}).get("data", {})
        virtual_machine = vm_data.get("result", False)

        # Suspect score
        suspect_data = products.get("suspectScore", {}).get("data", {})
        suspect_score = suspect_data.get("result", 0)

        # Velocity signals
        velocity = products.get("velocity", {}).get("data", {})

        return DeviceIntelligence(
            request_id=request_id,
            visitor_id=visitor_id,
            visitor_found=visitor_found,
            confidence_score=confidence,
            bot_result=bot_result,
            bot_type=bot_type,
            vpn=vpn_result,
            tampering=tampering,
            incognito=incognito,
            virtual_machine=virtual_machine,
            ip_blocklisted=ip_blocklisted,
            suspect_score=suspect_score,
            ip_address=ip_address,
            country=country,
            city=city,
            timezone=timezone,
            velocity=velocity,
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            raw_products=products,
        )


class FingerprintError(Exception):
    """Error from Fingerprint API or configuration."""
    pass


# ============ Convenience Singleton ============

_provider: FingerprintProvider | None = None


def get_fingerprint_provider() -> FingerprintProvider:
    """Get or create the global FingerprintProvider singleton."""
    global _provider
    if _provider is None:
        _provider = FingerprintProvider()
    return _provider
