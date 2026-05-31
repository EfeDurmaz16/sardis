"""``OfframpPort`` adapters over the offramp clients.

Three adapters, one per provider:

* :class:`OnramperOfframpAdapter` — aggregator sell intent; partner-custodied.
* :class:`TransakStreamOfframpAdapter` — address-based programmatic sell order
  (agent-friendly: returns a deposit address the agent funds); partner-custodied.
* :class:`CoinbaseOfframpAdapter` — CDP sell quote + hosted offramp URL (ACH /
  PayPal cashout); partner-custodied.

None of these authorizes, initiates, or settles money on its own.  Each only
*normalizes* the orchestrator's already-authorized payout instruction into the
vendor shape and reports back the resulting session/deposit/quote.  Money crosses
the port boundary as integer minor units of the **source crypto token**;
conversion to the vendors' decimal-string sell amounts uses ``Decimal`` only —
never ``float``.

``destination_bank_ref`` is an opaque payout descriptor the orchestrator already
authorized; the adapter passes it through to the provider's payout linkage
(Onramper payout method / Transak ``paymentInstrumentId`` / Coinbase cashout
method) without re-deciding it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from ..ports.types import (
    CustodyModel,
    MinorUnits,
    NormalizedTxn,
    ProviderCapability,
    ProviderError,
    ProviderResult,
    from_minor_units,
)
from .client import (
    CoinbaseOfframpClient,
    OnramperOfframpClient,
    TransakStreamClient,
)

# Default decimals for the crypto being sold.  USDC/USDC.e/EURC are 6-decimal on
# every chain Sardis settles; callers can override via ``metadata['decimals']``
# for an 18-decimal native asset, etc.
_DEFAULT_TOKEN_DECIMALS = 6


def _require_minor(
    amount_minor: MinorUnits, *, provider: str, capability: ProviderCapability
) -> None:
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ProviderError(
            "amount_minor must be integer minor units of the source crypto token",
            provider=provider,
            capability=capability,
        )


def _sell_amount_str(amount_minor: MinorUnits, metadata: dict[str, Any]) -> str:
    """Render the crypto sell amount as a precise decimal string (no float).

    Quantizes to the token's full precision so the string is exact and padded
    (e.g. ``"10.000000"`` for 6-decimal USDC).
    """
    decimals = int(metadata.get("decimals", _DEFAULT_TOKEN_DECIMALS))
    quantum = Decimal(1).scaleb(-decimals)
    return format(from_minor_units(amount_minor, decimals).quantize(quantum), "f")


class OnramperOfframpAdapter:
    """:class:`OfframpPort` over Onramper's sell (offramp) checkout intent."""

    capability = ProviderCapability.OFFRAMP

    def __init__(self, client: OnramperOfframpClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "onramper"

    @property
    def custody_model(self) -> CustodyModel:
        # The selected offramp takes custody of the crypto and settles fiat to
        # the user's payout destination; Sardis never holds the funds.
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

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
        _require_minor(amount_minor, provider=self.provider, capability=self.capability)
        meta = metadata or {}
        wallet_address = meta.get("source_address") or meta.get("wallet_address")
        if not wallet_address:
            raise ProviderError(
                "onramper offramp requires metadata['source_address'] "
                "(the wallet sending the crypto)",
                provider=self.provider,
                capability=self.capability,
            )
        amount_str = _sell_amount_str(amount_minor, meta)
        # destination_bank_ref names the payout method/rail the orchestrator
        # authorized (e.g. "banktransfer"); metadata may carry a richer id.
        payment_method = str(meta.get("payment_method") or destination_bank_ref)
        try:
            txn = await self._client.create_sell_intent(
                source_token=source_token,
                destination_fiat=fiat_currency,
                amount=amount_str,
                wallet_address=str(wallet_address),
                network=source_chain,
                payment_method=payment_method,
                offramp=meta.get("offramp"),
                partner_context=meta.get("partner_context") or idempotency_key,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"onramper_offramp_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return NormalizedTxn(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            reference=txn.transaction_id or (idempotency_key or _ref()),
            status=txn.status,
            amount_minor=amount_minor,
            currency=fiat_currency,
            sandbox=self.sandbox,
            chain=source_chain,
            source=source_token,
            destination=destination_bank_ref,
            raw={
                "url": txn.redirect_url,
                "transaction_id": txn.transaction_id,
                "sell_amount": amount_str,
                **txn.raw,
            },
        )

    async def get_status(self, payout_ref: str) -> ProviderResult:
        try:
            data = await self._client.get_transaction(payout_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"onramper_offramp_status_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=str(data.get("transactionId", payout_ref)),
            status=str(data.get("status", "pending")),
            raw=data,
        )


class TransakStreamOfframpAdapter:
    """:class:`OfframpPort` over Transak Stream (address-based offramp).

    Returns a deposit address in ``NormalizedTxn.raw['deposit_address']`` — the
    agent funds that address to trigger the automatic fiat payout.  This is the
    agent-friendly programmatic offramp: no widget, just an on-chain send the
    orchestrator already authorized.
    """

    capability = ProviderCapability.OFFRAMP

    def __init__(self, client: TransakStreamClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "transak_stream"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

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
        _require_minor(amount_minor, provider=self.provider, capability=self.capability)
        meta = metadata or {}
        partner_user_id = meta.get("partner_user_id") or meta.get("owner_ref")
        if not partner_user_id:
            raise ProviderError(
                "transak_stream offramp requires metadata['partner_user_id'] "
                "(the KYC'd user the deposit address + payout account belong to)",
                provider=self.provider,
                capability=self.capability,
            )
        # destination_bank_ref names the registered payout instrument the
        # orchestrator authorized (e.g. "sepa_bank_transfer"/"gbp_bank_transfer").
        payment_instrument_id = str(meta.get("payment_instrument_id") or destination_bank_ref)
        partner_order_id = idempotency_key or _ref("ord")
        amount_str = _sell_amount_str(amount_minor, meta)
        try:
            order = await self._client.create_sell_order(
                crypto_currency=source_token,
                network=source_chain,
                fiat_currency=fiat_currency,
                crypto_amount=amount_str,
                payment_instrument_id=payment_instrument_id,
                partner_user_id=str(partner_user_id),
                partner_order_id=partner_order_id,
                quote_id=meta.get("quote_id"),
                wallet_address=meta.get("source_address"),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"transak_stream_offramp_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return NormalizedTxn(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            reference=order.order_id or partner_order_id,
            status=order.status,
            amount_minor=amount_minor,
            currency=fiat_currency,
            sandbox=self.sandbox,
            chain=source_chain,
            source=source_token,
            destination=destination_bank_ref,
            raw={
                "deposit_address": order.deposit_address,
                "partner_order_id": partner_order_id,
                "sell_amount": amount_str,
                **order.raw,
            },
        )

    async def get_status(self, payout_ref: str) -> ProviderResult:
        # Transak Stream surfaces order status via webhook + Pusher websocket
        # (channel "<apiKey>_<partnerOrderId>"); there is no settle-by-GET that
        # would let us fabricate a state.  Report last-known rather than invent.
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=payout_ref,
            status="pending",
            raw={"note": "transak stream status arrives via webhook/websocket"},
        )


class CoinbaseOfframpAdapter:
    """:class:`OfframpPort` over Coinbase CDP offramp (ACH / PayPal cashout).

    Mints a session token, quotes the sale, and assembles the hosted
    ``pay.coinbase.com`` offramp URL the user completes (the user must have a
    Coinbase account with the linked ACH bank / PayPal).  ``destination_bank_ref``
    selects the cashout method; the actual bank/PayPal linkage lives in the
    user's Coinbase account, not in Sardis.
    """

    capability = ProviderCapability.OFFRAMP

    # Normalized cashout-method verbs -> CDP payment-method enum.
    _CASHOUT_METHODS = {
        "ach": "ACH_BANK_ACCOUNT",
        "ach_bank_account": "ACH_BANK_ACCOUNT",
        "bank": "ACH_BANK_ACCOUNT",
        "banktransfer": "ACH_BANK_ACCOUNT",
        "paypal": "PAYPAL",
        "rtp": "RTP",
        "fiat_wallet": "FIAT_WALLET",
        "crypto_account": "CRYPTO_ACCOUNT",
    }

    def __init__(self, client: CoinbaseOfframpClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "coinbase_offramp"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    def _resolve_cashout_method(self, ref: str, meta: dict[str, Any]) -> str:
        verb = str(meta.get("cashout_method") or ref).strip().lower()
        method = self._CASHOUT_METHODS.get(verb)
        if method is None:
            # Fail closed on a money path rather than guessing a rail.
            raise ProviderError(
                f"coinbase offramp: unknown cashout method {ref!r}; use one of "
                f"{sorted(set(self._CASHOUT_METHODS.values()))}",
                provider=self.provider,
                capability=self.capability,
            )
        return method

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
        _require_minor(amount_minor, provider=self.provider, capability=self.capability)
        meta = metadata or {}
        source_address = meta.get("source_address")
        if not source_address:
            raise ProviderError(
                "coinbase offramp requires metadata['source_address'] "
                "(the wallet the crypto is sold from)",
                provider=self.provider,
                capability=self.capability,
            )
        country = str(meta.get("country") or "US")
        partner_user_id = str(meta.get("partner_user_id") or idempotency_key or _ref("usr"))
        cashout_method = self._resolve_cashout_method(destination_bank_ref, meta)
        amount_str = _sell_amount_str(amount_minor, meta)
        blockchains = meta.get("blockchains") or [source_chain.lower()]
        try:
            session_token = await self._client.create_session_token(
                address=str(source_address),
                blockchains=list(blockchains),
                assets=meta.get("assets") or [source_token.upper()],
                client_ip=meta.get("client_ip"),
            )
            quote = await self._client.create_sell_quote(
                sell_currency=source_token,
                sell_amount=amount_str,
                cashout_currency=fiat_currency,
                payment_method=cashout_method,
                country=country,
                partner_user_id=partner_user_id,
                source_address=str(source_address),
                subdivision=meta.get("subdivision"),
                redirect_url=meta.get("redirect_url"),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"coinbase_offramp_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        offramp_url = quote.offramp_url or self._client.build_offramp_url(
            session_token=session_token,
            partner_user_ref=partner_user_id,
            redirect_url=str(meta.get("redirect_url") or "https://app.sardis.sh/offramp"),
            default_network=source_chain.lower(),
            default_asset=source_token.upper(),
            preset_crypto_amount=amount_str,
            default_cashout_method=cashout_method,
        )
        return NormalizedTxn(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            reference=quote.quote_id or partner_user_id,
            status="created",
            amount_minor=amount_minor,
            currency=fiat_currency,
            sandbox=self.sandbox,
            chain=source_chain,
            source=source_token,
            destination=destination_bank_ref,
            raw={
                "url": offramp_url,
                "quote_id": quote.quote_id,
                "cashout_method": cashout_method,
                "cashout_total": quote.cashout_total,
                "sell_amount": amount_str,
                **quote.raw,
            },
        )

    async def get_status(self, payout_ref: str) -> ProviderResult:
        # CDP offramp status is the Transaction Status API (poll), which is keyed
        # by partnerUserRef and lives behind a separate read scope; the
        # orchestrator records the ref at creation.  Report last-known rather
        # than fabricate a settlement here.
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=payout_ref,
            status="pending",
            raw={"note": "coinbase offramp status via Transaction Status API"},
        )


def _ref(prefix: str = "offramp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"
