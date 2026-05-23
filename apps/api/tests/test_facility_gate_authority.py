from __future__ import annotations

import pytest
from sardis.core.facility_gate import Facility
from sardis.core.spending_mandate import SpendingMandate

from server.repositories.facility_gate_repository import FacilityGateRepository
from server.services.facility_gate_authority import (
    InMemoryFacilityMandateResolver,
    InMemoryVersionedFacilityPolicyResolver,
    RepositoryBackedFacilityMandateResolver,
    RepositoryBackedFacilityPolicyResolver,
    RepositoryBackedFacilityRecordResolver,
)


@pytest.mark.asyncio
async def test_in_memory_policy_resolver_returns_latest_versioned_snapshot() -> None:
    resolver = InMemoryVersionedFacilityPolicyResolver()
    facility = Facility(facility_id="fac_1", organization_id="org_1", sponsor_id="sponsor_1")
    resolver.register_policy(
        organization_id="org_1",
        facility_id="fac_1",
        policy_version="facility_policy_v1",
        snapshot={"approval_threshold_minor": 250_000, "blocked_merchants": ["bad.example"]},
    )
    resolver.register_policy(
        organization_id="org_1",
        facility_id="fac_1",
        policy_version="facility_policy_v2",
        snapshot={"approval_threshold_minor": 125_000, "allowed_categories": ["cloud"]},
    )

    resolved = await resolver.resolve_policy(organization_id="org_1", facility=facility)

    assert resolved.policy_version == "facility_policy_v2"
    assert resolved.source == "in_memory_policy_registry"
    assert resolved.snapshot["approval_threshold_minor"] == 125_000
    assert resolved.snapshot["allowed_categories"] == ["cloud"]
    assert resolved.snapshot_hash


@pytest.mark.asyncio
async def test_repository_backed_facility_resolver_uses_persisted_record() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    facility = Facility(
        facility_id="fac_1",
        organization_id="org_1",
        sponsor_id="sponsor_1",
        version=7,
        allowed_categories=["cloud"],
    )
    await repo.upsert_facility_record(facility)

    resolved = await RepositoryBackedFacilityRecordResolver(repo).resolve_facility(
        organization_id="org_1",
        sponsor_id="sponsor_1",
        facility_id="fac_1",
        fallback_snapshot={"version": 1, "allowed_categories": ["wrong"]},
    )

    assert resolved is not None
    assert resolved.source == "facility_records"
    assert resolved.version_id == "fac_1:v7"
    assert resolved.facility.allowed_categories == ["cloud"]
    assert resolved.snapshot_hash


@pytest.mark.asyncio
async def test_in_memory_mandate_resolver_uses_registered_versioned_mandate() -> None:
    mandate = SpendingMandate(
        principal_id="principal_1",
        issuer_id="principal_1",
        org_id="org_1",
        agent_id="agent_1",
        id="mandate_1",
        facility_authority_allowed=True,
        allowed_facility_ids=["fac_1"],
        version=4,
    )
    resolver = InMemoryFacilityMandateResolver()
    resolver.register_mandate(mandate)

    resolved = await resolver.resolve_mandate(
        organization_id="org_1",
        mandate_id="mandate_1",
        agent_id="agent_1",
        fallback_snapshot=None,
    )

    assert resolved is not None
    assert resolved.source == "in_memory_mandate_registry"
    assert resolved.version_id == "mandate_1:v4"
    assert resolved.mandate.facility_authority_allowed is True
    assert resolved.snapshot_hash


@pytest.mark.asyncio
async def test_repository_backed_mandate_resolver_uses_latest_persisted_mandate() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    await repo.upsert_facility_mandate_record(
        SpendingMandate(
            principal_id="principal_1",
            issuer_id="principal_1",
            org_id="org_1",
            agent_id="agent_1",
            id="mandate_1",
            facility_authority_allowed=True,
            allowed_facility_ids=["fac_1"],
            version=8,
        ),
        created_by="ops_1",
    )

    resolved = await RepositoryBackedFacilityMandateResolver(repo).resolve_mandate(
        organization_id="org_1",
        mandate_id="mandate_1",
        agent_id="agent_1",
        fallback_snapshot=None,
    )

    assert resolved is not None
    assert resolved.source == "facility_mandate_records"
    assert resolved.version_id == "mandate_1:v8"
    assert resolved.mandate.allowed_facility_ids == ["fac_1"]
    assert resolved.snapshot_hash


@pytest.mark.asyncio
async def test_repository_backed_policy_resolver_uses_latest_persisted_policy() -> None:
    repo = FacilityGateRepository(dsn="memory://")
    facility = Facility(facility_id="fac_1", organization_id="org_1", sponsor_id="sponsor_1")
    await repo.upsert_facility_policy_record(
        organization_id="org_1",
        facility_id="fac_1",
        policy_version="facility_policy_v3",
        snapshot={"approval_threshold_minor": 42_000, "allowed_categories": ["cloud"]},
        created_by="ops_1",
    )

    resolved = await RepositoryBackedFacilityPolicyResolver(repo).resolve_policy(
        organization_id="org_1",
        facility=facility,
    )

    assert resolved.source == "facility_policy_records"
    assert resolved.policy_version == "facility_policy_v3"
    assert resolved.snapshot["approval_threshold_minor"] == 42_000
    assert resolved.snapshot_hash
