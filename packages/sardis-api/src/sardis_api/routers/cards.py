"""Virtual Card API endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

from sardis_v2_core import VirtualCard, CardStatus, CardType, FundingSource

router = APIRouter()


# Request/Response Models
class IssueCardRequest(BaseModel):
    """Request to issue a new virtual card."""
    wallet_id: str
    card_type: str = Field(default="multi_use", description="Card type: single_use, multi_use, merchant_locked")
    limit_per_tx: Decimal = Field(default=Decimal("500.00"), description="Maximum per-transaction amount")
    limit_daily: Decimal = Field(default=Decimal("2000.00"), description="Maximum daily spend")
    limit_monthly: Decimal = Field(default=Decimal("10000.00"), description="Maximum monthly spend")
    locked_merchant_id: Optional[str] = Field(default=None, description="Merchant ID for merchant-locked cards")
    funding_source: str = Field(default="stablecoin", description="Funding source: stablecoin, bank_transfer, crypto")


class FundCardRequest(BaseModel):
    """Request to fund a card."""
    amount: Decimal = Field(gt=0, description="Amount to fund")
    source: str = Field(default="stablecoin", description="Funding source")


class UpdateLimitsRequest(BaseModel):
    """Request to update card spending limits."""
    limit_per_tx: Optional[Decimal] = Field(default=None, description="New per-transaction limit")
    limit_daily: Optional[Decimal] = Field(default=None, description="New daily limit")
    limit_monthly: Optional[Decimal] = Field(default=None, description="New monthly limit")


class CardResponse(BaseModel):
    """Virtual card response."""
    card_id: str
    wallet_id: str
    provider: str
    card_number_last4: str
    expiry_month: int
    expiry_year: int
    card_type: str
    status: str
    funding_source: str
    funded_amount: str
    available_balance: str
    limit_per_tx: str
    limit_daily: str
    limit_monthly: str
    spent_today: str
    spent_this_month: str
    total_spent: str
    created_at: str
    activated_at: Optional[str]
    last_used_at: Optional[str]

    @classmethod
    def from_card(cls, card: VirtualCard) -> "CardResponse":
        return cls(
            card_id=card.card_id,
            wallet_id=card.wallet_id,
            provider=card.provider,
            card_number_last4=card.masked_number[-4:] if card.masked_number else "",
            expiry_month=card.expiry_month,
            expiry_year=card.expiry_year,
            card_type=card.card_type.value,
            status=card.status.value,
            funding_source=card.funding_source.value,
            funded_amount=str(card.funded_amount),
            available_balance=str(card.available_balance),
            limit_per_tx=str(card.limit_per_tx),
            limit_daily=str(card.limit_daily),
            limit_monthly=str(card.limit_monthly),
            spent_today=str(card.spent_today),
            spent_this_month=str(card.spent_this_month),
            total_spent=str(card.total_spent),
            created_at=card.created_at.isoformat(),
            activated_at=card.activated_at.isoformat() if card.activated_at else None,
            last_used_at=card.last_used_at.isoformat() if card.last_used_at else None,
        )


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
    settled_at: Optional[str]


# In-memory storage for demo (replace with database in production)
_cards_store: dict[str, VirtualCard] = {}


# Endpoints
@router.post("", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def issue_card(request: IssueCardRequest):
    """
    Issue a new virtual card linked to a wallet.
    
    The card is created and automatically activated.
    Cards can be funded from stablecoin balances or other sources.
    """
    from datetime import datetime, timezone
    import uuid
    
    # Map string to enums
    try:
        card_type = CardType(request.card_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid card_type: {request.card_type}. Must be one of: single_use, multi_use, merchant_locked"
        )
    
    try:
        funding_source = FundingSource(request.funding_source)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid funding_source: {request.funding_source}. Must be one of: stablecoin, bank_transfer, crypto"
        )
    
    # Validate merchant-locked cards
    if card_type == CardType.MERCHANT_LOCKED and not request.locked_merchant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merchant-locked cards require a locked_merchant_id"
        )
    
    # Create the card
    card = VirtualCard(
        card_id=f"vc_{uuid.uuid4().hex[:16]}",
        wallet_id=request.wallet_id,
        provider="internal",  # Use "lithic" when Lithic is integrated
        card_type=card_type,
        status=CardStatus.ACTIVE,
        funding_source=funding_source,
        limit_per_tx=request.limit_per_tx,
        limit_daily=request.limit_daily,
        limit_monthly=request.limit_monthly,
        locked_merchant_id=request.locked_merchant_id,
        activated_at=datetime.now(timezone.utc),
    )
    
    _cards_store[card.card_id] = card
    return CardResponse.from_card(card)


@router.get("", response_model=List[CardResponse])
async def list_cards(
    wallet_id: Optional[str] = Query(None, description="Filter by wallet ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by card status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List virtual cards."""
    cards = list(_cards_store.values())
    
    if wallet_id:
        cards = [c for c in cards if c.wallet_id == wallet_id]
    
    if status_filter:
        try:
            target_status = CardStatus(status_filter)
            cards = [c for c in cards if c.status == target_status]
        except ValueError:
            pass
    
    cards = cards[offset:offset + limit]
    return [CardResponse.from_card(c) for c in cards]


@router.get("/{card_id}", response_model=CardResponse)
async def get_card(card_id: str):
    """Get virtual card details."""
    card = _cards_store.get(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return CardResponse.from_card(card)


@router.post("/{card_id}/fund", response_model=CardResponse)
async def fund_card(card_id: str, request: FundCardRequest):
    """
    Fund a virtual card.
    
    Transfers funds from the agent's stablecoin balance to the card.
    """
    card = _cards_store.get(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    if card.status != CardStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Card is {card.status.value}, cannot fund"
        )
    
    card.funded_amount += request.amount
    return CardResponse.from_card(card)


@router.post("/{card_id}/freeze", response_model=CardResponse)
async def freeze_card(card_id: str):
    """
    Freeze a card to prevent transactions.
    
    The card can be unfrozen later.
    """
    from datetime import datetime, timezone
    
    card = _cards_store.get(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    if card.status == CardStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot freeze a cancelled card"
        )
    
    card.status = CardStatus.FROZEN
    card.frozen_at = datetime.now(timezone.utc)
    return CardResponse.from_card(card)


@router.post("/{card_id}/unfreeze", response_model=CardResponse)
async def unfreeze_card(card_id: str):
    """Unfreeze a previously frozen card."""
    card = _cards_store.get(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    if card.status != CardStatus.FROZEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Card is {card.status.value}, not frozen"
        )
    
    card.status = CardStatus.ACTIVE
    card.frozen_at = None
    return CardResponse.from_card(card)


@router.delete("/{card_id}", response_model=CardResponse)
async def cancel_card(card_id: str):
    """
    Cancel a card permanently.
    
    This action cannot be undone. Any remaining balance is returned to the wallet.
    """
    from datetime import datetime, timezone
    
    card = _cards_store.get(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    if card.status == CardStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card is already cancelled"
        )
    
    card.status = CardStatus.CANCELLED
    card.cancelled_at = datetime.now(timezone.utc)
    card.is_active = False
    return CardResponse.from_card(card)


@router.patch("/{card_id}/limits", response_model=CardResponse)
async def update_card_limits(card_id: str, request: UpdateLimitsRequest):
    """Update card spending limits."""
    card = _cards_store.get(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    if request.limit_per_tx is not None:
        card.limit_per_tx = request.limit_per_tx
    if request.limit_daily is not None:
        card.limit_daily = request.limit_daily
    if request.limit_monthly is not None:
        card.limit_monthly = request.limit_monthly
    
    return CardResponse.from_card(card)


@router.get("/{card_id}/transactions", response_model=List[CardTransactionResponse])
async def list_card_transactions(
    card_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List transactions for a card."""
    card = _cards_store.get(card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    # In production, fetch from database or provider
    # For now, return empty list
    return []


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def receive_card_webhook(request: Request):
    """
    Receive webhooks from card provider (Lithic).
    
    This endpoint handles transaction events, card status changes, etc.
    """
    # In production, verify signature and process webhook
    body = await request.body()
    # Process webhook...
    return {"status": "received"}
