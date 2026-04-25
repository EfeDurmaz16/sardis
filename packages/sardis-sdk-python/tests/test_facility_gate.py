from __future__ import annotations

from datetime import UTC, datetime

from sardis_sdk import SardisClient


async def test_async_facility_gate_create_authorize_and_audit_export(client, base_url, httpx_mock):
    request_payload = {
        "organization_id": "org_123",
        "agent_id": "agent_123",
        "facility_id": "fac_123",
        "mandate_id": "mandate_123",
        "merchant": {"name": "Example Cloud", "category": "cloud"},
        "amount": "2400.00",
        "currency": "USD",
        "purpose": "cloud infrastructure",
    }

    httpx_mock.add_response(
        method="POST",
        url=f"{base_url}/api/v2/facility-requests",
        json={"request_id": "fr_123", "state": "created"},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{base_url}/api/v2/facility-requests/fr_123/evidence",
        json={"request_id": "fr_123", "evidence_count": 1},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{base_url}/api/v2/facility-requests/fr_123/authorize",
        json={"decision_id": "fd_123", "verdict": "approved"},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{base_url}/api/v2/facility-requests/fr_123/audit/export",
        json={"request_id": "fr_123", "decision_packet": {"schema_version": "facility.decision_packet.v1"}},
    )

    created = await client.facility_gate.create_request(request_payload)
    evidence = await client.facility_gate.attach_evidence(
        "fr_123",
        [{"evidence_id": "ev_123", "evidence_type": "task_log", "hash": "sha256:abc"}],
        idempotency_key="idem_evidence_123",
    )
    decision = await client.facility_gate.authorize("fr_123")
    export = await client.facility_gate.export_audit("fr_123")

    assert created["request_id"] == "fr_123"
    assert evidence["evidence_count"] == 1
    assert decision["verdict"] == "approved"
    assert export["decision_packet"]["schema_version"] == "facility.decision_packet.v1"


async def test_async_facility_gate_list_and_export_events(client, base_url, httpx_mock):
    occurred_from = datetime(2026, 4, 24, 9, 0, tzinfo=UTC)

    httpx_mock.add_response(
        method="GET",
        url=f"{base_url}/api/v2/facility-requests?limit=25",
        json={"requests": [{"request_id": "fr_123"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url=(
            f"{base_url}/api/v2/facility-requests/audit/exports"
            "?event_type=facility.authorization.approved"
            "&limit=10"
            "&occurred_from=2026-04-24T09%3A00%3A00%2B00%3A00"
        ),
        json={"events": [{"event_id": "evt_123"}], "decision_packets": [{"decision_id": "fd_123"}]},
    )

    requests = await client.facility_gate.list(limit=25)
    export = await client.facility_gate.export_events(
        occurred_from=occurred_from,
        event_type="facility.authorization.approved",
        limit=10,
    )

    assert requests == [{"request_id": "fr_123"}]
    assert export["events"][0]["event_id"] == "evt_123"


def test_sync_facility_gate_operator_actions(api_key, base_url, httpx_mock):
    client = SardisClient(api_key=api_key, base_url=base_url)

    httpx_mock.add_response(
        method="GET",
        url=f"{base_url}/api/v2/facility-requests/manual-review",
        json={"requests": [{"request_id": "fr_step_up"}]},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{base_url}/api/v2/facility-requests/fr_step_up/approval",
        json={"request_id": "fr_step_up", "approved": True},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{base_url}/api/v2/facility-requests/revocations",
        json={"event_id": "evt_revoke", "scope": "agent"},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{base_url}/api/v2/facility-requests/exceptions",
        json={"exceptions": [{"event_id": "evt_exception"}]},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{base_url}/api/v2/facility-requests/exceptions/resolve",
        json={"event_id": "evt_resolution", "resolved": True},
    )

    manual_review = client.facility_gate.manual_review()
    approval = client.facility_gate.record_approval(
        "fr_step_up",
        approved=True,
        reviewed_by="ops_123",
        reason="approved for cloud expansion",
        idempotency_key="idem_approval_123",
    )
    revocation = client.facility_gate.revoke(
        scope="agent",
        target_id="agent_123",
        reason="compromised key",
        idempotency_key="idem_revoke_123",
    )
    exceptions = client.facility_gate.exceptions()
    resolution = client.facility_gate.resolve_exception(
        event_id="evt_exception",
        resolved_by="ops_123",
        resolution="adapter retry completed",
    )

    assert manual_review["requests"][0]["request_id"] == "fr_step_up"
    assert approval["approved"] is True
    assert revocation["scope"] == "agent"
    assert exceptions["exceptions"][0]["event_id"] == "evt_exception"
    assert resolution["resolved"] is True
