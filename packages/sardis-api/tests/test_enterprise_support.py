from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.repositories.enterprise_support_repository import EnterpriseSupportRepository
from sardis_api.routers.enterprise_support import (
    EnterpriseSupportDependencies,
    get_deps,
    router,
)


def _admin_principal() -> Principal:
    return Principal(kind="api_key", organization_id="org_demo", scopes=["*"], api_key=None)


def _viewer_principal() -> Principal:
    return Principal(kind="api_key", organization_id="org_demo", scopes=["read"], api_key=None)


def _build_app(*, deps: EnterpriseSupportDependencies, principal_fn) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: deps
    app.dependency_overrides[require_principal] = principal_fn
    app.include_router(router)
    return app


def test_support_profile_and_ticket_lifecycle(monkeypatch):
    monkeypatch.setenv(
        "SARDIS_ENTERPRISE_ORG_PLAN_OVERRIDES_JSON",
        '{"org_demo":"enterprise"}',
    )
    repo = EnterpriseSupportRepository(dsn=None)
    deps = EnterpriseSupportDependencies(support_repo=repo)
    app = _build_app(deps=deps, principal_fn=_admin_principal)
    client = TestClient(app)

    profile = client.get("/api/v2/enterprise/support/profile")
    assert profile.status_code == 200
    assert profile.json()["plan"] == "enterprise"
    assert profile.json()["first_response_sla_minutes"] <= 30

    created = client.post(
        "/api/v2/enterprise/support/tickets",
        json={
            "subject": "Payment rail outage",
            "description": "Turnkey signer path is failing intermittently.",
            "priority": "high",
            "category": "infrastructure",
            "metadata": {"impact": "payment_execution"},
        },
    )
    assert created.status_code == 201
    ticket = created.json()
    assert ticket["status"] == "open"
    assert ticket["priority"] == "high"
    assert ticket["response_sla_breached"] is False
    assert ticket["resolution_sla_breached"] is False
    ticket_id = ticket["id"]

    listed = client.get("/api/v2/enterprise/support/tickets?status_filter=open")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    ack = client.post(f"/api/v2/enterprise/support/tickets/{ticket_id}/acknowledge")
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"
    assert ack.json()["acknowledged_at"] is not None

    resolved = client.post(
        f"/api/v2/enterprise/support/tickets/{ticket_id}/resolve",
        json={"resolution_note": "Failover switched to Fireblocks path"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] is not None


def test_support_write_scope_required():
    repo = EnterpriseSupportRepository(dsn=None)
    deps = EnterpriseSupportDependencies(support_repo=repo)
    app = _build_app(deps=deps, principal_fn=_viewer_principal)
    client = TestClient(app)

    created = client.post(
        "/api/v2/enterprise/support/tickets",
        json={
            "subject": "Need invoice clarification",
            "description": "Please confirm monthly settlement timing.",
            "priority": "low",
            "category": "payments",
        },
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    ack = client.post(f"/api/v2/enterprise/support/tickets/{ticket_id}/acknowledge")
    assert ack.status_code == 403
    assert ack.json()["detail"] == "support_write_scope_required"

