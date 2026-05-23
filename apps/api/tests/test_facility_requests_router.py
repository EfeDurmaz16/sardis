from __future__ import annotations

import asyncio
import hmac
import json
from decimal import Decimal
from hashlib import sha256

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis.core.facility_gate import Facility, FacilityLimit, SimulatedFacilityAdapter
from sardis.core.spending_mandate import SpendingMandate

from server.authz import Principal, require_principal
from server.repositories.facility_gate_repository import FacilityGateRepository
from server.routes.authority import facility_requests
from server.services.facility_gate_authority import (
    InMemoryFacilityMandateResolver,
    RepositoryBackedFacilityMandateResolver,
    RepositoryBackedFacilityPolicyResolver,
    RepositoryBackedFacilityRecordResolver,
)


def _client(
    monkeypatch,
    enabled: bool = True,
    scopes: list[str] | None = None,
    organization_id: str = "org_test",
    org_allowlist: str | None = None,
) -> TestClient:
    if enabled:
        monkeypatch.setenv("SARDIS_FACILITY_GATE_ENABLED", "true")
    else:
        monkeypatch.delenv("SARDIS_FACILITY_GATE_ENABLED", raising=False)
    if org_allowlist is None:
        monkeypatch.delenv("SARDIS_FACILITY_GATE_ORG_ALLOWLIST", raising=False)
    else:
        monkeypatch.setenv("SARDIS_FACILITY_GATE_ORG_ALLOWLIST", org_allowlist)
    app = FastAPI()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id=organization_id,
        scopes=scopes or ["*"],
    )
    repo = FacilityGateRepository(dsn="memory://")
    adapter = SimulatedFacilityAdapter()
    app.dependency_overrides[facility_requests.get_deps] = lambda: facility_requests.FacilityDependencies(
        repository=repo,
        adapter=adapter,
    )
    app.include_router(facility_requests.router, prefix="/api/v2/facility-requests")
    app.include_router(facility_requests.provider_webhooks_router, prefix="/api/v2/provider-webhooks")
    return TestClient(app)


class FailingExecuteAdapter(SimulatedFacilityAdapter):
    async def execute_authorization(self, *, request, decision):  # type: ignore[no-untyped-def]
        raise RuntimeError("provider timeout")


class FailingRevokeAdapter(SimulatedFacilityAdapter):
    async def revoke_authorization(self, authorization_id: str, reason: str) -> bool:
        raise RuntimeError("provider revoke timeout")


def _client_with_adapter(monkeypatch, adapter, enabled: bool = True) -> TestClient:
    if enabled:
        monkeypatch.setenv("SARDIS_FACILITY_GATE_ENABLED", "true")
    else:
        monkeypatch.delenv("SARDIS_FACILITY_GATE_ENABLED", raising=False)
    app = FastAPI()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_test",
        scopes=["*"],
    )
    repo = FacilityGateRepository(dsn="memory://")
    app.dependency_overrides[facility_requests.get_deps] = lambda: facility_requests.FacilityDependencies(
        repository=repo,
        adapter=adapter,
    )
    app.include_router(facility_requests.router, prefix="/api/v2/facility-requests")
    return TestClient(app)


class FakeApproval:
    id = "appr_facility_1"
    status = "pending"


class FakeApprovalService:
    def __init__(self) -> None:
        self.requests = []

    async def create_approval(self, **kwargs):  # type: ignore[no-untyped-def]
        self.requests.append(kwargs)
        return FakeApproval()


class FailingApprovalService:
    async def create_approval(self, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("approval service unavailable")


def _client_with_approval_service(monkeypatch, approval_service) -> TestClient:
    monkeypatch.setenv("SARDIS_FACILITY_GATE_ENABLED", "true")
    app = FastAPI()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_test",
        scopes=["*"],
    )
    repo = FacilityGateRepository(dsn="memory://")
    adapter = SimulatedFacilityAdapter()
    app.dependency_overrides[facility_requests.get_deps] = lambda: facility_requests.FacilityDependencies(
        repository=repo,
        adapter=adapter,
        approval_service=approval_service,
    )
    app.include_router(facility_requests.router, prefix="/api/v2/facility-requests")
    return TestClient(app)


def _client_with_persisted_authority(monkeypatch) -> TestClient:
    monkeypatch.setenv("SARDIS_FACILITY_GATE_ENABLED", "true")
    monkeypatch.setenv("SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY", "true")
    app = FastAPI()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_test",
        scopes=["*"],
    )
    repo = FacilityGateRepository(dsn="memory://")
    asyncio.run(
        repo.upsert_facility_record(
            Facility(
                facility_id="fac_1",
                organization_id="org_test",
                sponsor_id="sponsor_1",
                limit=FacilityLimit(per_transaction_minor=500_000, currency="USD"),
                allowed_categories=["cloud"],
                approval_threshold_minor=100_000,
                version=2,
            )
        )
    )
    asyncio.run(
        repo.upsert_facility_policy_record(
            organization_id="org_test",
            facility_id="fac_1",
            policy_version="facility_policy_persisted_v1",
            snapshot={
                "allowed_categories": ["cloud"],
                "approval_threshold_minor": 100_000,
                "per_transaction_minor": 500_000,
                "currency": "USD",
            },
            created_by="test",
        )
    )
    asyncio.run(
        repo.upsert_facility_mandate_record(
            SpendingMandate(
                principal_id="principal_1",
                issuer_id="principal_1",
                org_id="org_test",
                agent_id="agent_1",
                id="mandate_1",
                amount_per_tx=Decimal("5000"),
                currency="USD",
                allowed_rails=["simulated_card"],
                facility_authority_allowed=True,
                allowed_facility_ids=["fac_1"],
                facility_max_draw=Decimal("5000"),
                facility_scope={"allowed_categories": ["cloud"]},
                version=5,
            ),
            created_by="test",
        )
    )
    mandate_resolver = InMemoryFacilityMandateResolver()
    mandate_resolver.register_mandate(
        SpendingMandate(
            principal_id="principal_1",
            issuer_id="principal_1",
            org_id="org_test",
            agent_id="agent_1",
            id="mandate_1",
            amount_per_tx=Decimal("5000"),
            currency="USD",
            allowed_rails=["simulated_card"],
            facility_authority_allowed=True,
            allowed_facility_ids=["fac_1"],
            facility_max_draw=Decimal("5000"),
            facility_scope={"allowed_categories": ["cloud"]},
            version=5,
        )
    )
    app.dependency_overrides[facility_requests.get_deps] = lambda: facility_requests.FacilityDependencies(
        repository=repo,
        adapter=SimulatedFacilityAdapter(),
        mandate_resolver=RepositoryBackedFacilityMandateResolver(repo, fallback=mandate_resolver),
        facility_resolver=RepositoryBackedFacilityRecordResolver(repo),
        policy_resolver=RepositoryBackedFacilityPolicyResolver(repo),
    )
    app.include_router(facility_requests.router, prefix="/api/v2/facility-requests")
    return TestClient(app)


def _client_with_repository_authority(monkeypatch) -> TestClient:
    monkeypatch.setenv("SARDIS_FACILITY_GATE_ENABLED", "true")
    app = FastAPI()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_test",
        scopes=["facility:admin", "facility:write", "facility:read"],
    )
    repo = FacilityGateRepository(dsn="memory://")
    app.dependency_overrides[facility_requests.get_deps] = lambda: facility_requests.FacilityDependencies(
        repository=repo,
        adapter=SimulatedFacilityAdapter(),
        mandate_resolver=RepositoryBackedFacilityMandateResolver(repo),
        facility_resolver=RepositoryBackedFacilityRecordResolver(repo),
        policy_resolver=RepositoryBackedFacilityPolicyResolver(repo),
    )
    app.include_router(facility_requests.router, prefix="/api/v2/facility-requests")
    return TestClient(app)


def _provider_webhook_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("SARDIS_FACILITY_GATE_ENABLED", "true")
    monkeypatch.setenv("SARDIS_FACILITY_PROVIDER_WEBHOOKS_ENABLED", "true")
    monkeypatch.setenv("SARDIS_FACILITY_PROVIDER_WEBHOOK_SECRET", "test_secret")
    app = FastAPI()
    repo = FacilityGateRepository(dsn="memory://")
    adapter = SimulatedFacilityAdapter()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_test",
        scopes=["*"],
    )
    app.dependency_overrides[facility_requests.get_deps] = lambda: facility_requests.FacilityDependencies(
        repository=repo,
        adapter=adapter,
    )
    app.include_router(facility_requests.router, prefix="/api/v2/facility-requests")
    app.include_router(facility_requests.provider_webhooks_router, prefix="/api/v2/provider-webhooks")
    return TestClient(app)


def _request_payload(amount_minor: int = 75_000, evidence: bool = True) -> dict:
    payload = {
        "agent_id": "agent_1",
        "sponsor_id": "sponsor_1",
        "facility_id": "fac_1",
        "mandate_id": "mandate_1",
        "merchant": "aws.amazon.com",
        "amount_minor": amount_minor,
        "currency": "USD",
        "category": "cloud",
        "purpose": "cloud infrastructure",
        "task_graph_hash": "sha256:task",
        "mandate_snapshot": {
            "principal_id": "principal_1",
            "issuer_id": "principal_1",
            "agent_id": "agent_1",
            "id": "mandate_1",
            "amount_per_tx": "5000",
            "currency": "USD",
            "allowed_rails": ["simulated_card"],
            "facility_authority_allowed": True,
            "allowed_facility_ids": ["fac_1"],
            "facility_max_draw": "5000",
            "facility_scope": {"allowed_categories": ["cloud"]},
        },
        "facility_snapshot": {
            "provider": "simulated",
            "approval_threshold_minor": 100_000,
            "limit": {"per_transaction_minor": 500_000, "currency": "USD"},
            "allowed_categories": ["cloud"],
        },
        "idempotency_key": "idem_create_1",
    }
    if evidence:
        payload["evidence"] = [
            {"evidence_type": "invoice", "content_hash": "sha256:invoice", "uri": "s3://invoice"}
        ]
    return payload


def test_facility_gate_is_feature_flagged(monkeypatch) -> None:
    with _client(monkeypatch, enabled=False) as client:
        response = client.post("/api/v2/facility-requests", json=_request_payload())

    assert response.status_code == 404
    assert "Facility Gate is disabled" in response.json()["detail"]


def test_facility_gate_org_allowlist_permits_enabled_org(monkeypatch) -> None:
    with _client(monkeypatch, org_allowlist="org_test,org_other") as client:
        response = client.get("/api/v2/facility-requests")

    assert response.status_code == 200, response.text
    assert response.json() == {"requests": [], "total": 0}


def test_facility_gate_org_allowlist_blocks_unlisted_org(monkeypatch) -> None:
    with _client(monkeypatch, org_allowlist="org_other") as client:
        response = client.get("/api/v2/facility-requests")

    assert response.status_code == 404
    assert "organization" in response.json()["detail"]


def test_facility_gate_org_allowlist_allows_wildcard(monkeypatch) -> None:
    with _client(monkeypatch, organization_id="org_unlisted", org_allowlist="*") as client:
        response = client.get("/api/v2/facility-requests")

    assert response.status_code == 200, response.text


def test_facility_request_authorize_execute_and_audit(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=_request_payload())
        assert created.status_code == 201, created.text
        request_id = created.json()["request_id"]

        duplicate = client.post("/api/v2/facility-requests", json=_request_payload())
        assert duplicate.status_code == 201, duplicate.text
        assert duplicate.json()["duplicate"] is True
        assert duplicate.json()["request_id"] == request_id

        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert decision.status_code == 200, decision.text
        body = decision.json()
        assert body["verdict"] == "approved"
        assert body["liability"]["repayment_obligor"] == "sponsor_1"
        assert body["risk"]["model_version"] == "facility_gate_rules_v0"

        execution = client.post(f"/api/v2/facility-requests/{request_id}/execute")
        assert execution.status_code == 200, execution.text
        assert execution.json()["credential"]["provider"] == "simulated"

        audit = client.get(f"/api/v2/facility-requests/{request_id}/audit")
        assert audit.status_code == 200, audit.text
        audit_body = audit.json()
        assert audit_body["latest_decision"]["verdict"] == "approved"
        assert audit_body["latest_decision"]["decision_id"] == body["decision_id"]
        assert audit_body["liability"]["repayment_obligor"] == "sponsor_1"
        assert len(audit_body["events"]) == 3

        export = client.get(f"/api/v2/facility-requests/{request_id}/audit/export")
        assert export.status_code == 200, export.text
        export_body = export.json()
        assert export_body["schema_version"] == "facility_audit_export_v1"
        assert export_body["decision_packet"]["schema_version"] == "facility_decision_packet_v1"
        assert export_body["decision_packet"]["decision_packet_hash"]
        assert export_body["event_hash_chain"]["ok"] is True


def test_facility_authorization_denies_missing_facility_authority(monkeypatch) -> None:
    payload = _request_payload()
    payload["idempotency_key"] = "idem_create_2"
    payload["mandate_snapshot"]["facility_authority_allowed"] = False

    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")

    assert decision.status_code == 200, decision.text
    assert decision.json()["verdict"] == "denied"
    assert "MANDATE_FACILITY_AUTHORITY_REQUIRED" in decision.json()["reason_codes"]


def test_duplicate_authorize_returns_existing_decision(monkeypatch) -> None:
    payload = _request_payload()
    payload["idempotency_key"] = "idem_duplicate_authorize"

    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        first = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        second = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        audit = client.get(f"/api/v2/facility-requests/{request_id}/audit/export")

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["decision_id"] == first.json()["decision_id"]
    assert second.json()["event_id"] == first.json()["event_id"]
    auth_events = [
        event for event in audit.json()["events"]
        if event["event_type"] == "facility.authorization.approved"
    ]
    assert len(auth_events) == 1


def test_repayment_mirror_snapshot_is_audited_and_affects_risk(monkeypatch) -> None:
    payload = _request_payload()
    payload["idempotency_key"] = "idem_repayment_mirror"
    payload["facility_snapshot"]["repayment_mirror"] = {
        "status": "delinquent",
        "source": "provider_snapshot",
        "statement_ref": "stmt_1",
        "days_past_due": 45,
    }

    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        exported = client.get(f"/api/v2/facility-requests/{request_id}/audit/export")

    assert decision.status_code == 200, decision.text
    assert "sponsor_repayment_delinquent" in decision.json()["risk"]["reason_codes"]
    assert exported.json()["decision_packet"]["repayment_mirror"]["status"] == "delinquent"
    assert exported.json()["decision_packet"]["repayment_mirror"]["statement_ref"] == "stmt_1"


def test_revocation_blocks_future_authorization(monkeypatch) -> None:
    payload = _request_payload()
    payload["idempotency_key"] = "idem_create_3"

    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        revoke = client.post(
            "/api/v2/facility-requests/revocations",
            json={"scope": "mandate", "target_id": "mandate_1", "reason": "operator revoked"},
        )
        assert revoke.status_code == 200, revoke.text
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")

    assert decision.status_code == 200, decision.text
    assert decision.json()["verdict"] == "denied"
    assert decision.json()["reason_codes"] == ["operator revoked"]


def test_step_up_can_be_human_approved_and_reauthorized(monkeypatch) -> None:
    payload = _request_payload(amount_minor=240_000, evidence=False)
    payload["idempotency_key"] = "idem_create_4"
    payload["task_graph_hash"] = None

    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]

        first_decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert first_decision.status_code == 200, first_decision.text
        assert first_decision.json()["verdict"] == "step_up_required"

        duplicate_step_up = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert duplicate_step_up.status_code == 200, duplicate_step_up.text
        assert duplicate_step_up.json()["decision_id"] == first_decision.json()["decision_id"]

        queue = client.get("/api/v2/facility-requests/manual-review")
        assert queue.status_code == 200, queue.text
        assert queue.json()["total"] == 1

        approval = client.post(
            f"/api/v2/facility-requests/{request_id}/approval",
            json={"approved": True, "reviewed_by": "finance_admin", "reason": "approved cloud burst"},
        )
        assert approval.status_code == 200, approval.text

        second_decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert second_decision.status_code == 200, second_decision.text
        assert second_decision.json()["verdict"] == "approved"
        assert second_decision.json()["reason_codes"][0] == "human_step_up_approved"
        assert second_decision.json()["decision_id"] != first_decision.json()["decision_id"]


def test_step_up_creates_approval_service_request_when_configured(monkeypatch) -> None:
    payload = _request_payload(amount_minor=240_000, evidence=False)
    payload["idempotency_key"] = "idem_create_approval_service"
    payload["task_graph_hash"] = None
    approval_service = FakeApprovalService()

    with _client_with_approval_service(monkeypatch, approval_service) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        audit = client.get(f"/api/v2/facility-requests/{request_id}/audit/export")

    assert decision.status_code == 200, decision.text
    assert decision.json()["verdict"] == "step_up_required"
    assert approval_service.requests[0]["action"] == "facility_gate.step_up"
    assert approval_service.requests[0]["metadata"]["facility_request_id"] == request_id
    assert any(event["event_type"] == "facility.approval.requested" for event in audit.json()["events"])


def test_step_up_records_exception_when_approval_service_unavailable(monkeypatch) -> None:
    payload = _request_payload(amount_minor=240_000)
    payload["idempotency_key"] = "idem_approval_service_unavailable"

    with _client_with_approval_service(monkeypatch, FailingApprovalService()) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        exceptions = client.get("/api/v2/facility-requests/exceptions")

    assert decision.status_code == 200, decision.text
    assert decision.json()["verdict"] == "step_up_required"
    assert exceptions.status_code == 200, exceptions.text
    assert exceptions.json()["total"] == 1
    assert exceptions.json()["exceptions"][0]["payload"]["reason"] == "facility_approval_service_unavailable"


def test_approval_fatigue_denies_additional_step_up_requests(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        for idx in range(20):
            payload = _request_payload(amount_minor=240_000, evidence=False)
            payload["task_graph_hash"] = None
            payload["merchant"] = f"vendor-{idx}.example"
            payload["idempotency_key"] = f"fatigue_{idx}"
            created = client.post("/api/v2/facility-requests", json=payload)
            assert created.status_code == 201, created.text
            decision = client.post(f"/api/v2/facility-requests/{created.json()['request_id']}/authorize")
            assert decision.status_code == 200, decision.text
            assert decision.json()["verdict"] == "step_up_required"

        payload = _request_payload(amount_minor=240_000, evidence=False)
        payload["task_graph_hash"] = None
        payload["merchant"] = "vendor-final.example"
        payload["idempotency_key"] = "fatigue_final"
        created = client.post("/api/v2/facility-requests", json=payload)
        assert created.status_code == 201, created.text
        decision = client.post(f"/api/v2/facility-requests/{created.json()['request_id']}/authorize")
        exceptions = client.get("/api/v2/facility-requests/exceptions")

    assert decision.status_code == 200, decision.text
    assert decision.json()["verdict"] == "denied"
    assert decision.json()["reason_codes"][0] == "facility_approval_fatigue_limit_exceeded"
    assert exceptions.json()["exceptions"][0]["payload"]["reason"] == "facility_approval_fatigue_limit_exceeded"


def test_strict_persisted_authority_mode_rejects_request_snapshots(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY", "true")
    payload = _request_payload()
    payload["idempotency_key"] = "idem_strict_authority"

    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")

    assert decision.status_code == 409
    assert decision.json()["detail"] == "Persisted mandate lookup is required"


def test_strict_persisted_authority_mode_authorizes_with_persisted_versions(monkeypatch) -> None:
    payload = _request_payload()
    payload["idempotency_key"] = "idem_strict_authority_persisted"
    payload.pop("mandate_snapshot")
    payload.pop("facility_snapshot")

    with _client_with_persisted_authority(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        exported = client.get(f"/api/v2/facility-requests/{request_id}/audit/export")

    assert decision.status_code == 200, decision.text
    assert decision.json()["verdict"] == "approved"
    packet = exported.json()["decision_packet"]
    assert packet["mandate"]["source"] == "facility_mandate_records"
    assert packet["mandate"]["mandate_version"] == 5
    assert packet["facility"]["source"] == "facility_records"
    assert packet["facility"]["facility_version"] == 2
    assert packet["policy"]["source"] == "facility_policy_records"
    assert packet["policy"]["policy_version"] == "facility_policy_persisted_v1"


def test_authority_admin_endpoints_seed_strict_authorization_records(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY", "true")
    request_payload = _request_payload()
    request_payload["idempotency_key"] = "idem_authority_admin_seeded"
    request_payload.pop("mandate_snapshot")
    request_payload.pop("facility_snapshot")

    with _client_with_repository_authority(monkeypatch) as client:
        facility = client.put(
            "/api/v2/facility-requests/authority/facilities/fac_1",
            json={
                "facility_id": "fac_1",
                "sponsor_id": "sponsor_1",
                "version": 9,
                "limit": {"per_transaction_minor": 500000, "currency": "USD"},
                "allowed_categories": ["cloud"],
                "approval_threshold_minor": 100000,
            },
        )
        mandate = client.put(
            "/api/v2/facility-requests/authority/mandates/mandate_1",
            json={
                "mandate": {
                    "principal_id": "principal_1",
                    "issuer_id": "principal_1",
                    "agent_id": "agent_1",
                    "id": "mandate_1",
                    "amount_per_tx": "5000",
                    "currency": "USD",
                    "allowed_rails": ["simulated_card"],
                    "facility_authority_allowed": True,
                    "allowed_facility_ids": ["fac_1"],
                    "facility_max_draw": "5000",
                    "facility_scope": {"allowed_categories": ["cloud"]},
                    "version": 10,
                }
            },
        )
        policy = client.put(
            "/api/v2/facility-requests/authority/facilities/fac_1/policy",
            json={
                "facility_id": "fac_1",
                "policy_version": "facility_policy_ops_v1",
                "snapshot": {
                    "allowed_categories": ["cloud"],
                    "approval_threshold_minor": 100000,
                    "per_transaction_minor": 500000,
                    "currency": "USD",
                },
            },
        )
        created = client.post("/api/v2/facility-requests", json=request_payload)
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        exported = client.get(f"/api/v2/facility-requests/{request_id}/audit/export")

    assert facility.status_code == 200, facility.text
    assert facility.json()["record"]["version"] == 9
    assert mandate.status_code == 200, mandate.text
    assert mandate.json()["record"]["version"] == 10
    assert policy.status_code == 200, policy.text
    assert decision.status_code == 200, decision.text
    assert decision.json()["verdict"] == "approved"
    packet = exported.json()["decision_packet"]
    assert packet["mandate"]["source"] == "facility_mandate_records"
    assert packet["facility"]["source"] == "facility_records"
    assert packet["policy"]["source"] == "facility_policy_records"


def test_request_creation_rejects_mismatched_snapshot_ownership(monkeypatch) -> None:
    payload = _request_payload()
    payload["mandate_snapshot"]["agent_id"] = "agent_other"

    with _client(monkeypatch) as client:
        response = client.post("/api/v2/facility-requests", json=payload)

    assert response.status_code == 403
    assert response.json()["detail"] == "Mandate snapshot agent does not match request"


def test_request_creation_rejects_mismatched_facility_snapshot(monkeypatch) -> None:
    payload = _request_payload()
    payload["facility_snapshot"]["facility_id"] = "fac_other"

    with _client(monkeypatch) as client:
        response = client.post("/api/v2/facility-requests", json=payload)

    assert response.status_code == 403
    assert response.json()["detail"] == "Facility snapshot id does not match request"


def test_read_only_scope_cannot_create_facility_request(monkeypatch) -> None:
    with _client(monkeypatch, scopes=["read"]) as client:
        response = client.post("/api/v2/facility-requests", json=_request_payload())

    assert response.status_code == 403
    assert response.json()["detail"] == "Facility Gate scope required"


def test_write_scope_cannot_revoke_facility_authority(monkeypatch) -> None:
    with _client(monkeypatch, scopes=["write"]) as client:
        response = client.post(
            "/api/v2/facility-requests/revocations",
            json={"scope": "agent", "target_id": "agent_1", "reason": "operator revoke"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Facility Gate scope required"


def test_adapter_failure_creates_exception_event(monkeypatch) -> None:
    with _client_with_adapter(monkeypatch, FailingExecuteAdapter()) as client:
        created = client.post("/api/v2/facility-requests", json=_request_payload())
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert decision.json()["verdict"] == "approved"

        execution = client.post(f"/api/v2/facility-requests/{request_id}/execute")
        assert execution.status_code == 502

        exceptions = client.get("/api/v2/facility-requests/exceptions")
        assert exceptions.status_code == 200, exceptions.text
    assert exceptions.json()["total"] == 1
    assert exceptions.json()["exceptions"][0]["payload"]["reason"] == "facility_adapter_execute_failed"


def test_revocation_adapter_failure_creates_exception_event(monkeypatch) -> None:
    with _client_with_adapter(monkeypatch, FailingRevokeAdapter()) as client:
        response = client.post(
            "/api/v2/facility-requests/revocations",
            json={"scope": "authorization", "target_id": "fac_dec_1", "reason": "operator revoked"},
        )
        exceptions = client.get("/api/v2/facility-requests/exceptions")

    assert response.status_code == 502
    assert exceptions.status_code == 200, exceptions.text
    assert exceptions.json()["total"] == 1
    assert exceptions.json()["exceptions"][0]["payload"]["reason"] == "facility_adapter_revoke_failed"


def test_exception_resolution_appends_auditable_event(monkeypatch) -> None:
    with _client_with_adapter(monkeypatch, FailingExecuteAdapter()) as client:
        created = client.post("/api/v2/facility-requests", json=_request_payload())
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert decision.json()["verdict"] == "approved"
        execution = client.post(f"/api/v2/facility-requests/{request_id}/execute")
        assert execution.status_code == 502
        exceptions = client.get("/api/v2/facility-requests/exceptions")
        exception_event_id = exceptions.json()["exceptions"][0]["event_id"]

        resolved = client.post(
            "/api/v2/facility-requests/exceptions/resolve",
            json={
                "event_id": exception_event_id,
                "resolved_by": "ops_admin",
                "resolution": "provider timeout reviewed; no credential issued",
            },
        )
        exported = client.get(f"/api/v2/facility-requests/{request_id}/audit/export")

    assert resolved.status_code == 200, resolved.text
    assert exported.json()["exception_resolutions"][0]["exception_event_id"] == exception_event_id
    assert exported.json()["exception_resolutions"][0]["resolved_by"] == "ops_admin"


def test_duplicate_execute_returns_existing_credential_without_second_adapter_call(monkeypatch) -> None:
    class CountingAdapter(SimulatedFacilityAdapter):
        def __init__(self) -> None:
            super().__init__()
            self.execute_calls = 0

        async def execute_authorization(self, *, request, decision):  # type: ignore[no-untyped-def]
            self.execute_calls += 1
            return await super().execute_authorization(request=request, decision=decision)

    adapter = CountingAdapter()
    with _client_with_adapter(monkeypatch, adapter) as client:
        created = client.post("/api/v2/facility-requests", json=_request_payload())
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert decision.json()["verdict"] == "approved"

        first = client.post(f"/api/v2/facility-requests/{request_id}/execute")
        second = client.post(f"/api/v2/facility-requests/{request_id}/execute")

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["credential"]["credential_id"] == second.json()["credential"]["credential_id"]
    assert adapter.execute_calls == 1


def test_revocation_blocks_execution_after_approval(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=_request_payload())
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert decision.json()["verdict"] == "approved"

        revoke = client.post(
            "/api/v2/facility-requests/revocations",
            json={"scope": "authorization", "target_id": request_id, "reason": "execution revoked"},
        )
        assert revoke.status_code == 200, revoke.text
        execution = client.post(f"/api/v2/facility-requests/{request_id}/execute")

    assert execution.status_code == 409
    assert "execution revoked" in execution.json()["detail"]


def test_adapter_missing_required_capability_fails_closed(monkeypatch) -> None:
    from sardis.core.facility_gate import FacilityAdapterCapabilities

    class WeakAdapter(SimulatedFacilityAdapter):
        capabilities = FacilityAdapterCapabilities(
            provider="weak",
            supports_merchant_lock=False,
        )

    with _client_with_adapter(monkeypatch, WeakAdapter()) as client:
        created = client.post("/api/v2/facility-requests", json=_request_payload())
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert decision.json()["verdict"] == "approved"

        execution = client.post(f"/api/v2/facility-requests/{request_id}/execute")
        exceptions = client.get("/api/v2/facility-requests/exceptions")

    assert execution.status_code == 409
    assert exceptions.json()["exceptions"][0]["payload"]["reason"] == "facility_adapter_capability_unsupported"


def test_probe_limit_throttles_repeated_agent_merchant_requests(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        for idx in range(10):
            payload = _request_payload()
            payload["idempotency_key"] = f"probe_{idx}"
            response = client.post("/api/v2/facility-requests", json=payload)
            assert response.status_code == 201, response.text

        payload = _request_payload()
        payload["idempotency_key"] = "probe_10"
        throttled = client.post("/api/v2/facility-requests", json=payload)

    assert throttled.status_code == 429


def test_provider_webhook_requires_valid_signature(monkeypatch) -> None:
    payload = {
        "organization_id": "org_test",
        "provider_event_id": "evt_1",
        "event_type": "authorization.captured",
        "request_id": "fac_req_1",
        "payload": {"amount_minor": 75000},
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()

    with _provider_webhook_client(monkeypatch) as client:
        response = client.post(
            "/api/v2/provider-webhooks/test-provider/facility-gate",
            content=raw,
            headers={"Content-Type": "application/json", "X-Sardis-Facility-Signature": "sha256=bad"},
        )

    assert response.status_code == 401


def test_provider_webhook_appends_and_deduplicates_event(monkeypatch) -> None:
    payload = {
        "organization_id": "org_test",
        "provider_event_id": "evt_1",
        "event_type": "authorization.captured",
        "request_id": "fac_req_1",
        "authorization_id": "fac_dec_1",
        "payload": {"amount_minor": 75000},
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(b"test_secret", raw, sha256).hexdigest()

    with _provider_webhook_client(monkeypatch) as client:
        first = client.post(
            "/api/v2/provider-webhooks/test-provider/facility-gate",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Sardis-Facility-Signature": f"sha256={signature}",
            },
        )
        second = client.post(
            "/api/v2/provider-webhooks/test-provider/facility-gate",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Sardis-Facility-Signature": f"sha256={signature}",
            },
        )

    assert first.status_code == 200, first.text
    assert first.json()["duplicate"] is False
    assert first.json()["aggregate_id"] == "fac_req_1"
    assert first.json()["raw_payload_hash"] == sha256(raw).hexdigest()
    assert first.json()["settlement_event_id"]
    assert first.json()["settlement_duplicate"] is False
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True
    assert second.json()["event_id"] == first.json()["event_id"]
    assert second.json()["settlement_duplicate"] is True


def test_provider_webhook_unsupported_type_creates_exception(monkeypatch) -> None:
    payload = {
        "organization_id": "org_test",
        "provider_event_id": "evt_unknown_1",
        "event_type": "unknown.provider.event",
        "request_id": "fac_req_1",
        "payload": {"amount_minor": 75000},
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(b"test_secret", raw, sha256).hexdigest()

    with _provider_webhook_client(monkeypatch) as client:
        response = client.post(
            "/api/v2/provider-webhooks/test-provider/facility-gate",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Sardis-Facility-Signature": f"sha256={signature}",
            },
        )
        exceptions = client.get("/api/v2/facility-requests/exceptions")

    assert response.status_code == 200, response.text
    assert response.json()["accepted"] is False
    assert exceptions.json()["exceptions"][0]["payload"]["reason"] == "facility_provider_webhook_unsupported_type"


def test_org_audit_export_lists_decision_packets_and_provider_webhooks(monkeypatch) -> None:
    payload = _request_payload()
    payload["idempotency_key"] = "audit_export_org_request"
    webhook_payload = {
        "organization_id": "org_test",
        "provider_event_id": "evt_audit_1",
        "event_type": "authorization.captured",
        "payload": {"amount_minor": 75000},
    }

    with _client(monkeypatch) as client:
        created = client.post("/api/v2/facility-requests", json=payload)
        request_id = created.json()["request_id"]
        decision = client.post(f"/api/v2/facility-requests/{request_id}/authorize")
        assert decision.json()["verdict"] == "approved"

        webhook_payload["request_id"] = request_id
        raw = json.dumps(webhook_payload, separators=(",", ":")).encode()
        monkeypatch.setenv("SARDIS_FACILITY_PROVIDER_WEBHOOKS_ENABLED", "true")
        monkeypatch.setenv("SARDIS_FACILITY_PROVIDER_WEBHOOK_SECRET", "test_secret")
        signature = hmac.new(b"test_secret", raw, sha256).hexdigest()
        webhook = client.post(
            "/api/v2/provider-webhooks/test-provider/facility-gate",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Sardis-Facility-Signature": f"sha256={signature}",
            },
        )
        exported = client.get("/api/v2/facility-requests/audit/exports")
        request_export = client.get(f"/api/v2/facility-requests/{request_id}/audit/export")

    assert webhook.status_code == 200, webhook.text
    assert exported.status_code == 200, exported.text
    assert exported.json()["decision_packets"][0]["request_id"] == request_id
    assert exported.json()["provider_webhooks"][0]["provider_event_id"] == "evt_audit_1"
    assert request_export.json()["provider_webhooks"][0]["provider_event_id"] == "evt_audit_1"
    assert exported.json()["settlements"][0]["status"] == "captured"
    assert request_export.json()["settlements"][0]["status"] == "captured"
