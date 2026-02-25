from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers import a2a


class _AgentRepo:
    def __init__(self) -> None:
        self._items = {
            "agent_a": SimpleNamespace(agent_id="agent_a", owner_id="org_demo", is_active=True),
            "agent_b": SimpleNamespace(agent_id="agent_b", owner_id="org_demo", is_active=True),
            "agent_external": SimpleNamespace(agent_id="agent_external", owner_id="org_other", is_active=True),
        }

    async def get(self, agent_id: str):
        return self._items.get(agent_id)


class _WalletRepo:
    async def get_by_agent(self, agent_id: str):
        return None


class _TrustRepo:
    def __init__(self) -> None:
        self.table: dict[str, dict[str, set[str]]] = {
            "org_demo": {"agent_a": {"agent_repo"}},
        }

    async def get_trust_table(self, organization_id: str):
        return self.table.get(organization_id, {})

    async def upsert_relation(self, *, organization_id: str, sender_agent_id: str, recipient_agent_id: str, metadata=None):
        _ = metadata
        self.table.setdefault(organization_id, {}).setdefault(sender_agent_id, set()).add(recipient_agent_id)
        return {"ok": True}

    async def delete_relation(self, *, organization_id: str, sender_agent_id: str, recipient_agent_id: str):
        org_table = self.table.setdefault(organization_id, {})
        recipients = org_table.setdefault(sender_agent_id, set())
        if recipient_agent_id in recipients:
            recipients.remove(recipient_agent_id)
            if not recipients:
                org_table.pop(sender_agent_id, None)
            return True
        return False


def _principal_admin() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _principal_member() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["read"],
        api_key=None,
    )


def _build_app(*, admin: bool, trust_repo=None) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal_admin if admin else _principal_member
    app.dependency_overrides[a2a.get_deps] = lambda: a2a.A2ADependencies(
        wallet_repo=_WalletRepo(),
        agent_repo=_AgentRepo(),
        chain_executor=None,
        wallet_manager=None,
        ledger=None,
        compliance=None,
        identity_registry=None,
        trust_repo=trust_repo,
    )
    app.include_router(a2a.router, prefix="/api/v2/a2a")
    return app


def test_admin_can_view_a2a_trust_table(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "agent_a>agent_b|agent_ops")
    client = TestClient(_build_app(admin=True))

    response = client.get("/api/v2/a2a/trust/table")
    assert response.status_code == 200
    payload = response.json()
    assert payload["enforced"] is True
    assert payload["relations"]["agent_a"] == ["agent_b", "agent_ops"]
    assert payload["source"] == "env"


def test_non_admin_cannot_view_a2a_trust_table():
    client = TestClient(_build_app(admin=False))
    response = client.get("/api/v2/a2a/trust/table")
    assert response.status_code == 403
    assert response.json()["detail"] == "admin_required"


def test_non_admin_can_check_trust_for_own_org_agents(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "agent_a>agent_b")
    client = TestClient(_build_app(admin=False))

    response = client.post(
        "/api/v2/a2a/trust/check",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_b"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["allowed"] is True
    assert payload["reason"] == "trusted_sender_relation"
    assert payload["source"] == "env"


def test_non_admin_trust_check_rejects_cross_org_agents(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "agent_a>agent_external")
    client = TestClient(_build_app(admin=False))

    response = client.post(
        "/api/v2/a2a/trust/check",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_external"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "access_denied"


def test_admin_trust_table_prefers_repository_when_available(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "agent_a>agent_env")
    trust_repo = _TrustRepo()
    client = TestClient(_build_app(admin=True, trust_repo=trust_repo))

    response = client.get("/api/v2/a2a/trust/table")
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "repository"
    assert payload["relations"]["agent_a"] == ["agent_repo"]


def test_admin_can_upsert_and_delete_trust_relations_with_repository(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    trust_repo = _TrustRepo()
    client = TestClient(_build_app(admin=True, trust_repo=trust_repo))

    upserted = client.post(
        "/api/v2/a2a/trust/relations",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_new", "metadata": {"reason": "ops"}},
    )
    assert upserted.status_code == 200
    upserted_payload = upserted.json()
    assert "agent_new" in upserted_payload["relations"]["agent_a"]

    deleted = client.request(
        "DELETE",
        "/api/v2/a2a/trust/relations",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_new"},
    )
    assert deleted.status_code == 200
    deleted_payload = deleted.json()
    assert "agent_new" not in deleted_payload["relations"]["agent_a"]
