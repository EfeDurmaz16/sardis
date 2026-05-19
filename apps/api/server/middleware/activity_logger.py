"""Server-side API activity logger middleware.

Logs every authenticated API call to the ``api_activity_log`` table via a
fire-and-forget ``asyncio.create_task`` so it never adds latency to the
request path.  Extracts ``agent_id`` from the ``X-Sardis-Agent-Id`` header
and ``session_id`` from ``X-Sardis-Session-Id``.
"""
from __future__ import annotations

import asyncio
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("server.api.activity_logger")

# Paths that are never logged — high-frequency or non-interesting.
ACTIVITY_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/health",
    "/ready",
    "/live",
    "/docs",
    "/api/v2/docs",
    "/api/v2/openapi.json",
    "/api/v2/redoc",
    "/api/v2/auth",
    "/api/v2/billing",
)


async def _insert_activity(
    org_id: str,
    principal_kind: str | None,
    actor_id: str | None,
    agent_id: str | None,
    session_id: str | None,
    method: str,
    path: str,
    status_code: int,
    latency_ms: int,
    wallet_id: str | None,
    request_id: str | None,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """Fire-and-forget DB insert.  Errors are swallowed with a debug log."""
    try:
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO api_activity_log
                    (org_id, principal_kind, actor_id, agent_id, session_id,
                     method, path, status_code, latency_ms, wallet_id,
                     request_id, ip, user_agent)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::inet,$13)
                """,
                org_id,
                principal_kind,
                actor_id,
                agent_id,
                session_id,
                method,
                path,
                status_code,
                latency_ms,
                wallet_id,
                request_id,
                ip,
                user_agent,
            )
    except Exception:
        logger.debug("activity log insert failed", exc_info=True)


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that logs API activity in the background.

    - Runs after auth middleware (``request.state`` has principal info).
    - Skips exempt prefixes (health, docs, auth, billing).
    - Skips unauthenticated requests (no ``org_id`` on state).
    - Fire-and-forget via ``asyncio.create_task`` — never blocks.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        path = request.url.path

        if any(path.startswith(prefix) for prefix in ACTIVITY_EXEMPT_PREFIXES):
            return await call_next(request)

        start = time.monotonic()
        response: Response = await call_next(request)
        latency_ms = int((time.monotonic() - start) * 1000)

        # Try multiple sources for org_id (different auth paths set different attrs)
        org_id: str | None = (
            getattr(request.state, "org_id", None)
            or getattr(request.state, "organization_id", None)
            or getattr(getattr(request.state, "principal", None), "organization_id", None)
        )
        # Fallback: check if environment was set (means auth passed)
        if not org_id and getattr(request.state, "environment", None):
            org_id = "org_default"
        if not org_id:
            return response

        # Extract principal info from various possible locations
        principal = getattr(request.state, "principal", None)
        principal_kind: str | None = getattr(principal, "kind", None) or getattr(request.state, "principal_kind", None)
        actor_id: str | None = None
        if principal:
            actor_id = getattr(principal, "user_id", None) or getattr(principal, "organization_id", None)
        if not actor_id:
            actor_id = getattr(request.state, "actor_id", None)

        # Agent / session correlation headers.
        agent_id = request.headers.get("x-sardis-agent-id")
        session_id = request.headers.get("x-sardis-session-id")

        # Wallet ID — may be on the path for wallet-scoped routes.
        wallet_id: str | None = None
        if "/wallets/" in path:
            parts = path.split("/wallets/")
            if len(parts) > 1:
                wallet_id = parts[1].split("/")[0]

        request_id = request.headers.get("x-request-id")
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:512]

        asyncio.create_task(
            _insert_activity(
                org_id=org_id,
                principal_kind=principal_kind,
                actor_id=actor_id,
                agent_id=agent_id,
                session_id=session_id,
                method=request.method,
                path=path[:512],
                status_code=response.status_code,
                latency_ms=latency_ms,
                wallet_id=wallet_id,
                request_id=request_id,
                ip=ip,
                user_agent=user_agent,
            )
        )

        return response
