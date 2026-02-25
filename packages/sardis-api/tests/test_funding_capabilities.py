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


def _non_admin_principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["read"],
        api_key=None,
    )


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        cards=SimpleNamespace(
            primary_provider="stripe_issuing",
            fallback_provider="lithic",
            on_chain_provider="coinbase_cdp",
        ),
        stripe=SimpleNamespace(
            treasury_financial_account_id="fa_test_123",
            connected_account_id="acct_test_123",
        ),
        coinbase=SimpleNamespace(
            api_key_name="",
            api_key_private_key="",
        ),
    )


def _build_app(settings_obj: SimpleNamespace, *, admin: bool = True) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: FundingCapabilitiesDeps(settings=settings_obj)
    app.dependency_overrides[require_principal] = (
        _admin_principal if admin else _non_admin_principal
    )
    app.include_router(router, prefix="/api/v2")
    return app


def test_capability_matrix_marks_stripe_fiat_ready(monkeypatch):
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_123")
    monkeypatch.delenv("COINBASE_CDP_API_KEY_NAME", raising=False)
    monkeypatch.delenv("COINBASE_CDP_API_KEY_PRIVATE_KEY", raising=False)

    app = _build_app(_settings())
    client = TestClient(app)

    response = client.get("/api/v2/funding/capabilities")
    assert response.status_code == 200
    payload = response.json()

    providers = {entry["provider"]: entry for entry in payload["providers"]}
    assert providers["stripe_issuing"]["funding_fiat_ready"] is True
    assert providers["stripe_issuing"]["card_issuing_ready"] is True
    assert providers["coinbase_cdp"]["onchain_rail_ready"] is False
    assert payload["primary_provider"] == "stripe_issuing"
    assert "stripe_issuing" in payload["rails"]["fiat_ready_providers"]


def test_capability_matrix_marks_coinbase_stablecoin_ready(monkeypatch):
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_123")
    monkeypatch.setenv("COINBASE_CDP_API_KEY_NAME", "cdp_key")
    monkeypatch.setenv("COINBASE_CDP_API_KEY_PRIVATE_KEY", "cdp_secret")

    app = _build_app(_settings())
    client = TestClient(app)

    response = client.get("/api/v2/funding/capabilities")
    assert response.status_code == 200
    payload = response.json()
    providers = {entry["provider"]: entry for entry in payload["providers"]}
    assert providers["coinbase_cdp"]["funding_stablecoin_ready"] is True
    assert providers["coinbase_cdp"]["onchain_rail_ready"] is True
    assert "coinbase_cdp" in payload["rails"]["stablecoin_ready_providers"]


def test_capability_matrix_requires_admin(monkeypatch):
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_123")
    app = _build_app(_settings(), admin=False)
    client = TestClient(app)

    response = client.get("/api/v2/funding/capabilities")
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin privileges required"
