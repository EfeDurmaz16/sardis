"""Tests for billing and Stripe integration."""
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


class TestBillingPlans:
    """Test billing plan definitions."""

    def test_all_plans_defined(self):
        from sardis_api.services.stripe_billing import PLANS
        assert "free" in PLANS
        assert "growth" in PLANS
        assert "scale" in PLANS
        assert "enterprise" in PLANS

    def test_free_plan_has_zero_price(self):
        from sardis_api.services.stripe_billing import PLANS
        assert PLANS["free"].monthly_price_cents == 0

    def test_growth_plan_pricing(self):
        from sardis_api.services.stripe_billing import PLANS
        assert PLANS["growth"].monthly_price_cents == 4900
        assert PLANS["growth"].tx_fee_bps == 50  # 0.5%
        assert PLANS["growth"].tx_limit == 10000

    def test_scale_plan_pricing(self):
        from sardis_api.services.stripe_billing import PLANS
        assert PLANS["scale"].monthly_price_cents == 29900
        assert PLANS["scale"].tx_fee_bps == 30  # 0.3%
        assert PLANS["scale"].tx_limit == 100000

    def test_enterprise_unlimited(self):
        from sardis_api.services.stripe_billing import PLANS
        assert PLANS["enterprise"].tx_limit == -1
        assert PLANS["enterprise"].agent_limit == -1
        assert PLANS["enterprise"].card_limit == -1


class TestStripeBillingService:
    """Test StripeBillingService."""

    def test_stripe_not_configured_by_default(self):
        from sardis_api.services.stripe_billing import StripeBillingService
        svc = StripeBillingService()
        assert not svc.stripe_configured

    @pytest.mark.asyncio
    async def test_get_subscription_returns_free_default(self):
        """When no DB row exists, return free tier."""
        from sardis_api.services.stripe_billing import StripeBillingService

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        with patch("sardis_v2_core.database.Database.get_pool", return_value=mock_pool):
            svc = StripeBillingService()
            sub = await svc.get_or_create_subscription("org_test")
            assert sub.plan == "free"
            assert sub.status == "active"

    def test_invalid_plan_raises(self):
        """Creating a subscription with an invalid plan should raise."""
        from sardis_api.services.stripe_billing import StripeBillingService
        svc = StripeBillingService()
        with pytest.raises(ValueError, match="Invalid plan"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                svc.create_subscription("org_test", "invalid_plan")
            )

    @pytest.mark.asyncio
    async def test_get_invoices_empty_without_stripe(self):
        """Without Stripe configured, invoices should be empty."""
        from sardis_api.services.stripe_billing import StripeBillingService

        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_conn)

        with patch("sardis_v2_core.database.Database.get_pool", return_value=mock_pool):
            svc = StripeBillingService()
            invoices = await svc.get_invoices("org_test")
            assert invoices == []


class TestBillingRouter:
    """Test billing router configuration."""

    def test_router_has_correct_prefix(self):
        from sardis_api.routers.billing import router
        assert router.prefix == "/api/v2/billing"

    def test_router_has_billing_tag(self):
        from sardis_api.routers.billing import router
        assert "billing" in router.tags

    def test_webhook_router_exists(self):
        from sardis_api.routers.billing import webhook_router
        assert webhook_router.prefix == "/api/v2/billing"

    def test_router_has_expected_routes(self):
        from sardis_api.routers.billing import router
        paths = [route.path for route in router.routes]
        # Routes include the router prefix
        assert any("usage" in p for p in paths)
        assert any("plan" in p for p in paths)
        assert any("subscribe" in p for p in paths)
        assert any("invoices" in p for p in paths)


class TestBillingModels:
    """Test Pydantic models."""

    def test_subscribe_request(self):
        from sardis_api.routers.billing import SubscribeRequest
        req = SubscribeRequest(plan="growth")
        assert req.plan == "growth"
        assert req.stripe_customer_id is None

    def test_usage_response(self):
        from sardis_api.routers.billing import UsageResponse
        resp = UsageResponse(
            org_id="org_test",
            period_start="2026-03-01T00:00:00",
            period_end="2026-03-10T00:00:00",
            transactions=500,
            api_calls=10000,
        )
        assert resp.transactions == 500

    def test_plan_response(self):
        from sardis_api.routers.billing import PlanResponse
        resp = PlanResponse(
            plan="growth",
            display_name="Growth",
            monthly_price_cents=4900,
            tx_fee_bps=50,
            tx_limit=10000,
            agent_limit=10,
            card_limit=25,
            status="active",
        )
        assert resp.monthly_price_cents == 4900
