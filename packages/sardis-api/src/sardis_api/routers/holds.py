"""Holds API routes for pre-authorization management."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sardis_v2_core.holds import Hold, HoldsRepository

from sardis_api.authz import Principal, require_admin_principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)], tags=["holds"])


# Request/Response Models

class CreateHoldRequest(BaseModel):
    """Request to create a hold."""
    wallet_id: str = Field(..., description="Wallet to hold funds from")
    amount: Decimal = Field(..., gt=0, description="Amount to hold")
    token: str = Field(default="USDC", description="Token to hold")
    merchant_id: str | None = Field(None, description="Merchant this hold is for")
    purpose: str | None = Field(None, description="Purpose of the hold")
    expiration_hours: int | None = Field(None, ge=1, le=720, description="Hours until expiration (default: 168)")


class CaptureHoldRequest(BaseModel):
    """Request to capture a hold."""
    amount: Decimal | None = Field(None, gt=0, description="Amount to capture (default: full amount)")
    tx_id: str | None = Field(None, description="Transaction ID for the capture")


class HoldResponse(BaseModel):
    """Hold response model."""
    hold_id: str
    wallet_id: str
    merchant_id: str | None
    amount: str
    token: str
    status: str
    purpose: str | None
    created_at: datetime
    expires_at: datetime | None
    captured_amount: str | None
    captured_at: datetime | None
    voided_at: datetime | None

    @classmethod
    def from_hold(cls, hold: Hold) -> HoldResponse:
        return cls(
            hold_id=hold.hold_id,
            wallet_id=hold.wallet_id,
            merchant_id=hold.merchant_id,
            amount=str(hold.amount),
            token=hold.token,
            status=hold.status,
            purpose=hold.purpose,
            created_at=hold.created_at,
            expires_at=hold.expires_at,
            captured_amount=str(hold.captured_amount) if hold.captured_amount else None,
            captured_at=hold.captured_at,
            voided_at=hold.voided_at,
        )


class HoldOperationResponse(BaseModel):
    """Response for hold operations."""
    success: bool
    hold: HoldResponse | None = None
    error: str | None = None


# Dependencies

class HoldsDependencies:
    """Dependencies for holds routes."""
    def __init__(self, holds_repo: HoldsRepository):
        self.holds_repo = holds_repo


def get_deps() -> HoldsDependencies:
    """Dependency injection placeholder."""
    raise NotImplementedError("Must be overridden")


# Routes

@router.post("", response_model=HoldOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_hold(
    request: CreateHoldRequest,
    deps: HoldsDependencies = Depends(get_deps),
):
    """Create a new hold (pre-authorization) on funds."""
    result = await deps.holds_repo.create(
        wallet_id=request.wallet_id,
        amount=request.amount,
        token=request.token,
        merchant_id=request.merchant_id,
        purpose=request.purpose,
        expiration_hours=request.expiration_hours,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )

    return HoldOperationResponse(
        success=True,
        hold=HoldResponse.from_hold(result.hold),
    )


@router.get("/{hold_id}", response_model=HoldResponse)
async def get_hold(
    hold_id: str,
    deps: HoldsDependencies = Depends(get_deps),
):
    """Get a hold by ID."""
    hold = await deps.holds_repo.get(hold_id)
    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hold {hold_id} not found",
        )
    return HoldResponse.from_hold(hold)


@router.post("/{hold_id}/capture", response_model=HoldOperationResponse)
async def capture_hold(
    hold_id: str,
    request: CaptureHoldRequest | None = None,
    deps: HoldsDependencies = Depends(get_deps),
):
    """Capture (complete) a hold."""
    amount = request.amount if request else None
    tx_id = request.tx_id if request else None

    result = await deps.holds_repo.capture(hold_id, amount=amount, tx_id=tx_id)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )

    return HoldOperationResponse(
        success=True,
        hold=HoldResponse.from_hold(result.hold),
    )


@router.post("/{hold_id}/void", response_model=HoldOperationResponse)
async def void_hold(
    hold_id: str,
    deps: HoldsDependencies = Depends(get_deps),
):
    """Void (cancel) a hold, releasing the funds."""
    result = await deps.holds_repo.void(hold_id)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error,
        )

    return HoldOperationResponse(
        success=True,
        hold=HoldResponse.from_hold(result.hold),
    )


@router.get("/wallet/{wallet_id}", response_model=list[HoldResponse])
async def list_wallet_holds(
    wallet_id: str,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    deps: HoldsDependencies = Depends(get_deps),
):
    """List holds for a wallet."""
    holds = await deps.holds_repo.list_by_wallet(
        wallet_id=wallet_id,
        status=status_filter,
        limit=limit,
    )
    return [HoldResponse.from_hold(h) for h in holds]


@router.get("", response_model=list[HoldResponse])
async def list_active_holds(
    limit: int = Query(default=100, ge=1, le=500),
    deps: HoldsDependencies = Depends(get_deps),
):
    """List all active holds."""
    holds = await deps.holds_repo.list_active(limit=limit)
    return [HoldResponse.from_hold(h) for h in holds]


@router.post("/expire", response_model=dict)
async def expire_old_holds(
    _: Principal = Depends(require_admin_principal),
    deps: HoldsDependencies = Depends(get_deps),
):
    """Mark expired holds as expired. Admin endpoint."""
    count = await deps.holds_repo.expire_old_holds()
    return {"expired_count": count}
