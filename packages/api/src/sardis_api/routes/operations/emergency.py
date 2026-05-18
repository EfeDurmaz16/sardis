"""Emergency freeze-all admin endpoint for incident response.

Provides bulk wallet freeze/unfreeze operations for emergency situations.
Individual wallet freeze exists at POST /wallets/{id}/freeze — this handles
bulk operations across all active wallets.

SECURITY: All endpoints require admin principal + MFA. Rate-limited at
5 req/min (sensitive admin action).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.audit_log import log_admin_action
from sardis_api.authz import Principal, require_principal
from sardis_api.middleware.mfa import require_mfa_if_enabled
from sardis_api.routers.admin import admin_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/admin/emergency",
    tags=["admin", "emergency"],
    dependencies=[Depends(require_mfa_if_enabled)],
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class FreezeAllRequest(BaseModel):
    reason: str = Field(
        default="manual_emergency",
        description="Reason for the emergency freeze",
    )
    notes: str | None = Field(
        default=None,
        description="Optional operator notes",
    )


class FreezeAllResponse(BaseModel):
    event_id: str
    action: str
    wallets_affected: int
    triggered_by: str
    timestamp: str
    reason: str
    notes: str | None = None


class EmergencyStatusResponse(BaseModel):
    is_frozen: bool
    last_event: FreezeAllResponse | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/freeze-all", response_model=FreezeAllResponse)
@admin_rate_limit(is_sensitive=True)
async def freeze_all_wallets(
    request: Request,
    body: FreezeAllRequest | None = None,
    principal: Principal = Depends(require_principal),
):
    """Freeze ALL active wallets. Emergency incident response only."""
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for emergency freeze",
        )

    body = body or FreezeAllRequest()
    now = datetime.now(UTC)

    try:
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            # Freeze all non-frozen wallets
            result = await conn.execute(
                """
                UPDATE wallets
                SET frozen = TRUE, updated_at = $1
                WHERE frozen = FALSE
                """,
                now,
            )
            # Parse "UPDATE N" to get count
            count = int(result.split()[-1]) if result else 0

            # Record the event
            event_id = str(uuid4())
            await conn.execute(
                """
                INSERT INTO emergency_freeze_events
                    (id, action, triggered_by, wallets_affected, reason, notes, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                event_id,
                "freeze_all",
                principal.user_id,
                count,
                body.reason,
                body.notes,
                now,
            )

        # Also activate global kill switch if available
        try:
            from sardis_guardrails.kill_switch import ActivationReason, get_kill_switch

            ks = get_kill_switch()
            await ks.activate_global(
                reason=ActivationReason.MANUAL,
                activated_by=principal.user_id,
                notes=f"Emergency freeze-all: {body.reason}",
            )
        except Exception as e:
            logger.warning("Kill switch activation failed (freeze still applied): %s", e)

        logger.critical(
            "EMERGENCY FREEZE-ALL: %d wallets frozen by %s — reason: %s",
            count,
            principal.user_id,
            body.reason,
        )

        await log_admin_action(
            request=request,
            user_id=principal.user_id,
            org_id=principal.organization_id,
            action="emergency_freeze_all",
            details={"wallets_affected": count, "reason": body.reason},
        )

        return FreezeAllResponse(
            event_id=event_id,
            action="freeze_all",
            wallets_affected=count,
            triggered_by=principal.user_id,
            timestamp=now.isoformat(),
            reason=body.reason,
            notes=body.notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Emergency freeze-all failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Emergency freeze-all failed — check server logs",
        )


@router.post("/unfreeze-all", response_model=FreezeAllResponse)
@admin_rate_limit(is_sensitive=True)
async def unfreeze_all_wallets(
    request: Request,
    body: FreezeAllRequest | None = None,
    principal: Principal = Depends(require_principal),
):
    """Unfreeze ALL frozen wallets. Reverses emergency freeze."""
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for emergency unfreeze",
        )

    body = body or FreezeAllRequest(reason="manual_unfreeze")
    now = datetime.now(UTC)

    try:
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE wallets
                SET frozen = FALSE, updated_at = $1
                WHERE frozen = TRUE
                """,
                now,
            )
            count = int(result.split()[-1]) if result else 0

            event_id = str(uuid4())
            await conn.execute(
                """
                INSERT INTO emergency_freeze_events
                    (id, action, triggered_by, wallets_affected, reason, notes, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                event_id,
                "unfreeze_all",
                principal.user_id,
                count,
                body.reason,
                body.notes,
                now,
            )

        # Deactivate global kill switch
        try:
            from sardis_guardrails.kill_switch import get_kill_switch

            ks = get_kill_switch()
            await ks.deactivate_global()
        except Exception as e:
            logger.warning("Kill switch deactivation failed: %s", e)

        logger.critical(
            "EMERGENCY UNFREEZE-ALL: %d wallets unfrozen by %s — reason: %s",
            count,
            principal.user_id,
            body.reason,
        )

        await log_admin_action(
            request=request,
            user_id=principal.user_id,
            org_id=principal.organization_id,
            action="emergency_unfreeze_all",
            details={"wallets_affected": count, "reason": body.reason},
        )

        return FreezeAllResponse(
            event_id=event_id,
            action="unfreeze_all",
            wallets_affected=count,
            triggered_by=principal.user_id,
            timestamp=now.isoformat(),
            reason=body.reason,
            notes=body.notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Emergency unfreeze-all failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Emergency unfreeze-all failed — check server logs",
        )


@router.get("/status", response_model=EmergencyStatusResponse)
@admin_rate_limit()
async def get_emergency_status(
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Get current emergency freeze status and last event."""
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    try:
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, action, triggered_by, wallets_affected, reason, notes, created_at
                FROM emergency_freeze_events
                ORDER BY created_at DESC
                LIMIT 1
                """
            )

            # Check if wallets are currently frozen
            frozen_count = await conn.fetchval(
                "SELECT COUNT(*) FROM wallets WHERE frozen = TRUE"
            )

        is_frozen = (frozen_count or 0) > 0

        last_event = None
        if row:
            last_event = FreezeAllResponse(
                event_id=str(row["id"]),
                action=row["action"],
                wallets_affected=row["wallets_affected"],
                triggered_by=row["triggered_by"],
                timestamp=row["created_at"].isoformat(),
                reason=row["reason"] or "",
                notes=row["notes"],
            )

        return EmergencyStatusResponse(
            is_frozen=is_frozen,
            last_event=last_event,
        )

    except Exception as e:
        logger.error("Emergency status check failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check emergency status",
        )
