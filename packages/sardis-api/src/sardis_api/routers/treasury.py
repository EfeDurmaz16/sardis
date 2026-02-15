"""Fiat treasury API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Literal, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_api.idempotency import get_idempotency_key, run_idempotent
from sardis_api.providers.lithic_treasury import (
    CreateExternalBankAccountRequest,
    CreatePaymentRequest,
    LithicTreasuryClient,
)

router = APIRouter(tags=["treasury"])


@dataclass
class TreasuryDependencies:
    treasury_repo: Any
    lithic_client: Optional[LithicTreasuryClient]


def get_deps() -> TreasuryDependencies:
    raise NotImplementedError("Dependency override required")


class SyncAccountHolderRequest(BaseModel):
    account_token: Optional[str] = None


class FinancialAccountResponse(BaseModel):
    organization_id: str
    financial_account_token: str
    account_token: Optional[str] = None
    account_role: str
    currency: str
    status: str
    is_program_level: bool = False
    nickname: Optional[str] = None


class CreateExternalBankAccountBody(BaseModel):
    financial_account_token: str
    verification_method: Literal["MICRO_DEPOSIT", "PRENOTE", "EXTERNALLY_VERIFIED"] = "MICRO_DEPOSIT"
    owner_type: Literal["INDIVIDUAL", "BUSINESS"] = "BUSINESS"
    owner: str = Field(min_length=1, max_length=100)
    account_type: Literal["CHECKING", "SAVINGS"] = "CHECKING"
    routing_number: str = Field(min_length=9, max_length=9)
    account_number: str = Field(min_length=4, max_length=32)
    name: Optional[str] = None
    currency: str = "USD"
    country: str = "USA"
    account_token: Optional[str] = None
    company_id: Optional[str] = None
    user_defined_id: Optional[str] = None
    address: Optional[dict[str, Any]] = None
    dob: Optional[str] = None
    doing_business_as: Optional[str] = None


class VerifyMicroDepositsBody(BaseModel):
    micro_deposits: list[str] = Field(min_length=2, max_length=2)


class TreasuryPaymentRequest(BaseModel):
    financial_account_token: str
    external_bank_account_token: str
    amount_minor: int = Field(gt=0, description="Amount in currency minor units (e.g. cents for USD)")
    method: Literal["ACH_NEXT_DAY", "ACH_SAME_DAY"] = "ACH_NEXT_DAY"
    sec_code: Literal["CCD", "PPD", "WEB"] = "CCD"
    memo: Optional[str] = None
    idempotency_key: Optional[str] = None
    user_defined_id: Optional[str] = None


class TreasuryPaymentResponse(BaseModel):
    payment_token: str
    status: str
    result: str
    direction: str
    method: str
    currency: str
    pending_amount: int
    settled_amount: int
    financial_account_token: str
    external_bank_account_token: str
    user_defined_id: Optional[str] = None


class TreasuryBalanceResponse(BaseModel):
    organization_id: str
    financial_account_token: str
    currency: str
    available_amount_minor: int
    pending_amount_minor: int
    total_amount_minor: int
    as_of_event_token: Optional[str] = None


def _to_financial_account_response(row: dict[str, Any]) -> FinancialAccountResponse:
    return FinancialAccountResponse(
        organization_id=str(row.get("organization_id", "")),
        financial_account_token=str(row.get("financial_account_token", "")),
        account_token=row.get("account_token"),
        account_role=str(row.get("account_role", "")),
        currency=str(row.get("currency", "USD")),
        status=str(row.get("status", "")),
        is_program_level=bool(row.get("is_program_level", False)),
        nickname=row.get("nickname"),
    )


def _to_payment_response(row: dict[str, Any]) -> TreasuryPaymentResponse:
    return TreasuryPaymentResponse(
        payment_token=str(row.get("payment_token") or row.get("token") or ""),
        status=str(row.get("status", "")),
        result=str(row.get("result", "")),
        direction=str(row.get("direction", "")),
        method=str(row.get("method", "")),
        currency=str(row.get("currency", "USD")),
        pending_amount=int(row.get("pending_amount", row.get("amount_minor", 0)) or 0),
        settled_amount=int(row.get("settled_amount", 0) or 0),
        financial_account_token=str(row.get("financial_account_token", "")),
        external_bank_account_token=str(row.get("external_bank_account_token", "")),
        user_defined_id=row.get("user_defined_id"),
    )


@router.post("/account-holders/sync", response_model=list[FinancialAccountResponse])
async def sync_account_holder_financial_accounts(
    payload: SyncAccountHolderRequest,
    deps: TreasuryDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if deps.lithic_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="lithic_not_configured")
    accounts = await deps.lithic_client.list_financial_accounts(account_token=payload.account_token)
    out: list[FinancialAccountResponse] = []
    for account in accounts:
        row = await deps.treasury_repo.upsert_financial_account(principal.organization_id, account.raw or {})
        out.append(_to_financial_account_response(row))
    return out


@router.get("/financial-accounts", response_model=list[FinancialAccountResponse])
async def list_financial_accounts(
    account_token: Optional[str] = Query(default=None),
    refresh: bool = Query(default=False),
    deps: TreasuryDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if refresh:
        if deps.lithic_client is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="lithic_not_configured")
        remote = await deps.lithic_client.list_financial_accounts(account_token=account_token)
        for account in remote:
            await deps.treasury_repo.upsert_financial_account(principal.organization_id, account.raw or {})
    rows = await deps.treasury_repo.list_financial_accounts(principal.organization_id, account_token=account_token)
    return [_to_financial_account_response(row) for row in rows]


@router.post("/external-bank-accounts")
async def create_external_bank_account(
    payload: CreateExternalBankAccountBody,
    deps: TreasuryDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if deps.lithic_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="lithic_not_configured")
    account = await deps.treasury_repo.get_financial_account(
        principal.organization_id, payload.financial_account_token
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="financial_account_not_found")
    result = await deps.lithic_client.create_external_bank_account(
        CreateExternalBankAccountRequest(
            financial_account_token=payload.financial_account_token,
            verification_method=payload.verification_method,
            owner_type=payload.owner_type,
            owner=payload.owner,
            account_type=payload.account_type,
            routing_number=payload.routing_number,
            account_number=payload.account_number,
            name=payload.name,
            currency=payload.currency,
            country=payload.country,
            account_token=payload.account_token,
            company_id=payload.company_id,
            user_defined_id=payload.user_defined_id,
            address=payload.address,
            dob=payload.dob,
            doing_business_as=payload.doing_business_as,
        )
    )
    row = await deps.treasury_repo.upsert_external_bank_account(principal.organization_id, result.raw or {})
    return row


@router.post("/external-bank-accounts/{token}/verify-micro-deposits")
async def verify_micro_deposits(
    token: str,
    payload: VerifyMicroDepositsBody,
    deps: TreasuryDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if deps.lithic_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="lithic_not_configured")
    record = await deps.treasury_repo.get_external_bank_account(principal.organization_id, token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="external_bank_account_not_found")
    result = await deps.lithic_client.verify_micro_deposits(token, payload.micro_deposits)
    row = await deps.treasury_repo.upsert_external_bank_account(principal.organization_id, result.raw or {})
    return row


async def _create_ach_payment(
    *,
    payment_type: Literal["COLLECTION", "PAYMENT"],
    payload: TreasuryPaymentRequest,
    request: Request,
    deps: TreasuryDependencies,
    principal: Principal,
) -> TreasuryPaymentResponse:
    if deps.lithic_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="lithic_not_configured")
    fa = await deps.treasury_repo.get_financial_account(principal.organization_id, payload.financial_account_token)
    if fa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="financial_account_not_found")
    eba = await deps.treasury_repo.get_external_bank_account(principal.organization_id, payload.external_bank_account_token)
    if eba is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="external_bank_account_not_found")
    if bool(eba.get("is_paused", False)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="external_bank_account_paused")

    idem = payload.idempotency_key or get_idempotency_key(request) or str(uuid.uuid4())

    async def _run() -> tuple[int, object]:
        payment = await deps.lithic_client.create_payment(
            CreatePaymentRequest(
                financial_account_token=payload.financial_account_token,
                external_bank_account_token=payload.external_bank_account_token,
                payment_type=payment_type,
                amount=payload.amount_minor,
                method=payload.method,
                sec_code=payload.sec_code,
                memo=payload.memo,
                idempotency_token=idem,
                user_defined_id=payload.user_defined_id,
            )
        )
        row = await deps.treasury_repo.upsert_ach_payment(
            principal.organization_id,
            payment.raw or {},
            idempotency_key=idem,
        )
        await deps.treasury_repo.append_ach_events(
            principal.organization_id,
            payment.token,
            payment.events,
        )
        await deps.treasury_repo.add_balance_snapshot(
            principal.organization_id,
            payment.financial_account_token,
            payment.currency,
            available_amount_minor=payment.settled_amount,
            pending_amount_minor=payment.pending_amount,
            total_amount_minor=payment.pending_amount + payment.settled_amount,
            as_of_event_token=(payment.events[-1].get("token") if payment.events else None),
        )
        return 200, _to_payment_response(row)

    return await run_idempotent(
        request=request,
        principal=principal,
        operation=f"treasury.ach.{payment_type.lower()}",
        key=idem,
        payload=payload.model_dump(),
        fn=_run,
        ttl_seconds=7 * 24 * 60 * 60,
    )


@router.post("/fund", response_model=TreasuryPaymentResponse)
async def fund_via_ach_collection(
    payload: TreasuryPaymentRequest,
    request: Request,
    deps: TreasuryDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    return await _create_ach_payment(
        payment_type="COLLECTION",
        payload=payload,
        request=request,
        deps=deps,
        principal=principal,
    )


@router.post("/withdraw", response_model=TreasuryPaymentResponse)
async def withdraw_via_ach_payment(
    payload: TreasuryPaymentRequest,
    request: Request,
    deps: TreasuryDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    return await _create_ach_payment(
        payment_type="PAYMENT",
        payload=payload,
        request=request,
        deps=deps,
        principal=principal,
    )


@router.get("/payments/{payment_token}", response_model=TreasuryPaymentResponse)
async def get_payment(
    payment_token: str,
    deps: TreasuryDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    if deps.lithic_client is None:
        row = await deps.treasury_repo.get_ach_payment(principal.organization_id, payment_token)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_not_found")
        return _to_payment_response(row)

    payment = await deps.lithic_client.get_payment(payment_token)
    row = await deps.treasury_repo.upsert_ach_payment(principal.organization_id, payment.raw or {})
    await deps.treasury_repo.append_ach_events(principal.organization_id, payment.token, payment.events)
    return _to_payment_response(row)


@router.get("/balances", response_model=list[TreasuryBalanceResponse])
async def get_treasury_balances(
    deps: TreasuryDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    snapshots = await deps.treasury_repo.list_latest_balance_snapshots(principal.organization_id)
    if snapshots:
        return [
            TreasuryBalanceResponse(
                organization_id=str(s.get("organization_id", principal.organization_id)),
                financial_account_token=str(s.get("financial_account_token", "")),
                currency=str(s.get("currency", "USD")),
                available_amount_minor=int(s.get("available_amount_minor", 0) or 0),
                pending_amount_minor=int(s.get("pending_amount_minor", 0) or 0),
                total_amount_minor=int(s.get("total_amount_minor", 0) or 0),
                as_of_event_token=s.get("as_of_event_token"),
            )
            for s in snapshots
        ]
    accounts = await deps.treasury_repo.list_financial_accounts(principal.organization_id)
    return [
        TreasuryBalanceResponse(
            organization_id=principal.organization_id,
            financial_account_token=str(a.get("financial_account_token", "")),
            currency=str(a.get("currency", "USD")),
            available_amount_minor=0,
            pending_amount_minor=0,
            total_amount_minor=0,
        )
        for a in accounts
    ]

