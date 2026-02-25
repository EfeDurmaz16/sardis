from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_admin_principal, require_principal
from sardis_api.routers.compliance import ComplianceDependencies, get_deps, router
from sardis_compliance import create_kya_service


class _KYCService:
    pass


class _SanctionsService:
    pass


def _admin_principal() -> Principal:
    return Principal(kind="api_key", organization_id="org_demo", scopes=["*"])


def _build_client() -> TestClient:
    app = FastAPI()
    deps = ComplianceDependencies(
        kyc_service=_KYCService(),
        sanctions_service=_SanctionsService(),
        audit_store=None,
        kya_service=create_kya_service(liveness_timeout=5),
    )
    app.dependency_overrides[get_deps] = lambda: deps
    app.dependency_overrides[require_principal] = _admin_principal
    app.dependency_overrides[require_admin_principal] = _admin_principal
    app.include_router(router, prefix="/api/v2/compliance")
    return TestClient(app)


def test_kya_register_and_status_roundtrip():
    client = _build_client()

    register = client.post(
        "/api/v2/compliance/kya/register",
        json={
            "agent_id": "agent_1",
            "owner_id": "org_1",
            "capabilities": ["payments"],
            "max_budget_per_tx": "75.00",
            "daily_budget": "300.00",
            "allowed_domains": ["example.com"],
        },
    )
    assert register.status_code == 200
    assert register.json()["allowed"] is True
    assert register.json()["reason"] == "registered"

    status_resp = client.get("/api/v2/compliance/kya/agent_1")
    assert status_resp.status_code == 200
    payload = status_resp.json()
    assert payload["agent_id"] == "agent_1"
    assert payload["owner_id"] == "org_1"
    assert payload["level"] == "basic"
    assert payload["status"] == "active"


def test_kya_check_denies_unregistered_agent():
    client = _build_client()

    check = client.post(
        "/api/v2/compliance/kya/missing_agent/check",
        json={"amount": "1.00", "merchant_id": "0xmerchant"},
    )

    assert check.status_code == 200
    payload = check.json()
    assert payload["allowed"] is False
    assert payload["reason"] == "agent_not_registered"


def test_kya_upgrade_verified_requires_anchor():
    client = _build_client()
    client.post(
        "/api/v2/compliance/kya/register",
        json={"agent_id": "agent_2", "owner_id": "org_2"},
    )

    upgrade = client.post(
        "/api/v2/compliance/kya/agent_2/upgrade",
        json={"target_level": "verified"},
    )

    assert upgrade.status_code == 200
    payload = upgrade.json()
    assert payload["allowed"] is False
    assert "anchor_verification_required" in (payload.get("reason") or "")


def test_kya_upgrade_verified_with_anchor_succeeds():
    client = _build_client()
    client.post(
        "/api/v2/compliance/kya/register",
        json={"agent_id": "agent_3", "owner_id": "org_3"},
    )

    upgrade = client.post(
        "/api/v2/compliance/kya/agent_3/upgrade",
        json={
            "target_level": "verified",
            "anchor_verification_id": "inquiry_123",
        },
    )

    assert upgrade.status_code == 200
    payload = upgrade.json()
    assert payload["allowed"] is True
    assert payload["level"] == "verified"


def test_kya_suspend_and_reactivate_flow():
    client = _build_client()
    client.post(
        "/api/v2/compliance/kya/register",
        json={"agent_id": "agent_4", "owner_id": "org_4"},
    )

    suspended = client.post(
        "/api/v2/compliance/kya/agent_4/suspend",
        json={"reason": "manual_review"},
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    reactivated = client.post("/api/v2/compliance/kya/agent_4/reactivate")
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"


def test_kya_heartbeat_reports_alive():
    client = _build_client()
    client.post(
        "/api/v2/compliance/kya/register",
        json={"agent_id": "agent_5", "owner_id": "org_5"},
    )

    heartbeat = client.post("/api/v2/compliance/kya/agent_5/heartbeat")
    assert heartbeat.status_code == 200
    payload = heartbeat.json()
    assert payload["agent_id"] == "agent_5"
    assert payload["is_alive"] is True
