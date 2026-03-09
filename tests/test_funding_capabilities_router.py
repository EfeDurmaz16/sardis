from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_api.authz import Principal, require_principal
from sardis_api.routers.funding_capabilities import (
    FundingCapabilitiesDeps,
    get_deps,
    router,
)


def _admin_principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        cards=SimpleNamespace(
            primary_provider="stripe_issuing",
            fallback_provider="lithic",
            on_chain_provider="coinbase_cdp",
        ),
        funding=SimpleNamespace(
            primary_adapter="circle_cpn",
            fallback_adapter="bridge",
        ),
        stripe=SimpleNamespace(
            treasury_financial_account_id="fa_test_123",
            connected_account_id="acct_test_123",
        ),
        coinbase=SimpleNamespace(
            api_key_name="",
            api_key_private_key="",
        ),
        circle_cpn=SimpleNamespace(
            enabled=False,
            api_key="",
        ),
    )


def _build_app(settings_obj: SimpleNamespace) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: FundingCapabilitiesDeps(settings=settings_obj)
    app.dependency_overrides[require_principal] = _admin_principal
    app.include_router(router, prefix="/api/v2")
    return app


def test_retry_order_falls_back_to_stripe_when_cpn_is_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_API_KEY", "stripe_test_key_123")
    monkeypatch.delenv("SARDIS_CIRCLE_CPN__ENABLED", raising=False)
    monkeypatch.delenv("SARDIS_CIRCLE_CPN__API_KEY", raising=False)
    monkeypatch.delenv("BRIDGE_API_KEY", raising=False)

    app = _build_app(_settings())
    client = TestClient(app)

    response = client.get("/api/v2/funding/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["funding_primary_adapter"] == "circle_cpn"
    assert payload["funding_fallback_adapter"] == "bridge_cards"
    assert payload["rails"]["fiat_retry_order"][0] == "stripe_issuing"


def test_retry_order_prefers_cpn_then_bridge_when_ready(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_API_KEY", "stripe_test_key_123")
    monkeypatch.setenv("SARDIS_CIRCLE_CPN__ENABLED", "true")
    monkeypatch.setenv("SARDIS_CIRCLE_CPN__API_KEY", "cpn_key")
    monkeypatch.setenv("BRIDGE_API_KEY", "bridge_key")

    app = _build_app(_settings())
    client = TestClient(app)

    response = client.get("/api/v2/funding/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["rails"]["fiat_retry_order"][:2] == ["circle_cpn", "bridge_cards"]
