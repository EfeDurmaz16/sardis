"""Port adapters over the existing Circle clients.

Two adapters:

* :class:`CircleCpnOfframpAdapter` — :class:`OfframpPort` over the Circle
  Payments Network client (cross-border payout/collection).
* :class:`CircleGatewayOnrampAdapter` is intentionally NOT provided here:
  the Gateway nanopayments client is an x402 payment-intent surface, not an
  onramp, and is already wired through ``configure_provider_runtime``.  It is
  left on its existing path to avoid changing behavior.

Custody: Circle CPN is **partner-custodied** — Circle moves funds across the
network; Sardis never holds them.
"""

from __future__ import annotations

from typing import Any

from ..circle_cpn import CircleCPNClient
from ..ports.types import (
    CustodyModel,
    MinorUnits,
    NormalizedTxn,
    ProviderCapability,
    ProviderError,
    ProviderResult,
    from_minor_units,
)


class CircleCpnOfframpAdapter:
    """:class:`OfframpPort` over Circle Payments Network payouts."""

    capability = ProviderCapability.OFFRAMP

    def __init__(self, client: CircleCPNClient, *, sandbox: bool = True) -> None:
        self._client = client
        self._sandbox = sandbox

    @property
    def provider(self) -> str:
        return "circle_cpn"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._sandbox

    async def create_payout(
        self,
        *,
        source_chain: str,
        source_token: str,
        amount_minor: MinorUnits,
        destination_bank_ref: str,
        fiat_currency: str = "USD",
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> NormalizedTxn:
        if not isinstance(amount_minor, int):
            raise ProviderError(
                "amount_minor must be integer minor units",
                provider=self.provider,
                capability=self.capability,
            )
        # CPN expects an explicit amount/currency; build a decimal-string from
        # minor units (no float).  The orchestrator already authorized this.
        amount_str = format(from_minor_units(amount_minor, 2), "f")
        payload: dict[str, Any] = {
            "amount": {"amount": amount_str, "currency": fiat_currency},
            "destination": destination_bank_ref,
            "source": {"chain": source_chain, "token": source_token},
        }
        if idempotency_key:
            payload["idempotencyKey"] = idempotency_key
        if metadata:
            payload["metadata"] = metadata
        try:
            payment = await self._client.create_payout(payload)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"circle_cpn_payout_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return NormalizedTxn(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            reference=payment.payment_id,
            status=payment.status,
            amount_minor=amount_minor,
            currency=fiat_currency,
            sandbox=self.sandbox,
            chain=source_chain,
            source=source_token,
            destination=destination_bank_ref,
            raw=payment.raw,
        )

    async def get_status(self, payout_ref: str) -> ProviderResult:
        try:
            payment = await self._client.get_payment_status(payout_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"circle_cpn_status_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=payment.payment_id,
            status=payment.status,
            raw=payment.raw,
        )
