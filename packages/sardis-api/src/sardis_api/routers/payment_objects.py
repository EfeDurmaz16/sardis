"""Payment Object API endpoints.

Payment objects are signed, one-time, merchant-bound payment tokens.
They are the core settlement primitive in the Sardis protocol.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class MintPaymentObjectRequest(BaseModel):
    mandate_id: str = Field(..., description="Spending mandate to mint from")
    merchant_id: str = Field(..., description="Merchant this payment is for")
    amount: Decimal = Field(..., gt=0, description="Exact payment amount")
    currency: str = Field(default="USDC")
    privacy_tier: str = Field(default="transparent", pattern="^(transparent|hybrid|full_zk)$")
    memo: str | None = Field(default=None, max_length=256, description="Optional payment memo")
    expires_in_seconds: int = Field(default=3600, ge=60, le=86400, description="TTL in seconds")
    metadata: dict | None = None


class PresentPaymentObjectRequest(BaseModel):
    merchant_id: str = Field(..., description="Merchant presenting to")
    merchant_signature: str | None = Field(default=None, description="Merchant's verification signature")


class VerifyPaymentObjectRequest(BaseModel):
    merchant_id: str = Field(..., description="Verifying merchant")
    merchant_signature: str = Field(..., description="Merchant signature over object hash")


class PaymentObjectResponse(BaseModel):
    object_id: str
    mandate_id: str
    merchant_id: str
    exact_amount: str  # Decimal as string for JSON safety
    currency: str
    status: str
    privacy_tier: str
    session_hash: str
    cell_ids: list[str]
    signature_chain: list[str]
    object_hash: str | None = None
    expires_at: str | None
    created_at: str
    metadata: dict


class PaymentObjectListResponse(BaseModel):
    objects: list[PaymentObjectResponse]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/payment-objects/mint",
    response_model=PaymentObjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mint a new payment object",
    description="Creates a signed, one-time payment token from a spending mandate.",
)
async def mint_payment_object(
    req: MintPaymentObjectRequest,
    principal: Principal = Depends(require_principal),
) -> PaymentObjectResponse:
    """Mint a payment object from a spending mandate.

    Validates mandate bounds, claims funding cells, signs the object,
    and returns a ready-to-present payment token.
    """
    from sardis_v2_core.database import Database
    from sardis_v2_core.payment_object import PaymentObject, PaymentObjectStatus, PrivacyTier

    # Verify mandate ownership and status
    row = await Database.fetchrow(
        "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2",
        req.mandate_id, principal.org_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Mandate not found")
    if row["status"] != "active":
        raise HTTPException(status_code=409, detail=f"Mandate is {row['status']}")

    # Check amount bounds
    if row["amount_per_tx"] is not None and req.amount > row["amount_per_tx"]:
        raise HTTPException(
            status_code=422,
            detail=f"Amount {req.amount} exceeds per-tx limit {row['amount_per_tx']}",
        )
    if row["amount_total"] is not None:
        remaining = row["amount_total"] - (row["spent_total"] or 0)
        if req.amount > remaining:
            raise HTTPException(
                status_code=422,
                detail=f"Amount {req.amount} exceeds remaining budget {remaining}",
            )

    # Claim funding cells
    claimed_cell_ids: list[str] = []
    async with Database.transaction() as conn:
        rows = await conn.fetch(
            """SELECT cell_id, value FROM funding_cells
               WHERE currency = $1 AND status = 'available'
               ORDER BY value DESC
               FOR UPDATE SKIP LOCKED""",
            req.currency,
        )
        remaining_amount = req.amount
        for cell_row in rows:
            if remaining_amount <= 0:
                break
            claimed_cell_ids.append(cell_row["cell_id"])
            remaining_amount -= cell_row["value"]
            await conn.execute(
                """UPDATE funding_cells
                   SET status = 'claimed', owner_mandate_id = $1, claimed_at = now()
                   WHERE cell_id = $2""",
                req.mandate_id, cell_row["cell_id"],
            )

    # Create payment object
    expires_at = datetime.now(UTC) + timedelta(seconds=req.expires_in_seconds)
    po = PaymentObject(
        mandate_id=req.mandate_id,
        cell_ids=claimed_cell_ids,
        merchant_id=req.merchant_id,
        exact_amount=req.amount,
        currency=req.currency,
        privacy_tier=PrivacyTier(req.privacy_tier),
        expires_at=expires_at,
        metadata=req.metadata or {},
    )

    # Persist
    await Database.execute(
        """INSERT INTO payment_objects
           (object_id, mandate_id, cell_ids, merchant_id, exact_amount,
            currency, one_time_use, signature_chain, session_hash,
            privacy_tier, status, object_hash, expires_at, metadata)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)""",
        po.object_id, po.mandate_id, po.cell_ids, po.merchant_id,
        po.exact_amount, po.currency, po.one_time_use, po.signature_chain,
        po.session_hash, po.privacy_tier.value, po.status.value,
        po.compute_hash(), po.expires_at, po.metadata,
    )

    logger.info("Minted payment object %s for mandate %s", po.object_id, po.mandate_id)

    return PaymentObjectResponse(
        object_id=po.object_id,
        mandate_id=po.mandate_id,
        merchant_id=po.merchant_id,
        exact_amount=str(po.exact_amount),
        currency=po.currency,
        status=po.status.value,
        privacy_tier=po.privacy_tier.value,
        session_hash=po.session_hash,
        cell_ids=po.cell_ids,
        signature_chain=po.signature_chain,
        object_hash=po.compute_hash(),
        expires_at=po.expires_at.isoformat() if po.expires_at else None,
        created_at=po.created_at.isoformat(),
        metadata=po.metadata,
    )


@router.post(
    "/payment-objects/{object_id}/present",
    response_model=PaymentObjectResponse,
    summary="Present a payment object to a merchant",
)
async def present_payment_object(
    object_id: str,
    req: PresentPaymentObjectRequest,
    principal: Principal = Depends(require_principal),
) -> PaymentObjectResponse:
    """Transition a payment object from MINTED → PRESENTED."""
    from sardis_v2_core.database import Database

    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM payment_objects WHERE object_id = $1 FOR UPDATE NOWAIT",
            object_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Payment object not found")
        if row["status"] != "minted":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot present: object is {row['status']}",
            )
        if row["merchant_id"] != req.merchant_id:
            raise HTTPException(status_code=403, detail="Merchant ID mismatch")

        # Check expiry
        if row["expires_at"] and datetime.now(UTC) > row["expires_at"]:
            await conn.execute(
                "UPDATE payment_objects SET status = 'expired', updated_at = now() WHERE object_id = $1",
                object_id,
            )
            raise HTTPException(status_code=410, detail="Payment object has expired")

        await conn.execute(
            """UPDATE payment_objects
               SET status = 'presented', presented_at = now(), updated_at = now()
               WHERE object_id = $1""",
            object_id,
        )

        # Log transition
        from uuid import uuid4
        await conn.execute(
            """INSERT INTO payment_state_transitions
               (id, payment_object_id, from_state, to_state, transition_name, actor)
               VALUES ($1,$2,$3,$4,$5,$6)""",
            f"str_{uuid4().hex[:16]}", object_id, "minted", "presented",
            "present", principal.principal_id,
        )

    updated = await Database.fetchrow(
        "SELECT * FROM payment_objects WHERE object_id = $1", object_id
    )
    return _row_to_response(updated)


@router.post(
    "/payment-objects/{object_id}/verify",
    response_model=PaymentObjectResponse,
    summary="Verify a payment object (merchant-side)",
)
async def verify_payment_object(
    object_id: str,
    req: VerifyPaymentObjectRequest,
    principal: Principal = Depends(require_principal),
) -> PaymentObjectResponse:
    """Transition a payment object from PRESENTED → VERIFIED."""
    from sardis_v2_core.database import Database

    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM payment_objects WHERE object_id = $1 FOR UPDATE NOWAIT",
            object_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Payment object not found")
        if row["status"] != "presented":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot verify: object is {row['status']}",
            )
        if row["merchant_id"] != req.merchant_id:
            raise HTTPException(status_code=403, detail="Merchant ID mismatch")

        await conn.execute(
            """UPDATE payment_objects
               SET status = 'verified', verified_at = now(), updated_at = now()
               WHERE object_id = $1""",
            object_id,
        )

        from uuid import uuid4
        await conn.execute(
            """INSERT INTO payment_state_transitions
               (id, payment_object_id, from_state, to_state, transition_name, actor)
               VALUES ($1,$2,$3,$4,$5,$6)""",
            f"str_{uuid4().hex[:16]}", object_id, "presented", "verified",
            "verify", principal.principal_id,
        )

    updated = await Database.fetchrow(
        "SELECT * FROM payment_objects WHERE object_id = $1", object_id
    )
    return _row_to_response(updated)


@router.get(
    "/payment-objects/{object_id}",
    response_model=PaymentObjectResponse,
    summary="Get a payment object by ID",
)
async def get_payment_object(
    object_id: str,
    principal: Principal = Depends(require_principal),
) -> PaymentObjectResponse:
    from sardis_v2_core.database import Database

    row = await Database.fetchrow(
        "SELECT * FROM payment_objects WHERE object_id = $1", object_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Payment object not found")
    return _row_to_response(row)


@router.get(
    "/payment-objects",
    response_model=PaymentObjectListResponse,
    summary="List payment objects",
)
async def list_payment_objects(
    principal: Principal = Depends(require_principal),
    mandate_id: str | None = Query(default=None),
    merchant_id: str | None = Query(default=None),
    object_status: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> PaymentObjectListResponse:
    from sardis_v2_core.database import Database

    conditions = []
    params: list = []
    idx = 1

    if mandate_id:
        conditions.append(f"mandate_id = ${idx}")
        params.append(mandate_id)
        idx += 1
    if merchant_id:
        conditions.append(f"merchant_id = ${idx}")
        params.append(merchant_id)
        idx += 1
    if object_status:
        conditions.append(f"status = ${idx}")
        params.append(object_status)
        idx += 1

    where = " AND ".join(conditions) if conditions else "TRUE"

    count = await Database.fetchval(
        f"SELECT COUNT(*) FROM payment_objects WHERE {where}", *params
    )
    rows = await Database.fetch(
        f"""SELECT * FROM payment_objects WHERE {where}
            ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}""",
        *params, limit, offset,
    )

    return PaymentObjectListResponse(
        objects=[_row_to_response(r) for r in rows],
        total=count,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_response(row) -> PaymentObjectResponse:
    return PaymentObjectResponse(
        object_id=row["object_id"],
        mandate_id=row["mandate_id"],
        merchant_id=row["merchant_id"],
        exact_amount=str(row["exact_amount"]),
        currency=row["currency"],
        status=row["status"],
        privacy_tier=row["privacy_tier"],
        session_hash=row["session_hash"],
        cell_ids=row["cell_ids"] or [],
        signature_chain=row["signature_chain"] or [],
        object_hash=row.get("object_hash"),
        expires_at=row["expires_at"].isoformat() if row.get("expires_at") else None,
        created_at=row["created_at"].isoformat(),
        metadata=row["metadata"] or {},
    )
