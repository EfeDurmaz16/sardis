from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_admin_principal
from sardis_api.routers.cpn import CPNDependencies, get_deps, router


@dataclass(frozen=True)
class _FakePayment:
    payment_id: str
    status: str
    raw: dict[str, Any]


class _FakeCPNClient:
    def __init__(self) -> None:
        self.payout_payloads: list[dict[str, Any]] = []
        self.collection_payloads: list[dict[str, Any]] = []
        self.status_calls: list[str] = []

    async def create_payout(self, payload: dict[str, Any]) -> _FakePayment:
        self.payout_payloads.append(payload)
        return _FakePayment(payment_id="cpn_pay_1", status="processing", raw=payload)

    async def create_collection(self, payload: dict[str, Any]) -> _FakePayment:
        self.collection_payloads.append(payload)
        return _FakePayment(payment_id="cpn_col_1", status="processing", raw=payload)

    async def get_payment_status(self, payment_id: str) -> _FakePayment:
        self.status_calls.append(payment_id)
        return _FakePayment(
            payment_id=payment_id,
            status="settled",
            raw={"id": payment_id, "status": "settled"},
        )


def _admin_principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _build_app(deps: CPNDependencies) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: deps
    app.dependency_overrides[require_admin_principal] = _admin_principal
    app.include_router(router, prefix="/api/v2")
    return app


def test_cpn_payout_returns_normalized_response() -> None:
    client_impl = _FakeCPNClient()
    app = _build_app(CPNDependencies(treasury_repo=None, cpn_client=client_impl))
    client = TestClient(app)

    response = client.post(
        "/api/v2/cpn/payouts",
        json={
            "amount": "125.50",
            "currency": "usd",
            "description": "Vendor payout",
            "metadata": {"invoice_id": "inv_123"},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["provider"] == "circle_cpn"
    assert payload["payment_id"] == "cpn_pay_1"
    assert payload["status"] == "processing"
    sent = client_impl.payout_payloads[0]
    assert sent["currency"] == "USD"
    assert sent["metadata"]["invoice_id"] == "inv_123"
    assert sent["metadata"]["requested_by"] == "org_demo"


def test_cpn_collection_returns_normalized_response() -> None:
    client_impl = _FakeCPNClient()
    app = _build_app(CPNDependencies(treasury_repo=None, cpn_client=client_impl))
    client = TestClient(app)

    response = client.post(
        "/api/v2/cpn/collections",
        json={
            "amount": "40.00",
            "currency": "USD",
            "description": "Collection",
            "connected_account_id": "acct_123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["payment_id"] == "cpn_col_1"
    sent = client_impl.collection_payloads[0]
    assert sent["connected_account_id"] == "acct_123"


def test_cpn_status_returns_payment_state() -> None:
    client_impl = _FakeCPNClient()
    app = _build_app(CPNDependencies(treasury_repo=None, cpn_client=client_impl))
    client = TestClient(app)

    response = client.get("/api/v2/cpn/payments/cpn_pay_99")
    assert response.status_code == 200
    payload = response.json()
    assert payload["payment_id"] == "cpn_pay_99"
    assert payload["status"] == "settled"
    assert client_impl.status_calls == ["cpn_pay_99"]


def test_cpn_admin_endpoints_require_client() -> None:
    app = _build_app(CPNDependencies(treasury_repo=None, cpn_client=None))
    client = TestClient(app)

    create = client.post("/api/v2/cpn/payouts", json={"amount": "10.0", "currency": "USD"})
    status = client.get("/api/v2/cpn/payments/cpn_pay_missing")

    assert create.status_code == 503
    assert create.json()["detail"] == "circle_cpn_not_configured"
    assert status.status_code == 503
    assert status.json()["detail"] == "circle_cpn_not_configured"
