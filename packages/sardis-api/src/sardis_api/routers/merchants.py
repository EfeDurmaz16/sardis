"""Merchant management API router for Pay with Sardis."""
from __future__ import annotations

import logging
from dataclasses import dataclass
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


# ── Dependencies ──────────────────────────────────────────────────

@dataclass
class MerchantDependencies:
    merchant_repo: Any
    wallet_manager: Any
    settlement_service: Any = None


def get_deps() -> MerchantDependencies:
    raise RuntimeError("MerchantDependencies not configured")


# ── Endpoints ─────────────────────────────────────────────────────

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

    return MerchantResponse(
        merchant_id=merchant.merchant_id,
        name=merchant.name,
        logo_url=merchant.logo_url,
        webhook_url=merchant.webhook_url,
        settlement_preference=merchant.settlement_preference,
        settlement_wallet_id=merchant.settlement_wallet_id,
        has_bank_account=bool(merchant.bank_account),
        mcc_code=merchant.mcc_code,
        category=merchant.category,
        platform_fee_bps=merchant.platform_fee_bps,
        is_active=merchant.is_active,
        created_at=merchant.created_at.isoformat(),
        updated_at=merchant.updated_at.isoformat(),
    )


@router.get("/", response_model=list[MerchantResponse])
async def list_merchants(
    org_id: str = "default",
    deps: MerchantDependencies = Depends(get_deps),
):
    """List merchants for an organization."""
    merchants = await deps.merchant_repo.list_merchants(org_id)
    return [
        MerchantResponse(
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
        for m in merchants
    ]


@router.get("/{merchant_id}", response_model=MerchantResponse)
async def get_merchant(
    merchant_id: str,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Get merchant details."""
    merchant = await deps.merchant_repo.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return MerchantResponse(
        merchant_id=merchant.merchant_id,
        name=merchant.name,
        logo_url=merchant.logo_url,
        webhook_url=merchant.webhook_url,
        settlement_preference=merchant.settlement_preference,
        settlement_wallet_id=merchant.settlement_wallet_id,
        has_bank_account=bool(merchant.bank_account),
        mcc_code=merchant.mcc_code,
        category=merchant.category,
        platform_fee_bps=merchant.platform_fee_bps,
        is_active=merchant.is_active,
        created_at=merchant.created_at.isoformat(),
        updated_at=merchant.updated_at.isoformat(),
    )


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
    return MerchantResponse(
        merchant_id=merchant.merchant_id,
        name=merchant.name,
        logo_url=merchant.logo_url,
        webhook_url=merchant.webhook_url,
        settlement_preference=merchant.settlement_preference,
        settlement_wallet_id=merchant.settlement_wallet_id,
        has_bank_account=bool(merchant.bank_account),
        mcc_code=merchant.mcc_code,
        category=merchant.category,
        platform_fee_bps=merchant.platform_fee_bps,
        is_active=merchant.is_active,
        created_at=merchant.created_at.isoformat(),
        updated_at=merchant.updated_at.isoformat(),
    )


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
    return MerchantResponse(
        merchant_id=updated.merchant_id,
        name=updated.name,
        logo_url=updated.logo_url,
        webhook_url=updated.webhook_url,
        settlement_preference=updated.settlement_preference,
        settlement_wallet_id=updated.settlement_wallet_id,
        has_bank_account=bool(updated.bank_account),
        mcc_code=updated.mcc_code,
        category=updated.category,
        platform_fee_bps=updated.platform_fee_bps,
        is_active=updated.is_active,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


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
