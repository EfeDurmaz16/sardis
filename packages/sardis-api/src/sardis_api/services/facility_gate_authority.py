"""Authority/version resolution ports for Facility Gate authorization."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from sardis_v2_core.facility_gate import Facility, stable_payload_hash, to_jsonable
from sardis_v2_core.spending_mandate import ApprovalMode, MandateStatus, SpendingMandate


@dataclass(frozen=True)
class ResolvedMandate:
    mandate: SpendingMandate
    source: str
    version_id: str
    snapshot_hash: str


@dataclass(frozen=True)
class ResolvedFacility:
    facility: Facility
    source: str
    version_id: str
    snapshot_hash: str


@dataclass(frozen=True)
class ResolvedFacilityPolicy:
    policy_version: str
    source: str
    snapshot: dict[str, Any]
    snapshot_hash: str


class FacilityMandateResolver(Protocol):
    async def resolve_mandate(
        self,
        *,
        organization_id: str,
        mandate_id: str,
        agent_id: str,
        fallback_snapshot: dict[str, Any] | None,
    ) -> ResolvedMandate | None:
        ...


class FacilityRecordResolver(Protocol):
    async def resolve_facility(
        self,
        *,
        organization_id: str,
        sponsor_id: str,
        facility_id: str,
        fallback_snapshot: dict[str, Any] | None,
    ) -> ResolvedFacility | None:
        ...


class FacilityPolicyResolver(Protocol):
    async def resolve_policy(
        self,
        *,
        organization_id: str,
        facility: Facility,
    ) -> ResolvedFacilityPolicy:
        ...


def mandate_from_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    fallback_id: str,
    org_id: str,
    agent_id: str,
) -> SpendingMandate | None:
    if snapshot is None:
        return None
    data = dict(snapshot)
    data["id"] = data.get("id") or fallback_id
    data["org_id"] = data.get("org_id") or org_id
    data["agent_id"] = data.get("agent_id") or agent_id
    data["approval_mode"] = ApprovalMode(data.get("approval_mode", "auto"))
    if data.get("status") is not None:
        data["status"] = MandateStatus(data["status"])
    for datetime_field in ("valid_from", "expires_at", "revoked_at", "created_at", "updated_at"):
        if isinstance(data.get(datetime_field), str):
            data[datetime_field] = datetime.fromisoformat(data[datetime_field])
    for decimal_field in (
        "amount_per_tx",
        "amount_daily",
        "amount_weekly",
        "amount_monthly",
        "amount_total",
        "approval_threshold",
        "facility_max_draw",
    ):
        if data.get(decimal_field) is not None:
            data[decimal_field] = Decimal(str(data[decimal_field]))
    return SpendingMandate(**data)


class SnapshotBackedFacilityMandateResolver:
    """Development resolver; production should inject persisted lookup."""

    async def resolve_mandate(
        self,
        *,
        organization_id: str,
        mandate_id: str,
        agent_id: str,
        fallback_snapshot: dict[str, Any] | None,
    ) -> ResolvedMandate | None:
        mandate = mandate_from_snapshot(
            fallback_snapshot,
            fallback_id=mandate_id,
            org_id=organization_id,
            agent_id=agent_id,
        )
        if mandate is None:
            return None
        snapshot = to_jsonable(fallback_snapshot or {})
        return ResolvedMandate(
            mandate=mandate,
            source="request_snapshot",
            version_id=f"{mandate.id}:v{mandate.version}",
            snapshot_hash=stable_payload_hash({"mandate": snapshot}),
        )


class InMemoryFacilityMandateResolver:
    """Versioned mandate registry used by tests and controlled migrations."""

    def __init__(self) -> None:
        self._mandates: dict[tuple[str, str, str], SpendingMandate] = {}

    def register_mandate(self, mandate: SpendingMandate) -> None:
        agent_id = mandate.agent_id or ""
        self._mandates[(mandate.org_id, mandate.id, agent_id)] = mandate

    async def resolve_mandate(
        self,
        *,
        organization_id: str,
        mandate_id: str,
        agent_id: str,
        fallback_snapshot: dict[str, Any] | None,
    ) -> ResolvedMandate | None:
        mandate = self._mandates.get((organization_id, mandate_id, agent_id)) or self._mandates.get(
            (organization_id, mandate_id, "")
        )
        if mandate is None:
            return None
        snapshot = to_jsonable(mandate)
        return ResolvedMandate(
            mandate=mandate,
            source="in_memory_mandate_registry",
            version_id=f"{mandate.id}:v{mandate.version}",
            snapshot_hash=stable_payload_hash({"mandate": snapshot}),
        )


class RepositoryBackedFacilityMandateResolver:
    """Mandate resolver backed by versioned Facility Gate mandate records."""

    def __init__(self, repository, fallback: FacilityMandateResolver | None = None) -> None:
        self._repository = repository
        self._fallback = fallback

    async def resolve_mandate(
        self,
        *,
        organization_id: str,
        mandate_id: str,
        agent_id: str,
        fallback_snapshot: dict[str, Any] | None,
    ) -> ResolvedMandate | None:
        record = await self._repository.get_latest_facility_mandate_record(
            organization_id=organization_id,
            mandate_id=mandate_id,
            agent_id=agent_id,
        )
        if record is None:
            if self._fallback is None:
                return None
            return await self._fallback.resolve_mandate(
                organization_id=organization_id,
                mandate_id=mandate_id,
                agent_id=agent_id,
                fallback_snapshot=fallback_snapshot,
            )
        mandate = mandate_from_snapshot(
            record["snapshot"],
            fallback_id=mandate_id,
            org_id=organization_id,
            agent_id=agent_id,
        )
        if mandate is None:
            return None
        return ResolvedMandate(
            mandate=mandate,
            source="facility_mandate_records",
            version_id=f"{mandate.id}:v{mandate.version}",
            snapshot_hash=str(record.get("snapshot_hash") or stable_payload_hash({"mandate": to_jsonable(mandate)})),
        )


class SnapshotBackedFacilityRecordResolver:
    def __init__(self, factory) -> None:
        self._factory = factory

    async def resolve_facility(
        self,
        *,
        organization_id: str,
        sponsor_id: str,
        facility_id: str,
        fallback_snapshot: dict[str, Any] | None,
    ) -> ResolvedFacility | None:
        facility = self._factory(organization_id, sponsor_id, facility_id, fallback_snapshot)
        return ResolvedFacility(
            facility=facility,
            source="request_snapshot" if fallback_snapshot else "default_simulated",
            version_id=f"{facility.facility_id}:v{facility.version}",
            snapshot_hash=stable_payload_hash({"facility": to_jsonable(fallback_snapshot or facility)}),
        )


class RepositoryBackedFacilityRecordResolver:
    """Facility resolver backed by the Facility Gate facility_records table."""

    def __init__(self, repository, fallback: FacilityRecordResolver | None = None) -> None:
        self._repository = repository
        self._fallback = fallback

    async def resolve_facility(
        self,
        *,
        organization_id: str,
        sponsor_id: str,
        facility_id: str,
        fallback_snapshot: dict[str, Any] | None,
    ) -> ResolvedFacility | None:
        facility = await self._repository.get_facility_record(
            organization_id=organization_id,
            sponsor_id=sponsor_id,
            facility_id=facility_id,
        )
        if facility is None:
            if self._fallback is None:
                return None
            return await self._fallback.resolve_facility(
                organization_id=organization_id,
                sponsor_id=sponsor_id,
                facility_id=facility_id,
                fallback_snapshot=fallback_snapshot,
            )
        snapshot = to_jsonable(facility)
        return ResolvedFacility(
            facility=facility,
            source="facility_records",
            version_id=f"{facility.facility_id}:v{facility.version}",
            snapshot_hash=stable_payload_hash({"facility": snapshot}),
        )


class DefaultFacilityPolicyResolver:
    def _snapshot_for_facility(
        self,
        *,
        organization_id: str,
        facility: Facility,
        policy_version: str = "facility_policy_v0",
        source: str = "default_policy_v0",
        overrides: dict[str, Any] | None = None,
    ) -> ResolvedFacilityPolicy:
        snapshot = {
            "policy_version": policy_version,
            "organization_id": organization_id,
            "facility_id": facility.facility_id,
            "allowed_categories": facility.allowed_categories,
            "allowed_merchants": facility.allowed_merchants,
            "blocked_merchants": facility.blocked_merchants,
            "approval_threshold_minor": facility.approval_threshold_minor,
            "per_transaction_minor": facility.limit.per_transaction_minor,
            "currency": facility.limit.currency,
        }
        if overrides:
            snapshot.update(to_jsonable(overrides))
        return ResolvedFacilityPolicy(
            policy_version=policy_version,
            source=source,
            snapshot=snapshot,
            snapshot_hash=stable_payload_hash({"policy": snapshot}),
        )

    async def resolve_policy(
        self,
        *,
        organization_id: str,
        facility: Facility,
    ) -> ResolvedFacilityPolicy:
        return self._snapshot_for_facility(organization_id=organization_id, facility=facility)


class RepositoryBackedFacilityPolicyResolver(DefaultFacilityPolicyResolver):
    """Policy resolver backed by versioned Facility Gate policy records."""

    def __init__(self, repository, fallback: FacilityPolicyResolver | None = None) -> None:
        self._repository = repository
        self._fallback = fallback or DefaultFacilityPolicyResolver()

    async def resolve_policy(
        self,
        *,
        organization_id: str,
        facility: Facility,
    ) -> ResolvedFacilityPolicy:
        record = await self._repository.get_latest_facility_policy_record(
            organization_id=organization_id,
            facility_id=facility.facility_id,
        )
        if record is None:
            return await self._fallback.resolve_policy(organization_id=organization_id, facility=facility)
        snapshot = to_jsonable(record["snapshot"])
        return self._snapshot_for_facility(
            organization_id=organization_id,
            facility=facility,
            policy_version=str(record["policy_version"]),
            source="facility_policy_records",
            overrides=snapshot,
        )


class InMemoryVersionedFacilityPolicyResolver(DefaultFacilityPolicyResolver):
    """Versioned policy registry used until Facility Gate policies are persisted."""

    def __init__(self) -> None:
        self._policies: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def register_policy(
        self,
        *,
        organization_id: str,
        facility_id: str,
        policy_version: str,
        snapshot: dict[str, Any],
    ) -> None:
        key = (organization_id, facility_id)
        self._policies.setdefault(key, []).append(
            {
                "policy_version": policy_version,
                "snapshot": to_jsonable(snapshot),
            }
        )

    async def resolve_policy(
        self,
        *,
        organization_id: str,
        facility: Facility,
    ) -> ResolvedFacilityPolicy:
        versions = self._policies.get((organization_id, facility.facility_id), [])
        if not versions:
            return await super().resolve_policy(organization_id=organization_id, facility=facility)
        latest = versions[-1]
        return self._snapshot_for_facility(
            organization_id=organization_id,
            facility=facility,
            policy_version=str(latest["policy_version"]),
            source="in_memory_policy_registry",
            overrides=dict(latest["snapshot"]),
        )
