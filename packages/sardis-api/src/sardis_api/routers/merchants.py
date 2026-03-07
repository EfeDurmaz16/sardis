"""Merchant management API router for Pay with Sardis."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


# ── Request / Response Models ──────────────────────────────────────

class CreateMerchantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    logo_url: Optional[str] = None
    webhook_url: Optional[str] = None
    settlement_preference: str = Field(default="usdc", pattern="^(usdc|fiat)$")
    mcc_code: Optional[str] = Field(default=None, max_length=4)
    category: Optional[str] = None
    platform_fee_bps: int = Field(default=0, ge=0, le=500)


class UpdateMerchantRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = None
    webhook_url: Optional[str] = None
    settlement_preference: Optional[str] = Field(default=None, pattern="^(usdc|fiat)$")
    mcc_code: Optional[str] = Field(default=None, max_length=4)
    category: Optional[str] = None
    platform_fee_bps: Optional[int] = Field(default=None, ge=0, le=500)


class SetBankAccountRequest(BaseModel):
    account_holder_name: str
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None
    swift_bic: Optional[str] = None
    bank_name: Optional[str] = None
    bridge_account_id: Optional[str] = None


class MerchantResponse(BaseModel):
    merchant_id: str
    name: str
    logo_url: Optional[str] = None
    webhook_url: Optional[str] = None
    settlement_preference: str
    settlement_wallet_id: Optional[str] = None
    has_bank_account: bool = False
    mcc_code: Optional[str] = None
    category: Optional[str] = None
    platform_fee_bps: int = 0
    is_active: bool = True
    created_at: str
    updated_at: str


class SettlementResponse(BaseModel):
    session_id: str
    amount: str
    currency: str
    status: str
    settlement_status: Optional[str] = None
    offramp_id: Optional[str] = None
    tx_hash: Optional[str] = None
    created_at: str


# ── Checkout Links Models ─────────────────────────────────────────

class CreateCheckoutLinkRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USDC")
    description: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$")


class UpdateCheckoutLinkRequest(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = Field(default=None, max_length=100, pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    is_active: Optional[bool] = None


class CheckoutLinkResponse(BaseModel):
    link_id: str
    merchant_id: str
    amount: str
    currency: str
    description: Optional[str] = None
    slug: str
    checkout_url: str
    is_active: bool
    created_at: str
    updated_at: str


# ── Dependencies ──────────────────────────────────────────────────

@dataclass
class MerchantDependencies:
    merchant_repo: Any
    wallet_manager: Any
    settlement_service: Any = None
    checkout_base_url: str = "https://checkout.sardis.sh"


def get_deps() -> MerchantDependencies:
    raise RuntimeError("MerchantDependencies not configured")


def _merchant_response(m) -> MerchantResponse:
    return MerchantResponse(
        merchant_id=m.merchant_id,
        name=m.name,
        logo_url=m.logo_url,
        webhook_url=m.webhook_url,
        settlement_preference=m.settlement_preference,
        settlement_wallet_id=m.settlement_wallet_id,
        has_bank_account=bool(m.bank_account),
        mcc_code=m.mcc_code,
        category=m.category,
        platform_fee_bps=m.platform_fee_bps,
        is_active=m.is_active,
        created_at=m.created_at.isoformat(),
        updated_at=m.updated_at.isoformat(),
    )


# ── Merchant Endpoints ────────────────────────────────────────────

@router.post("/", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant(
    body: CreateMerchantRequest,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Create a merchant with auto-provisioned settlement wallet."""
    from sardis_v2_core.merchant import Merchant

    merchant = Merchant(
        name=body.name,
        logo_url=body.logo_url,
        webhook_url=body.webhook_url,
        settlement_preference=body.settlement_preference,
        mcc_code=body.mcc_code,
        category=body.category,
        platform_fee_bps=body.platform_fee_bps,
    )

    # Auto-provision settlement wallet
    if deps.wallet_manager:
        try:
            settlement_wallet = await deps.wallet_manager.create_wallet(
                agent_id=f"merchant_{merchant.merchant_id}",
                label=f"Settlement wallet for {body.name}",
            )
            merchant.settlement_wallet_id = settlement_wallet.wallet_id
        except Exception:
            logger.exception("Failed to auto-provision settlement wallet for merchant %s", merchant.merchant_id)

    await deps.merchant_repo.create_merchant(merchant)
    return _merchant_response(merchant)


@router.get("/", response_model=list[MerchantResponse])
async def list_merchants(
    org_id: str = "default",
    deps: MerchantDependencies = Depends(get_deps),
):
    """List merchants for an organization."""
    merchants = await deps.merchant_repo.list_merchants(org_id)
    return [_merchant_response(m) for m in merchants]


@router.get("/{merchant_id}", response_model=MerchantResponse)
async def get_merchant(
    merchant_id: str,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Get merchant details."""
    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return _merchant_response(merchant)


@router.patch("/{merchant_id}", response_model=MerchantResponse)
async def update_merchant(
    merchant_id: str,
    body: UpdateMerchantRequest,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Update merchant details."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    merchant = await deps.merchant_repo.update_merchant(merchant_id, **updates)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return _merchant_response(merchant)


@router.post("/{merchant_id}/bank-account", response_model=MerchantResponse)
async def set_bank_account(
    merchant_id: str,
    body: SetBankAccountRequest,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Set bank account for fiat settlement."""
    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    bank_data = body.model_dump(exclude_none=True)
    updated = await deps.merchant_repo.update_merchant(merchant_id, bank_account=bank_data)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update bank account")
    return _merchant_response(updated)


@router.get("/{merchant_id}/settlements", response_model=list[SettlementResponse])
async def list_settlements(
    merchant_id: str,
    deps: MerchantDependencies = Depends(get_deps),
):
    """List settlement history for a merchant."""
    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    sessions = await deps.merchant_repo.list_sessions_by_merchant(merchant_id)
    return [
        SettlementResponse(
            session_id=s.session_id,
            amount=str(s.amount),
            currency=s.currency,
            status=s.status,
            settlement_status=s.settlement_status,
            offramp_id=s.offramp_id,
            tx_hash=s.tx_hash,
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
        if s.status in ("paid", "settled")
    ]


# ── Checkout Links Endpoints ──────────────────────────────────────

@router.post("/{merchant_id}/links", response_model=CheckoutLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout_link(
    merchant_id: str,
    body: CreateCheckoutLinkRequest,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Create a reusable checkout link for a merchant."""
    from sardis_v2_core.merchant import MerchantCheckoutLink

    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    link = MerchantCheckoutLink(
        merchant_id=merchant_id,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        slug=body.slug,
    )

    try:
        await deps.merchant_repo.create_checkout_link(link)
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Slug already in use for this merchant")
        raise

    return CheckoutLinkResponse(
        link_id=link.link_id,
        merchant_id=link.merchant_id,
        amount=f"{link.amount:.2f}",
        currency=link.currency,
        description=link.description,
        slug=link.slug,
        checkout_url=f"{deps.checkout_base_url}/link/{link.slug}",
        is_active=link.is_active,
        created_at=link.created_at.isoformat(),
        updated_at=link.updated_at.isoformat(),
    )


@router.get("/{merchant_id}/links", response_model=list[CheckoutLinkResponse])
async def list_checkout_links(
    merchant_id: str,
    deps: MerchantDependencies = Depends(get_deps),
):
    """List checkout links for a merchant."""
    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    links = await deps.merchant_repo.list_checkout_links(merchant_id)
    return [
        CheckoutLinkResponse(
            link_id=l.link_id,
            merchant_id=l.merchant_id,
            amount=f"{l.amount:.2f}",
            currency=l.currency,
            description=l.description,
            slug=l.slug,
            checkout_url=f"{deps.checkout_base_url}/link/{l.slug}",
            is_active=l.is_active,
            created_at=l.created_at.isoformat(),
            updated_at=l.updated_at.isoformat(),
        )
        for l in links
    ]


@router.patch("/{merchant_id}/links/{link_id}", response_model=CheckoutLinkResponse)
async def update_checkout_link(
    merchant_id: str,
    link_id: str,
    body: UpdateCheckoutLinkRequest,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Update a checkout link."""
    link = await deps.merchant_repo.get_checkout_link(link_id)
    if not link or link.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="Checkout link not found")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = await deps.merchant_repo.update_checkout_link(link_id, **updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Checkout link not found")

    return CheckoutLinkResponse(
        link_id=updated.link_id,
        merchant_id=updated.merchant_id,
        amount=f"{updated.amount:.2f}",
        currency=updated.currency,
        description=updated.description,
        slug=updated.slug,
        checkout_url=f"{deps.checkout_base_url}/link/{updated.slug}",
        is_active=updated.is_active,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{merchant_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checkout_link(
    merchant_id: str,
    link_id: str,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Delete a checkout link."""
    link = await deps.merchant_repo.get_checkout_link(link_id)
    if not link or link.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="Checkout link not found")

    await deps.merchant_repo.delete_checkout_link(link_id)
