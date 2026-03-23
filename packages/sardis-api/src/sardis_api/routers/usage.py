"""Usage reporting API endpoints.

Metered billing: report usage deltas, query meter state, and list meters
for a subscription.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class UsageReportRequest(BaseModel):
    meter_id: str = Field(..., description="Meter to report usage against")
    usage_delta: Decimal = Field(..., gt=0, description="Incremental usage units to add")
    countersignature: str | None = Field(
        default=None,
        description="HMAC-SHA256 hex digest over '<meter_id>:<usage_delta>' "
                    "using the meter's countersignature secret. "
                    "Required when the meter has requires_countersignature=true.",
    )
    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
        description="Client-supplied idempotency key to prevent duplicate reports",
    )


class UsageReportResponse(BaseModel):
    report_id: str
    meter_id: str
    usage_delta: str
    cumulative_usage: str
    billable_amount: str
    recorded_at: str


class MeterResponse(BaseModel):
    meter_id: str
    subscription_id: str
    name: str
    unit: str
    unit_price: str
    cumulative_usage: str
    billable_amount: str
    requires_countersignature: bool
    created_at: str
    updated_at: str


class MeterListResponse(BaseModel):
    meters: list[MeterResponse]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/usage/report",
    response_model=UsageReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a usage delta for a metered billing meter",
)
async def report_usage(
    req: UsageReportRequest,
    principal: Principal = Depends(require_principal),
) -> UsageReportResponse:
    """Record incremental usage against a meter.

    If the meter has ``requires_countersignature`` enabled, the request
    **must** include a valid HMAC-SHA256 countersignature.  The message
    is ``"<meter_id>:<usage_delta>"`` and the key is the meter's
    countersignature secret (stored server-side, set at meter creation).
    """
    from sardis_v2_core.database import Database

    # Fetch the meter (and lock for atomic update)
    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM usage_meters WHERE meter_id = $1 FOR UPDATE NOWAIT",
            req.meter_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Meter not found")

        # --- countersignature verification ---------------------------------
        if row["requires_countersignature"]:
            if not req.countersignature:
                raise HTTPException(
                    status_code=422,
                    detail="Meter requires a countersignature but none was provided",
                )
            secret = row.get("countersignature_secret", "")
            if not secret:
                raise HTTPException(
                    status_code=500,
                    detail="Meter is misconfigured: missing countersignature secret",
                )
            message = f"{req.meter_id}:{req.usage_delta}"
            expected = hmac.new(
                secret.encode(), message.encode(), hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, req.countersignature):
                raise HTTPException(
                    status_code=403,
                    detail="Invalid countersignature",
                )

        # --- idempotency check ---------------------------------------------
        if req.idempotency_key:
            dup = await conn.fetchrow(
                "SELECT report_id FROM usage_reports WHERE idempotency_key = $1",
                req.idempotency_key,
            )
            if dup:
                # Return the previously recorded report
                existing = await conn.fetchrow(
                    "SELECT * FROM usage_reports WHERE report_id = $1",
                    dup["report_id"],
                )
                meter = await conn.fetchrow(
                    "SELECT * FROM usage_meters WHERE meter_id = $1",
                    req.meter_id,
                )
                return _report_row_to_response(existing, meter)

        # --- record usage --------------------------------------------------
        report_id = f"urpt_{uuid4().hex[:12]}"
        new_cumulative = Decimal(str(row["cumulative_usage"])) + req.usage_delta
        unit_price = Decimal(str(row["unit_price"]))
        new_billable = (new_cumulative * unit_price).quantize(Decimal("0.000001"))
        now = datetime.now(UTC)

        await conn.execute(
            """INSERT INTO usage_reports
               (report_id, meter_id, usage_delta, cumulative_after,
                billable_after, idempotency_key, recorded_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            report_id, req.meter_id, req.usage_delta,
            new_cumulative, new_billable,
            req.idempotency_key, now,
        )

        await conn.execute(
            """UPDATE usage_meters
               SET cumulative_usage = $1,
                   billable_amount  = $2,
                   updated_at       = $3
               WHERE meter_id = $4""",
            new_cumulative, new_billable, now, req.meter_id,
        )

    logger.info(
        "Usage reported: meter=%s delta=%s cumulative=%s billable=%s",
        req.meter_id, req.usage_delta, new_cumulative, new_billable,
    )

    return UsageReportResponse(
        report_id=report_id,
        meter_id=req.meter_id,
        usage_delta=str(req.usage_delta),
        cumulative_usage=str(new_cumulative),
        billable_amount=str(new_billable),
        recorded_at=now.isoformat(),
    )


@router.get(
    "/usage/meters/{meter_id}",
    response_model=MeterResponse,
    summary="Get meter details and current billable amount",
)
async def get_meter(
    meter_id: str,
    principal: Principal = Depends(require_principal),
) -> MeterResponse:
    from sardis_v2_core.database import Database

    row = await Database.fetchrow(
        "SELECT * FROM usage_meters WHERE meter_id = $1",
        meter_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Meter not found")

    return _meter_row_to_response(row)


@router.get(
    "/usage/meters",
    response_model=MeterListResponse,
    summary="List meters for a subscription",
)
async def list_meters(
    subscription_id: str = Query(..., description="Subscription to list meters for"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_principal),
) -> MeterListResponse:
    from sardis_v2_core.database import Database

    rows = await Database.fetch(
        """SELECT * FROM usage_meters
           WHERE subscription_id = $1
           ORDER BY created_at DESC
           LIMIT $2 OFFSET $3""",
        subscription_id, limit, offset,
    )

    count_row = await Database.fetchrow(
        "SELECT count(*) AS cnt FROM usage_meters WHERE subscription_id = $1",
        subscription_id,
    )
    total = int(count_row["cnt"]) if count_row else 0

    return MeterListResponse(
        meters=[_meter_row_to_response(r) for r in rows],
        total=total,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _meter_row_to_response(row) -> MeterResponse:
    return MeterResponse(
        meter_id=row["meter_id"],
        subscription_id=row["subscription_id"],
        name=row["name"],
        unit=row["unit"],
        unit_price=str(row["unit_price"]),
        cumulative_usage=str(row["cumulative_usage"]),
        billable_amount=str(row["billable_amount"]),
        requires_countersignature=bool(row["requires_countersignature"]),
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


def _report_row_to_response(report_row, meter_row) -> UsageReportResponse:
    return UsageReportResponse(
        report_id=report_row["report_id"],
        meter_id=report_row["meter_id"],
        usage_delta=str(report_row["usage_delta"]),
        cumulative_usage=str(report_row["cumulative_after"]),
        billable_amount=str(report_row["billable_after"]),
        recorded_at=report_row["recorded_at"].isoformat(),
    )
