"""OnrampPort adapter over the existing TurnkeyOnrampService.

Turnkey's native ``init_fiat_on_ramp`` activity returns an embeddable widget
URL (Coinbase / MoonPay).  Behavior is unchanged here.

Custody: **non-custodial** — Turnkey signs/derives for a wallet the user
controls; the onramp delivers crypto straight to that wallet.  (The fiat leg
is handled by the underlying provider, but Sardis/Turnkey never custody it.)
"""

from __future__ import annotations

from typing import Any

from ...services.turnkey_onramp import TurnkeyOnrampService
from ..ports.types import (
    CustodyModel,
    MinorUnits,
    ProviderCapability,
    ProviderError,
    ProviderResult,
    from_minor_units,
)


class TurnkeyOnrampAdapter:
    """:class:`OnrampPort` over Turnkey native fiat onramp."""

    capability = ProviderCapability.ONRAMP

    def __init__(self, service: TurnkeyOnrampService, *, sandbox: bool = True) -> None:
        self._service = service
        self._sandbox = sandbox

    @property
    def provider(self) -> str:
        return "turnkey"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.NON_CUSTODIAL

    @property
    def sandbox(self) -> bool:
        return self._sandbox

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
        # Convert minor units -> decimal string only if provided (Turnkey lets
        # the user choose the amount in-widget otherwise).  No float.
        amount_str = (
            format(from_minor_units(amount_minor, 2), "f")
            if amount_minor is not None
            else None
        )
        provider = (metadata or {}).get("provider", "coinbase")
        try:
            session = await self._service.create_onramp_session(
                wallet_address=wallet_address,
                amount_usd=amount_str,
                currency=fiat_currency,
                provider=provider,
                network=chain,
                crypto_currency=crypto_currency,
                sandbox=self._sandbox,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"turnkey_onramp_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=session.transaction_id or session.session_id,
            status="created",
            raw={
                "session_id": session.session_id,
                "onramp_url": session.onramp_url,
                "transaction_id": session.transaction_id,
                "provider": session.provider,
                "target_chain": session.target_chain,
                "target_token": session.target_token,
                "wallet_address": session.wallet_address,
            },
        )

    async def get_status(self, session_ref: str) -> ProviderResult:
        try:
            status = await self._service.get_transaction_status(session_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"turnkey_onramp_status_failed: {exc}",
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
            raw={},
        )
