"""Agent events — batch ingest and query for SDK telemetry events.

SDKs buffer tool calls, payments, errors, etc. and flush them in batches
to ``POST /agents/{id}/events/batch``.  The dashboard reads them via
``GET /agents/{id}/events``.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class EventItem(BaseModel):
    event_type: str = Field(..., description="e.g. tool_call, payment, error, session.start")
    data: dict = Field(default_factory=dict, description="Arbitrary event payload")
    timestamp: str | None = Field(default=None, description="ISO-8601 SDK-side timestamp")


class BatchEventsRequest(BaseModel):
    session_id: str | None = None
    events: list[EventItem] = Field(..., max_length=MAX_BATCH_SIZE)


class BatchEventsResponse(BaseModel):
    inserted: int


class EventResponse(BaseModel):
    id: int
    agent_id: str
    session_id: str | None
    event_type: str
    event_data: dict
    sdk_timestamp: str | None
    created_at: str


class EventsListResponse(BaseModel):
    events: list[EventResponse]
    count: int


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

class EventsDependencies:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool


def get_deps() -> EventsDependencies:
    raise NotImplementedError("Dependency override required")


def _get_events_deps(request: Request) -> EventsDependencies:
    deps = getattr(request.app.state, "agent_events_deps", None)
    if deps is None:
        deps = getattr(request.app.state, "events_deps", None)
    if deps is not None:
        return deps

    database_url = getattr(request.app.state, "database_url", None)
    if database_url:
        return EventsDependencies(database_url=database_url)

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Agent events require app.state.agent_events_deps, app.state.events_deps, "
            "or app.state.database_url wiring."
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/events/batch", response_model=BatchEventsResponse, status_code=status.HTTP_200_OK)
async def batch_events(
    agent_id: str,
    body: BatchEventsRequest,
    principal: Principal = Depends(require_principal),
    deps: EventsDependencies = Depends(_get_events_deps),
):
    """Ingest a batch of events from the SDK.

    Also updates ``agents.last_seen_at`` as a side effect so heartbeats
    are implicitly refreshed by event flushes.
    """
    if not body.events:
        return BatchEventsResponse(inserted=0)

    if len(body.events) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Max {MAX_BATCH_SIZE} events per batch",
        )

    pool = await deps._get_pool()
    org_id = principal.org_id
    now = datetime.now(UTC)

    import json as _json

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Bulk insert events
            records = []
            for evt in body.events:
                sdk_ts = None
                if evt.timestamp:
                    try:
                        sdk_ts = datetime.fromisoformat(evt.timestamp)
                    except (ValueError, TypeError):
                        sdk_ts = None
                records.append((
                    org_id,
                    agent_id,
                    body.session_id,
                    evt.event_type,
                    _json.dumps(evt.data),
                    sdk_ts,
                    now,
                ))

            await conn.executemany(
                """
                INSERT INTO agent_events (org_id, agent_id, session_id, event_type, event_data, sdk_timestamp, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                """,
                records,
            )

            # Side-effect: refresh last_seen_at
            await conn.execute(
                """
                UPDATE agents
                SET last_seen_at = $2, updated_at = NOW()
                WHERE external_id = $1
                """,
                agent_id,
                now,
            )

    # Publish SSE events (best-effort, outside transaction)
    try:
        from sardis_api.routers.event_stream import publish_event
        for evt in body.events:
            await publish_event(org_id, f"agent.event.{evt.event_type}", {
                "agent_id": agent_id,
                "session_id": body.session_id,
                **evt.data,
            })
    except Exception:
        pass  # SSE is best-effort

    return BatchEventsResponse(inserted=len(body.events))


@router.get("/{agent_id}/events", response_model=EventsListResponse, status_code=status.HTTP_200_OK)
async def list_events(
    agent_id: str,
    event_type: str | None = Query(default=None, description="Filter by event type"),
    session_id: str | None = Query(default=None, description="Filter by session"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_principal),
    deps: EventsDependencies = Depends(_get_events_deps),
):
    """Query events for an agent with optional type/session filters."""
    pool = await deps._get_pool()
    org_id = principal.org_id

    where_clauses = ["org_id = $1", "agent_id = $2"]
    params: list[Any] = [org_id, agent_id]
    idx = 3

    if event_type:
        where_clauses.append(f"event_type = ${idx}")
        params.append(event_type)
        idx += 1
    if session_id:
        where_clauses.append(f"session_id = ${idx}")
        params.append(session_id)
        idx += 1

    where_sql = " AND ".join(where_clauses)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, agent_id, session_id, event_type, event_data, sdk_timestamp, created_at
            FROM agent_events
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params,
            limit,
            offset,
        )

    events = [
        EventResponse(
            id=r["id"],
            agent_id=r["agent_id"],
            session_id=r["session_id"],
            event_type=r["event_type"],
            event_data=r["event_data"] if isinstance(r["event_data"], dict) else {},
            sdk_timestamp=r["sdk_timestamp"].isoformat() if r["sdk_timestamp"] else None,
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]

    return EventsListResponse(events=events, count=len(events))
