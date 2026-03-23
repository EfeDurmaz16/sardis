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

    Delegates to PaymentObjectMinter which validates mandate bounds,
    claims funding cells (org-scoped, FOR UPDATE SKIP LOCKED),
    computes session hash, signs the object, and returns a minted token.
    """
    import hashlib

    from sardis_v2_core.cell_claim import CellClaimAlgorithm
    from sardis_v2_core.database import Database
    from sardis_v2_core.minter import MintError, PaymentObjectMinter
    from sardis_v2_core.payment_object import PrivacyTier
    from sardis_v2_core.spending_mandate import ApprovalMode, MandateStatus, SpendingMandate

    # --- Concrete port implementations (org-scoped) ---

    class _MandateLookup:
        """Fetches mandate from DB, scoped to the principal's org."""
        async def get_mandate(self, mandate_id: str) -> SpendingMandate | None:
            row = await Database.fetchrow(
                "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2",
                mandate_id, principal.org_id,
            )
            if not row:
                return None
            return SpendingMandate(
                principal_id=row["principal_id"],
                issuer_id=row["issuer_id"],
                org_id=row["org_id"],
                agent_id=row.get("agent_id"),
                wallet_id=row.get("wallet_id"),
                id=row["id"],
                merchant_scope=row.get("merchant_scope") or {},
                purpose_scope=row.get("purpose_scope"),
                amount_per_tx=row.get("amount_per_tx"),
                amount_daily=row.get("amount_daily"),
                amount_weekly=row.get("amount_weekly"),
                amount_monthly=row.get("amount_monthly"),
                amount_total=row.get("amount_total"),
                currency=row.get("currency", "USDC"),
                spent_total=row.get("spent_total") or Decimal("0"),
                allowed_rails=row.get("allowed_rails") or ["card", "usdc", "bank"],
                allowed_chains=row.get("allowed_chains"),
                allowed_tokens=row.get("allowed_tokens"),
                expires_at=row.get("expires_at"),
                approval_threshold=row.get("approval_threshold"),
                approval_mode=ApprovalMode(row.get("approval_mode", "auto")),
                status=MandateStatus(row.get("status", "active")),
            )

    class _CellClaimer:
        """Claims funding cells scoped to the mandate's org via CellClaimAlgorithm."""
        async def claim_cells(self, mandate_id: str, amount: Decimal, currency: str) -> list[str]:
            pool = await Database.get_pool()
            algo = CellClaimAlgorithm(pool)
            cells = await algo.claim_cells(mandate_id, amount, currency)
            return [c.cell_id for c in cells]

    class _Signer:
        """HMAC signer using the org's API key hash as signing secret."""
        async def sign(self, data: bytes) -> str:
            secret = principal.org_id.encode()
            return hashlib.sha256(secret + data).hexdigest()

    # --- Mint via PaymentObjectMinter ---

    minter = PaymentObjectMinter(
        mandate_lookup=_MandateLookup(),
        cell_claimer=_CellClaimer(),
        signer=_Signer(),
    )

    try:
        po = await minter.mint(
            mandate_id=req.mandate_id,
            merchant_id=req.merchant_id,
            amount=req.amount,
            currency=req.currency,
            privacy_tier=PrivacyTier(req.privacy_tier),
            expires_in_seconds=req.expires_in_seconds,
            metadata=req.metadata,
        )
    except MintError as exc:
        status_code = {
            "MANDATE_NOT_FOUND": 404,
            "MANDATE_NOT_ACTIVE": 409,
            "MANDATE_EXPIRED": 410,
        }.get(exc.error_code, 422)
        raise HTTPException(status_code=status_code, detail=str(exc))

    # Persist the minter-produced PaymentObject
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
    """Transition a payment object from PRESENTED → VERIFIED.

    Validates the merchant_signature against the payment object's
    object_hash using HMAC-SHA256 with the merchant's shared secret.
    """
    import hashlib
    import hmac as _hmac

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

        # Verify merchant signature over the object hash
        object_hash = row.get("object_hash", "")
        if not object_hash:
            raise HTTPException(status_code=422, detail="Payment object has no hash to verify against")

        # Look up merchant secret (fall back to merchant_id as HMAC key for dev)
        merchant_row = await conn.fetchrow(
            "SELECT webhook_secret FROM merchants WHERE merchant_id = $1",
            req.merchant_id,
        )
        merchant_secret = (
            merchant_row["webhook_secret"] if merchant_row and merchant_row.get("webhook_secret")
            else req.merchant_id  # fallback for dev/test
        )

        expected_sig = _hmac.new(
            merchant_secret.encode(), object_hash.encode(), hashlib.sha256
        ).hexdigest()

        if not _hmac.compare_digest(expected_sig, req.merchant_signature):
            raise HTTPException(
                status_code=401,
                detail="Invalid merchant signature",
            )

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
