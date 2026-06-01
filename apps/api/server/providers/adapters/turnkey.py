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


class TurnkeyCustodyAdapter:
    """:class:`CustodyPort` over the Turnkey MPC client.

    **Non-custodial.**  Turnkey signs/derives for a wallet the user controls;
    the adapter NEVER initiates or broadcasts a transfer.  ``sign_payload``
    only stamps an *already-authorized* payload the orchestrator handed it
    (the orchestrator's Phase-3 chain executor builds the unsigned tx and
    broadcasts the returned signature) — no policy, KYA, or mandate logic
    lives here.

    ``wallet_ref`` is the Turnkey ``walletId``.  The signing address /
    public key is supplied per call via ``payload["sign_with"]`` (the
    orchestrator already resolved which key it authorized).
    """

    capability = ProviderCapability.CUSTODY

    def __init__(self, client: Any, *, sandbox: bool = False) -> None:
        self._client = client
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

    async def get_address(self, wallet_ref: str, *, chain: str) -> str:
        try:
            wallet = await self._client.get_wallet(wallet_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"turnkey_get_wallet_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        # Turnkey returns wallet accounts; pick the first matching address/pubkey.
        accounts = (
            wallet.get("wallet", {}).get("accounts")
            or wallet.get("accounts")
            or []
        )
        for acct in accounts:
            addr = acct.get("address") or acct.get("publicKey")
            if addr:
                return addr
        raise ProviderError(
            "turnkey_no_account_for_wallet",
            provider=self.provider,
            capability=self.capability,
        )

    async def sign_payload(
        self, wallet_ref: str, *, payload: dict[str, Any]
    ) -> ProviderResult:
        sign_with = payload.get("sign_with") or payload.get("address")
        unsigned = payload.get("unsigned_transaction") or payload.get("unsignedTransaction")
        if not sign_with or not unsigned:
            raise ProviderError(
                "turnkey_sign_payload_missing_fields: require sign_with + unsigned_transaction",
                provider=self.provider,
                capability=self.capability,
            )
        tx_type = payload.get("transaction_type", "TRANSACTION_TYPE_ETHEREUM")
        try:
            result = await self._client.sign_transaction(
                wallet_id=wallet_ref,
                unsigned_transaction=unsigned,
                sign_with=sign_with,
                transaction_type=tx_type,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"turnkey_sign_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        signed = result.get("signedTransaction") if isinstance(result, dict) else None
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=sign_with,
            status="signed" if signed else "failed",
            ok=bool(signed),
            raw=dict(result) if isinstance(result, dict) else {"result": result},
        )
