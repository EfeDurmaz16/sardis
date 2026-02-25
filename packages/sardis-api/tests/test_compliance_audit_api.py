from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

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
        metadata = {}
        if self.audit_id == "a1":
            metadata = {
                "policy_hash": "sha256:policy",
                "audit_anchor": "anchor_1",
                "decision_id": "decision_1",
                "approval_id": "appr_demo_1",
            }
        elif self.audit_id == "a2":
            metadata = {"approval_id": "appr_demo_1"}
        evaluated_at = {
            "a1": "2026-02-24T10:00:00+00:00",
            "a2": "2026-02-25T10:00:00+00:00",
            "a3": "2026-02-26T10:00:00+00:00",
        }.get(self.audit_id, datetime.now(timezone.utc).isoformat())
        return {
            "audit_id": self.audit_id,
            "mandate_id": self.mandate_id,
            "subject": "agent_1",
            "allowed": True,
            "reason": "ok",
            "rule_id": "rule_1",
            "provider": "policy_engine",
            "evaluated_at": evaluated_at,
            "metadata": metadata,
        }


class _ApprovalService:
    async def get_approval(self, approval_id: str):
        if approval_id != "appr_demo_1":
            return None
        return SimpleNamespace(
            id=approval_id,
            status="approved",
            action="onchain_payment",
            requested_by="agent_1",
            reviewed_by="ops@sardis.sh",
            amount="42.00",
        )


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


def _build_client(audit_store, approval_service=None) -> TestClient:
    app = FastAPI()
    deps = ComplianceDependencies(
        kyc_service=_KYCService(),
        sanctions_service=_SanctionsService(),
        audit_store=audit_store,
        approval_service=approval_service,
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


def test_mandate_audit_proof_returns_merkle_proof():
    client = _build_client(_AuditStoreWithChain())

    response = client.get("/api/v2/compliance/audit/mandate/m1/proof/a2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mandate_id"] == "m1"
    assert payload["audit_id"] == "a2"
    assert payload["leaf_hash"]
    assert payload["merkle_root"].startswith("merkle::")
    assert payload["proof_verified"] is True
    assert payload["entry_count"] == 2


def test_mandate_audit_proof_missing_entry_returns_404():
    client = _build_client(_AuditStoreWithChain())

    response = client.get("/api/v2/compliance/audit/mandate/m1/proof/unknown_audit")

    assert response.status_code == 404
    assert response.json()["detail"] == "audit_id_not_found_for_mandate"


def test_export_evidence_bundle_contains_integrity_and_artifacts():
    client = _build_client(_AuditStoreWithChain(), approval_service=_ApprovalService())

    response = client.get(
        "/api/v2/compliance/audit/evidence/export",
        params={"mandate_id": "m1", "approval_id": "appr_demo_1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["counts"]["total_entries"] == 2
    assert payload["metadata"]["counts"]["policy_entries"] == 2
    assert payload["metadata"]["counts"]["approval_related_entries"] == 2
    assert payload["metadata"]["counts"]["attestation_entries"] >= 1
    assert payload["integrity"]["bundle_digest"].startswith("sha256:")
    assert payload["integrity"]["entries_digest"].startswith("sha256:")
    assert payload["integrity"]["merkle_root"].startswith("merkle::")
    assert payload["integrity"]["hash_chain"]["length"] == 2
    assert payload["integrity"]["chain_verification"]["supported_by_store"] is True
    assert payload["integrity"]["chain_verification"]["verified"] is True
    assert payload["artifacts"]["approval"]["id"] == "appr_demo_1"


def test_export_evidence_bundle_requires_selector():
    client = _build_client(_AuditStoreWithChain())
    response = client.get("/api/v2/compliance/audit/evidence/export")
    assert response.status_code == 400
    assert response.json()["detail"] == "mandate_id_or_approval_id_required"


def test_export_evidence_bundle_supports_time_window_filter():
    client = _build_client(_AuditStoreWithChain(), approval_service=_ApprovalService())
    response = client.get(
        "/api/v2/compliance/audit/evidence/export",
        params={
            "mandate_id": "m1",
            "approval_id": "appr_demo_1",
            "start_at": "2026-02-25T00:00:00+00:00",
            "end_at": "2026-02-25T23:59:59+00:00",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["counts"]["total_entries"] == 1
    assert payload["metadata"]["scope"]["start_at"] == "2026-02-25T00:00:00+00:00"
    assert payload["metadata"]["scope"]["end_at"] == "2026-02-25T23:59:59+00:00"
