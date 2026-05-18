"""Tests for the Stripe Billing API router.

Covers:
- GET /api/v2/billing/plans   — public, returns 4 plans (dev/starter/growth/enterprise)
- GET /api/v2/billing/account — auth required, returns dev plan default
- POST /api/v2/billing/checkout — returns 503 when billing disabled
- POST /api/v2/billing/webhook  — rejects invalid Stripe signature
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routes.billing.billing import router, webhook_router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with only the billing routers."""
    app = FastAPI()

    # Override auth so tests don't need a real JWT / API key
    fake_principal = Principal(
        kind="api_key",
        organization_id="org_test_001",
        scopes=["*"],
    )
    app.dependency_overrides[require_principal] = lambda: fake_principal

    app.include_router(router)
    app.include_router(webhook_router)
    return app


@pytest.fixture()
def client():
    app = _make_app()
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListPlans:
    def test_returns_four_plans(self, client):
        resp = client.get("/api/v2/billing/plans")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        plans = data["plans"]
        assert len(plans) == 4

    def test_plan_names(self, client):
        resp = client.get("/api/v2/billing/plans")
        names = {p["plan"] for p in resp.json()["plans"]}
        assert names == {"dev", "starter", "growth", "enterprise"}

    def test_dev_plan_price(self, client):
        resp = client.get("/api/v2/billing/plans")
        dev = next(p for p in resp.json()["plans"] if p["plan"] == "dev")
        assert dev["price_monthly_cents"] == 4_900

    def test_starter_plan_price(self, client):
        resp = client.get("/api/v2/billing/plans")
        starter = next(p for p in resp.json()["plans"] if p["plan"] == "starter")
        assert starter["price_monthly_cents"] == 19_900

    def test_growth_plan_price(self, client):
        resp = client.get("/api/v2/billing/plans")
        growth = next(p for p in resp.json()["plans"] if p["plan"] == "growth")
        assert growth["price_monthly_cents"] == 49_900

    def test_plan_info_has_required_fields(self, client):
        resp = client.get("/api/v2/billing/plans")
        plan = resp.json()["plans"][0]
        required_fields = {
            "plan",
            "price_monthly_cents",
            "api_calls_per_month",
            "agents",
            "tx_fee_bps",
            "monthly_tx_volume_cents",
        }
        assert required_fields.issubset(plan.keys())

    def test_no_auth_required(self):
        """Plans endpoint must be publicly accessible without credentials."""
        app = FastAPI()
        app.include_router(webhook_router)
        with TestClient(app) as c:
            resp = c.get("/api/v2/billing/plans")
        assert resp.status_code == 200


class TestGetAccount:
    def test_returns_dev_plan_by_default(self, client):
        mock_sub = MagicMock()
        mock_sub.plan = "dev"
        mock_sub.status = "active"
        mock_sub.stripe_customer_id = None
        mock_sub.stripe_subscription_id = None

        with patch(
            "sardis_api.routes.billing.billing.StripeBillingService.get_or_create_subscription",
            new=AsyncMock(return_value=mock_sub),
        ):
            resp = client.get("/api/v2/billing/account")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["account"]["plan"] == "dev"
        assert data["account"]["status"] == "active"

    def test_account_contains_usage_snapshot(self, client):
        mock_sub = MagicMock()
        mock_sub.plan = "dev"
        mock_sub.status = "active"
        mock_sub.stripe_customer_id = None
        mock_sub.stripe_subscription_id = None

        with patch(
            "sardis_api.routes.billing.billing.StripeBillingService.get_or_create_subscription",
            new=AsyncMock(return_value=mock_sub),
        ):
            resp = client.get("/api/v2/billing/account")

        data = resp.json()
        usage = data["usage"]
        assert "api_calls_used" in usage
        assert "api_calls_limit" in usage
        assert "tx_volume_cents" in usage

    def test_account_org_id_matches_principal(self, client):
        mock_sub = MagicMock()
        mock_sub.plan = "dev"
        mock_sub.status = "active"
        mock_sub.stripe_customer_id = None
        mock_sub.stripe_subscription_id = None

        with patch(
            "sardis_api.routes.billing.billing.StripeBillingService.get_or_create_subscription",
            new=AsyncMock(return_value=mock_sub),
        ):
            resp = client.get("/api/v2/billing/account")

        data = resp.json()
        assert data["account"]["org_id"] == "org_test_001"


class TestCheckout:
    def test_returns_503_when_billing_disabled(self, client):
        """POST /checkout returns 503 when billing_enabled is False (default)."""
        resp = client.post("/api/v2/billing/checkout", json={"plan": "starter"})
        assert resp.status_code == 503, resp.text
        assert "billing" in resp.json()["detail"].lower()

    def test_returns_400_for_invalid_plan(self, client):
        """POST /checkout with an invalid plan returns 400 even before billing check."""
        # Patch billing_enabled to True to reach plan validation
        with patch(
            "sardis_api.routes.billing.billing._billing_config",
            MagicMock(
                billing_enabled=True,
                stripe_secret_key="stripe_key_for_testing",
                stripe_price_dev="price_dev",
                stripe_price_starter="price_starter",
                stripe_price_growth="price_growth",
            ),
        ):
            resp = client.post("/api/v2/billing/checkout", json={"plan": "enterprise"})
        assert resp.status_code == 400, resp.text

    def test_checkout_with_billing_enabled_and_stripe_mocked(self, client):
        """POST /checkout with billing enabled and stripe mocked returns checkout_url."""
        fake_session = MagicMock()
        fake_session.url = "https://checkout.stripe.com/pay/cs_test_abc"

        fake_stripe = MagicMock()
        fake_stripe.checkout.Session.create.return_value = fake_session

        with patch(
            "sardis_api.routes.billing.billing._billing_config",
            MagicMock(
                billing_enabled=True,
                stripe_secret_key="stripe_key_for_testing",
                stripe_price_dev="price_dev",
                stripe_price_starter="price_starter",
                stripe_price_growth="price_growth",
            ),
        ):
            # Inject the mock into sys.modules so the `import stripe` inside the
            # function body resolves to our fake.
            with patch.dict("sys.modules", {"stripe": fake_stripe}):
                resp = client.post(
                    "/api/v2/billing/checkout", json={"plan": "starter"}
                )

        assert resp.status_code == 200, resp.text
        assert resp.json()["checkout_url"] == fake_session.url
        fake_stripe.checkout.Session.create.assert_called_once()


class TestWebhook:
    def test_rejects_missing_signature(self, client):
        """POST /webhook without Stripe-Signature header returns 400."""
        payload = json.dumps({"type": "checkout.session.completed", "data": {}}).encode()
        resp = client.post(
            "/api/v2/billing/webhook",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400, resp.text

    def test_rejects_invalid_signature(self, client):
        """POST /webhook with bad stripe-signature returns 400."""
        payload = json.dumps({"type": "checkout.session.completed", "data": {}}).encode()
        resp = client.post(
            "/api/v2/billing/webhook",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=bad,v1=invalid",
            },
        )
        assert resp.status_code == 400, resp.text

    def test_accepts_valid_signature(self, client):
        """POST /webhook with a valid signature (mocked) returns 200."""
        payload = json.dumps(
            {"type": "invoice.paid", "data": {"object": {}}}
        ).encode()

        with patch(
            "sardis_api.routes.billing.billing.StripeBillingService.verify_webhook_signature",
            return_value=True,
        ):
            with patch(
                "sardis_api.routes.billing.billing.StripeBillingService.handle_webhook_event",
                new=AsyncMock(),
            ):
                resp = client.post(
                    "/api/v2/billing/webhook",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": "t=1,v1=valid",
                    },
                )

        assert resp.status_code == 200, resp.text
