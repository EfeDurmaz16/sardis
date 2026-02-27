"""Repository for enterprise support SLA profiles and support tickets."""

from __future__ import annotations

import os
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Optional


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EnterpriseSupportRepository:
    """Support ticket storage with in-memory fallback and optional PostgreSQL persistence."""

    _PLAN_SLA: dict[str, dict[str, Any]] = {
        "free": {
            "first_response_sla_minutes": 1440,
            "resolution_sla_hours": 72,
            "channels": ["email"],
            "pager": False,
        },
        "pro": {
            "first_response_sla_minutes": 240,
            "resolution_sla_hours": 24,
            "channels": ["email", "slack_connect"],
            "pager": False,
        },
        "enterprise": {
            "first_response_sla_minutes": 30,
            "resolution_sla_hours": 4,
            "channels": ["email", "slack_connect", "pager"],
            "pager": True,
        },
    }
    _PRIORITY_MULTIPLIER: dict[str, float] = {
        "low": 1.25,
        "medium": 1.0,
        "high": 0.75,
        "urgent": 0.5,
    }

    def __init__(self, pool=None, dsn: str | None = None):
        self._pool = pool
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._table_ready = False
        self._tickets_mem: dict[str, dict[str, Any]] = {}
        self._org_plan_overrides = self._load_org_plan_overrides()
        self._default_plan = (
            (os.getenv("SARDIS_ENTERPRISE_DEFAULT_PLAN", "pro") or "pro").strip().lower()
        )
        if self._default_plan not in self._PLAN_SLA:
            self._default_plan = "pro"

    @staticmethod
    def _load_org_plan_overrides() -> dict[str, str]:
        raw = (os.getenv("SARDIS_ENTERPRISE_ORG_PLAN_OVERRIDES_JSON", "") or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, str] = {}
        for org_id, plan in parsed.items():
            org_key = str(org_id).strip()
            plan_value = str(plan).strip().lower()
            if not org_key or not plan_value:
                continue
            out[org_key] = plan_value
        return out

    def _use_postgres(self) -> bool:
        if self._pool is not None:
            return True
        return self._dsn.startswith(("postgresql://", "postgres://"))

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    async def _ensure_table(self) -> None:
        if self._table_ready or not self._use_postgres():
            return
        pool = await self._get_pool()
        if pool is None:
            return
        env = (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").strip().lower()
        async with pool.acquire() as conn:
            if env in {"prod", "production"}:
                exists = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_name = 'enterprise_support_tickets'
                    )
                    """
                )
                if not exists:
                    raise RuntimeError(
                        "enterprise_support_tickets table not found in production; "
                        "run migrations before starting API"
                    )
            else:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS enterprise_support_tickets (
                        id TEXT PRIMARY KEY,
                        organization_id TEXT NOT NULL,
                        requester_id TEXT NOT NULL,
                        requester_kind TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        description TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        category TEXT NOT NULL,
                        status TEXT NOT NULL,
                        first_response_due_at TIMESTAMPTZ NOT NULL,
                        resolution_due_at TIMESTAMPTZ NOT NULL,
                        acknowledged_at TIMESTAMPTZ NULL,
                        resolved_at TIMESTAMPTZ NULL,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_support_tickets_org_created
                      ON enterprise_support_tickets(organization_id, created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_support_tickets_org_status
                      ON enterprise_support_tickets(organization_id, status);
                    CREATE INDEX IF NOT EXISTS idx_support_tickets_org_priority
                      ON enterprise_support_tickets(organization_id, priority);
                    """
                )
        self._table_ready = True

    @staticmethod
    def _normalize_text(value: str) -> str:
        return (value or "").strip()

    def get_support_profile(self, organization_id: str) -> dict[str, Any]:
        org_id = self._normalize_text(organization_id)
        plan = self._org_plan_overrides.get(org_id, self._default_plan)
        if plan not in self._PLAN_SLA:
            plan = "pro"
        cfg = self._PLAN_SLA[plan]
        return {
            "organization_id": org_id,
            "plan": plan,
            "first_response_sla_minutes": int(cfg["first_response_sla_minutes"]),
            "resolution_sla_hours": int(cfg["resolution_sla_hours"]),
            "channels": list(cfg["channels"]),
            "pager": bool(cfg["pager"]),
        }

    def _compute_due_times(self, organization_id: str, priority: str) -> tuple[datetime, datetime]:
        now = _utc_now()
        profile = self.get_support_profile(organization_id)
        pri = self._normalize_text(priority).lower()
        factor = self._PRIORITY_MULTIPLIER.get(pri, 1.0)
        response_minutes = max(1, int(profile["first_response_sla_minutes"] * factor))
        resolution_hours = max(1, int(profile["resolution_sla_hours"] * factor))
        return (
            now + timedelta(minutes=response_minutes),
            now + timedelta(hours=resolution_hours),
        )

    async def create_ticket(
        self,
        *,
        organization_id: str,
        requester_id: str,
        requester_kind: str,
        subject: str,
        description: str,
        priority: str,
        category: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        org_id = self._normalize_text(organization_id)
        ticket_id = f"sup_{uuid.uuid4().hex[:16]}"
        now = _utc_now()
        response_due_at, resolution_due_at = self._compute_due_times(org_id, priority)
        row: dict[str, Any] = {
            "id": ticket_id,
            "organization_id": org_id,
            "requester_id": self._normalize_text(requester_id),
            "requester_kind": self._normalize_text(requester_kind) or "unknown",
            "subject": self._normalize_text(subject),
            "description": self._normalize_text(description),
            "priority": self._normalize_text(priority).lower() or "medium",
            "category": self._normalize_text(category).lower() or "other",
            "status": "open",
            "first_response_due_at": response_due_at,
            "resolution_due_at": resolution_due_at,
            "acknowledged_at": None,
            "resolved_at": None,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }

        if not self._use_postgres():
            self._tickets_mem[ticket_id] = row
            return row

        await self._ensure_table()
        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("enterprise_support_repository_pool_unavailable")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO enterprise_support_tickets (
                    id, organization_id, requester_id, requester_kind,
                    subject, description, priority, category, status,
                    first_response_due_at, resolution_due_at,
                    acknowledged_at, resolved_at, metadata, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4,
                    $5, $6, $7, $8, $9,
                    $10, $11, NULL, NULL, $12::jsonb, NOW(), NOW()
                )
                """,
                row["id"],
                row["organization_id"],
                row["requester_id"],
                row["requester_kind"],
                row["subject"],
                row["description"],
                row["priority"],
                row["category"],
                row["status"],
                row["first_response_due_at"],
                row["resolution_due_at"],
                row["metadata"],
            )
            db_row = await conn.fetchrow(
                "SELECT * FROM enterprise_support_tickets WHERE id = $1",
                row["id"],
            )
        return dict(db_row) if db_row else row

    async def list_tickets(
        self,
        *,
        organization_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        org_id = self._normalize_text(organization_id)
        s = self._normalize_text(status).lower() if status else None
        p = self._normalize_text(priority).lower() if priority else None
        if not self._use_postgres():
            rows = [
                value
                for value in self._tickets_mem.values()
                if value.get("organization_id") == org_id
            ]
            if s:
                rows = [r for r in rows if str(r.get("status", "")).lower() == s]
            if p:
                rows = [r for r in rows if str(r.get("priority", "")).lower() == p]
            rows.sort(key=lambda row: row.get("created_at") or _utc_now(), reverse=True)
            return rows[offset : offset + limit]

        await self._ensure_table()
        pool = await self._get_pool()
        if pool is None:
            return []
        query = "SELECT * FROM enterprise_support_tickets WHERE organization_id = $1"
        args: list[Any] = [org_id]
        idx = 2
        if s:
            query += f" AND status = ${idx}"
            args.append(s)
            idx += 1
        if p:
            query += f" AND priority = ${idx}"
            args.append(p)
            idx += 1
        query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        args.extend([int(limit), int(offset)])
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]

    async def get_ticket(self, *, organization_id: str, ticket_id: str) -> Optional[dict[str, Any]]:
        org_id = self._normalize_text(organization_id)
        tid = self._normalize_text(ticket_id)
        if not self._use_postgres():
            row = self._tickets_mem.get(tid)
            if not row or row.get("organization_id") != org_id:
                return None
            return row
        await self._ensure_table()
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM enterprise_support_tickets
                WHERE organization_id = $1 AND id = $2
                """,
                org_id,
                tid,
            )
        return dict(row) if row else None

    async def acknowledge_ticket(
        self,
        *,
        organization_id: str,
        ticket_id: str,
        actor_id: str,
    ) -> Optional[dict[str, Any]]:
        now = _utc_now()
        row = await self.get_ticket(organization_id=organization_id, ticket_id=ticket_id)
        if row is None:
            return None
        if str(row.get("status")) in {"resolved", "closed"}:
            return row

        if not self._use_postgres():
            row["status"] = "acknowledged"
            row["acknowledged_at"] = now
            meta = dict(row.get("metadata") or {})
            meta["acknowledged_by"] = actor_id
            row["metadata"] = meta
            row["updated_at"] = now
            return row

        await self._ensure_table()
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            db_row = await conn.fetchrow(
                """
                UPDATE enterprise_support_tickets
                SET status = 'acknowledged',
                    acknowledged_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) || $3::jsonb,
                    updated_at = NOW()
                WHERE organization_id = $1 AND id = $2
                RETURNING *
                """,
                self._normalize_text(organization_id),
                self._normalize_text(ticket_id),
                {"acknowledged_by": actor_id},
            )
        return dict(db_row) if db_row else None

    async def resolve_ticket(
        self,
        *,
        organization_id: str,
        ticket_id: str,
        actor_id: str,
        resolution_note: str | None = None,
    ) -> Optional[dict[str, Any]]:
        now = _utc_now()
        row = await self.get_ticket(organization_id=organization_id, ticket_id=ticket_id)
        if row is None:
            return None
        if str(row.get("status")) in {"resolved", "closed"}:
            return row

        if not self._use_postgres():
            row["status"] = "resolved"
            row["resolved_at"] = now
            meta = dict(row.get("metadata") or {})
            meta["resolved_by"] = actor_id
            if resolution_note:
                meta["resolution_note"] = resolution_note
            row["metadata"] = meta
            row["updated_at"] = now
            return row

        await self._ensure_table()
        pool = await self._get_pool()
        if pool is None:
            return None
        meta: dict[str, Any] = {"resolved_by": actor_id}
        if resolution_note:
            meta["resolution_note"] = resolution_note
        async with pool.acquire() as conn:
            db_row = await conn.fetchrow(
                """
                UPDATE enterprise_support_tickets
                SET status = 'resolved',
                    resolved_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) || $3::jsonb,
                    updated_at = NOW()
                WHERE organization_id = $1 AND id = $2
                RETURNING *
                """,
                self._normalize_text(organization_id),
                self._normalize_text(ticket_id),
                meta,
            )
        return dict(db_row) if db_row else None

