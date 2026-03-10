from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers import evidence_export


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(evidence_export.router, prefix="/api/v2/evidence/export")

    def _principal() -> Principal:
        return Principal(kind="api_key", organization_id="org_demo", scopes=["*"])

    app.dependency_overrides[require_principal] = _principal
    return TestClient(app)


def test_export_bundle_includes_expected_sections_and_integrity() -> None:
    client = _build_client()

    response = client.post("/api/v2/evidence/export/tx_demo_123")

    assert response.status_code == 200
    body = response.json()
    assert body["tx_id"] == "tx_demo_123"
    assert set(body["sections"].keys()) >= {
        "transaction",
        "policy_decision",
        "approval",
        "execution_receipt",
        "ledger_artifacts",
        "side_effects",
        "exception_state",
        "webhook_logs",
    }
    assert body["integrity"]["content_hash"]
    assert body["integrity"]["signature"]


def test_verify_bundle_integrity_round_trip() -> None:
    client = _build_client()

    bundle = client.post("/api/v2/evidence/export/tx_demo_456").json()
    verify = client.post(
        "/api/v2/evidence/export/verify",
        json={
            "tx_id": bundle["tx_id"],
            "content_hash": bundle["integrity"]["content_hash"],
            "signature": bundle["integrity"]["signature"],
        },
    )

    assert verify.status_code == 200
    body = verify.json()
    assert body["valid"] is True
    assert "verified" in body["message"].lower()
