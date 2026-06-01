"""Port adapters over the existing LithicTreasuryClient.

Wraps the real client (``server.providers.lithic_treasury``) behind the typed
:class:`FiatAccountPort`.  Behavior is unchanged — this only normalizes the
client's dataclasses into the unified port envelopes and declares custody.

Lithic is **partner-custodied**: Lithic (a regulated partner) holds the USD
while ACH/wire settle.  Sardis remains non-custodial.
"""

from __future__ import annotations

from typing import Any

from ..lithic_treasury import (
    CreateExternalBankAccountRequest,
    CreatePaymentRequest,
    LithicTreasuryClient,
)
from ..ports.types import (
    CustodyModel,
    MinorUnits,
    NormalizedTxn,
    ProviderCapability,
    ProviderError,
    ProviderResult,
)


class LithicFiatAccountAdapter:
    """:class:`FiatAccountPort` over Lithic financial accounts + ACH payments."""

    capability = ProviderCapability.FIAT_ACCOUNT

    def __init__(self, client: LithicTreasuryClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "lithic"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return getattr(self._client, "_env", "sandbox") in {
            "sandbox",
            "test",
            "development",
            "dev",
        }

    async def create_account(
        self,
        *,
        owner_ref: str,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        # Lithic financial accounts are provisioned out-of-band; we surface the
        # existing account for the owner rather than minting one here (no money
        # authority in an adapter).
        try:
            accounts = await self._client.list_financial_accounts(account_token=owner_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"lithic_list_accounts_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        account = accounts[0] if accounts else None
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            ok=account is not None,
            reference=account.token if account else None,
            status=account.status if account else "not_found",
            raw=(account.raw or {}) if account else {},
        )

    async def get_balance(self, account_ref: str) -> tuple[MinorUnits, str]:
        accounts = await self._client.list_financial_accounts()
        for acct in accounts:
            if acct.token == account_ref:
                # Lithic financial-account balances are read via the balances
                # endpoint; this adapter exposes 0 until that surface is wired,
                # but never returns a float.
                return (0, acct.currency)
        raise ProviderError(
            "lithic_account_not_found",
            provider=self.provider,
            capability=self.capability,
        )

    async def create_payout(
        self,
        *,
        account_ref: str,
        destination_ref: str,
        amount_minor: MinorUnits,
        currency: str = "USD",
        method: str = "ACH_NEXT_DAY",
        idempotency_key: str | None = None,
        memo: str | None = None,
    ) -> NormalizedTxn:
        if not isinstance(amount_minor, int):
            raise ProviderError(
                "amount_minor must be integer minor units",
                provider=self.provider,
                capability=self.capability,
            )
        req = CreatePaymentRequest(
            financial_account_token=account_ref,
            external_bank_account_token=destination_ref,
            payment_type="PAYMENT",
            amount=amount_minor,  # Lithic ACH amounts are integer cents.
            method=method if method in ("ACH_NEXT_DAY", "ACH_SAME_DAY") else "ACH_NEXT_DAY",
            memo=memo,
            idempotency_token=idempotency_key,
        )
        try:
            payment = await self._client.create_payment(req)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"lithic_create_payment_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return NormalizedTxn(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            reference=payment.token,
            status=payment.status or "pending",
            amount_minor=payment.pending_amount or amount_minor,
            currency=payment.currency or currency,
            sandbox=self.sandbox,
            source=account_ref,
            destination=destination_ref,
            raw=payment.raw or {},
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        return self._client.verify_webhook(body=body, headers=headers)

    # Convenience passthrough used by treasury routes that need to register an
    # external bank account.  Kept thin; no behavior change.
    async def register_external_bank_account(
        self, request: CreateExternalBankAccountRequest
    ) -> ProviderResult:
        result = await self._client.create_external_bank_account(request)
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=result.token,
            status=result.state or "pending",
            raw=result.raw or {},
        )
