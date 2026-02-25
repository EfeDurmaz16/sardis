from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_admin_principal, require_principal
from sardis_api.routers.compliance import ComplianceDependencies, get_deps, router


class _MockProvider:
    pass


class _KYCService:
    def __init__(self):
        self._provider = _MockProvider()
        self._require_kyc_above = 100_000


class _SanctionsService:
    def __init__(self):
        self._provider = _MockProvider()
        self._cache_ttl = 3600


@dataclass
class _AuditEntry:
    audit_id: str
    mandate_id: str

    def to_dict(self):
        return {
            "audit_id": self.audit_id,
            "mandate_id": self.mandate_id,
            "subject": "agent_1",
            "allowed": True,
            "reason": "ok",
            "rule_id": "rule_1",
            "provider": "policy_engine",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }


class _AuditStoreWithChain:
    def __init__(self):
        self._entries = [
            _AuditEntry(audit_id="a1", mandate_id="m1"),
            _AuditEntry(audit_id="a2", mandate_id="m1"),
            _AuditEntry(audit_id="a3", mandate_id="m2"),
        ]

    def get_by_mandate(self, mandate_id: str):
        return [e for e in self._entries if e.mandate_id == mandate_id]

    def get_recent(self, limit: int):
        return self._entries[-limit:]

    def count(self):
        return len(self._entries)

    def verify_chain_integrity(self):
        return True, None


class _AuditStoreNoChain:
    def __init__(self):
        self._entries = [_AuditEntry(audit_id="a1", mandate_id="m1")]

    def get_by_mandate(self, mandate_id: str):
        return [e for e in self._entries if e.mandate_id == mandate_id]

    def get_recent(self, limit: int):
        return self._entries[-limit:]

    def count(self):
        return len(self._entries)


def _admin_principal() -> Principal:
    return Principal(kind="api_key", organization_id="org_demo", scopes=["*"])


def _build_client(audit_store) -> TestClient:
    app = FastAPI()
    deps = ComplianceDependencies(
        kyc_service=_KYCService(),
        sanctions_service=_SanctionsService(),
        audit_store=audit_store,
    )
    app.dependency_overrides[get_deps] = lambda: deps
    app.dependency_overrides[require_principal] = _admin_principal
    app.dependency_overrides[require_admin_principal] = _admin_principal
    app.include_router(router, prefix="/api/v2/compliance")
    return TestClient(app)


def test_mandate_audit_trail_includes_deterministic_digest():
    client = _build_client(_AuditStoreWithChain())

    response = client.get("/api/v2/compliance/audit/mandate/m1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mandate_id"] == "m1"
    assert payload["count"] == 2
    assert payload["entries_digest"].startswith("sha256:")
    assert len(payload["entries"]) == 2


def test_recent_audit_trail_respects_limit():
    client = _build_client(_AuditStoreWithChain())

    response = client.get("/api/v2/compliance/audit/recent", params={"limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["entries_digest"].startswith("sha256:")


def test_verify_chain_integrity_supported_store():
    client = _build_client(_AuditStoreWithChain())

    response = client.get("/api/v2/compliance/audit/verify-chain")

    assert response.status_code == 200
    payload = response.json()
    assert payload["supported"] is True
    assert payload["verified"] is True
    assert payload["entry_count"] == 3


def test_verify_chain_integrity_unsupported_store():
    client = _build_client(_AuditStoreNoChain())

    response = client.get("/api/v2/compliance/audit/verify-chain")

    assert response.status_code == 200
    payload = response.json()
    assert payload["supported"] is False
    assert payload["verified"] is None
    assert payload["error"] == "chain_verification_not_supported_by_store"
