"""Treasury models for Sardis SDK."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import Field

from .base import SardisModel


class FinancialAccount(SardisModel):
    """Treasury financial account metadata."""

    organization_id: str
    financial_account_token: str
    account_token: Optional[str] = None
    account_role: str
    currency: str = "USD"
    status: str
    is_program_level: bool = False
    nickname: Optional[str] = None


class SyncAccountHolderRequest(SardisModel):
    """Request payload for account holder sync."""

    account_token: Optional[str] = None


class TreasuryAddress(SardisModel):
    """Business address for external bank account creation."""

    address1: str
    city: str
    state: str
    postal_code: str
    country: str = "USA"
    address2: Optional[str] = None


class CreateExternalBankAccountRequest(SardisModel):
    """Request payload for creating external bank accounts."""

    financial_account_token: str
    verification_method: Literal["MICRO_DEPOSIT", "PRENOTE", "EXTERNALLY_VERIFIED"] = "MICRO_DEPOSIT"
    owner_type: Literal["INDIVIDUAL", "BUSINESS"] = "BUSINESS"
    owner: str
    account_type: Literal["CHECKING", "SAVINGS"] = "CHECKING"
    routing_number: str
    account_number: str
    name: Optional[str] = None
    currency: str = "USD"
    country: str = "USA"
    account_token: Optional[str] = None
    company_id: Optional[str] = None
    user_defined_id: Optional[str] = None
    address: Optional[TreasuryAddress] = None
    dob: Optional[str] = None
    doing_business_as: Optional[str] = None


class VerifyMicroDepositsRequest(SardisModel):
    """Request payload for micro-deposit verification."""

    micro_deposits: list[str] = Field(min_length=2, max_length=2)


class ExternalBankAccount(SardisModel):
    """External bank account registered for ACH rails."""

    organization_id: str
    external_bank_account_token: str
    financial_account_token: Optional[str] = None
    owner_type: str
    owner: str
    account_type: str
    verification_method: str
    verification_state: str
    state: str
    currency: str = "USD"
    country: str = "USA"
    name: Optional[str] = None
    routing_number: Optional[str] = None
    last_four: Optional[str] = None
    user_defined_id: Optional[str] = None
    company_id: Optional[str] = None
    is_paused: bool = False
    pause_reason: Optional[str] = None
    last_return_reason_code: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TreasuryPaymentRequest(SardisModel):
    """Request payload for ACH funding/withdrawal."""

    financial_account_token: str
    external_bank_account_token: str
    amount_minor: int = Field(gt=0)
    method: Literal["ACH_NEXT_DAY", "ACH_SAME_DAY"] = "ACH_NEXT_DAY"
    sec_code: Literal["CCD", "PPD", "WEB"] = "CCD"
    memo: Optional[str] = None
    idempotency_key: Optional[str] = None
    user_defined_id: Optional[str] = None


class TreasuryPaymentResponse(SardisModel):
    """ACH payment response."""

    payment_token: str
    status: str
    result: str
    direction: str
    method: str
    currency: str = "USD"
    pending_amount: int = 0
    settled_amount: int = 0
    financial_account_token: str
    external_bank_account_token: str
    user_defined_id: Optional[str] = None


class TreasuryBalance(SardisModel):
    """Latest treasury snapshot per financial account."""

    organization_id: str
    financial_account_token: str
    currency: str = "USD"
    available_amount_minor: int = 0
    pending_amount_minor: int = 0
    total_amount_minor: int = 0
    as_of_event_token: Optional[str] = None
