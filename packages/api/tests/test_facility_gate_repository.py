from __future__ import annotations

import pytest
from sardis_v2_core.facility_gate import Facility, FacilityEventType, FacilityLimit
from sardis_v2_core.spending_mandate import SpendingMandate

from sardis_api.repositories.facility_gate_repository import FacilityGateRepository
from sardis_api.services.facility_gate_replay import FacilityGateReplayService


@pytest.mark.asyncio
async def test_facility_event_repository_is_idempotent_and_hash_chained() -> None:
    repo = FacilityGateRepository(dsn="memory://")

    first = await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.REQUEST_CREATED,
        payload={
            "request": {
                "request_id": "fac_req_1",
                "organization_id": "org_1",
                "facility_id": "fac_1",
                "agent_id": "agent_1",
                "mandate_id": "mandate_1",
                "merchant": "aws.amazon.com",
                "amount_minor": 75000,
                "currency": "USD",
            }
        },
        idempotency_key="idem_1",
    )
    duplicate = await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.REQUEST_CREATED,
        payload={"request": {"request_id": "fac_req_1"}},
        idempotency_key="idem_1",
    )
    second = await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.AUTH_APPROVED,
        payload={"decision": {"decision_id": "fac_dec_1", "verdict": "approved"}},
    )

    assert duplicate.duplicate is True
    assert duplicate.event["event_id"] == first.event["event_id"]
    assert second.event["previous_event_hash"] == first.event["event_hash"]

    events = await repo.list_events(organization_id="org_1", aggregate_id="fac_req_1")
    assert [event["event_type"] for event in events] == [
        "facility.request.created",
        "facility.authorization.approved",
    ]


@pytest.mark.asyncio
async def test_facility_projection_replay_rebuilds_current_state() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.REQUEST_CREATED,
        payload={
            "request": {
                "request_id": "fac_req_1",
                "organization_id": "org_1",
                "facility_id": "fac_1",
                "agent_id": "agent_1",
                "mandate_id": "mandate_1",
                "merchant": "aws.amazon.com",
                "amount_minor": 75000,
                "currency": "USD",
            }
        },
    )
    await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.EVIDENCE_ATTACHED,
        payload={"evidence": [{"evidence_id": "evd_1", "content_hash": "sha256:invoice"}]},
    )
    await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.AUTH_STEP_UP_REQUIRED,
        payload={"decision": {"decision_id": "fac_dec_1", "verdict": "step_up_required"}},
    )

    expected = await repo.replay_request_state(
        organization_id="org_1",
        request_id="fac_req_1",
    )
    verification = await repo.verify_request_state_projection(
        organization_id="org_1",
        request_id="fac_req_1",
    )

    assert expected is not None
    assert expected["status"] == "step_up_required"
    assert expected["payload"]["attached_evidence"][0]["evidence_id"] == "evd_1"
    assert verification["ok"] is True


@pytest.mark.asyncio
async def test_facility_replay_service_detects_projection_drift() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.REQUEST_CREATED,
        payload={
            "request": {
                "request_id": "fac_req_1",
                "organization_id": "org_1",
                "facility_id": "fac_1",
                "agent_id": "agent_1",
                "mandate_id": "mandate_1",
                "merchant": "aws.amazon.com",
                "amount_minor": 75000,
                "currency": "USD",
            }
        },
    )
    repo._request_states[("org_1", "fac_req_1")]["status"] = "corrupted"

    result = await FacilityGateReplayService(repo).rebuild(organization_id="org_1", dry_run=True)

    assert result.rebuilt == 1
    assert result.drifted == 1
    assert result.drift[0]["expected"]["status"] == "created"


@pytest.mark.asyncio
async def test_facility_hash_chain_verification_detects_tampering() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.REQUEST_CREATED,
        payload={
            "request": {
                "request_id": "fac_req_1",
                "organization_id": "org_1",
                "facility_id": "fac_1",
                "agent_id": "agent_1",
                "mandate_id": "mandate_1",
                "merchant": "aws.amazon.com",
                "amount_minor": 75000,
                "currency": "USD",
            }
        },
    )

    assert (await repo.verify_event_hash_chain(organization_id="org_1", aggregate_id="fac_req_1"))["ok"] is True
    repo._events[0]["payload"]["request"]["amount_minor"] = 1

    verification = await repo.verify_event_hash_chain(organization_id="org_1", aggregate_id="fac_req_1")

    assert verification["ok"] is False
    assert verification["errors"][0]["error"] == "event_hash_mismatch"


@pytest.mark.asyncio
async def test_facility_repository_lists_org_events_with_type_filter() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.REQUEST_CREATED,
        payload={
            "request": {
                "request_id": "fac_req_1",
                "organization_id": "org_1",
                "facility_id": "fac_1",
                "agent_id": "agent_1",
                "mandate_id": "mandate_1",
                "merchant": "aws.amazon.com",
                "amount_minor": 75000,
                "currency": "USD",
            }
        },
    )
    await repo.append_event(
        organization_id="org_1",
        aggregate_id="fac_req_1",
        event_type=FacilityEventType.AUTH_DENIED,
        payload={"decision": {"decision_id": "fac_dec_1", "verdict": "denied"}},
    )

    all_events = await repo.list_events_for_organization(organization_id="org_1")
    denied_events = await repo.list_events_for_organization(
        organization_id="org_1",
        event_type=FacilityEventType.AUTH_DENIED,
    )

    assert len(all_events) == 2
    assert [event["event_type"] for event in denied_events] == ["facility.authorization.denied"]


@pytest.mark.asyncio
async def test_facility_repository_persists_facility_records_for_authority_lookup() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    facility = Facility(
        facility_id="fac_1",
        organization_id="org_1",
        sponsor_id="sponsor_1",
        limit=FacilityLimit(per_transaction_minor=250_000, currency="USD"),
        allowed_categories=["cloud"],
        blocked_merchants=["blocked.example"],
        approval_threshold_minor=100_000,
        version=3,
    )

    await repo.upsert_facility_record(facility)
    resolved = await repo.get_facility_record(
        organization_id="org_1",
        sponsor_id="sponsor_1",
        facility_id="fac_1",
    )
    cross_sponsor = await repo.get_facility_record(
        organization_id="org_1",
        sponsor_id="sponsor_other",
        facility_id="fac_1",
    )

    assert resolved is not None
    assert resolved.version == 3
    assert resolved.limit.per_transaction_minor == 250_000
    assert resolved.allowed_categories == ["cloud"]
    assert resolved.blocked_merchants == ["blocked.example"]
    assert cross_sponsor is None


@pytest.mark.asyncio
async def test_facility_repository_persists_latest_policy_records() -> None:
    repo = FacilityGateRepository(dsn="memory://")

    await repo.upsert_facility_policy_record(
        organization_id="org_1",
        facility_id="fac_1",
        policy_version="facility_policy_v1",
        snapshot={"approval_threshold_minor": 250_000},
        created_by="ops_1",
    )
    await repo.upsert_facility_policy_record(
        organization_id="org_1",
        facility_id="fac_1",
        policy_version="facility_policy_v2",
        snapshot={"approval_threshold_minor": 125_000, "blocked_merchants": ["bad.example"]},
        created_by="ops_1",
    )

    latest = await repo.get_latest_facility_policy_record(
        organization_id="org_1",
        facility_id="fac_1",
    )

    assert latest is not None
    assert latest["policy_version"] == "facility_policy_v2"
    assert latest["snapshot"]["approval_threshold_minor"] == 125_000
    assert latest["snapshot_hash"]


@pytest.mark.asyncio
async def test_facility_repository_persists_latest_mandate_records() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    first = SpendingMandate(
        principal_id="principal_1",
        issuer_id="principal_1",
        org_id="org_1",
        agent_id="agent_1",
        id="mandate_1",
        facility_authority_allowed=True,
        allowed_facility_ids=["fac_1"],
        version=1,
    )
    second = SpendingMandate(
        principal_id="principal_1",
        issuer_id="principal_1",
        org_id="org_1",
        agent_id="agent_1",
        id="mandate_1",
        facility_authority_allowed=True,
        allowed_facility_ids=["fac_2"],
        version=2,
    )

    await repo.upsert_facility_mandate_record(first, created_by="ops_1")
    await repo.upsert_facility_mandate_record(second, created_by="ops_1")
    latest = await repo.get_latest_facility_mandate_record(
        organization_id="org_1",
        mandate_id="mandate_1",
        agent_id="agent_1",
    )

    assert latest is not None
    assert latest["version"] == 2
    assert latest["snapshot"]["allowed_facility_ids"] == ["fac_2"]
    assert latest["snapshot_hash"]
