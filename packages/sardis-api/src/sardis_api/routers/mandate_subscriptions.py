"""Mandate-based Subscription API endpoints.

New subscription system backed by spending mandates (vs legacy wallet-based).
Uses the SubscriptionMandate model from sardis-core and the 083_subscriptions
migration tables.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)

CYCLE_DAYS = {
    "daily": 1, "weekly": 7, "biweekly": 14,
    "monthly": 30, "quarterly": 90, "annual": 365,
}


class CreateMandateSubscriptionRequest(BaseModel):
    mandate_id: str
    merchant_id: str
    agent_id: str | None = None
    billing_cycle: str = Field(default="monthly", pattern="^(daily|weekly|biweekly|monthly|quarterly|annual)$")
    charge_amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USDC")
    description: str | None = None
    grace_period_days: int = Field(default=3, ge=0)
    trial_days: int = Field(default=0, ge=0)
    metadata: dict | None = None


class MandateSubscriptionResponse(BaseModel):
    subscription_id: str
    mandate_id: str
    merchant_id: str
    agent_id: str | None
    billing_cycle: str
    charge_amount: str
    currency: str
    status: str
    next_charge_at: str | None
    created_at: str


class AmendRequest(BaseModel):
    charge_amount: Decimal | None = Field(default=None, gt=0)
    billing_cycle: str | None = None


@router.post(
    "/mandate-subscriptions",
    response_model=MandateSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a mandate-based subscription",
)
async def create_mandate_subscription(
    req: CreateMandateSubscriptionRequest,
    principal: Principal = Depends(require_principal),
) -> MandateSubscriptionResponse:
    from sardis_v2_core.database import Database

    mandate = await Database.fetchrow(
        "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2 AND status = 'active'",
        req.mandate_id, principal.org_id,
    )
    if not mandate:
        raise HTTPException(status_code=404, detail="Active mandate not found")

    # Validate charge amount against mandate limits
    if mandate["amount_per_tx"] and req.charge_amount > mandate["amount_per_tx"]:
        raise HTTPException(
            status_code=422,
            detail=f"Charge amount exceeds mandate per-tx limit {mandate['amount_per_tx']}",
        )

    sub_id = f"sub_{uuid4().hex[:12]}"
    now = datetime.now(UTC)
    days = CYCLE_DAYS.get(req.billing_cycle, 30)
    next_charge = now + timedelta(days=days)
    initial_status = "trial" if req.trial_days > 0 else "pending"

    if req.trial_days > 0:
        next_charge = now + timedelta(days=req.trial_days)

    await Database.execute(
        """INSERT INTO subscriptions
           (subscription_id, org_id, mandate_id, merchant_id, agent_id,
            billing_cycle, charge_amount, currency, description,
            grace_period_days, trial_days,
            status, next_charge_at, metadata)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)""",
        sub_id, principal.org_id, req.mandate_id, req.merchant_id,
        req.agent_id, req.billing_cycle, req.charge_amount, req.currency,
        req.description, req.grace_period_days, req.trial_days,
        initial_status, next_charge, req.metadata or {},
    )

    return MandateSubscriptionResponse(
        subscription_id=sub_id,
        mandate_id=req.mandate_id,
        merchant_id=req.merchant_id,
        agent_id=req.agent_id,
        billing_cycle=req.billing_cycle,
        charge_amount=str(req.charge_amount),
        currency=req.currency,
        status=initial_status,
        next_charge_at=next_charge.isoformat(),
        created_at=now.isoformat(),
    )


@router.get(
    "/mandate-subscriptions",
    response_model=list[MandateSubscriptionResponse],
    summary="List mandate-based subscriptions",
)
async def list_mandate_subscriptions(
    principal: Principal = Depends(require_principal),
    mandate_id: str | None = Query(default=None),
    sub_status: str | None = Query(default=None, alias="status"),
) -> list[MandateSubscriptionResponse]:
    from sardis_v2_core.database import Database

    conditions = ["org_id = $1"]
    params: list = [principal.org_id]
    idx = 2
    if mandate_id:
        conditions.append(f"mandate_id = ${idx}")
        params.append(mandate_id)
        idx += 1
    if sub_status:
        conditions.append(f"status = ${idx}")
        params.append(sub_status)
        idx += 1

    where = " AND ".join(conditions)
    rows = await Database.fetch(
        f"SELECT * FROM subscriptions WHERE {where} ORDER BY created_at DESC",
        *params,
    )
    return [_row_to_response(r) for r in rows]


@router.post(
    "/mandate-subscriptions/{subscription_id}/cancel",
    response_model=MandateSubscriptionResponse,
    summary="Cancel a mandate-based subscription",
)
async def cancel_mandate_subscription(
    subscription_id: str,
    principal: Principal = Depends(require_principal),
) -> MandateSubscriptionResponse:
    from sardis_v2_core.database import Database

    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM subscriptions WHERE subscription_id = $1 AND org_id = $2 FOR UPDATE NOWAIT",
            subscription_id, principal.org_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Subscription not found")
        if row["status"] in ("cancelled", "expired"):
            raise HTTPException(status_code=409, detail=f"Already {row['status']}")

        await conn.execute(
            "UPDATE subscriptions SET status = 'cancelled', cancelled_at = now(), updated_at = now() WHERE subscription_id = $1",
            subscription_id,
        )

    updated = await Database.fetchrow(
        "SELECT * FROM subscriptions WHERE subscription_id = $1", subscription_id
    )
    return _row_to_response(updated)


@router.patch(
    "/mandate-subscriptions/{subscription_id}/amend",
    response_model=MandateSubscriptionResponse,
    summary="Amend a mandate-based subscription",
)
async def amend_mandate_subscription(
    subscription_id: str,
    req: AmendRequest,
    principal: Principal = Depends(require_principal),
) -> MandateSubscriptionResponse:
    from sardis_v2_core.database import Database

    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM subscriptions WHERE subscription_id = $1 AND org_id = $2 FOR UPDATE NOWAIT",
            subscription_id, principal.org_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Subscription not found")
        if row["status"] not in ("active", "trial", "pending"):
            raise HTTPException(status_code=409, detail=f"Cannot amend: {row['status']}")

        updates, params = [], []
        idx = 1
        if req.charge_amount is not None:
            updates.append(f"charge_amount = ${idx}")
            params.append(req.charge_amount)
            idx += 1
        if req.billing_cycle is not None:
            updates.append(f"billing_cycle = ${idx}")
            params.append(req.billing_cycle)
            idx += 1
        if not updates:
            raise HTTPException(status_code=422, detail="No fields to update")

        updates.append("updated_at = now()")
        params.append(subscription_id)
        await conn.execute(
            f"UPDATE subscriptions SET {', '.join(updates)} WHERE subscription_id = ${idx}",
            *params,
        )

    updated = await Database.fetchrow(
        "SELECT * FROM subscriptions WHERE subscription_id = $1", subscription_id
    )
    return _row_to_response(updated)


def _row_to_response(row) -> MandateSubscriptionResponse:
    return MandateSubscriptionResponse(
        subscription_id=row["subscription_id"],
        mandate_id=row["mandate_id"],
        merchant_id=row["merchant_id"],
        agent_id=row.get("agent_id"),
        billing_cycle=row["billing_cycle"],
        charge_amount=str(row["charge_amount"]),
        currency=row["currency"],
        status=row["status"],
        next_charge_at=row["next_charge_at"].isoformat() if row.get("next_charge_at") else None,
        created_at=row["created_at"].isoformat(),
    )
