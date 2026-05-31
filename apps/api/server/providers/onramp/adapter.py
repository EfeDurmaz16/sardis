"""``OnrampPort`` adapters over the onramp clients.

Three adapters, one per provider:

* :class:`OnramperOnrampAdapter`  — aggregator widget; partner-custodied.
* :class:`TransakOnrampAdapter`   — backend-minted widget URL; partner-custodied.
* :class:`DaimoOnrampAdapter`     — any-token->USDC wallet funding; non-custodial.

None of these authorizes, initiates, or settles money on its own.  Each only
*normalizes* the orchestrator's already-authorized instruction into the vendor
shape and reports back the session/redirect.  Money crosses the port boundary
as integer minor units; conversions to the vendors' decimal-string fields use
``Decimal`` only — never ``float``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..ports.types import (
    CustodyModel,
    MinorUnits,
    ProviderCapability,
    ProviderError,
    ProviderResult,
    from_minor_units,
)
from .client import DaimoClient, OnramperClient, TransakClient

# USD minor units are cents (2 decimals); USDC carries 6 decimals on every chain.
_FIAT_DECIMALS = 2
_USDC_DECIMALS = 6

#: Native-token sentinel address used by Daimo (and most EVM routers).
_NATIVE_TOKEN = "0x0000000000000000000000000000000000000000"

#: Minimal chain-name -> EVM chain-id map for the chains Daimo settles to that
#: Sardis cares about.  Unknown names fail closed in the adapter rather than
#: guessing a chain id on a money path.
_DAIMO_CHAIN_IDS: dict[str, int] = {
    "ethereum": 1,
    "mainnet": 1,
    "optimism": 10,
    "bsc": 56,
    "polygon": 137,
    "base": 8453,
    "arbitrum": 42161,
    "linea": 59144,
    "blast": 81457,
    "worldchain": 480,
}

#: Canonical USDC token addresses for Daimo destination chains (lowercased).
_USDC_BY_CHAIN_ID: dict[int, str] = {
    1: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    10: "0x0b2c639c533813f4aa9d7837caf62653d097ff85",
    137: "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",
    8453: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    42161: "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
}


class OnramperOnrampAdapter:
    """:class:`OnrampPort` over Onramper's aggregator checkout intent."""

    capability = ProviderCapability.ONRAMP

    def __init__(self, client: OnramperClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "onramper"

    @property
    def custody_model(self) -> CustodyModel:
        # The selected onramp takes the user's fiat and delivers crypto to the
        # destination wallet; Sardis never holds the funds.
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

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
                "onramper checkout requires a fiat amount",
                provider=self.provider,
                capability=self.capability,
            )
        # Convert USD cents -> decimal string exactly (no float).
        amount_str = format(from_minor_units(amount_minor, _FIAT_DECIMALS), "f")
        meta = metadata or {}
        try:
            txn = await self._client.create_checkout_intent(
                source_currency=fiat_currency,
                destination_token=crypto_currency,
                amount=amount_str,
                wallet_address=wallet_address,
                network=chain,
                payment_method=str(meta.get("payment_method", "creditcard")),
                onramp=meta.get("onramp"),
                wallet_memo=meta.get("wallet_memo"),
                partner_context=meta.get("partner_context"),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"onramper_checkout_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=txn.transaction_id or None,
            status=txn.status,
            raw={
                "url": txn.redirect_url,
                "transaction_id": txn.transaction_id,
                "wallet_address": wallet_address,
                "chain": chain,
                "crypto_currency": crypto_currency,
                **txn.raw,
            },
        )

    async def get_status(self, session_ref: str) -> ProviderResult:
        try:
            data = await self._client.get_transaction(session_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"onramper_status_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=str(data.get("transactionId", session_ref)),
            status=str(data.get("status", "pending")),
            raw=data,
        )


class TransakOnrampAdapter:
    """:class:`OnrampPort` over Transak's backend-minted widget URL.

    Transak's flow returns a single-use widget URL, not a queryable status
    resource; transaction status arrives via webhook (verified upstream).
    ``get_status`` therefore reports the session as ``created`` rather than
    fabricating a settlement state.
    """

    capability = ProviderCapability.ONRAMP

    def __init__(self, client: TransakClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "transak"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

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
        # Amount is optional — the user may pick it in-widget.  When supplied,
        # convert USD cents -> decimal string exactly (no float).
        fiat_amount = (
            format(from_minor_units(amount_minor, _FIAT_DECIMALS), "f")
            if amount_minor is not None
            else None
        )
        meta = metadata or {}
        try:
            widget = await self._client.create_widget_url(
                wallet_address=wallet_address,
                crypto_currency_code=crypto_currency,
                network=chain,
                fiat_amount=fiat_amount,
                fiat_currency=fiat_currency,
                referrer_domain=meta.get("referrer_domain"),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"transak_widget_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=None,  # widget URL is single-use; no server-side ref yet
            status="created",
            raw={
                "url": widget.widget_url,
                "wallet_address": wallet_address,
                "chain": chain,
                "crypto_currency": crypto_currency,
            },
        )

    async def get_status(self, session_ref: str) -> ProviderResult:
        # Transak surfaces status via webhook; there is no GET-by-widget-url.
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=session_ref,
            status="created",
            raw={"note": "transak status arrives via webhook"},
        )


class DaimoOnrampAdapter:
    """:class:`OnrampPort` over Daimo Pay (any-token/any-chain -> USDC).

    Funds the destination wallet with USDC from any source token/chain/wallet.
    Non-custodial: the payer signs from their own wallet; Daimo never holds the
    funds.  ``amount_minor`` is the USDC (6-decimal) amount the destination must
    receive *exactly* — converted to Daimo's decimal-string ``amountUnits`` with
    ``Decimal`` only.
    """

    capability = ProviderCapability.ONRAMP

    def __init__(self, client: DaimoClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "daimo"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.NON_CUSTODIAL

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    def _resolve_chain(self, chain: str, meta: dict[str, Any]) -> int:
        explicit = meta.get("chain_id")
        if explicit is not None:
            if not isinstance(explicit, int) or isinstance(explicit, bool):
                raise ProviderError(
                    "metadata['chain_id'] must be an integer EVM chain id",
                    provider=self.provider,
                    capability=self.capability,
                )
            return explicit
        chain_id = _DAIMO_CHAIN_IDS.get(chain.strip().lower())
        if chain_id is None:
            # Fail closed on a money path rather than guessing a chain id.
            raise ProviderError(
                f"daimo: unknown destination chain {chain!r}; pass metadata['chain_id']",
                provider=self.provider,
                capability=self.capability,
            )
        return chain_id

    def _resolve_token(self, chain_id: int, crypto_currency: str, meta: dict[str, Any]) -> str:
        token = meta.get("token_address")
        if token:
            return str(token)
        cc = crypto_currency.strip().lower()
        if cc in {"eth", "native"}:
            return _NATIVE_TOKEN
        if cc == "usdc":
            addr = _USDC_BY_CHAIN_ID.get(chain_id)
            if addr is None:
                raise ProviderError(
                    f"daimo: no known USDC address for chain id {chain_id}; "
                    "pass metadata['token_address']",
                    provider=self.provider,
                    capability=self.capability,
                )
            return addr
        raise ProviderError(
            f"daimo: cannot resolve token {crypto_currency!r}; pass metadata['token_address']",
            provider=self.provider,
            capability=self.capability,
        )

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
                "daimo payment requires an exact destination amount",
                provider=self.provider,
                capability=self.capability,
            )
        if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
            raise ProviderError(
                "amount_minor must be integer minor units (USDC base units)",
                provider=self.provider,
                capability=self.capability,
            )
        meta = metadata or {}
        chain_id = self._resolve_chain(chain, meta)
        token_address = self._resolve_token(chain_id, crypto_currency, meta)
        # Destination amount is denominated in the destination token's decimals
        # (USDC = 6).  Build the precise decimal string with Decimal — no float.
        decimals = int(meta.get("token_decimals", _USDC_DECIMALS))
        # Quantize to the token's full precision so amountUnits is the precise,
        # padded decimal string Daimo expects ("1.00") — exact, never float.
        quantum = Decimal(1).scaleb(-decimals)
        amount_units = format(from_minor_units(amount_minor, decimals).quantize(quantum), "f")
        try:
            payment = await self._client.create_payment(
                intent=str(meta.get("intent", "Fund wallet")),
                destination_address=wallet_address,
                chain_id=chain_id,
                token_address=token_address,
                amount_units=amount_units,
                refund_address=meta.get("refund_address"),
                external_id=meta.get("external_id"),
                metadata=meta.get("metadata"),
                redirect_uri=meta.get("redirect_uri"),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"daimo_payment_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=payment.id or None,
            status=payment.status,
            raw={
                "url": payment.url,
                "id": payment.id,
                "chain_id": chain_id,
                "token_address": token_address,
                "amount_units": amount_units,
                "destination_address": wallet_address,
                **payment.raw,
            },
        )

    async def get_status(self, session_ref: str) -> ProviderResult:
        try:
            payment = await self._client.get_payment(session_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"daimo_status_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=payment.id,
            status=payment.status,
            raw=payment.raw,
        )
