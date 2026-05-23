"""Merchant management API router for Pay with Sardis."""
from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from server.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


# ── Request / Response Models ──────────────────────────────────────

class CreateMerchantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    logo_url: str | None = None
    webhook_url: str | None = None
    settlement_preference: str = Field(default="usdc", pattern="^(usdc|fiat|stripe_connect)$")
    mcc_code: str | None = Field(default=None, max_length=4)
    category: str | None = None
    platform_fee_bps: int = Field(default=0, ge=0, le=500)


class UpdateMerchantRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    logo_url: str | None = None
    webhook_url: str | None = None
    settlement_preference: str | None = Field(default=None, pattern="^(usdc|fiat)$")
    mcc_code: str | None = Field(default=None, max_length=4)
    category: str | None = None
    platform_fee_bps: int | None = Field(default=None, ge=0, le=500)


class SetBankAccountRequest(BaseModel):
    account_holder_name: str
    routing_number: str | None = None
    account_number: str | None = None
    iban: str | None = None
    swift_bic: str | None = None
    bank_name: str | None = None
    bridge_account_id: str | None = None


class MerchantResponse(BaseModel):
    merchant_id: str
    name: str
    logo_url: str | None = None
    webhook_url: str | None = None
    settlement_preference: str
    settlement_wallet_id: str | None = None
    has_bank_account: bool = False
    mcc_code: str | None = None
    category: str | None = None
    platform_fee_bps: int = 0
    is_active: bool = True
    stripe_account_id: str | None = None
    stripe_onboarding_state: str = "not_started"
    stripe_charges_enabled: bool = False
    stripe_payouts_enabled: bool = False
    created_at: str
    updated_at: str


class SettlementResponse(BaseModel):
    session_id: str
    amount: str
    currency: str
    status: str
    settlement_status: str | None = None
    offramp_id: str | None = None
    tx_hash: str | None = None
    created_at: str


# ── Checkout Links Models ─────────────────────────────────────────

class CreateCheckoutLinkRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USDC")
    description: str | None = None
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$")


class UpdateCheckoutLinkRequest(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = None
    description: str | None = None
    slug: str | None = Field(default=None, max_length=100, pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    is_active: bool | None = None


class CheckoutLinkResponse(BaseModel):
    link_id: str
    merchant_id: str
    amount: str
    currency: str
    description: str | None = None
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
        stripe_account_id=m.stripe_account_id,
        stripe_onboarding_state=m.stripe_onboarding_state,
        stripe_charges_enabled=m.stripe_charges_enabled,
        stripe_payouts_enabled=m.stripe_payouts_enabled,
        created_at=m.created_at.isoformat(),
        updated_at=m.updated_at.isoformat(),
    )


# ── Merchant Endpoints ────────────────────────────────────────────

@router.post("", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant(
    body: CreateMerchantRequest,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Create a merchant with auto-provisioned settlement wallet."""
    from sardis.core.merchant import Merchant

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


@router.get("", response_model=list[MerchantResponse])
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


# ── Merchant Lookup (for unified payment client) ─────────────────

@router.get("/lookup", response_model=MerchantResponse)
async def lookup_merchant(
    domain: str | None = None,
    name: str | None = None,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Look up a merchant by domain or name.

    Used by the unified payment client for merchant discovery.
    Agents call this to find if a merchant is registered on Sardis
    and what payment protocols they support.
    """
    if not domain and not name:
        raise HTTPException(status_code=400, detail="Provide 'domain' or 'name' query parameter")

    from sardis.core.database import Database

    if domain:
        # Strip protocol and path
        clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
        row = await Database.fetchrow(
            """
            SELECT m.external_id, o.external_id AS org_ext_id, m.name, m.logo_url,
                m.webhook_url, m.webhook_secret, m.settlement_preference,
                m.settlement_wallet_id, m.bank_account, m.mcc_code, m.category,
                m.platform_fee_bps, m.is_active,
                m.stripe_account_id, m.stripe_onboarding_state,
                m.stripe_charges_enabled, m.stripe_payouts_enabled,
                m.stripe_details_submitted, m.stripe_disabled_reason,
                m.stripe_current_deadline, m.stripe_last_synced_at,
                m.created_at, m.updated_at
            FROM merchants m
            LEFT JOIN organizations o ON o.id = m.org_id
            WHERE m.website ILIKE $1 OR m.website ILIKE $2
            LIMIT 1
            """,
            f"%{clean_domain}%",
            f"%{clean_domain}%",
        )
    else:
        row = await Database.fetchrow(
            """
            SELECT m.external_id, o.external_id AS org_ext_id, m.name, m.logo_url,
                m.webhook_url, m.webhook_secret, m.settlement_preference,
                m.settlement_wallet_id, m.bank_account, m.mcc_code, m.category,
                m.platform_fee_bps, m.is_active,
                m.stripe_account_id, m.stripe_onboarding_state,
                m.stripe_charges_enabled, m.stripe_payouts_enabled,
                m.stripe_details_submitted, m.stripe_disabled_reason,
                m.stripe_current_deadline, m.stripe_last_synced_at,
                m.created_at, m.updated_at
            FROM merchants m
            LEFT JOIN organizations o ON o.id = m.org_id
            WHERE m.name ILIKE $1
            LIMIT 1
            """,
            f"%{name}%",
        )

    if not row:
        raise HTTPException(status_code=404, detail="Merchant not found")

    from sardis.core.merchant import MerchantRepository
    merchant = MerchantRepository._row_to_merchant(row)
    return _merchant_response(merchant)


# ── Checkout Links Endpoints ──────────────────────────────────────

@router.post("/{merchant_id}/links", response_model=CheckoutLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout_link(
    merchant_id: str,
    body: CreateCheckoutLinkRequest,
    deps: MerchantDependencies = Depends(get_deps),
):
    """Create a reusable checkout link for a merchant."""
    from sardis.core.merchant import MerchantCheckoutLink

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


# ── Self-Registration Endpoint ───────────────────────────────────
# POST /api/v2/merchants/register
# Allows authenticated users to register as merchants without manual
# intervention. Returns the created merchant + client credentials for
# the checkout embed SDK.


class MerchantRegisterRequest(BaseModel):
    """Self-registration payload for new merchants."""
    business_name: str = Field(..., min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    settlement_address: str | None = Field(
        default=None,
        description="EVM wallet address for USDC settlement. If omitted, a Sardis wallet is auto-provisioned.",
    )
    webhook_url: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=100)


class MerchantCredentials(BaseModel):
    """Client credentials returned after merchant registration."""
    client_id: str
    client_secret: str


class MerchantRegisterResponse(BaseModel):
    """Response from self-registration."""
    merchant_id: str
    business_name: str
    settlement_wallet_id: str | None = None
    settlement_address: str | None = None
    webhook_url: str | None = None
    credentials: MerchantCredentials
    embed_snippet: str
    created_at: str


def _generate_client_id(merchant_id: str) -> str:
    """Generate a deterministic client ID from merchant ID."""
    return f"mch_live_{merchant_id[:16]}"


def _generate_client_secret() -> str:
    """Generate a cryptographically secure client secret."""
    return f"msk_live_{secrets.token_urlsafe(32)}"


def _generate_embed_snippet(client_id: str) -> str:
    """Generate the HTML embed snippet for the checkout widget."""
    return (
        f'<script src="https://checkout.sardis.sh/sardis-checkout.js"></script>\n'
        f'<sardis-pay\n'
        f'  client-id="{client_id}"\n'
        f'  amount="25.00"\n'
        f'  currency="USDC"\n'
        f'></sardis-pay>'
    )


@router.post(
    "/register",
    response_model=MerchantRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Self-register as a merchant",
    description=(
        "Register a new merchant account for Pay with Sardis. "
        "Returns client credentials for the checkout embed SDK."
    ),
)
async def register_merchant(
    body: MerchantRegisterRequest,
    principal: Principal = Depends(require_principal),
    deps: MerchantDependencies = Depends(get_deps),
) -> MerchantRegisterResponse:
    """Self-register a merchant — no manual approval required."""
    from sardis.core.merchant import Merchant

    merchant = Merchant(
        name=body.business_name,
        org_id=principal.organization_id,
        logo_url=body.logo_url,
        webhook_url=body.webhook_url,
        settlement_preference="usdc",
        category=body.category,
    )

    # Settlement: use provided address or auto-provision a Sardis wallet
    if body.settlement_address:
        merchant.settlement_wallet_id = body.settlement_address
    elif deps.wallet_manager:
        try:
            settlement_wallet = await deps.wallet_manager.create_wallet(
                agent_id=f"merchant_{merchant.merchant_id}",
                label=f"Settlement wallet for {body.business_name}",
            )
            merchant.settlement_wallet_id = settlement_wallet.wallet_id
        except Exception:
            logger.exception(
                "Failed to auto-provision settlement wallet for merchant %s",
                merchant.merchant_id,
            )

    await deps.merchant_repo.create_merchant(merchant)

    # Generate client credentials
    client_id = _generate_client_id(merchant.merchant_id)
    client_secret = _generate_client_secret()

    # Store credentials (hashed secret) in merchant metadata
    secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
    try:
        await deps.merchant_repo.update_merchant(
            merchant.merchant_id,
            client_id=client_id,
            client_secret_hash=secret_hash,
            website=body.website,
            registered_by=principal.subject_id,
        )
    except Exception:
        logger.warning(
            "Could not persist client credentials for merchant %s — "
            "merchant was created but credentials may need manual setup",
            merchant.merchant_id,
        )

    embed_snippet = _generate_embed_snippet(client_id)

    return MerchantRegisterResponse(
        merchant_id=merchant.merchant_id,
        business_name=body.business_name,
        settlement_wallet_id=merchant.settlement_wallet_id,
        settlement_address=body.settlement_address,
        webhook_url=body.webhook_url,
        credentials=MerchantCredentials(
            client_id=client_id,
            client_secret=client_secret,
        ),
        embed_snippet=embed_snippet,
        created_at=merchant.created_at.isoformat(),
    )
