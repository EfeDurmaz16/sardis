"""Virtual Card API endpoints with dependency injection."""
from __future__ import annotations

import hashlib
import hmac
import logging
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import APIRouter, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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

def create_cards_router(
    card_repo,
    card_provider,
    webhook_secret: str | None = None,
    offramp_service=None,
    chain_executor=None,
    wallet_repo=None,
) -> APIRouter:
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

        # If offramp_service is available, use real USDC→USD→Lithic flow
        if offramp_service and chain_executor and wallet_repo and request.source == "stablecoin":
            wallet_id = card.get("wallet_id")
            if not wallet_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Card not linked to wallet")

            wallet = await wallet_repo.get(wallet_id)
            if not wallet:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked wallet not found")

            amount_minor = int(request.amount * 10**6)

            # 1. Get offramp quote (USDC→USD)
            try:
                quote = await offramp_service.get_quote(
                    input_token="USDC",
                    input_amount_minor=amount_minor,
                    input_chain="base",
                    output_currency="USD",
                )
            except Exception as e:
                logger.error("Offramp quote failed: %s", e)
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to get offramp quote")

            # 2. Get source address from wallet
            source_address = wallet.get_address("base") or ""
            for chain, addr in wallet.addresses.items():
                if addr:
                    source_address = addr
                    break

            if not source_address:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet has no on-chain address")

            # 3. Get destination (Lithic funding account or Bridge deposit)
            import os
            funding_account = os.getenv("LITHIC_FUNDING_ACCOUNT_ID", "")

            # 4. Execute offramp (Bridge converts USDC→USD→Lithic)
            try:
                tx = await offramp_service.execute(
                    quote=quote,
                    source_address=source_address,
                    destination_account=funding_account,
                )
            except Exception as e:
                logger.error("Offramp execute failed: %s", e)
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to execute offramp")

            # 5. Update card spend limit via Lithic provider
            try:
                await card_provider.fund_card(card_id=card_id, amount=float(request.amount))
            except Exception as e:
                logger.warning("Lithic fund_card call failed (offramp still processing): %s", e)

            # 6. Update funded_amount in DB
            current = card.get("funded_amount", 0) or 0
            row = await card_repo.update_funded_amount(card_id, float(current) + float(request.amount))
            return {
                **(row or {}),
                "offramp_tx_id": tx.transaction_id,
                "offramp_status": tx.status.value,
            }

        # Fallback: simple provider-based funding
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

        if webhook_secret:
            signature = request.headers.get("x-lithic-hmac")
            if not signature:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")
            expected = hmac.new(
                webhook_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

        import json
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

        event_type = payload.get("event_type", "")
        card_token = payload.get("card_token") or payload.get("data", {}).get("card_token")

        if event_type in ("card.transaction.created", "card.transaction.updated") and card_token:
            txn = payload.get("data", {})
            card = await card_repo.get_by_card_id(card_token)
            if card:
                await card_repo.record_transaction(
                    card_id=card_token,
                    transaction_id=txn.get("token", f"txn_{uuid.uuid4().hex[:12]}"),
                    amount=txn.get("amount", 0),
                    currency=txn.get("currency", "USD"),
                    merchant_name=txn.get("merchant", {}).get("descriptor", "Unknown"),
                    merchant_category=txn.get("merchant", {}).get("mcc", "0000"),
                    status=txn.get("status", "pending"),
                )

        logger.info("Processed webhook event_type=%s", event_type)
        return {"status": "received"}

    return r
