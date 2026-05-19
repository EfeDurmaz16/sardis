"""Agent activity query endpoints.

Provides paginated access to the ``api_activity_log`` table, scoped to the
caller's organisation.
"""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from sardis_server.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


class ActivityEntry(BaseModel):
    id: int
    org_id: str
    principal_kind: str | None = None
    actor_id: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    method: str
    path: str
    status_code: int
    latency_ms: int | None = None
    wallet_id: str | None = None
    request_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    created_at: str


class ActivitySummary(BaseModel):
    agent_id: str
    request_count: int
    error_count: int
    avg_latency_ms: float | None = None
    unique_endpoints: int
    first_seen: str | None = None
    last_seen: str | None = None


@router.get("/{agent_id}/activity")
async def get_agent_activity(
    agent_id: str,
    principal: Principal = Depends(require_principal),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    method: str | None = Query(default=None, description="Filter by HTTP method"),
    since: datetime | None = Query(default=None, description="Only entries after this timestamp"),
) -> dict:
    """Paginated activity log for a specific agent."""
    from sardis_v2_core.database import Database

    pool = await Database.get_pool()

    conditions = ["org_id = $1", "agent_id = $2"]
    params: list = [principal.organization_id, agent_id]
    idx = 3

    if method:
        conditions.append(f"method = ${idx}")
        params.append(method.upper())
        idx += 1

    if since:
        conditions.append(f"created_at >= ${idx}")
        params.append(since)
        idx += 1

    where = " AND ".join(conditions)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM api_activity_log WHERE {where} "  # noqa: S608
            f"ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *params,
            limit,
            offset,
        )
        count_row = await conn.fetchrow(
            f"SELECT count(*) as total FROM api_activity_log WHERE {where}",  # noqa: S608
            *params,
        )

    total = count_row["total"] if count_row else 0

    entries = [
        ActivityEntry(
            id=r["id"],
            org_id=r["org_id"],
            principal_kind=r["principal_kind"],
            actor_id=r["actor_id"],
            agent_id=r["agent_id"],
            session_id=r["session_id"],
            method=r["method"],
            path=r["path"],
            status_code=r["status_code"],
            latency_ms=r["latency_ms"],
            wallet_id=r["wallet_id"],
            request_id=r["request_id"],
            ip=str(r["ip"]) if r["ip"] else None,
            user_agent=r["user_agent"],
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
        )
        for r in rows
    ]

    return {"data": [e.model_dump() for e in entries], "total": total, "limit": limit, "offset": offset}


@router.get("/{agent_id}/activity/summary")
async def get_agent_activity_summary(
    agent_id: str,
    principal: Principal = Depends(require_principal),
) -> ActivitySummary:
    """Aggregate activity summary for an agent."""
    from sardis_v2_core.database import Database

    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                count(*)                                       AS request_count,
                count(*) FILTER (WHERE status_code >= 400)     AS error_count,
                avg(latency_ms)                                AS avg_latency_ms,
                count(DISTINCT path)                           AS unique_endpoints,
                min(created_at)                                AS first_seen,
                max(created_at)                                AS last_seen
            FROM api_activity_log
            WHERE org_id = $1 AND agent_id = $2
            """,
            principal.organization_id,
            agent_id,
        )

    if not row or row["request_count"] == 0:
        return ActivitySummary(
            agent_id=agent_id,
            request_count=0,
            error_count=0,
            avg_latency_ms=None,
            unique_endpoints=0,
            first_seen=None,
            last_seen=None,
        )

    return ActivitySummary(
        agent_id=agent_id,
        request_count=row["request_count"],
        error_count=row["error_count"],
        avg_latency_ms=round(float(row["avg_latency_ms"]), 1) if row["avg_latency_ms"] else None,
        unique_endpoints=row["unique_endpoints"],
        first_seen=row["first_seen"].isoformat() if row["first_seen"] else None,
        last_seen=row["last_seen"].isoformat() if row["last_seen"] else None,
    )
