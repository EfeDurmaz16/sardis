from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers.stripe_funding import (
    StripeFundingDeps,
    get_deps,
    router,
)


class _FakeTreasuryProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def fund_issuing_balance(
        self,
        amount,
        description,
        connected_account_id=None,
        metadata=None,
    ):
        self.calls.append(
            {
                "amount": amount,
                "description": description,
                "connected_account_id": connected_account_id,
                "metadata": metadata,
            }
        )
        return SimpleNamespace(
            id="tu_test_1",
            amount=amount,
            currency="usd",
            status="posted",
        )


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _build_app(deps: StripeFundingDeps) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: deps
    app.dependency_overrides[require_principal] = _principal
    app.include_router(router, prefix="/api/v2")
    return app


def test_topup_uses_request_connected_account_id():
    treasury = _FakeTreasuryProvider()
    deps = StripeFundingDeps(treasury_provider=treasury)
    app = _build_app(deps)
    client = TestClient(app)

    response = client.post(
        "/api/v2/stripe/funding/issuing/topups",
        json={
            "amount": "12.50",
            "description": "Tenant topup",
            "connected_account_id": "acct_req_123",
            "metadata": {"ticket": "t_1"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected_account_id"] == "acct_req_123"
    assert payload["connected_account_source"] == "request"
    assert treasury.calls[0]["connected_account_id"] == "acct_req_123"
    assert treasury.calls[0]["metadata"]["org_id"] == "org_demo"
    assert treasury.calls[0]["metadata"]["ticket"] == "t_1"


def test_topup_resolves_connected_account_from_org_map():
    treasury = _FakeTreasuryProvider()
    deps = StripeFundingDeps(
        treasury_provider=treasury,
        default_connected_account_id="acct_default_123",
        connected_account_map={"org_demo": "acct_org_456"},
    )
    app = _build_app(deps)
    client = TestClient(app)

    response = client.post(
        "/api/v2/stripe/funding/issuing/topups",
        json={"amount": "5.00", "description": "Mapped org topup"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected_account_id"] == "acct_org_456"
    assert payload["connected_account_source"] == "org_map"
    assert treasury.calls[0]["connected_account_id"] == "acct_org_456"


def test_topup_rejects_invalid_connected_account_id():
    treasury = _FakeTreasuryProvider()
    deps = StripeFundingDeps(treasury_provider=treasury)
    app = _build_app(deps)
    client = TestClient(app)

    response = client.post(
        "/api/v2/stripe/funding/issuing/topups",
        json={"amount": "1.00", "connected_account_id": "not_acct"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_connected_account_id"


def test_resolve_connected_account_endpoint_uses_default():
    treasury = _FakeTreasuryProvider()
    deps = StripeFundingDeps(
        treasury_provider=treasury,
        default_connected_account_id="acct_default_123",
    )
    app = _build_app(deps)
    client = TestClient(app)

    response = client.get("/api/v2/stripe/funding/resolve-connected-account")

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected_account_id"] == "acct_default_123"
    assert payload["source"] == "default"
