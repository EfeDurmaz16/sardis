"""Stripe Stablecoin-Backed Card Issuing API endpoints.

Enables agents to fund Visa prepaid cards directly with USDC on Base.
No fiat off-ramp needed — Stripe handles USDC→USD conversion at spend time.

Endpoints:
- POST /stablecoin-cards/onboard     — Create connected account + financial account
- GET  /stablecoin-cards/deposit-info — Get USDC deposit address on Base
- GET  /stablecoin-cards/balance      — Get USDC + USD balances
- POST /stablecoin-cards/issue        — Issue a stablecoin-backed virtual card
- GET  /stablecoin-cards/deposits     — List USDC deposit history
"""
from __future__ import annotations

import logging
import os
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stablecoin-cards", tags=["stablecoin-cards"])


# ── Request/Response Models ──────────────────────────────────────────


class OnboardAgentRequest(BaseModel):
    agent_name: str = Field(description="Display name for the agent/org")
    email: str = Field(description="Contact email for the connected account")
    wallet_id: str | None = Field(default=None, description="Sardis wallet ID")


class OnboardAgentResponse(BaseModel):
    account_id: str
    connected_account_id: str
    deposit_address: str | None = None
    deposit_chain: str = "base"
    deposit_token: str = "USDC"
    status: str


class DepositInfoResponse(BaseModel):
    deposit_address: str | None = None
    chain: str = "base"
    token: str = "USDC"
    token_contract: str
    usdc_balance: str
    usd_balance: str
    status: str


class BalanceResponse(BaseModel):
    usdc: str
    usd: str
    total_usd_equivalent: str


class IssueCardRequest(BaseModel):
    connected_account_id: str = Field(description="Stripe Connect account (acct_...)")
    cardholder_name: str = Field(description="Full name for the cardholder")
    cardholder_email: str = Field(description="Email for the cardholder")
    wallet_id: str | None = Field(default=None, description="Sardis wallet ID")
    limit_per_tx: Decimal = Field(default=Decimal("500"), description="Per-transaction limit (USD)")
    limit_daily: Decimal = Field(default=Decimal("2000"), description="Daily spending limit (USD)")
    limit_monthly: Decimal = Field(default=Decimal("10000"), description="Monthly spending limit (USD)")


class IssueCardResponse(BaseModel):
    card_id: str
    last4: str
    exp_month: int
    exp_year: int
    status: str
    funding_source: str = "stablecoin"
    connected_account_id: str
    cardholder_id: str
    limits: dict


class DepositHistoryItem(BaseModel):
    deposit_id: str
    amount: str
    currency: str
    chain: str
    tx_hash: str | None = None
    status: str
    created_at: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────


def _get_stablecoin_client():
    """Get or create Stripe Stablecoin client."""
    from sardis_cards.providers.stripe_stablecoin import StripeStablecoinClient

    api_key = os.getenv("STRIPE_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured (STRIPE_API_KEY missing)",
        )

    stablecoin_enabled = os.getenv("STRIPE_STABLECOIN_ISSUING_ENABLED", "false").lower() == "true"
    if not stablecoin_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stablecoin card issuing not enabled (set STRIPE_STABLECOIN_ISSUING_ENABLED=true)",
        )

    return StripeStablecoinClient(api_key=api_key)


def _get_stablecoin_service():
    """Get or create Stripe Stablecoin Card Service."""
    from sardis_cards.providers.stripe_stablecoin import StablecoinCardService

    client = _get_stablecoin_client()
    return StablecoinCardService(client)


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/onboard", response_model=OnboardAgentResponse)
async def onboard_agent(request: OnboardAgentRequest):
    """Onboard an agent for stablecoin-backed card issuing.

    Creates a Stripe Connect account and Financial Account v2 with
    USDC support on Base. Returns the deposit address where USDC
    should be sent to fund the account.
    """
    service = _get_stablecoin_service()
    try:
        fa = await service.onboard_agent(
            agent_name=request.agent_name,
            email=request.email,
            wallet_id=request.wallet_id,
        )
        return OnboardAgentResponse(
            account_id=fa.account_id,
            connected_account_id=fa.connected_account_id,
            deposit_address=fa.deposit_address,
            deposit_chain=fa.deposit_chain,
            status=fa.status.value,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Onboarding failed: {e}",
        ) from e
    finally:
        await service.close()


@router.get("/deposit-info", response_model=DepositInfoResponse)
async def get_deposit_info(
    financial_account_id: str,
    connected_account_id: str,
):
    """Get USDC deposit address and balance for a financial account.

    Returns the Base address where USDC should be sent, along with
    current USDC and USD balances.
    """
    service = _get_stablecoin_service()
    try:
        info = await service.get_deposit_info(
            financial_account_id, connected_account_id
        )
        return DepositInfoResponse(**info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get deposit info: {e}",
        ) from e
    finally:
        await service.close()


@router.get("/balance", response_model=BalanceResponse)
async def get_stablecoin_balance(
    financial_account_id: str,
    connected_account_id: str,
):
    """Get USDC and USD balances for a stablecoin financial account."""
    client = _get_stablecoin_client()
    try:
        balance = await client.get_stablecoin_balance(
            financial_account_id, connected_account_id
        )
        return BalanceResponse(
            usdc=str(balance["usdc"]),
            usd=str(balance["usd"]),
            total_usd_equivalent=str(balance["total_usd_equivalent"]),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Balance query failed: {e}",
        ) from e
    finally:
        await client.close()


@router.post("/issue", response_model=IssueCardResponse)
async def issue_stablecoin_card(request: IssueCardRequest):
    """Issue a stablecoin-backed Visa virtual card.

    Creates a cardholder and virtual card on the connected account.
    The card is backed by the USDC balance in the financial account.
    Stripe converts USDC to USD at the point of sale.
    """
    service = _get_stablecoin_service()
    try:
        card = await service.issue_card(
            connected_account_id=request.connected_account_id,
            cardholder_name=request.cardholder_name,
            cardholder_email=request.cardholder_email,
            limit_per_tx=request.limit_per_tx,
            limit_daily=request.limit_daily,
            limit_monthly=request.limit_monthly,
            wallet_id=request.wallet_id,
        )
        return IssueCardResponse(
            card_id=card["card_id"],
            last4=card["last4"],
            exp_month=card["exp_month"],
            exp_year=card["exp_year"],
            status=card["status"],
            connected_account_id=card["connected_account_id"],
            cardholder_id=card["cardholder_id"],
            limits=card["limits"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Card issuance failed: {e}",
        ) from e
    finally:
        await service.close()


@router.get("/deposits", response_model=list[DepositHistoryItem])
async def list_deposits(
    financial_account_id: str,
    connected_account_id: str,
    limit: int = 20,
):
    """List USDC deposits received by a financial account."""
    client = _get_stablecoin_client()
    try:
        deposits = await client.list_received_credits(
            financial_account_id, connected_account_id, limit=limit
        )
        return [
            DepositHistoryItem(
                deposit_id=d.deposit_id,
                amount=str(d.amount),
                currency=d.currency,
                chain=d.chain,
                tx_hash=d.tx_hash,
                status=d.status.value,
                created_at=d.created_at.isoformat() if d.created_at else None,
            )
            for d in deposits
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list deposits: {e}",
        ) from e
    finally:
        await client.close()
