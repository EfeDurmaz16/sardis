"""Access audit logging for SOC 2 compliance.

Logs all authentication events, admin actions, and sensitive API access
to the access_audit_log table.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import Request

logger = logging.getLogger("sardis.audit")


async def log_access_event(
    event_type: str,
    request: Optional[Request] = None,
    user_id: str | None = None,
    org_id: str | None = None,
    status_code: int | None = None,
    auth_method: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Record an access event to the audit log table.

    Best-effort — failures are logged but do not block the request.
    """
    ip_address = ""
    user_agent = ""
    endpoint = ""
    method = ""

    if request:
        if request.client:
            ip_address = request.client.host
        user_agent = request.headers.get("User-Agent", "")[:500]
        endpoint = str(request.url.path)
        method = request.method

    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO access_audit_log
                    (event_type, user_id, org_id, ip_address, user_agent,
                     endpoint, method, status_code, auth_method, details)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
                """,
                event_type,
                user_id,
                org_id,
                ip_address,
                user_agent[:500],
                endpoint[:500],
                method,
                status_code,
                auth_method,
                json.dumps(details or {}),
            )
    except Exception as e:
        # Best-effort — don't let audit logging break requests
        logger.warning("Audit log write failed: %s", e)


async def log_auth_success(
    request: Request,
    user_id: str,
    org_id: str,
    auth_method: str,
) -> None:
    """Log a successful authentication."""
    await log_access_event(
        event_type="auth_success",
        request=request,
        user_id=user_id,
        org_id=org_id,
        auth_method=auth_method,
    )


async def log_auth_failure(
    request: Request,
    auth_method: str,
    reason: str = "",
) -> None:
    """Log a failed authentication attempt."""
    await log_access_event(
        event_type="auth_failure",
        request=request,
        auth_method=auth_method,
        details={"reason": reason},
    )


async def log_admin_action(
    request: Request,
    user_id: str,
    org_id: str,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Log an admin action for compliance."""
    await log_access_event(
        event_type="admin_action",
        request=request,
        user_id=user_id,
        org_id=org_id,
        auth_method="admin",
        details={"action": action, **(details or {})},
    )
