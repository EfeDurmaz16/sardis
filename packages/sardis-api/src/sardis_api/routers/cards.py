"""Virtual Card API endpoints with dependency injection."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import APIRouter, HTTPException, status, Query, Request
from pydantic import BaseModel, Field


# ---- Request/Response Models ----

class IssueCardRequest(BaseModel):
    """Request to issue a new virtual card."""
    wallet_id: str
    card_type: str = Field(default="multi_use")
    limit_per_tx: Decimal = Field(default=Decimal("500.00"))
    limit_daily: Decimal = Field(default=Decimal("2000.00"))
    limit_monthly: Decimal = Field(default=Decimal("10000.00"))
    locked_merchant_id: Optional[str] = None
    funding_source: str = Field(default="stablecoin")


class FundCardRequest(BaseModel):
    """Request to fund a card."""
    amount: Decimal = Field(gt=0)
    source: str = Field(default="stablecoin")


class UpdateLimitsRequest(BaseModel):
    """Request to update card spending limits."""
    limit_per_tx: Optional[Decimal] = None
    limit_daily: Optional[Decimal] = None
    limit_monthly: Optional[Decimal] = None


class CardTransactionResponse(BaseModel):
    """Card transaction response."""
    transaction_id: str
    card_id: str
    amount: str
    currency: str
    merchant_name: str
    merchant_category: str
    status: str
    created_at: str
    settled_at: Optional[str] = None


# ---- Backward-compatible empty router (so existing imports don't break) ----
router = APIRouter()


# ---- Factory function with dependency injection ----

def create_cards_router(card_repo, card_provider, webhook_secret: str | None = None) -> APIRouter:
    """Create a cards router with injected dependencies."""
    r = APIRouter()

    @r.post("", status_code=status.HTTP_201_CREATED)
    async def issue_card(request: IssueCardRequest):
        card_id = f"vc_{uuid.uuid4().hex[:16]}"
        provider_result = await card_provider.create_card(
            card_id=card_id,
            wallet_id=request.wallet_id,
            card_type=request.card_type,
            limit_per_tx=float(request.limit_per_tx),
            limit_daily=float(request.limit_daily),
            limit_monthly=float(request.limit_monthly),
        )
        row = await card_repo.create(
            card_id=card_id,
            wallet_id=request.wallet_id,
            provider="lithic",
            provider_card_id=provider_result.provider_card_id,
            card_type=request.card_type,
            limit_per_tx=float(request.limit_per_tx),
            limit_daily=float(request.limit_daily),
            limit_monthly=float(request.limit_monthly),
        )
        return row

    @r.get("")
    async def list_cards(
        wallet_id: Optional[str] = Query(None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ):
        if wallet_id:
            return await card_repo.get_by_wallet_id(wallet_id)
        return []

    @r.get("/{card_id}")
    async def get_card(card_id: str):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        return card

    @r.post("/{card_id}/fund")
    async def fund_card(card_id: str, request: FundCardRequest):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        await card_provider.fund_card(card_id=card_id, amount=float(request.amount))
        current = card.get("funded_amount", 0) or 0
        row = await card_repo.update_funded_amount(card_id, float(current) + float(request.amount))
        return row

    @r.post("/{card_id}/freeze")
    async def freeze_card(card_id: str):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        await card_provider.freeze_card(provider_card_id=card.get("provider_card_id"))
        row = await card_repo.update_status(card_id, "frozen")
        return row

    @r.post("/{card_id}/unfreeze")
    async def unfreeze_card(card_id: str):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        await card_provider.unfreeze_card(provider_card_id=card.get("provider_card_id"))
        row = await card_repo.update_status(card_id, "active")
        return row

    @r.delete("/{card_id}")
    async def cancel_card(card_id: str):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        await card_provider.cancel_card(provider_card_id=card.get("provider_card_id"))
        row = await card_repo.update_status(card_id, "cancelled")
        return row

    @r.patch("/{card_id}/limits")
    async def update_card_limits(card_id: str, request: UpdateLimitsRequest):
        row = await card_repo.update_limits(
            card_id,
            limit_per_tx=float(request.limit_per_tx) if request.limit_per_tx is not None else None,
            limit_daily=float(request.limit_daily) if request.limit_daily is not None else None,
            limit_monthly=float(request.limit_monthly) if request.limit_monthly is not None else None,
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        return row

    @r.get("/{card_id}/transactions")
    async def list_card_transactions(
        card_id: str,
        limit: int = Query(default=50, ge=1, le=100),
    ):
        return await card_repo.list_transactions(card_id, limit)

    @r.post("/webhooks", status_code=status.HTTP_200_OK)
    async def receive_card_webhook(request: Request):
        body = await request.body()
        return {"status": "received"}

    return r
