"""Recurring subscription API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_api.services.recurring_billing import compute_next_billing

router = APIRouter(dependencies=[Depends(require_principal)])


class CreateSubscriptionRequest(BaseModel):
    wallet_id: str
    merchant: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = "USD"
    billing_cycle: Literal["daily", "weekly", "monthly", "yearly"] = "monthly"
    billing_day: int = Field(default=1, ge=1, le=31)
    destination_address: str
    token: str = "USDC"
    chain: str = "base_sepolia"
    memo: Optional[str] = None
    merchant_mcc: Optional[str] = None
    card_id: Optional[str] = None
    auto_approve: bool = True
    auto_approve_threshold: Decimal = Field(default=Decimal("100.00"))
    amount_tolerance: Decimal = Field(default=Decimal("5.00"))
    notify_owner: bool = True
    notification_channel: Optional[str] = None
    max_failures: int = Field(default=3, ge=1, le=20)
    autofund_enabled: bool = False
    autofund_amount: Optional[Decimal] = None
    start_at: Optional[datetime] = None


class SubscriptionResponse(BaseModel):
    id: str
    wallet_id: str
    owner_id: str
    merchant: str
    amount_cents: int
    currency: str
    billing_cycle: str
    billing_day: int
    next_billing: datetime
    status: str
    destination_address: Optional[str] = None
    token: str = "USDC"
    chain: str = "base_sepolia"
    memo: Optional[str] = None
    autofund_enabled: bool = False
    autofund_amount_cents: Optional[int] = None
    failure_count: int = 0
    max_failures: int = 3
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: dict) -> "SubscriptionResponse":
        return cls(
            id=str(row.get("id")),
            wallet_id=str(row.get("wallet_id")),
            owner_id=str(row.get("owner_id")),
            merchant=str(row.get("merchant")),
            amount_cents=int(row.get("amount_cents", 0) or 0),
            currency=str(row.get("currency", "USD")),
            billing_cycle=str(row.get("billing_cycle", "monthly")),
            billing_day=int(row.get("billing_day", 1) or 1),
            next_billing=row.get("next_billing"),
            status=str(row.get("status", "active")),
            destination_address=row.get("destination_address"),
            token=str(row.get("token", "USDC")),
            chain=str(row.get("chain", "base_sepolia")),
            memo=row.get("memo"),
            autofund_enabled=bool(row.get("autofund_enabled", False)),
            autofund_amount_cents=(
                int(row.get("autofund_amount_cents"))
                if row.get("autofund_amount_cents") is not None
                else None
            ),
            failure_count=int(row.get("failure_count", 0) or 0),
            max_failures=int(row.get("max_failures", 3) or 3),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


class CancelSubscriptionResponse(BaseModel):
    id: str
    status: str


class ProcessDueResponse(BaseModel):
    processed: int
    charged: int
    failed: int
    results: list[dict]


class SubscriptionDependencies:
    def __init__(self, *, subscription_repo, wallet_repo, agent_repo, recurring_service):
        self.subscription_repo = subscription_repo
        self.wallet_repo = wallet_repo
        self.agent_repo = agent_repo
        self.recurring_service = recurring_service


def get_deps() -> SubscriptionDependencies:
    raise NotImplementedError("Dependency override required")


async def _require_wallet_access(wallet_id: str, principal: Principal, deps: SubscriptionDependencies):
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return wallet


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: CreateSubscriptionRequest,
    deps: SubscriptionDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    wallet = await _require_wallet_access(payload.wallet_id, principal, deps)

    amount_cents = int((payload.amount * Decimal(100)).to_integral_value())
    auto_approve_threshold_cents = int((payload.auto_approve_threshold * Decimal(100)).to_integral_value())
    amount_tolerance_cents = int((payload.amount_tolerance * Decimal(100)).to_integral_value())
    autofund_amount_cents = (
        int((payload.autofund_amount * Decimal(100)).to_integral_value())
        if payload.autofund_amount is not None
        else None
    )

    next_billing = payload.start_at or datetime.now(timezone.utc)
    if payload.start_at is None:
        next_billing = compute_next_billing(
            current=next_billing,
            billing_cycle=payload.billing_cycle,
            billing_day=payload.billing_day,
        )

    row = await deps.subscription_repo.create_subscription(
        wallet_id=wallet.wallet_id,
        owner_id=principal.organization_id,
        merchant=payload.merchant,
        amount_cents=amount_cents,
        currency=payload.currency,
        billing_cycle=payload.billing_cycle,
        billing_day=payload.billing_day,
        next_billing=next_billing,
        merchant_mcc=payload.merchant_mcc,
        card_id=payload.card_id,
        auto_approve=payload.auto_approve,
        auto_approve_threshold_cents=auto_approve_threshold_cents,
        amount_tolerance_cents=amount_tolerance_cents,
        notify_owner=payload.notify_owner,
        notification_channel=payload.notification_channel,
        max_failures=payload.max_failures,
        destination_address=payload.destination_address,
        token=payload.token.upper(),
        chain=payload.chain,
        memo=payload.memo,
        autofund_enabled=payload.autofund_enabled,
        autofund_amount_cents=autofund_amount_cents,
    )
    return SubscriptionResponse.from_row(row)


@router.get("", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    wallet_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    deps: SubscriptionDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if wallet_id:
        await _require_wallet_access(wallet_id, principal, deps)
    rows = await deps.subscription_repo.list_subscriptions(
        owner_id=None if principal.is_admin else principal.organization_id,
        wallet_id=wallet_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [SubscriptionResponse.from_row(row) for row in rows]


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    deps: SubscriptionDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    row = await deps.subscription_repo.get_subscription(subscription_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    owner_id = str(row.get("owner_id", ""))
    if not principal.is_admin and owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return SubscriptionResponse.from_row(row)


@router.post("/{subscription_id}/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    deps: SubscriptionDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    row = await deps.subscription_repo.get_subscription(subscription_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    owner_id = str(row.get("owner_id", ""))
    if not principal.is_admin and owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    cancelled = await deps.subscription_repo.cancel_subscription(subscription_id)
    if not cancelled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return CancelSubscriptionResponse(id=subscription_id, status="cancelled")


@router.post("/ops/run-due", response_model=ProcessDueResponse)
async def run_due_subscriptions(
    limit: int = Query(default=50, ge=1, le=500),
    deps: SubscriptionDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    results = await deps.recurring_service.process_due_subscriptions(limit=limit)
    charged = sum(1 for item in results if item.status == "charged")
    failed = sum(1 for item in results if item.status == "failed")
    return ProcessDueResponse(
        processed=len(results),
        charged=charged,
        failed=failed,
        results=[
            {
                "subscription_id": item.subscription_id,
                "billing_event_id": item.billing_event_id,
                "status": item.status,
                "tx_hash": item.tx_hash,
                "reason": item.reason,
            }
            for item in results
        ],
    )
