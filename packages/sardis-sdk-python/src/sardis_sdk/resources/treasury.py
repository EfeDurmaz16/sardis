"""Treasury resource for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from ..models.treasury import (
    CreateExternalBankAccountRequest,
    ExternalBankAccount,
    FinancialAccount,
    SyncAccountHolderRequest,
    TreasuryBalance,
    TreasuryPaymentRequest,
    TreasuryPaymentResponse,
    VerifyMicroDepositsRequest,
)
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncTreasuryResource(AsyncBaseResource):
    """Async treasury operations for fiat-first rails."""

    async def sync_account_holders(
        self,
        *,
        account_token: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> list[FinancialAccount]:
        payload = SyncAccountHolderRequest(account_token=account_token).model_dump(exclude_none=True)
        data = await self._post("treasury/account-holders/sync", payload, timeout=timeout)
        return [FinancialAccount.model_validate(item) for item in data]

    async def list_financial_accounts(
        self,
        *,
        account_token: Optional[str] = None,
        refresh: bool = False,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> list[FinancialAccount]:
        params: dict[str, object] = {"refresh": refresh}
        params["refresh"] = str(refresh).lower()
        if account_token:
            params["account_token"] = account_token
        data = await self._get("treasury/financial-accounts", params=params, timeout=timeout)
        return [FinancialAccount.model_validate(item) for item in data]

    async def create_external_bank_account(
        self,
        request: CreateExternalBankAccountRequest,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExternalBankAccount:
        data = await self._post(
            "treasury/external-bank-accounts",
            request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return ExternalBankAccount.model_validate(data)

    async def verify_micro_deposits(
        self,
        token: str,
        request: VerifyMicroDepositsRequest,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExternalBankAccount:
        data = await self._post(
            f"treasury/external-bank-accounts/{token}/verify-micro-deposits",
            request.model_dump(),
            timeout=timeout,
        )
        return ExternalBankAccount.model_validate(data)

    async def fund(
        self,
        request: TreasuryPaymentRequest,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> TreasuryPaymentResponse:
        data = await self._post("treasury/fund", request.model_dump(exclude_none=True), timeout=timeout)
        return TreasuryPaymentResponse.model_validate(data)

    async def withdraw(
        self,
        request: TreasuryPaymentRequest,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> TreasuryPaymentResponse:
        data = await self._post("treasury/withdraw", request.model_dump(exclude_none=True), timeout=timeout)
        return TreasuryPaymentResponse.model_validate(data)

    async def get_payment(
        self,
        payment_token: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> TreasuryPaymentResponse:
        data = await self._get(f"treasury/payments/{payment_token}", timeout=timeout)
        return TreasuryPaymentResponse.model_validate(data)

    async def get_balances(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> list[TreasuryBalance]:
        data = await self._get("treasury/balances", timeout=timeout)
        return [TreasuryBalance.model_validate(item) for item in data]


class TreasuryResource(SyncBaseResource):
    """Sync treasury operations for fiat-first rails."""

    def sync_account_holders(
        self,
        *,
        account_token: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> list[FinancialAccount]:
        payload = SyncAccountHolderRequest(account_token=account_token).model_dump(exclude_none=True)
        data = self._post("treasury/account-holders/sync", payload, timeout=timeout)
        return [FinancialAccount.model_validate(item) for item in data]

    def list_financial_accounts(
        self,
        *,
        account_token: Optional[str] = None,
        refresh: bool = False,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> list[FinancialAccount]:
        params: dict[str, object] = {"refresh": refresh}
        params["refresh"] = str(refresh).lower()
        if account_token:
            params["account_token"] = account_token
        data = self._get("treasury/financial-accounts", params=params, timeout=timeout)
        return [FinancialAccount.model_validate(item) for item in data]

    def create_external_bank_account(
        self,
        request: CreateExternalBankAccountRequest,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExternalBankAccount:
        data = self._post(
            "treasury/external-bank-accounts",
            request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return ExternalBankAccount.model_validate(data)

    def verify_micro_deposits(
        self,
        token: str,
        request: VerifyMicroDepositsRequest,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExternalBankAccount:
        data = self._post(
            f"treasury/external-bank-accounts/{token}/verify-micro-deposits",
            request.model_dump(),
            timeout=timeout,
        )
        return ExternalBankAccount.model_validate(data)

    def fund(
        self,
        request: TreasuryPaymentRequest,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> TreasuryPaymentResponse:
        data = self._post("treasury/fund", request.model_dump(exclude_none=True), timeout=timeout)
        return TreasuryPaymentResponse.model_validate(data)

    def withdraw(
        self,
        request: TreasuryPaymentRequest,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> TreasuryPaymentResponse:
        data = self._post("treasury/withdraw", request.model_dump(exclude_none=True), timeout=timeout)
        return TreasuryPaymentResponse.model_validate(data)

    def get_payment(
        self,
        payment_token: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> TreasuryPaymentResponse:
        data = self._get(f"treasury/payments/{payment_token}", timeout=timeout)
        return TreasuryPaymentResponse.model_validate(data)

    def get_balances(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> list[TreasuryBalance]:
        data = self._get("treasury/balances", timeout=timeout)
        return [TreasuryBalance.model_validate(item) for item in data]


__all__ = ["AsyncTreasuryResource", "TreasuryResource"]
