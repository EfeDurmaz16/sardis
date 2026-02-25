from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers import a2a


class _AgentRepo:
    def __init__(self) -> None:
        self._items = {
            "agent_a": SimpleNamespace(
                agent_id="agent_a",
                owner_id="org_demo",
                is_active=True,
                wallet_id="wallet_a",
                kya_level="verified",
                kya_status="active",
            ),
            "agent_b": SimpleNamespace(
                agent_id="agent_b",
                owner_id="org_demo",
                is_active=True,
                wallet_id="wallet_b",
                kya_level="basic",
                kya_status="active",
            ),
            "agent_c": SimpleNamespace(
                agent_id="agent_c",
                owner_id="org_demo",
                is_active=False,
                wallet_id=None,
                kya_level="none",
                kya_status="pending",
            ),
            "agent_external": SimpleNamespace(
                agent_id="agent_external",
                owner_id="org_other",
                is_active=True,
                wallet_id="wallet_external",
                kya_level="verified",
                kya_status="active",
            ),
        }

    async def get(self, agent_id: str):
        return self._items.get(agent_id)

    async def list(self, owner_id=None, is_active=None, limit=50, offset=0):
        items = list(self._items.values())
        if owner_id is not None:
            items = [item for item in items if item.owner_id == owner_id]
        if is_active is not None:
            items = [item for item in items if bool(item.is_active) == bool(is_active)]
        return items[offset : offset + limit]


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


class _AuditStore:
    def __init__(self) -> None:
        self.entries = []

    def append(self, entry):
        self.entries.append(entry)
        return entry.audit_id

    def get_recent(self, limit=100):
        return self.entries[-limit:]


class _ApprovalService:
    def __init__(self) -> None:
        self.items = {}

    def add(
        self,
        approval_id: str,
        *,
        status: str = "approved",
        reviewed_by: str = "reviewer@sardis.sh",
        organization_id: str = "org_demo",
        action: str = "a2a_trust_mutation",
        metadata: dict | None = None,
    ) -> None:
        self.items[approval_id] = SimpleNamespace(
            id=approval_id,
            status=status,
            reviewed_by=reviewed_by,
            organization_id=organization_id,
            action=action,
            metadata=metadata or {},
        )

    async def get_approval(self, approval_id: str):
        return self.items.get(approval_id)


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


def _build_app(*, admin: bool, trust_repo=None, audit_store=None, approval_service=None) -> FastAPI:
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
        audit_store=audit_store,
        approval_service=approval_service,
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
    assert payload["table_hash"]


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
    assert payload["table_hash"]


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
    assert payload["table_hash"]


def test_admin_can_upsert_and_delete_trust_relations_with_repository(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    trust_repo = _TrustRepo()
    audit_store = _AuditStore()
    client = TestClient(_build_app(admin=True, trust_repo=trust_repo, audit_store=audit_store))

    upserted = client.post(
        "/api/v2/a2a/trust/relations",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_new", "metadata": {"reason": "ops"}},
    )
    assert upserted.status_code == 200
    upserted_payload = upserted.json()
    assert "agent_new" in upserted_payload["relations"]["agent_a"]
    assert upserted_payload["table_hash"]
    assert upserted_payload["audit_id"]

    deleted = client.request(
        "DELETE",
        "/api/v2/a2a/trust/relations",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_new"},
    )
    assert deleted.status_code == 200
    deleted_payload = deleted.json()
    assert "agent_new" not in deleted_payload["relations"]["agent_a"]
    assert deleted_payload["table_hash"]
    assert deleted_payload["audit_id"]
    assert len(audit_store.entries) == 2
    assert audit_store.entries[0].provider == "a2a_trust"
    assert audit_store.entries[0].reason == "upsert_relation_applied"
    assert audit_store.entries[1].reason == "delete_relation_applied"


def test_trust_peers_returns_only_trusted_by_default(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "agent_a>agent_b")
    client = TestClient(_build_app(admin=False))

    response = client.get("/api/v2/a2a/trust/peers", params={"sender_agent_id": "agent_a"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["sender_agent_id"] == "agent_a"
    assert payload["source"] == "env"
    assert payload["total_candidates"] == 1
    assert payload["trusted_count"] == 1
    assert [item["agent_id"] for item in payload["peers"]] == ["agent_b"]
    assert payload["peers"][0]["trusted"] is True
    assert payload["peers"][0]["wallet_id"] == "wallet_b"
    assert payload["table_hash"]


def test_trust_peers_can_include_untrusted_and_inactive(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATIONS", "agent_a>agent_b")
    client = TestClient(_build_app(admin=False))

    response = client.get(
        "/api/v2/a2a/trust/peers",
        params={
            "sender_agent_id": "agent_a",
            "include_untrusted": "true",
            "include_inactive": "true",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    peers = {item["agent_id"]: item for item in payload["peers"]}
    assert payload["total_candidates"] == 2
    assert payload["trusted_count"] == 1
    assert peers["agent_b"]["trusted"] is True
    assert peers["agent_c"]["trusted"] is False
    assert peers["agent_c"]["trust_reason"] == "a2a_agent_not_trusted"


def test_trust_peers_rejects_non_admin_cross_org_sender(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    client = TestClient(_build_app(admin=False))

    response = client.get("/api/v2/a2a/trust/peers", params={"sender_agent_id": "agent_external"})
    assert response.status_code == 403
    assert response.json()["detail"] == "access_denied"


def test_admin_can_list_recent_a2a_trust_audit_entries(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    trust_repo = _TrustRepo()
    audit_store = _AuditStore()
    client = TestClient(_build_app(admin=True, trust_repo=trust_repo, audit_store=audit_store))

    client.post(
        "/api/v2/a2a/trust/relations",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_new", "metadata": {"reason": "ops"}},
    )
    client.request(
        "DELETE",
        "/api/v2/a2a/trust/relations",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_new"},
    )

    response = client.get("/api/v2/a2a/trust/audit/recent", params={"limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["organization_id"] == "org_demo"
    assert payload["count"] == 2
    assert payload["entries"][0]["provider"] == "a2a_trust"
    assert payload["entries"][0]["metadata"]["organization_id"] == "org_demo"
    assert payload["entries"][0]["proof_path"].startswith("/api/v2/compliance/audit/mandate/")


def test_trust_relation_mutation_requires_approval_when_enabled(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATION_MUTATION_REQUIRE_APPROVAL", "1")
    trust_repo = _TrustRepo()
    client = TestClient(_build_app(admin=True, trust_repo=trust_repo))

    response = client.post(
        "/api/v2/a2a/trust/relations",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_new"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "approval_required"


def test_trust_relation_mutation_accepts_valid_approval(monkeypatch):
    monkeypatch.setenv("SARDIS_A2A_ENFORCE_TRUST_TABLE", "1")
    monkeypatch.setenv("SARDIS_A2A_TRUST_RELATION_MUTATION_REQUIRE_APPROVAL", "1")
    trust_repo = _TrustRepo()
    approval_service = _ApprovalService()
    approval_service.add(
        "appr_trust_1",
        metadata={
            "operation": "upsert_relation",
            "sender_agent_id": "agent_a",
            "recipient_agent_id": "agent_new",
            "organization_id": "org_demo",
        },
    )
    client = TestClient(_build_app(admin=True, trust_repo=trust_repo, approval_service=approval_service))

    response = client.post(
        "/api/v2/a2a/trust/relations",
        json={"sender_agent_id": "agent_a", "recipient_agent_id": "agent_new", "approval_id": "appr_trust_1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["approval_id"] == "appr_trust_1"
    assert "agent_new" in payload["relations"]["agent_a"]
