"""Tests for usage metering service."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Bootstrap monorepo imports
packages_dir = Path(__file__).parent.parent / "packages"
for pkg in ["sardis-core", "sardis-wallet", "sardis-chain", "sardis-protocol",
            "sardis-ledger", "sardis-cards", "sardis-compliance", "sardis-checkout",
            "sardis-coinbase", "sardis-api"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists() and str(pkg_path) not in sys.path:
        sys.path.insert(0, str(pkg_path))

os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("DATABASE_URL", "memory://")
os.environ.setdefault("SARDIS_CHAIN_MODE", "simulated")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing_purposes_only_32chars")


class TestUsageMeteringService:
    """Test UsageMeteringService."""

    @pytest.mark.asyncio
    async def test_track_event_best_effort(self):
        """track_event should not raise even if DB is unavailable."""
        from sardis_api.services.usage_metering import UsageMeteringService

        with patch("sardis_v2_core.database.Database.get_pool", side_effect=Exception("DB down")):
            svc = UsageMeteringService()
            # Should not raise
            await svc.track_event("org_test", "transaction", 1)

    @pytest.mark.asyncio
    async def test_get_usage_returns_summary(self):
        """get_usage should return a UsageSummary with correct totals."""
        from sardis_api.services.usage_metering import UsageMeteringService

        mock_rows = [
            {"event_type": "transaction", "total": 150},
            {"event_type": "card_issued", "total": 3},
            {"event_type": "api_call", "total": 5000},
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        with patch("sardis_v2_core.database.Database.get_pool", return_value=mock_pool):
            svc = UsageMeteringService()
            usage = await svc.get_usage("org_test")
            assert usage.transactions == 150
            assert usage.cards_issued == 3
            assert usage.api_calls == 5000
            assert usage.policy_checks == 0  # Not in mock data

    @pytest.mark.asyncio
    async def test_get_usage_handles_db_error(self):
        """get_usage should return empty summary on DB error."""
        from sardis_api.services.usage_metering import UsageMeteringService

        with patch("sardis_v2_core.database.Database.get_pool", side_effect=Exception("DB down")):
            svc = UsageMeteringService()
            usage = await svc.get_usage("org_test")
            assert usage.transactions == 0
            assert usage.org_id == "org_test"


class TestTierLimits:
    """Test tier limit definitions."""

    def test_free_tier_limits(self):
        from sardis_api.services.usage_metering import TIER_LIMITS
        free = TIER_LIMITS["free"]
        assert free["transaction"] == 100
        assert free["card_issued"] == 1

    def test_growth_tier_limits(self):
        from sardis_api.services.usage_metering import TIER_LIMITS
        growth = TIER_LIMITS["growth"]
        assert growth["transaction"] == 10000
        assert growth["card_issued"] == 25

    def test_scale_tier_unlimited(self):
        from sardis_api.services.usage_metering import TIER_LIMITS
        scale = TIER_LIMITS["scale"]
        assert scale["card_issued"] == -1  # unlimited

    def test_enterprise_all_unlimited(self):
        from sardis_api.services.usage_metering import TIER_LIMITS
        enterprise = TIER_LIMITS["enterprise"]
        for limit in enterprise.values():
            assert limit == -1


class TestCheckLimit:
    """Test limit checking logic."""

    @pytest.mark.asyncio
    async def test_under_limit_returns_true(self):
        """Should return True when under the limit."""
        from sardis_api.services.usage_metering import UsageMeteringService, UsageSummary

        svc = UsageMeteringService()
        with patch.object(svc, "get_usage", return_value=UsageSummary(
            org_id="org_test",
            period_start="2026-03-01",
            period_end="2026-03-10",
            transactions=50,
        )):
            result = await svc.check_limit("org_test", "transaction", "free")
            assert result is True  # 50 < 100

    @pytest.mark.asyncio
    async def test_over_limit_returns_false(self):
        """Should return False when at or over the limit."""
        from sardis_api.services.usage_metering import UsageMeteringService, UsageSummary

        svc = UsageMeteringService()
        with patch.object(svc, "get_usage", return_value=UsageSummary(
            org_id="org_test",
            period_start="2026-03-01",
            period_end="2026-03-10",
            transactions=100,
        )):
            result = await svc.check_limit("org_test", "transaction", "free")
            assert result is False  # 100 >= 100

    @pytest.mark.asyncio
    async def test_unlimited_always_returns_true(self):
        """Enterprise/scale unlimited should always return True."""
        from sardis_api.services.usage_metering import UsageMeteringService, UsageSummary

        svc = UsageMeteringService()
        with patch.object(svc, "get_usage", return_value=UsageSummary(
            org_id="org_test",
            period_start="2026-03-01",
            period_end="2026-03-10",
            transactions=999999,
        )):
            result = await svc.check_limit("org_test", "transaction", "enterprise")
            assert result is True


class TestSDKMetrics:
    """Test SDK metrics service."""

    def test_pypi_packages_defined(self):
        from sardis_api.services.sdk_metrics import PYPI_PACKAGES
        assert "sardis" in PYPI_PACKAGES
        assert len(PYPI_PACKAGES) > 0

    def test_npm_packages_defined(self):
        from sardis_api.services.sdk_metrics import NPM_PACKAGES
        assert "@sardis/sdk" in NPM_PACKAGES

    def test_sdk_metrics_router_routes(self):
        from sardis_api.routers.sdk_metrics import router
        paths = [route.path for route in router.routes]
        # Routes include the router prefix
        assert any("sdk-installs" in p for p in paths)
        assert any("growth" in p for p in paths)
