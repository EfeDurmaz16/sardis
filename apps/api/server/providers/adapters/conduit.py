"""OnrampPort adapter over the existing ConduitOnrampService.

Conduit is Tempo's official fiat->USDC onramp partner (native, no bridge).
Behavior is unchanged — this normalizes the service's dataclasses into the
unified port envelopes.

Custody: **partner-custodied** — Conduit takes the user's fiat and delivers
USDC to the destination wallet; Sardis never holds the funds.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ...services.conduit_onramp import ConduitOnrampService
from ..ports.types import (
    CustodyModel,
    MinorUnits,
    ProviderCapability,
    ProviderError,
    ProviderResult,
    from_minor_units,
)


class ConduitOnrampAdapter:
    """:class:`OnrampPort` over Conduit Pay (fiat -> USDC on Tempo)."""

    capability = ProviderCapability.ONRAMP

    def __init__(self, service: ConduitOnrampService) -> None:
        self._service = service

    @property
    def provider(self) -> str:
        return "conduit"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return bool(getattr(self._service, "sandbox", True))

    async def create_session(
        self,
        *,
        wallet_address: str,
        chain: str,
        crypto_currency: str = "usdc",
        fiat_currency: str = "USD",
        amount_minor: MinorUnits | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        if amount_minor is None:
            raise ProviderError(
                "conduit onramp requires an amount",
                provider=self.provider,
                capability=self.capability,
            )
        # Conduit's API takes a decimal-string fiat amount; convert exactly
        # from minor units (USD has 2 decimals) — never via float.
        amount_str = format(from_minor_units(amount_minor, 2), "f")
        try:
            quote = await self._service.get_quote(
                amount_usd=amount_str,
                target_asset=crypto_currency.upper(),
                target_network=chain.lower(),
                source_currency=fiat_currency.upper(),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"conduit_quote_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=quote.quote_id,
            status="quoted",
            raw={
                "quote_id": quote.quote_id,
                "source_amount": quote.source_amount,
                "target_amount": quote.target_amount,
                "target_asset": quote.target_asset,
                "target_network": quote.target_network,
                "expires_at": quote.expires_at,
                "wallet_address": wallet_address,
            },
        )

    async def get_status(self, session_ref: str) -> ProviderResult:
        try:
            status = await self._service.get_transaction_status(session_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"conduit_status_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=status.transaction_id,
            status=status.status,
            raw={"completed_at": status.completed_at},
        )
