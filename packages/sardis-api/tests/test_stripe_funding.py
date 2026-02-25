from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers.stripe_funding import (
    StripeFundingDeps,
    get_deps,
    router,
)
from sardis_v2_core.funding import FundingRequest, FundingResult


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


class _FakeTreasuryRepo:
    def __init__(self) -> None:
        self.record_calls: list[dict[str, object]] = []
        self.items: list[dict[str, object]] = []

    async def record_issuing_funding_event(self, **kwargs):
        self.record_calls.append(kwargs)
        row = dict(kwargs)
        row["created_at"] = "2026-02-25T00:00:00+00:00"
        self.items.append(row)
        return row

    async def list_issuing_funding_events(self, organization_id: str, **kwargs):
        return [i for i in self.items if i.get("organization_id") == organization_id]

    async def summarize_issuing_funding_events(self, organization_id: str, *, hours: int = 24):
        items = [i for i in self.items if i.get("organization_id") == organization_id]
        total_minor = sum(int(i.get("amount_minor", 0) or 0) for i in items)
        return {
            "organization_id": organization_id,
            "window_hours": hours,
            "count": len(items),
            "total_minor": total_minor,
            "by_status": {"posted": len(items)},
        }


class _FakeCanonicalRepo:
    def __init__(self) -> None:
        self.events = []

    async def ingest_event(self, event, *, drift_tolerance_minor: int = 0):
        self.events.append((event, drift_tolerance_minor))
        return {"ok": True}


class _FakeFundingAdapter:
    provider = "coinbase_cdp"
    rail = "stablecoin"

    def __init__(self) -> None:
        self.requests: list[FundingRequest] = []

    async def fund(self, request: FundingRequest) -> FundingResult:
        self.requests.append(request)
        return FundingResult(
            provider=self.provider,
            rail=self.rail,
            transfer_id="cdp_topup_1",
            amount=request.amount,
            currency=request.currency,
            status="posted",
            metadata={"path": "stablecoin"},
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


def test_topup_records_audit_and_canonical_event():
    treasury = _FakeTreasuryProvider()
    treasury_repo = _FakeTreasuryRepo()
    canonical_repo = _FakeCanonicalRepo()
    deps = StripeFundingDeps(
        treasury_provider=treasury,
        treasury_repo=treasury_repo,
        canonical_repo=canonical_repo,
    )
    app = _build_app(deps)
    client = TestClient(app)

    response = client.post(
        "/api/v2/stripe/funding/issuing/topups",
        json={"amount": "10.00", "description": "Audit me"},
        headers={"Idempotency-Key": "idem-topup-1"},
    )

    assert response.status_code == 200
    assert len(treasury_repo.record_calls) == 1
    rec = treasury_repo.record_calls[0]
    assert rec["organization_id"] == "org_demo"
    assert rec["transfer_id"] == "tu_test_1"
    assert rec["amount_minor"] == 1000
    assert rec["status_value"] == "posted"
    assert len(canonical_repo.events) == 1


def test_topup_history_and_reconcile_endpoints():
    treasury = _FakeTreasuryProvider()
    treasury_repo = _FakeTreasuryRepo()
    deps = StripeFundingDeps(treasury_provider=treasury, treasury_repo=treasury_repo)
    app = _build_app(deps)
    client = TestClient(app)

    client.post(
        "/api/v2/stripe/funding/issuing/topups",
        json={"amount": "7.50", "description": "Seed history"},
    )

    history = client.get("/api/v2/stripe/funding/issuing/topups/history")
    assert history.status_code == 200
    items = history.json()
    assert len(items) == 1
    assert items[0]["transfer_id"] == "tu_test_1"

    reconcile = client.get("/api/v2/stripe/funding/issuing/topups/reconcile", params={"hours": 48})
    assert reconcile.status_code == 200
    summary = reconcile.json()
    assert summary["organization_id"] == "org_demo"
    assert summary["count"] == 1
    assert summary["total_minor"] == 750


def test_topup_supports_provider_agnostic_adapter():
    adapter = _FakeFundingAdapter()
    treasury_repo = _FakeTreasuryRepo()
    deps = StripeFundingDeps(
        treasury_provider=None,
        funding_adapter=adapter,
        treasury_repo=treasury_repo,
    )
    app = _build_app(deps)
    client = TestClient(app)

    response = client.post(
        "/api/v2/stripe/funding/issuing/topups",
        json={"amount": "4.25", "description": "Stablecoin-backed funding"},
    )

    assert response.status_code == 200
    assert adapter.requests
    assert adapter.requests[0].amount == Decimal("4.25")
    assert len(treasury_repo.record_calls) == 1
    assert treasury_repo.record_calls[0]["provider"] == "coinbase_cdp"
