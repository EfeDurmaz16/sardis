from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from sardis_api.authz import Principal, require_admin_principal
from sardis_api.canonical_state_machine import normalize_stablecoin_event
from sardis_api.repositories.canonical_ledger_repository import CanonicalLedgerRepository
from sardis_api.routers import treasury_ops as treasury_ops_router


@pytest.mark.asyncio
async def test_treasury_ops_endpoints_expose_journeys_and_reviews():
    repo = CanonicalLedgerRepository(dsn="memory://")
    event = normalize_stablecoin_event(
        organization_id="org_demo",
        rail="stablecoin_tx",
        reference="0xops",
        provider_event_id="0xops:submitted",
        provider_event_type="ONCHAIN_TX_SUBMITTED",
        canonical_event_type="stablecoin.tx.submitted",
        canonical_state="processing",
        amount_minor=100,
        currency="USDC",
    )
    await repo.ingest_event(event)
    await repo.enqueue_manual_review(
        organization_id="org_demo",
        journey_id="jrny_manual",
        reason_code="stale_processing",
        priority="medium",
        payload={"test": True},
    )

    app = FastAPI()
    app.dependency_overrides[treasury_ops_router.get_deps] = lambda: treasury_ops_router.TreasuryOpsDependencies(
        canonical_repo=repo
    )
    app.dependency_overrides[require_admin_principal] = lambda: Principal(
        kind="jwt",
        organization_id="org_demo",
        scopes=["*"],
        user=None,
        api_key=None,
    )
    app.include_router(treasury_ops_router.router, prefix="/api/v2/treasury/ops")

    client = TestClient(app)
    journeys_resp = client.get("/api/v2/treasury/ops/journeys")
    assert journeys_resp.status_code == 200
    journeys_data = journeys_resp.json()
    assert journeys_data["count"] >= 1

    reviews_resp = client.get("/api/v2/treasury/ops/manual-reviews?status_value=queued")
    assert reviews_resp.status_code == 200
    reviews_data = reviews_resp.json()
    assert reviews_data["count"] >= 1

    export_resp = client.get("/api/v2/treasury/ops/audit-evidence/export?format=json")
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["organization_id"] == "org_demo"
    assert "journeys" in export_data

