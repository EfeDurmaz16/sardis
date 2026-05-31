"""Port adapter over :class:`DakotaClient`.

:class:`DakotaFiatAccountAdapter` implements :class:`FiatAccountPort`:

* ``create_account`` provisions a *named* Dakota account.  Inbound fiat
  (ACH/Fedwire/SWIFT) to that account auto-settles to USDC on the destination
  chain — Dakota's crypto-native model.
* ``get_balance`` reports the account's USDC balance in integer minor units
  (6-decimal base units), never a float.
* ``create_payout`` executes an already-authorized transfer to a destination
  the orchestrator supplied (a bank recipient for offramp, or a crypto
  address).

Custody: **partner-custodied** — Dakota holds the fiat/USDC while a rail
settles.  The adapter authorizes nothing; the moat already did.
"""

from __future__ import annotations

from typing import Any

from ..ports.types import (
    CustodyModel,
    MinorUnits,
    NormalizedTxn,
    ProviderCapability,
    ProviderError,
    ProviderResult,
)
from .client import DakotaClient


class DakotaFiatAccountAdapter:
    """:class:`FiatAccountPort` over Dakota named accounts (USDC-native)."""

    capability = ProviderCapability.FIAT_ACCOUNT

    def __init__(self, client: DakotaClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "dakota"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def create_account(
        self,
        *,
        owner_ref: str,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        meta = metadata or {}
        try:
            account = await self._client.create_account(
                name=meta.get("name") or owner_ref,
                account_type=str(meta.get("account_type", "onramp")),
                customer_id=meta.get("customer_id"),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"dakota_create_account_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=account.id,
            status=account.status,
            raw=account.raw,
        )

    async def get_balance(self, account_ref: str) -> tuple[MinorUnits, str]:
        # ``account_ref`` is treated as a wallet id for the balances surface;
        # Dakota groups balances by asset+network. We report the USDC total in
        # integer 6-decimal minor units.
        try:
            balances = await self._client.get_wallet_balances(account_ref)
            minor = self._client.usdc_minor_from_balances(balances)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"dakota_get_balance_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return (minor, "USDC")

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
        if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
            raise ProviderError(
                "amount_minor must be integer minor units (USDC 6-decimal base units)",
                provider=self.provider,
                capability=self.capability,
            )
        try:
            transfer = await self._client.create_transfer(
                source_account_id=account_ref,
                destination_id=destination_ref,
                amount_minor=amount_minor,
                asset="USDC",
                idempotency_key=idempotency_key,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"dakota_create_payout_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return NormalizedTxn(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            reference=transfer.id,
            status=transfer.status,
            amount_minor=transfer.amount_minor,
            currency=transfer.asset,
            sandbox=self.sandbox,
            source=account_ref,
            destination=destination_ref,
            raw={"method": method, **transfer.raw},
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        return self._client.verify_webhook(body=body, headers=headers)
