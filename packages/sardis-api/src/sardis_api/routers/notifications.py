"""REST API endpoints for notification webhook configuration and testing."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class UpdateNotificationConfigRequest(BaseModel):
    webhook_url: str = Field(..., description="Webhook URL to deliver events to")
    event_types: list[str] = Field(
        default_factory=list,
        description="Event types to subscribe to (empty = all)",
    )
    provider: str = Field(default="slack", description="Provider hint (slack, discord, custom)")


class NotificationConfigResponse(BaseModel):
    id: str
    org_id: str
    webhook_url: str
    event_types: list[str]
    provider: str
    is_active: bool
    consecutive_failures: int
    created_at: str


class DeliveryLogEntry(BaseModel):
    id: str
    config_id: str
    event_type: str
    status_code: int | None
    error: str | None
    attempt_number: int
    success: bool
    duration_ms: int
    created_at: str


class TestNotificationResponse(BaseModel):
    success: bool
    message: str
    status_code: int | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

async def _get_pool():
    """Lazy DB pool accessor."""
    from sardis_v2_core.database import Database
    return await Database.get_pool()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/config", response_model=NotificationConfigResponse | None)
async def get_notification_config(
    principal: Principal = Depends(require_principal),
) -> NotificationConfigResponse | None:
    """Get the org's current notification webhook configuration."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, org_id, webhook_url, event_types, provider,
                   is_active, consecutive_failures, created_at
            FROM notification_configs
            WHERE org_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            principal.organization_id,
        )

    if not row:
        return None

    return NotificationConfigResponse(
        id=row["id"],
        org_id=row["org_id"],
        webhook_url=row["webhook_url"],
        event_types=row["event_types"] or [],
        provider=row["provider"],
        is_active=row["is_active"],
        consecutive_failures=row["consecutive_failures"],
        created_at=row["created_at"].isoformat(),
    )


@router.put("/config", response_model=NotificationConfigResponse, status_code=status.HTTP_200_OK)
async def update_notification_config(
    request: UpdateNotificationConfigRequest,
    principal: Principal = Depends(require_principal),
) -> NotificationConfigResponse:
    """Create or update the org's notification webhook configuration."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO notification_configs (org_id, webhook_url, event_types, provider)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (org_id) DO UPDATE SET
                webhook_url = EXCLUDED.webhook_url,
                event_types = EXCLUDED.event_types,
                provider = EXCLUDED.provider,
                is_active = true,
                consecutive_failures = 0,
                last_failure_at = NULL,
                updated_at = now()
            RETURNING id::text, org_id, webhook_url, event_types, provider,
                      is_active, consecutive_failures, created_at
            """,
            principal.organization_id,
            request.webhook_url,
            request.event_types,
            request.provider,
        )

    return NotificationConfigResponse(
        id=row["id"],
        org_id=row["org_id"],
        webhook_url=row["webhook_url"],
        event_types=row["event_types"] or [],
        provider=row["provider"],
        is_active=row["is_active"],
        consecutive_failures=row["consecutive_failures"],
        created_at=row["created_at"].isoformat(),
    )


@router.post("/test", response_model=TestNotificationResponse)
async def test_notification(
    principal: Principal = Depends(require_principal),
) -> TestNotificationResponse:
    """Send a sample event to the org's configured webhook."""
    from sardis_v2_core.database import Database
    from sardis_v2_core.notification_service import NotificationService

    svc = NotificationService(database=Database)
    result = await svc.send_test(org_id=principal.organization_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active notification config found for this org",
        )

    return TestNotificationResponse(
        success=result.success,
        message="Test notification delivered" if result.success else "Delivery failed",
        status_code=result.status_code,
        error=result.error,
    )


@router.get("/delivery-log", response_model=list[DeliveryLogEntry])
async def get_delivery_log(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_principal),
) -> list[DeliveryLogEntry]:
    """Get recent webhook delivery attempts for the org."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT dl.id::text, dl.config_id::text, dl.event_type,
                   dl.status_code, dl.error, dl.attempt_number,
                   dl.success, dl.duration_ms, dl.created_at
            FROM notification_delivery_log dl
            JOIN notification_configs nc ON nc.id = dl.config_id
            WHERE nc.org_id = $1
            ORDER BY dl.created_at DESC
            LIMIT $2 OFFSET $3
            """,
            principal.organization_id,
            limit,
            offset,
        )

    return [
        DeliveryLogEntry(
            id=row["id"],
            config_id=row["config_id"],
            event_type=row["event_type"],
            status_code=row["status_code"],
            error=row["error"],
            attempt_number=row["attempt_number"],
            success=row["success"],
            duration_ms=row["duration_ms"],
            created_at=row["created_at"].isoformat(),
        )
        for row in rows
    ]
