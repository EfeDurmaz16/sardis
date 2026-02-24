"""Stripe tenant-aware funding endpoints for Issuing balance top-ups."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_api.idempotency import get_idempotency_key, run_idempotent

router = APIRouter(prefix="/stripe/funding", tags=["stripe-funding"])


@dataclass
class StripeFundingDeps:
    treasury_provider: Any
    default_connected_account_id: str = ""
    connected_account_map: dict[str, str] | None = None


def get_deps() -> StripeFundingDeps:
    """Dependency injection placeholder."""
    raise NotImplementedError("Must be overridden")


class FundIssuingBalanceRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    description: str = Field(default="Fund agent virtual cards")
    connected_account_id: Optional[str] = Field(
        default=None,
        description="Optional Stripe Connect account id (acct_...).",
    )
    metadata: dict[str, str] | None = None


class FundIssuingBalanceResponse(BaseModel):
    transfer_id: str
    amount: str
    currency: str
    status: str
    connected_account_id: Optional[str] = None
    connected_account_source: str


class ConnectedAccountResolution(BaseModel):
    connected_account_id: Optional[str] = None
    source: str


def _resolve_connected_account(
    *,
    principal: Principal,
    deps: StripeFundingDeps,
    requested: Optional[str],
) -> tuple[Optional[str], str]:
    if requested:
        return requested, "request"

    account_map = deps.connected_account_map or {}
    mapped = account_map.get(principal.organization_id)
    if mapped:
        return mapped, "org_map"

    default = (deps.default_connected_account_id or "").strip()
    if default:
        return default, "default"

    return None, "none"


@router.get("/resolve-connected-account", response_model=ConnectedAccountResolution)
async def resolve_connected_account(
    deps: StripeFundingDeps = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    connected_account_id, source = _resolve_connected_account(
        principal=principal,
        deps=deps,
        requested=None,
    )
    return ConnectedAccountResolution(connected_account_id=connected_account_id, source=source)


@router.post("/issuing/topups", response_model=FundIssuingBalanceResponse)
async def fund_issuing_balance(
    payload: FundIssuingBalanceRequest,
    request: Request,
    deps: StripeFundingDeps = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not deps.treasury_provider:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="stripe_treasury_not_configured",
        )

    connected_account_id, source = _resolve_connected_account(
        principal=principal,
        deps=deps,
        requested=payload.connected_account_id,
    )

    if connected_account_id and not connected_account_id.startswith("acct_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_connected_account_id",
        )

    idem_key = get_idempotency_key(request) or (
        f"{principal.organization_id}:{payload.amount}:{connected_account_id or 'platform'}:{payload.description}"
    )

    async def _fund() -> tuple[int, object]:
        metadata = {
            "org_id": principal.organization_id,
            "connected_account_source": source,
        }
        if payload.metadata:
            metadata.update(payload.metadata)

        transfer = await deps.treasury_provider.fund_issuing_balance(
            amount=payload.amount,
            description=payload.description,
            connected_account_id=connected_account_id,
            metadata=metadata,
        )
        return 200, FundIssuingBalanceResponse(
            transfer_id=str(getattr(transfer, "id", "")),
            amount=str(getattr(transfer, "amount", payload.amount)),
            currency=str(getattr(transfer, "currency", "usd")),
            status=str(getattr(transfer, "status", "processing")),
            connected_account_id=connected_account_id,
            connected_account_source=source,
        ).model_dump()

    return await run_idempotent(
        request=request,
        principal=principal,
        operation="stripe.funding.issuing",
        key=str(idem_key),
        payload=payload.model_dump(),
        fn=_fund,
        ttl_seconds=7 * 24 * 60 * 60,
    )
