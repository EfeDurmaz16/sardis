"""Repository for canonical cross-rail ledger normalization and reconciliation ops."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib
import os
import uuid

from sardis_api.canonical_state_machine import CanonicalEvent, apply_state_transition


@dataclass(frozen=True)
class CanonicalIngestResult:
    journey: dict[str, Any]
    event: dict[str, Any] | None
    duplicate: bool
    out_of_order: bool
    break_detected: bool
    manual_review_created: bool


class CanonicalLedgerRepository:
    def __init__(self, pool=None, dsn: str | None = None) -> None:
        self._pool = pool
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._journeys: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._event_keys: set[tuple[str, str]] = set()
        self._breaks: list[dict[str, Any]] = []
        self._manual_reviews: list[dict[str, Any]] = []

    def _use_postgres(self) -> bool:
        if self._pool is not None:
            return True
        return self._dsn.startswith(("postgresql://", "postgres://"))

    async def _get_pool(self):
        if self._pool is None:
            if not self._use_postgres():
                return None
            import asyncpg

            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=8)
        return self._pool

    @staticmethod
    def _journey_id(organization_id: str, rail: str, external_reference: str) -> str:
        digest = hashlib.sha256(f"{organization_id}:{rail}:{external_reference}".encode()).hexdigest()
        return f"jrny_{digest[:24]}"

    async def _existing_provider_event(self, provider: str, provider_event_id: str) -> bool:
        if not provider_event_id:
            return False
        key = (provider, provider_event_id)
        if not self._use_postgres():
            return key in self._event_keys
        pool = await self._get_pool()
        if pool is None:
            return False
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1
                FROM canonical_ledger_events
                WHERE provider = $1 AND provider_event_id = $2
                LIMIT 1
                """,
                provider,
                provider_event_id,
            )
            return row is not None

    async def _get_or_create_journey(
        self,
        *,
        organization_id: str,
        rail: str,
        provider: str,
        external_reference: str,
        currency: str,
        direction: Optional[str],
        event_ts: datetime,
    ) -> dict[str, Any]:
        key = (organization_id, rail, external_reference)
        journey_id = self._journey_id(organization_id, rail, external_reference)
        if not self._use_postgres():
            existing = self._journeys.get(key)
            if existing:
                return existing
            row = {
                "journey_id": journey_id,
                "organization_id": organization_id,
                "rail": rail,
                "provider": provider,
                "external_reference": external_reference,
                "direction": direction,
                "currency": currency or "USD",
                "canonical_state": "created",
                "expected_amount_minor": 0,
                "settled_amount_minor": 0,
                "retry_count": 0,
                "last_return_code": None,
                "break_status": "ok",
                "first_event_at": event_ts,
                "last_event_at": event_ts,
                "metadata": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._journeys[key] = row
            return row

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO canonical_ledger_journeys (
                    journey_id, organization_id, rail, provider, external_reference,
                    direction, currency, canonical_state, first_event_at, last_event_at,
                    metadata, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, 'created', $8, $8, '{}'::jsonb, NOW(), NOW()
                )
                ON CONFLICT (organization_id, rail, external_reference) DO NOTHING
                """,
                journey_id,
                organization_id,
                rail,
                provider,
                external_reference,
                direction,
                currency or "USD",
                event_ts,
            )
            row = await conn.fetchrow(
                """
                SELECT * FROM canonical_ledger_journeys
                WHERE organization_id = $1 AND rail = $2 AND external_reference = $3
                """,
                organization_id,
                rail,
                external_reference,
            )
            if row is None:
                raise RuntimeError("failed to get canonical journey after upsert")
            return dict(row)

    async def _create_break(
        self,
        *,
        organization_id: str,
        journey_id: str,
        break_type: str,
        severity: str,
        expected_amount_minor: Optional[int],
        settled_amount_minor: Optional[int],
        delta_minor: Optional[int],
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        # Avoid spamming duplicate open breaks for the same journey/type.
        if not self._use_postgres():
            for b in self._breaks:
                if (
                    b.get("organization_id") == organization_id
                    and b.get("journey_id") == journey_id
                    and b.get("break_type") == break_type
                    and b.get("status") == "open"
                ):
                    return False
            self._breaks.append(
                {
                    "break_id": str(uuid.uuid4()),
                    "organization_id": organization_id,
                    "journey_id": journey_id,
                    "break_type": break_type,
                    "severity": severity,
                    "expected_amount_minor": expected_amount_minor,
                    "settled_amount_minor": settled_amount_minor,
                    "delta_minor": delta_minor,
                    "status": "open",
                    "metadata": metadata or {},
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            return True

        pool = await self._get_pool()
        if pool is None:
            return False
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                """
                SELECT 1
                FROM reconciliation_breaks
                WHERE organization_id = $1
                  AND journey_id = $2
                  AND break_type = $3
                  AND status = 'open'
                LIMIT 1
                """,
                organization_id,
                journey_id,
                break_type,
            )
            if existing:
                return False
            await conn.execute(
                """
                INSERT INTO reconciliation_breaks (
                    break_id, organization_id, journey_id, break_type, severity,
                    expected_amount_minor, settled_amount_minor, delta_minor, status, metadata, detected_at
                ) VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, 'open', $9::jsonb, NOW())
                """,
                str(uuid.uuid4()),
                organization_id,
                journey_id,
                break_type,
                severity,
                expected_amount_minor,
                settled_amount_minor,
                delta_minor,
                metadata or {},
            )
            return True

    async def enqueue_manual_review(
        self,
        *,
        organization_id: str,
        journey_id: Optional[str],
        reason_code: str,
        priority: str = "medium",
        payload: Optional[dict[str, Any]] = None,
    ) -> bool:
        if not self._use_postgres():
            for review in self._manual_reviews:
                if (
                    review.get("organization_id") == organization_id
                    and review.get("journey_id") == journey_id
                    and review.get("reason_code") == reason_code
                    and review.get("status") in {"queued", "in_review"}
                ):
                    return False
            self._manual_reviews.append(
                {
                    "review_id": str(uuid.uuid4()),
                    "organization_id": organization_id,
                    "journey_id": journey_id,
                    "reason_code": reason_code,
                    "priority": priority,
                    "status": "queued",
                    "assigned_to": None,
                    "payload": payload or {},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "resolved_at": None,
                }
            )
            return True

        pool = await self._get_pool()
        if pool is None:
            return False
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                """
                SELECT 1
                FROM manual_review_queue
                WHERE organization_id = $1
                  AND COALESCE(journey_id, '') = COALESCE($2, '')
                  AND reason_code = $3
                  AND status IN ('queued', 'in_review')
                LIMIT 1
                """,
                organization_id,
                journey_id,
                reason_code,
            )
            if existing:
                return False
            await conn.execute(
                """
                INSERT INTO manual_review_queue (
                    review_id, organization_id, journey_id, reason_code, priority,
                    status, payload, created_at, updated_at
                ) VALUES ($1::uuid, $2, $3, $4, $5, 'queued', $6::jsonb, NOW(), NOW())
                """,
                str(uuid.uuid4()),
                organization_id,
                journey_id,
                reason_code,
                priority,
                payload or {},
            )
            return True

    async def ingest_event(
        self,
        event: CanonicalEvent,
        *,
        drift_tolerance_minor: int = 0,
    ) -> CanonicalIngestResult:
        if not event.organization_id:
            raise ValueError("organization_id is required")
        if not event.rail:
            raise ValueError("rail is required")
        if not event.external_reference:
            raise ValueError("external_reference is required")

        provider = str(event.provider or "unknown").strip().lower()
        provider_event_id = (event.provider_event_id or "").strip()
        if provider_event_id and await self._existing_provider_event(provider, provider_event_id):
            journey = await self._get_or_create_journey(
                organization_id=event.organization_id,
                rail=event.rail,
                provider=provider,
                external_reference=event.external_reference,
                currency=event.currency or "USD",
                direction=event.direction,
                event_ts=event.event_ts or datetime.now(timezone.utc),
            )
            return CanonicalIngestResult(
                journey=journey,
                event=None,
                duplicate=True,
                out_of_order=False,
                break_detected=False,
                manual_review_created=False,
            )

        event_ts = event.event_ts or datetime.now(timezone.utc)
        journey = await self._get_or_create_journey(
            organization_id=event.organization_id,
            rail=event.rail,
            provider=provider,
            external_reference=event.external_reference,
            currency=event.currency or "USD",
            direction=event.direction,
            event_ts=event_ts,
        )

        current_state = str(journey.get("canonical_state", "") or "created")
        next_state, out_of_order = apply_state_transition(current_state, event.canonical_state)

        expected_amount = int(journey.get("expected_amount_minor", 0) or 0)
        settled_amount = int(journey.get("settled_amount_minor", 0) or 0)
        if event.amount_minor is not None and expected_amount <= 0:
            expected_amount = int(event.amount_minor)
        if event.canonical_state == "settled" and event.amount_minor is not None:
            settled_amount = int(event.amount_minor)
        if event.canonical_state in {"returned", "failed"}:
            settled_amount = 0

        last_event_at = event_ts
        if isinstance(journey.get("last_event_at"), datetime) and journey["last_event_at"] > event_ts:
            out_of_order = True
            last_event_at = journey["last_event_at"]

        break_detected = False
        manual_review_created = False
        delta_minor: Optional[int] = None
        if next_state == "settled" and expected_amount > 0:
            delta_minor = abs(expected_amount - settled_amount)
            if delta_minor > max(0, int(drift_tolerance_minor)):
                break_detected = await self._create_break(
                    organization_id=event.organization_id,
                    journey_id=str(journey.get("journey_id")),
                    break_type="expected_settled_mismatch",
                    severity="high" if delta_minor > max(1000, drift_tolerance_minor * 5) else "medium",
                    expected_amount_minor=expected_amount,
                    settled_amount_minor=settled_amount,
                    delta_minor=delta_minor,
                    metadata={
                        "rail": event.rail,
                        "provider": provider,
                    },
                )
                if break_detected:
                    manual_review_created = await self.enqueue_manual_review(
                        organization_id=event.organization_id,
                        journey_id=str(journey.get("journey_id")),
                        reason_code="drift_mismatch",
                        priority="high",
                        payload={
                            "expected_amount_minor": expected_amount,
                            "settled_amount_minor": settled_amount,
                            "delta_minor": delta_minor,
                        },
                    )

        if event.return_code in {"R29"}:
            created = await self._create_break(
                organization_id=event.organization_id,
                journey_id=str(journey.get("journey_id")),
                break_type="provider_return_high_risk",
                severity="critical",
                expected_amount_minor=expected_amount,
                settled_amount_minor=settled_amount,
                delta_minor=None,
                metadata={"return_code": event.return_code},
            )
            break_detected = break_detected or created
            review = await self.enqueue_manual_review(
                organization_id=event.organization_id,
                journey_id=str(journey.get("journey_id")),
                reason_code="R29",
                priority="critical",
                payload={"return_code": event.return_code},
            )
            manual_review_created = manual_review_created or review

        if not self._use_postgres():
            journey.update(
                {
                    "provider": provider,
                    "direction": event.direction or journey.get("direction"),
                    "currency": event.currency or journey.get("currency", "USD"),
                    "canonical_state": next_state or current_state,
                    "expected_amount_minor": expected_amount,
                    "settled_amount_minor": settled_amount,
                    "last_return_code": event.return_code or journey.get("last_return_code"),
                    "first_event_at": journey.get("first_event_at") or event_ts,
                    "last_event_at": last_event_at,
                    "break_status": "review_open" if manual_review_created else ("drift_open" if break_detected else journey.get("break_status", "ok")),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            event_row = {
                "id": str(uuid.uuid4()),
                "journey_id": journey.get("journey_id"),
                "organization_id": event.organization_id,
                "provider": provider,
                "provider_event_id": provider_event_id or None,
                "provider_event_type": event.provider_event_type,
                "canonical_event_type": event.canonical_event_type,
                "canonical_state": event.canonical_state,
                "event_ts": event_ts.isoformat(),
                "amount_minor": event.amount_minor,
                "currency": event.currency,
                "return_code": event.return_code,
                "out_of_order": out_of_order,
                "metadata": event.metadata or {},
                "raw_payload": event.raw_payload or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._events.append(event_row)
            if provider_event_id:
                self._event_keys.add((provider, provider_event_id))
            return CanonicalIngestResult(
                journey=journey,
                event=event_row,
                duplicate=False,
                out_of_order=out_of_order,
                break_detected=break_detected,
                manual_review_created=manual_review_created,
            )

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            updated_row = await conn.fetchrow(
                """
                UPDATE canonical_ledger_journeys
                SET provider = $4,
                    direction = COALESCE($5, direction),
                    currency = COALESCE($6, currency),
                    canonical_state = COALESCE($7, canonical_state),
                    expected_amount_minor = $8,
                    settled_amount_minor = $9,
                    last_return_code = COALESCE($10, last_return_code),
                    last_event_at = $11,
                    break_status = CASE
                        WHEN $12 THEN 'review_open'
                        WHEN $13 THEN 'drift_open'
                        ELSE break_status
                    END,
                    updated_at = NOW()
                WHERE journey_id = $1
                RETURNING *
                """,
                journey.get("journey_id"),
                journey.get("organization_id"),
                journey.get("rail"),
                provider,
                event.direction,
                event.currency,
                next_state,
                expected_amount,
                settled_amount,
                event.return_code,
                last_event_at,
                manual_review_created,
                break_detected,
            )
            if updated_row is None:
                raise RuntimeError("failed to update canonical journey")

            inserted = await conn.fetchrow(
                """
                INSERT INTO canonical_ledger_events (
                    id, journey_id, organization_id, provider, provider_event_id, provider_event_type,
                    canonical_event_type, canonical_state, event_ts, amount_minor, currency, return_code,
                    out_of_order, metadata, raw_payload, created_at
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11, $12,
                    $13, $14::jsonb, $15::jsonb, NOW()
                )
                RETURNING id, journey_id, organization_id, provider, provider_event_id, provider_event_type,
                          canonical_event_type, canonical_state, event_ts, amount_minor, currency, return_code,
                          out_of_order, metadata, raw_payload, created_at
                """,
                str(uuid.uuid4()),
                journey.get("journey_id"),
                event.organization_id,
                provider,
                provider_event_id or None,
                event.provider_event_type,
                event.canonical_event_type,
                event.canonical_state,
                event_ts,
                event.amount_minor,
                event.currency,
                event.return_code,
                out_of_order,
                event.metadata or {},
                event.raw_payload or {},
            )
            return CanonicalIngestResult(
                journey=dict(updated_row),
                event=dict(inserted) if inserted else None,
                duplicate=False,
                out_of_order=out_of_order,
                break_detected=break_detected,
                manual_review_created=manual_review_created,
            )

    async def bump_retry_count(
        self,
        *,
        organization_id: str,
        rail: str,
        external_reference: str,
        max_retry: int = 2,
    ) -> dict[str, Any] | None:
        key = (organization_id, rail, external_reference)
        if not self._use_postgres():
            row = self._journeys.get(key)
            if not row:
                return None
            row["retry_count"] = int(row.get("retry_count", 0) or 0) + 1
            if int(row["retry_count"]) >= max_retry:
                await self.enqueue_manual_review(
                    organization_id=organization_id,
                    journey_id=str(row.get("journey_id")),
                    reason_code="retry_exhausted",
                    priority="high",
                    payload={"retry_count": row["retry_count"]},
                )
            row["updated_at"] = datetime.now(timezone.utc).isoformat()
            return row

        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE canonical_ledger_journeys
                SET retry_count = retry_count + 1,
                    updated_at = NOW()
                WHERE organization_id = $1
                  AND rail = $2
                  AND external_reference = $3
                RETURNING *
                """,
                organization_id,
                rail,
                external_reference,
            )
            row_dict = dict(row) if row else None
            if row_dict and int(row_dict.get("retry_count", 0) or 0) >= max_retry:
                await self.enqueue_manual_review(
                    organization_id=organization_id,
                    journey_id=str(row_dict.get("journey_id")),
                    reason_code="retry_exhausted",
                    priority="high",
                    payload={"retry_count": int(row_dict.get("retry_count", 0) or 0)},
                )
            return row_dict

    async def list_journeys(
        self,
        organization_id: str,
        *,
        rail: Optional[str] = None,
        canonical_state: Optional[str] = None,
        break_status: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not self._use_postgres():
            rows = [j for j in self._journeys.values() if j.get("organization_id") == organization_id]
            if rail:
                rows = [j for j in rows if str(j.get("rail", "")) == rail]
            if canonical_state:
                rows = [j for j in rows if str(j.get("canonical_state", "")) == canonical_state]
            if break_status:
                rows = [j for j in rows if str(j.get("break_status", "")) == break_status]
            rows.sort(key=lambda r: str(r.get("updated_at", "")), reverse=True)
            return rows[:limit]

        pool = await self._get_pool()
        if pool is None:
            return []
        query = """
            SELECT *
            FROM canonical_ledger_journeys
            WHERE organization_id = $1
        """
        args: list[Any] = [organization_id]
        pos = 2
        if rail:
            query += f" AND rail = ${pos}"
            args.append(rail)
            pos += 1
        if canonical_state:
            query += f" AND canonical_state = ${pos}"
            args.append(canonical_state)
            pos += 1
        if break_status:
            query += f" AND break_status = ${pos}"
            args.append(break_status)
            pos += 1
        query += f" ORDER BY updated_at DESC LIMIT ${pos}"
        args.append(limit)
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(r) for r in rows]

    async def list_breaks(
        self,
        organization_id: str,
        *,
        status_value: str = "open",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not self._use_postgres():
            rows = [b for b in self._breaks if b.get("organization_id") == organization_id]
            if status_value:
                rows = [b for b in rows if b.get("status") == status_value]
            rows.sort(key=lambda r: str(r.get("detected_at", "")), reverse=True)
            return rows[:limit]

        pool = await self._get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT *
                FROM reconciliation_breaks
                WHERE organization_id = $1
                  AND ($2::text IS NULL OR status = $2)
                ORDER BY detected_at DESC
                LIMIT $3
                """,
                organization_id,
                status_value if status_value else None,
                limit,
            )
            return [dict(r) for r in rows]

    async def list_manual_reviews(
        self,
        organization_id: str,
        *,
        status_value: str = "queued",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not self._use_postgres():
            rows = [r for r in self._manual_reviews if r.get("organization_id") == organization_id]
            if status_value:
                rows = [r for r in rows if r.get("status") == status_value]
            rows.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
            return rows[:limit]

        pool = await self._get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT *
                FROM manual_review_queue
                WHERE organization_id = $1
                  AND ($2::text IS NULL OR status = $2)
                ORDER BY created_at DESC
                LIMIT $3
                """,
                organization_id,
                status_value if status_value else None,
                limit,
            )
            return [dict(r) for r in rows]

    async def resolve_manual_review(
        self,
        *,
        organization_id: str,
        review_id: str,
        status_value: str,
        notes: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        if status_value not in {"resolved", "dismissed", "in_review"}:
            raise ValueError("invalid manual review status")
        if not self._use_postgres():
            for row in self._manual_reviews:
                if row.get("review_id") == review_id and row.get("organization_id") == organization_id:
                    row["status"] = status_value
                    row["updated_at"] = datetime.now(timezone.utc).isoformat()
                    if status_value in {"resolved", "dismissed"}:
                        row["resolved_at"] = datetime.now(timezone.utc).isoformat()
                    payload = dict(row.get("payload") or {})
                    if notes:
                        payload["resolution_notes"] = notes
                    row["payload"] = payload
                    return row
            return None

        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE manual_review_queue
                SET status = $3,
                    payload = CASE
                        WHEN $4::text IS NULL OR $4 = '' THEN payload
                        ELSE payload || jsonb_build_object('resolution_notes', $4::text)
                    END,
                    resolved_at = CASE
                        WHEN $3 IN ('resolved', 'dismissed') THEN NOW()
                        ELSE resolved_at
                    END,
                    updated_at = NOW()
                WHERE organization_id = $1 AND review_id = $2::uuid
                RETURNING *
                """,
                organization_id,
                review_id,
                status_value,
                notes or "",
            )
            return dict(row) if row else None

    async def export_audit_evidence(
        self,
        organization_id: str,
        *,
        journey_id: Optional[str] = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        if not self._use_postgres():
            journeys = [j for j in self._journeys.values() if j.get("organization_id") == organization_id]
            if journey_id:
                journeys = [j for j in journeys if j.get("journey_id") == journey_id]
            events = [e for e in self._events if e.get("organization_id") == organization_id]
            if journey_id:
                events = [e for e in events if e.get("journey_id") == journey_id]
            breaks = [b for b in self._breaks if b.get("organization_id") == organization_id]
            if journey_id:
                breaks = [b for b in breaks if b.get("journey_id") == journey_id]
            reviews = [r for r in self._manual_reviews if r.get("organization_id") == organization_id]
            if journey_id:
                reviews = [r for r in reviews if r.get("journey_id") == journey_id]
            return {
                "organization_id": organization_id,
                "journeys": journeys[:limit],
                "events": events[:limit],
                "breaks": breaks[:limit],
                "manual_reviews": reviews[:limit],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        pool = await self._get_pool()
        if pool is None:
            return {
                "organization_id": organization_id,
                "journeys": [],
                "events": [],
                "breaks": [],
                "manual_reviews": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        async with pool.acquire() as conn:
            if journey_id:
                journeys_rows = await conn.fetch(
                    """
                    SELECT * FROM canonical_ledger_journeys
                    WHERE organization_id = $1 AND journey_id = $2
                    ORDER BY updated_at DESC
                    LIMIT $3
                    """,
                    organization_id,
                    journey_id,
                    limit,
                )
                events_rows = await conn.fetch(
                    """
                    SELECT * FROM canonical_ledger_events
                    WHERE organization_id = $1 AND journey_id = $2
                    ORDER BY event_ts DESC
                    LIMIT $3
                    """,
                    organization_id,
                    journey_id,
                    limit,
                )
                breaks_rows = await conn.fetch(
                    """
                    SELECT * FROM reconciliation_breaks
                    WHERE organization_id = $1 AND journey_id = $2
                    ORDER BY detected_at DESC
                    LIMIT $3
                    """,
                    organization_id,
                    journey_id,
                    limit,
                )
                reviews_rows = await conn.fetch(
                    """
                    SELECT * FROM manual_review_queue
                    WHERE organization_id = $1 AND journey_id = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                    """,
                    organization_id,
                    journey_id,
                    limit,
                )
            else:
                journeys_rows = await conn.fetch(
                    """
                    SELECT * FROM canonical_ledger_journeys
                    WHERE organization_id = $1
                    ORDER BY updated_at DESC
                    LIMIT $2
                    """,
                    organization_id,
                    limit,
                )
                events_rows = await conn.fetch(
                    """
                    SELECT * FROM canonical_ledger_events
                    WHERE organization_id = $1
                    ORDER BY event_ts DESC
                    LIMIT $2
                    """,
                    organization_id,
                    limit,
                )
                breaks_rows = await conn.fetch(
                    """
                    SELECT * FROM reconciliation_breaks
                    WHERE organization_id = $1
                    ORDER BY detected_at DESC
                    LIMIT $2
                    """,
                    organization_id,
                    limit,
                )
                reviews_rows = await conn.fetch(
                    """
                    SELECT * FROM manual_review_queue
                    WHERE organization_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    organization_id,
                    limit,
                )
            return {
                "organization_id": organization_id,
                "journeys": [dict(r) for r in journeys_rows],
                "events": [dict(r) for r in events_rows],
                "breaks": [dict(r) for r in breaks_rows],
                "manual_reviews": [dict(r) for r in reviews_rows],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
