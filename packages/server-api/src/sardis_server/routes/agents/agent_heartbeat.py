"""Agent heartbeat and auto-registration endpoints.

SDK clients call these to register themselves on first use and
send periodic heartbeats so the dashboard can show online status.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_server.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AutoRegisterRequest(BaseModel):
    agent_id: str = Field(..., description="SDK-generated agent identifier (e.g. agent_abc123)")
    name: str = Field(default="unnamed-agent", description="Human-readable agent name")
    framework: str | None = Field(default=None, description="Agent framework (openai-agents, crewai, claude-agent-sdk, etc.)")
    sdk_version: str | None = Field(default=None, description="Sardis SDK version string")
    session_id: str | None = Field(default=None, description="Current session identifier")
    metadata: dict | None = Field(default=None, description="Additional agent metadata")


class AutoRegisterResponse(BaseModel):
    agent_id: str
    created: bool
    last_seen_at: str


class HeartbeatRequest(BaseModel):
    agent_id: str
    session_id: str | None = None
    sdk_version: str | None = None
    framework: str | None = None


class HeartbeatResponse(BaseModel):
    ok: bool = True
    last_seen_at: str


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

class HeartbeatDependencies:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool


def get_deps() -> HeartbeatDependencies:
    raise NotImplementedError("Dependency override required")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/auto-register", response_model=AutoRegisterResponse, status_code=status.HTTP_200_OK)
async def auto_register(
    body: AutoRegisterRequest,
    principal: Principal = Depends(require_principal),
    deps: HeartbeatDependencies = Depends(get_deps),
):
    """Upsert an agent from SDK telemetry.

    If the agent already exists (by external_id), updates last_seen_at and
    telemetry columns. If it does not exist, creates a new agent row.
    Returns the agent_id and whether a new row was created.
    """
    pool = await deps._get_pool()
    now = datetime.now(UTC)
    import json as _json

    meta = dict(body.metadata or {})
    meta["owner_id"] = principal.org_id or principal.subject

    async with pool.acquire() as conn:
        # Ensure org exists
        org_uuid = None
        if principal.org_id:
            row = await conn.fetchrow(
                "SELECT id FROM organizations WHERE external_id = $1",
                principal.org_id,
            )
            if row:
                org_uuid = str(row["id"])

        result = await conn.fetchrow(
            """
            INSERT INTO agents (external_id, organization_id, name, description, metadata,
                                is_active, last_seen_at, session_id, sdk_version, framework)
            VALUES ($1, $2::uuid, $3, NULL, $4::jsonb,
                    TRUE, $5, $6, $7, $8)
            ON CONFLICT (external_id) DO UPDATE SET
                last_seen_at = EXCLUDED.last_seen_at,
                session_id   = COALESCE(EXCLUDED.session_id, agents.session_id),
                sdk_version  = COALESCE(EXCLUDED.sdk_version, agents.sdk_version),
                framework    = COALESCE(EXCLUDED.framework, agents.framework),
                updated_at   = NOW()
            RETURNING external_id, (xmax = 0) AS inserted, last_seen_at
            """,
            body.agent_id,
            org_uuid,
            body.name,
            _json.dumps(meta),
            now,
            body.session_id,
            body.sdk_version,
            body.framework,
        )

    created = bool(result["inserted"])

    if created:
        logger.info("Auto-registered new agent %s (framework=%s)", body.agent_id, body.framework)
        # Publish SSE event for dashboard
        try:
            from sardis_server.routes.operations.event_stream import publish_event
            org_id = principal.org_id or principal.subject
            await publish_event(org_id, "agent.registered", {
                "agent_id": body.agent_id,
                "name": body.name,
                "framework": body.framework,
            })
        except Exception:
            pass  # SSE is best-effort
    else:
        logger.debug("Heartbeat-update for agent %s via auto-register", body.agent_id)

    return AutoRegisterResponse(
        agent_id=str(result["external_id"]),
        created=created,
        last_seen_at=result["last_seen_at"].isoformat(),
    )


@router.post("/heartbeat", response_model=HeartbeatResponse, status_code=status.HTTP_200_OK)
async def heartbeat(
    body: HeartbeatRequest,
    principal: Principal = Depends(require_principal),
    deps: HeartbeatDependencies = Depends(get_deps),
):
    """Lightweight heartbeat — updates last_seen_at only.

    Called every ~60s by the SDK. Single UPDATE, no joins.
    """
    pool = await deps._get_pool()
    now = datetime.now(UTC)

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE agents
            SET last_seen_at = $2,
                session_id   = COALESCE($3, session_id),
                sdk_version  = COALESCE($4, sdk_version),
                framework    = COALESCE($5, framework),
                updated_at   = NOW()
            WHERE external_id = $1
            """,
            body.agent_id,
            now,
            body.session_id,
            body.sdk_version,
            body.framework,
        )

    if "UPDATE 0" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {body.agent_id} not found. Call /auto-register first.",
        )

    return HeartbeatResponse(ok=True, last_seen_at=now.isoformat())
