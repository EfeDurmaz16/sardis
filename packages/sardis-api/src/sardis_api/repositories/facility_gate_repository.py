"""Append-only repository for Facility Gate events and materialized state."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sardis_v2_core.facility_gate import (
    Facility,
    FacilityEventType,
    FacilityLimit,
    FacilityStatus,
    FacilityType,
    stable_payload_hash,
    to_jsonable,
)
from sardis_v2_core.spending_mandate import SpendingMandate


@dataclass(frozen=True)
class FacilityEventAppendResult:
    event: dict[str, Any]
    duplicate: bool = False


class FacilityGateRepository:
    def __init__(self, pool=None, dsn: str | None = None) -> None:
        self._pool = pool
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._events: list[dict[str, Any]] = []
        self._idempotency: dict[tuple[str, str], dict[str, Any]] = {}
        self._request_states: dict[tuple[str, str], dict[str, Any]] = {}
        self._facility_records: dict[tuple[str, str], dict[str, Any]] = {}
        self._facility_policy_records: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._facility_mandate_records: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    def _use_postgres(self) -> bool:
        return self._pool is not None or self._dsn.startswith(("postgresql://", "postgres://"))

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    @staticmethod
    def _hash_event(
        *,
        event_id: str,
        organization_id: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
        previous_event_hash: str | None,
        occurred_at: datetime,
    ) -> str:
        body = {
            "event_id": event_id,
            "organization_id": organization_id,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "payload_hash": stable_payload_hash(payload),
            "previous_event_hash": previous_event_hash,
            "occurred_at": occurred_at.isoformat(),
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    async def append_event(
        self,
        *,
        organization_id: str,
        aggregate_id: str,
        event_type: FacilityEventType | str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        actor_id: str | None = None,
    ) -> FacilityEventAppendResult:
        event_type_value = event_type.value if isinstance(event_type, FacilityEventType) else event_type
        payload_json = to_jsonable(payload)
        if idempotency_key:
            key = (organization_id, idempotency_key)
            if not self._use_postgres() and key in self._idempotency:
                return FacilityEventAppendResult(event=self._idempotency[key], duplicate=True)

        occurred_at = datetime.now(UTC)
        event_id = f"fac_evt_{uuid4().hex[:20]}"
        previous_hash = await self._latest_hash(organization_id=organization_id, aggregate_id=aggregate_id)
        event_hash = self._hash_event(
            event_id=event_id,
            organization_id=organization_id,
            aggregate_id=aggregate_id,
            event_type=event_type_value,
            payload=payload_json,
            previous_event_hash=previous_hash,
            occurred_at=occurred_at,
        )
        event = {
            "event_id": event_id,
            "organization_id": organization_id,
            "aggregate_id": aggregate_id,
            "event_type": event_type_value,
            "idempotency_key": idempotency_key,
            "actor_id": actor_id,
            "payload": payload_json,
            "previous_event_hash": previous_hash,
            "event_hash": event_hash,
            "occurred_at": occurred_at.isoformat(),
        }

        if not self._use_postgres():
            self._events.append(event)
            if idempotency_key:
                self._idempotency[(organization_id, idempotency_key)] = event
            self._project_event(event)
            return FacilityEventAppendResult(event=event)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if idempotency_key:
                existing = await conn.fetchrow(
                    """
                    SELECT * FROM facility_events
                    WHERE organization_id = $1 AND idempotency_key = $2
                    """,
                    organization_id,
                    idempotency_key,
                )
                if existing:
                    row = self._row_to_event(existing)
                    return FacilityEventAppendResult(event=row, duplicate=True)
            try:
                await conn.execute(
                    """
                    INSERT INTO facility_events (
                        event_id, organization_id, aggregate_id, event_type, idempotency_key,
                        actor_id, payload, previous_event_hash, event_hash, occurred_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10)
                    """,
                    event_id,
                    organization_id,
                    aggregate_id,
                    event_type_value,
                    idempotency_key,
                    actor_id,
                    json.dumps(payload_json),
                    previous_hash,
                    event_hash,
                    occurred_at,
                )
            except Exception:
                if not idempotency_key:
                    raise
                existing = await conn.fetchrow(
                    """
                    SELECT * FROM facility_events
                    WHERE organization_id = $1 AND idempotency_key = $2
                    """,
                    organization_id,
                    idempotency_key,
                )
                if existing:
                    return FacilityEventAppendResult(event=self._row_to_event(existing), duplicate=True)
                raise
        await self._project_postgres_event(event)
        return FacilityEventAppendResult(event=event)

    @staticmethod
    def _row_to_event(row: Any) -> dict[str, Any]:
        item = dict(row)
        if hasattr(item.get("occurred_at"), "isoformat"):
            item["occurred_at"] = item["occurred_at"].isoformat()
        if hasattr(item.get("created_at"), "isoformat"):
            item["created_at"] = item["created_at"].isoformat()
        payload = item.get("payload")
        if isinstance(payload, str):
            item["payload"] = json.loads(payload)
        return item

    async def _latest_hash(self, *, organization_id: str, aggregate_id: str) -> str | None:
        if not self._use_postgres():
            for event in reversed(self._events):
                if event["organization_id"] == organization_id and event["aggregate_id"] == aggregate_id:
                    return event["event_hash"]
            return None
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT event_hash FROM facility_events
                WHERE organization_id = $1 AND aggregate_id = $2
                ORDER BY occurred_at DESC, created_at DESC
                LIMIT 1
                """,
                organization_id,
                aggregate_id,
            )

    async def list_events(self, *, organization_id: str, aggregate_id: str) -> list[dict[str, Any]]:
        if not self._use_postgres():
            return [
                event for event in self._events
                if event["organization_id"] == organization_id and event["aggregate_id"] == aggregate_id
            ]
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM facility_events
                WHERE organization_id = $1 AND aggregate_id = $2
                ORDER BY occurred_at ASC, created_at ASC
                """,
                organization_id,
                aggregate_id,
            )
        result = []
        for row in rows:
            result.append(self._row_to_event(row))
        return result

    async def list_events_by_type(
        self,
        *,
        organization_id: str,
        event_type: FacilityEventType | str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        event_type_value = event_type.value if isinstance(event_type, FacilityEventType) else event_type
        if not self._use_postgres():
            rows = [
                event for event in self._events
                if event["organization_id"] == organization_id and event["event_type"] == event_type_value
            ]
            return rows[-limit:]
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM facility_events
                WHERE organization_id = $1 AND event_type = $2
                ORDER BY occurred_at DESC, created_at DESC
                LIMIT $3
                """,
                organization_id,
                event_type_value,
                limit,
            )
        result = []
        for row in rows:
            result.append(self._row_to_event(row))
        return result

    async def list_events_for_organization(
        self,
        *,
        organization_id: str,
        event_type: FacilityEventType | str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        event_type_value = event_type.value if isinstance(event_type, FacilityEventType) else event_type
        if not self._use_postgres():
            rows = [
                event for event in self._events
                if event["organization_id"] == organization_id
            ]
            if event_type_value:
                rows = [event for event in rows if event["event_type"] == event_type_value]
            if occurred_from:
                rows = [event for event in rows if datetime.fromisoformat(str(event["occurred_at"])) >= occurred_from]
            if occurred_to:
                rows = [event for event in rows if datetime.fromisoformat(str(event["occurred_at"])) <= occurred_to]
            return rows[-limit:]
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM facility_events
                WHERE organization_id = $1
                  AND ($2::text IS NULL OR event_type = $2)
                  AND ($3::timestamptz IS NULL OR occurred_at >= $3)
                  AND ($4::timestamptz IS NULL OR occurred_at <= $4)
                ORDER BY occurred_at ASC, created_at ASC
                LIMIT $5
                """,
                organization_id,
                event_type_value,
                occurred_from,
                occurred_to,
                limit,
            )
        return [self._row_to_event(row) for row in rows]

    async def get_request_state(self, *, organization_id: str, request_id: str) -> dict[str, Any] | None:
        if not self._use_postgres():
            return self._request_states.get((organization_id, request_id))
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM facility_request_states WHERE organization_id = $1 AND request_id = $2",
                organization_id,
                request_id,
            )
        return dict(row) if row else None

    async def upsert_facility_record(self, facility: Facility) -> dict[str, Any]:
        record = self._facility_to_record(facility)
        if not self._use_postgres():
            self._facility_records[(facility.organization_id, facility.facility_id)] = record
            return record
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO facility_records (
                    facility_id, organization_id, sponsor_id, provider, facility_type, status, version,
                    limit_payload, allowed_categories, allowed_merchants, blocked_merchants,
                    approval_threshold_minor, metadata, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10::jsonb, $11::jsonb, $12, $13::jsonb, NOW())
                ON CONFLICT (facility_id) DO UPDATE SET
                    organization_id = EXCLUDED.organization_id,
                    sponsor_id = EXCLUDED.sponsor_id,
                    provider = EXCLUDED.provider,
                    facility_type = EXCLUDED.facility_type,
                    status = EXCLUDED.status,
                    version = EXCLUDED.version,
                    limit_payload = EXCLUDED.limit_payload,
                    allowed_categories = EXCLUDED.allowed_categories,
                    allowed_merchants = EXCLUDED.allowed_merchants,
                    blocked_merchants = EXCLUDED.blocked_merchants,
                    approval_threshold_minor = EXCLUDED.approval_threshold_minor,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                record["facility_id"],
                record["organization_id"],
                record["sponsor_id"],
                record["provider"],
                record["facility_type"],
                record["status"],
                record["version"],
                json.dumps(record["limit_payload"]),
                json.dumps(record["allowed_categories"]),
                json.dumps(record["allowed_merchants"]),
                json.dumps(record["blocked_merchants"]),
                record["approval_threshold_minor"],
                json.dumps(record["metadata"]),
            )
        return record

    async def get_facility_record(
        self,
        *,
        organization_id: str,
        sponsor_id: str,
        facility_id: str,
    ) -> Facility | None:
        if not self._use_postgres():
            record = self._facility_records.get((organization_id, facility_id))
            if not record or record["sponsor_id"] != sponsor_id:
                return None
            return self._facility_from_record(record)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM facility_records
                WHERE organization_id = $1 AND sponsor_id = $2 AND facility_id = $3
                """,
                organization_id,
                sponsor_id,
                facility_id,
            )
        if not row:
            return None
        return self._facility_from_record(dict(row))

    async def upsert_facility_policy_record(
        self,
        *,
        organization_id: str,
        facility_id: str,
        policy_version: str,
        snapshot: dict[str, Any],
        created_by: str | None = None,
    ) -> dict[str, Any]:
        snapshot_json = to_jsonable(snapshot)
        snapshot_hash = stable_payload_hash({"policy": snapshot_json})
        record = {
            "policy_record_id": f"{organization_id}:{facility_id}:{policy_version}",
            "organization_id": organization_id,
            "facility_id": facility_id,
            "policy_version": policy_version,
            "snapshot": snapshot_json,
            "snapshot_hash": snapshot_hash,
            "created_by": created_by,
        }
        if not self._use_postgres():
            key = (organization_id, facility_id)
            versions = [
                existing
                for existing in self._facility_policy_records.get(key, [])
                if existing["policy_version"] != policy_version
            ]
            versions.append(record)
            self._facility_policy_records[key] = versions
            return record
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO facility_policy_records (
                    policy_record_id, organization_id, facility_id, policy_version, snapshot,
                    snapshot_hash, created_by
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                ON CONFLICT (organization_id, facility_id, policy_version) DO UPDATE SET
                    snapshot = EXCLUDED.snapshot,
                    snapshot_hash = EXCLUDED.snapshot_hash,
                    created_by = EXCLUDED.created_by
                """,
                record["policy_record_id"],
                organization_id,
                facility_id,
                policy_version,
                json.dumps(snapshot_json),
                snapshot_hash,
                created_by,
            )
        return record

    async def get_latest_facility_policy_record(
        self,
        *,
        organization_id: str,
        facility_id: str,
    ) -> dict[str, Any] | None:
        if not self._use_postgres():
            versions = self._facility_policy_records.get((organization_id, facility_id), [])
            return versions[-1] if versions else None
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM facility_policy_records
                WHERE organization_id = $1 AND facility_id = $2
                ORDER BY created_at DESC
                LIMIT 1
                """,
                organization_id,
                facility_id,
            )
        if not row:
            return None
        record = dict(row)
        if isinstance(record.get("snapshot"), str):
            record["snapshot"] = json.loads(record["snapshot"])
        return record

    async def upsert_facility_mandate_record(
        self,
        mandate: SpendingMandate,
        *,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        agent_id = mandate.agent_id or ""
        snapshot = to_jsonable(mandate)
        snapshot_hash = stable_payload_hash({"mandate": snapshot})
        record = {
            "mandate_record_id": f"{mandate.org_id}:{mandate.id}:{agent_id}:v{mandate.version}",
            "organization_id": mandate.org_id,
            "mandate_id": mandate.id,
            "agent_id": agent_id,
            "version": mandate.version,
            "snapshot": snapshot,
            "snapshot_hash": snapshot_hash,
            "created_by": created_by,
        }
        if not self._use_postgres():
            key = (mandate.org_id, mandate.id, agent_id)
            versions = [
                existing
                for existing in self._facility_mandate_records.get(key, [])
                if existing["version"] != mandate.version
            ]
            versions.append(record)
            self._facility_mandate_records[key] = sorted(versions, key=lambda item: int(item["version"]))
            return record
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO facility_mandate_records (
                    mandate_record_id, organization_id, mandate_id, agent_id, version, snapshot,
                    snapshot_hash, created_by, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, NOW())
                ON CONFLICT (organization_id, mandate_id, agent_id, version) DO UPDATE SET
                    snapshot = EXCLUDED.snapshot,
                    snapshot_hash = EXCLUDED.snapshot_hash,
                    created_by = EXCLUDED.created_by,
                    updated_at = NOW()
                """,
                record["mandate_record_id"],
                mandate.org_id,
                mandate.id,
                agent_id,
                mandate.version,
                json.dumps(snapshot),
                snapshot_hash,
                created_by,
            )
        return record

    async def get_latest_facility_mandate_record(
        self,
        *,
        organization_id: str,
        mandate_id: str,
        agent_id: str,
    ) -> dict[str, Any] | None:
        normalized_agent_id = agent_id or ""
        if not self._use_postgres():
            versions = self._facility_mandate_records.get((organization_id, mandate_id, normalized_agent_id), [])
            if not versions and normalized_agent_id:
                versions = self._facility_mandate_records.get((organization_id, mandate_id, ""), [])
            return versions[-1] if versions else None
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM facility_mandate_records
                WHERE organization_id = $1
                  AND mandate_id = $2
                  AND agent_id IN ($3, '')
                ORDER BY version DESC, updated_at DESC
                LIMIT 1
                """,
                organization_id,
                mandate_id,
                normalized_agent_id,
            )
        if not row:
            return None
        record = dict(row)
        if isinstance(record.get("snapshot"), str):
            record["snapshot"] = json.loads(record["snapshot"])
        return record

    @staticmethod
    def _facility_to_record(facility: Facility) -> dict[str, Any]:
        return {
            "facility_id": facility.facility_id,
            "organization_id": facility.organization_id,
            "sponsor_id": facility.sponsor_id,
            "provider": facility.provider,
            "facility_type": facility.facility_type.value,
            "status": facility.status.value,
            "version": facility.version,
            "limit_payload": to_jsonable(facility.limit),
            "allowed_categories": list(facility.allowed_categories),
            "allowed_merchants": list(facility.allowed_merchants),
            "blocked_merchants": list(facility.blocked_merchants),
            "approval_threshold_minor": facility.approval_threshold_minor,
            "metadata": to_jsonable(facility.metadata),
        }

    @staticmethod
    def _facility_from_record(record: dict[str, Any]) -> Facility:
        def _json_value(value: Any) -> Any:
            return json.loads(value) if isinstance(value, str) else value

        limit_payload = _json_value(record.get("limit_payload") or {})
        return Facility(
            facility_id=str(record["facility_id"]),
            organization_id=str(record["organization_id"]),
            sponsor_id=str(record["sponsor_id"]),
            provider=str(record.get("provider") or "simulated"),
            facility_type=FacilityType(str(record.get("facility_type") or FacilityType.SPONSOR_BACKED.value)),
            status=FacilityStatus(str(record.get("status") or FacilityStatus.ACTIVE.value)),
            limit=FacilityLimit(
                per_transaction_minor=int(limit_payload.get("per_transaction_minor", 500_000)),
                daily_minor=limit_payload.get("daily_minor"),
                monthly_minor=limit_payload.get("monthly_minor"),
                currency=str(limit_payload.get("currency") or "USD"),
            ),
            allowed_categories=list(_json_value(record.get("allowed_categories") or [])),
            allowed_merchants=list(_json_value(record.get("allowed_merchants") or [])),
            blocked_merchants=list(_json_value(record.get("blocked_merchants") or [])),
            approval_threshold_minor=int(record.get("approval_threshold_minor") or 100_000),
            version=int(record.get("version") or 1),
            metadata=dict(_json_value(record.get("metadata") or {})),
        )

    async def list_request_states(self, *, organization_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self._use_postgres():
            rows = [
                state for (org_id, _), state in self._request_states.items()
                if org_id == organization_id
            ]
            return rows[-limit:]
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM facility_request_states
                WHERE organization_id = $1
                ORDER BY updated_at DESC
                LIMIT $2
                """,
                organization_id,
                limit,
            )
        return [dict(row) for row in rows]

    async def find_event_by_idempotency_key(
        self,
        *,
        organization_id: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        if not self._use_postgres():
            return self._idempotency.get((organization_id, idempotency_key))
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM facility_events
                WHERE organization_id = $1 AND idempotency_key = $2
                """,
                organization_id,
                idempotency_key,
            )
        return self._row_to_event(row) if row else None

    async def list_aggregate_ids(self, *, organization_id: str) -> list[str]:
        if not self._use_postgres():
            return sorted({
                event["aggregate_id"]
                for event in self._events
                if event["organization_id"] == organization_id
            })
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT aggregate_id FROM facility_events
                WHERE organization_id = $1
                ORDER BY aggregate_id ASC
                """,
                organization_id,
            )
        return [row["aggregate_id"] for row in rows]

    async def replay_request_state(
        self,
        *,
        organization_id: str,
        request_id: str,
        persist: bool = False,
    ) -> dict[str, Any] | None:
        events = await self.list_events(organization_id=organization_id, aggregate_id=request_id)
        state: dict[str, Any] | None = None
        for event in events:
            state = self._project_state_event(state, event)
        if state and persist:
            if not self._use_postgres():
                self._request_states[(organization_id, request_id)] = state
            else:
                await self._persist_request_state(state)
        return state

    async def rebuild_request_states(
        self,
        *,
        organization_id: str,
        persist: bool = False,
    ) -> list[dict[str, Any]]:
        states: list[dict[str, Any]] = []
        for aggregate_id in await self.list_aggregate_ids(organization_id=organization_id):
            state = await self.replay_request_state(
                organization_id=organization_id,
                request_id=aggregate_id,
                persist=persist,
            )
            if state:
                states.append(state)
        return states

    async def verify_request_state_projection(
        self,
        *,
        organization_id: str,
        request_id: str,
    ) -> dict[str, Any]:
        expected = await self.replay_request_state(
            organization_id=organization_id,
            request_id=request_id,
            persist=False,
        )
        current = await self.get_request_state(organization_id=organization_id, request_id=request_id)
        return {
            "organization_id": organization_id,
            "request_id": request_id,
            "ok": self._state_equivalence(expected, current),
            "expected": expected,
            "current": current,
        }

    async def verify_event_hash_chain(self, *, organization_id: str, aggregate_id: str) -> dict[str, Any]:
        events = await self.list_events(organization_id=organization_id, aggregate_id=aggregate_id)
        previous_hash = None
        errors: list[dict[str, Any]] = []
        for event in events:
            payload = event["payload"]
            occurred_at = datetime.fromisoformat(str(event["occurred_at"]))
            expected = self._hash_event(
                event_id=event["event_id"],
                organization_id=organization_id,
                aggregate_id=aggregate_id,
                event_type=event["event_type"],
                payload=payload,
                previous_event_hash=previous_hash,
                occurred_at=occurred_at,
            )
            if event.get("previous_event_hash") != previous_hash:
                errors.append({"event_id": event["event_id"], "error": "previous_event_hash_mismatch"})
            if event.get("event_hash") != expected:
                errors.append({"event_id": event["event_id"], "error": "event_hash_mismatch"})
            previous_hash = event.get("event_hash")
        return {"ok": not errors, "errors": errors, "event_count": len(events)}

    @staticmethod
    def _state_equivalence(expected: dict[str, Any] | None, current: dict[str, Any] | None) -> bool:
        if expected is None or current is None:
            return expected == current
        fields = {
            "request_id",
            "organization_id",
            "facility_id",
            "agent_id",
            "mandate_id",
            "status",
            "latest_decision_id",
            "latest_verdict",
            "merchant",
            "amount_minor",
            "currency",
        }
        return all(expected.get(field) == current.get(field) for field in fields)

    def _project_state_event(
        self,
        state: dict[str, Any] | None,
        event: dict[str, Any],
    ) -> dict[str, Any] | None:
        payload = event["payload"]
        org_id = event["organization_id"]
        aggregate_id = event["aggregate_id"]
        next_state = (state or {}).copy()
        if event["event_type"] == FacilityEventType.REQUEST_CREATED.value:
            request = payload["request"]
            next_state.update(
                {
                    "request_id": aggregate_id,
                    "organization_id": org_id,
                    "facility_id": request["facility_id"],
                    "agent_id": request["agent_id"],
                    "mandate_id": request["mandate_id"],
                    "status": "created",
                    "latest_decision_id": None,
                    "latest_verdict": None,
                    "merchant": request["merchant"],
                    "amount_minor": request["amount_minor"],
                    "currency": request["currency"],
                    "payload": payload,
                    "updated_at": event["occurred_at"],
                }
            )
            next_state.setdefault("events", []).append(event["event_id"])
        elif event["event_type"] in {
            FacilityEventType.AUTH_APPROVED.value,
            FacilityEventType.AUTH_DENIED.value,
            FacilityEventType.AUTH_STEP_UP_REQUIRED.value,
        }:
            decision = payload["decision"]
            next_state.update(
                {
                    "status": decision["verdict"],
                    "latest_decision_id": decision["decision_id"],
                    "latest_verdict": decision["verdict"],
                    "payload": {**next_state.get("payload", {}), "latest_decision": decision},
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.EXECUTION_SIMULATED.value:
            next_state.update(
                {
                    "status": "executed_simulated",
                    "payload": {**next_state.get("payload", {}), "execution": payload.get("credential")},
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.REVOCATION_CREATED.value:
            next_state.update(
                {
                    "status": "revoked",
                    "payload": {**next_state.get("payload", {}), "revocation": payload},
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.EVIDENCE_ATTACHED.value:
            existing = list(next_state.get("payload", {}).get("attached_evidence", []))
            next_state.update(
                {
                    "payload": {
                        **next_state.get("payload", {}),
                        "attached_evidence": [*existing, *payload.get("evidence", [])],
                    },
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.APPROVAL_RECORDED.value:
            next_state.update(
                {
                    "payload": {**next_state.get("payload", {}), "latest_approval": payload},
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.APPROVAL_REQUESTED.value:
            next_state.update(
                {
                    "payload": {**next_state.get("payload", {}), "approval_request": payload},
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.PROVIDER_WEBHOOK_RECEIVED.value and state:
            existing = list(next_state.get("payload", {}).get("provider_webhooks", []))
            next_state.update(
                {
                    "payload": {**next_state.get("payload", {}), "provider_webhooks": [*existing, payload]},
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.SETTLEMENT_UPDATED.value and state:
            existing = list(next_state.get("payload", {}).get("settlements", []))
            next_state.update(
                {
                    "payload": {**next_state.get("payload", {}), "settlements": [*existing, payload]},
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.EXCEPTION_CREATED.value:
            existing = list(next_state.get("payload", {}).get("exceptions", []))
            next_state.update(
                {
                    "payload": {**next_state.get("payload", {}), "exceptions": [*existing, payload]},
                    "updated_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == FacilityEventType.EXCEPTION_RESOLVED.value:
            existing = list(next_state.get("payload", {}).get("exception_resolutions", []))
            next_state.update(
                {
                    "payload": {**next_state.get("payload", {}), "exception_resolutions": [*existing, payload]},
                    "updated_at": event["occurred_at"],
                }
            )
        return next_state or None

    def _project_event(self, event: dict[str, Any]) -> None:
        org_id = event["organization_id"]
        aggregate_id = event["aggregate_id"]
        state = self._project_state_event(self._request_states.get((org_id, aggregate_id)), event)
        if state:
            self._request_states[(org_id, aggregate_id)] = state

    async def _project_postgres_event(self, event: dict[str, Any]) -> None:
        self._project_event(event)
        state = self._request_states.get((event["organization_id"], event["aggregate_id"]))
        if not state:
            return
        await self._persist_request_state(state)

    async def _persist_request_state(self, state: dict[str, Any]) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO facility_request_states (
                    request_id, organization_id, facility_id, agent_id, mandate_id, status,
                    latest_decision_id, latest_verdict, merchant, amount_minor, currency, payload, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, NOW())
                ON CONFLICT (request_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    latest_decision_id = EXCLUDED.latest_decision_id,
                    latest_verdict = EXCLUDED.latest_verdict,
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
                """,
                state["request_id"],
                state["organization_id"],
                state["facility_id"],
                state["agent_id"],
                state["mandate_id"],
                state["status"],
                state.get("latest_decision_id"),
                state.get("latest_verdict"),
                state["merchant"],
                state["amount_minor"],
                state["currency"],
                json.dumps(to_jsonable(state["payload"])),
            )
