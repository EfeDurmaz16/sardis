"""Stripe tenant-aware funding endpoints for Issuing balance top-ups."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_api.canonical_state_machine import normalize_stripe_issuing_funding_event
from sardis_api.idempotency import get_idempotency_key, run_idempotent

router = APIRouter(prefix="/stripe/funding", tags=["stripe-funding"])


@dataclass
class StripeFundingDeps:
    treasury_provider: Any
    treasury_repo: Any = None
    canonical_repo: Any = None
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


class IssuingFundingHistoryItem(BaseModel):
    transfer_id: str
    provider: str
    amount_minor: int
    currency: str
    status: str
    connected_account_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IssuingFundingReconcileResponse(BaseModel):
    organization_id: str
    window_hours: int
    count: int
    total_minor: int
    by_status: dict[str, int] = Field(default_factory=dict)


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


def _status_value(value: Any) -> str:
    if value is None:
        return "processing"
    return str(getattr(value, "value", value)).strip().lower() or "processing"


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


@router.get("/issuing/topups/history", response_model=list[IssuingFundingHistoryItem])
async def list_issuing_topup_history(
    limit: int = Query(default=100, ge=1, le=500),
    provider: Optional[str] = Query(default=None),
    connected_account_id: Optional[str] = Query(default=None),
    deps: StripeFundingDeps = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if deps.treasury_repo is None:
        return []
    rows = await deps.treasury_repo.list_issuing_funding_events(
        principal.organization_id,
        limit=limit,
        provider=provider,
        connected_account_id=connected_account_id,
    )
    out: list[IssuingFundingHistoryItem] = []
    for row in rows:
        out.append(
            IssuingFundingHistoryItem(
                transfer_id=str(row.get("transfer_id", "")),
                provider=str(row.get("provider", "stripe")),
                amount_minor=int(row.get("amount_minor", 0) or 0),
                currency=str(row.get("currency", "USD")),
                status=str(row.get("status", "processing")),
                connected_account_id=row.get("connected_account_id"),
                idempotency_key=row.get("idempotency_key"),
                created_at=(
                    row.get("created_at").isoformat()
                    if hasattr(row.get("created_at"), "isoformat")
                    else str(row.get("created_at")) if row.get("created_at") is not None else None
                ),
                metadata=row.get("metadata") or {},
            )
        )
    return out


@router.get("/issuing/topups/reconcile", response_model=IssuingFundingReconcileResponse)
async def reconcile_issuing_topups(
    hours: int = Query(default=24, ge=1, le=24 * 90),
    deps: StripeFundingDeps = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if deps.treasury_repo is None:
        return IssuingFundingReconcileResponse(
            organization_id=principal.organization_id,
            window_hours=hours,
            count=0,
            total_minor=0,
            by_status={},
        )
    summary = await deps.treasury_repo.summarize_issuing_funding_events(
        principal.organization_id,
        hours=hours,
    )
    return IssuingFundingReconcileResponse(
        organization_id=str(summary.get("organization_id") or principal.organization_id),
        window_hours=int(summary.get("window_hours", hours)),
        count=int(summary.get("count", 0)),
        total_minor=int(summary.get("total_minor", 0)),
        by_status={str(k): int(v) for k, v in (summary.get("by_status") or {}).items()},
    )


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
        transfer_id = str(getattr(transfer, "id", "")) or "unknown"
        amount_value = Decimal(str(getattr(transfer, "amount", payload.amount)))
        currency_value = str(getattr(transfer, "currency", "usd")).upper()
        status_value = _status_value(getattr(transfer, "status", "processing"))
        amount_minor = int((amount_value * Decimal("100")).to_integral_value())

        if deps.treasury_repo is not None:
            await deps.treasury_repo.record_issuing_funding_event(
                organization_id=principal.organization_id,
                provider="stripe",
                transfer_id=transfer_id,
                amount_minor=amount_minor,
                currency=currency_value,
                status_value=status_value,
                connected_account_id=connected_account_id,
                idempotency_key=str(idem_key),
                metadata=metadata,
            )

        if deps.canonical_repo is not None:
            normalized = normalize_stripe_issuing_funding_event(
                organization_id=principal.organization_id,
                payload={
                    "transfer_id": transfer_id,
                    "status": status_value,
                    "amount_minor": amount_minor,
                    "currency": currency_value,
                    "description": payload.description,
                    "created_at": None,
                },
                transfer_id=transfer_id,
                connected_account_id=connected_account_id,
            )
            await deps.canonical_repo.ingest_event(
                normalized,
                drift_tolerance_minor=int(os.getenv("SARDIS_CANONICAL_DRIFT_TOLERANCE_MINOR", "1000")),
            )

        return 200, FundIssuingBalanceResponse(
            transfer_id=transfer_id,
            amount=str(amount_value),
            currency=currency_value.lower(),
            status=status_value,
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
