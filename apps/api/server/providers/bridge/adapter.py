""":class:`BridgePort` adapters over the bridge clients.

Two adapters, one per provider:

* :class:`SquidBridgeAdapter` — Squid v2 intent-based aggregation (Axelar /
  CCTP / LayerZero under the hood); live on Tempo day-one for pathUSD.  The
  ``POST /v2/route`` response already carries the ``transactionRequest`` the
  CustodyPort signs.  Non-custodial.
* :class:`CctpBridgeAdapter`  — Circle CCTP v2 native USDC burn/mint.  The
  adapter ABI-encodes ``depositForBurn`` for the source-chain TokenMessengerV2
  and the CustodyPort signs it; mint on the destination is permissionless via
  the Iris attestation.  Canonical and fully non-custodial.

Neither adapter authorizes, initiates, or settles money on its own.  Each only
*normalizes* the orchestrator's already-authorized cross-chain instruction into
the vendor shape, returns a quote, and (via :meth:`build_execution`) hands back
the pre-shaped transaction the CustodyPort signs + broadcasts.  No policy / KYA /
sanctions / mandate checks happen here (those live in the moat).  Money crosses
the port boundary as integer minor units and is converted to base-unit strings
with ``int``/``str`` only — never ``float``.

The :class:`BridgePort` protocol calls ``quote`` then ``build_execution`` by
``quote_ref`` alone, so each adapter keeps a small bounded in-memory cache of
quotes it issued.  ``build_execution`` fails closed when the ref is unknown
rather than fabricating a transaction on a money path.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from ..ports.types import (
    CustodyModel,
    MinorUnits,
    ProviderCapability,
    ProviderError,
    ProviderResult,
)
from .client import (
    CCTP_FINALITY_FAST,
    CCTP_FINALITY_STANDARD,
    CCTP_TOKEN_MESSENGER_V2,
    CctpClient,
    SquidClient,
)

#: Bound the per-adapter quote cache so a long-lived adapter cannot leak memory.
_MAX_CACHED_QUOTES = 256


def _require_int_minor(amount_minor: MinorUnits, *, provider: str) -> int:
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ProviderError(
            "amount_minor must be integer minor units (base units)",
            provider=provider,
            capability=ProviderCapability.BRIDGE,
        )
    if amount_minor <= 0:
        raise ProviderError(
            "amount_minor must be positive",
            provider=provider,
            capability=ProviderCapability.BRIDGE,
        )
    return amount_minor


class _BridgeAdapterBase:
    """Shared metadata + bounded quote cache for the bridge adapters.

    Bridges are non-custodial: Squid returns an executable tx the user signs;
    CCTP burn/mint is canonical (the user burns from their own wallet, Circle
    mints to the recipient).  Sardis / the provider never holds the funds.
    """

    capability = ProviderCapability.BRIDGE

    def __init__(self) -> None:
        self._quotes: OrderedDict[str, dict[str, Any]] = OrderedDict()

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.NON_CUSTODIAL

    def _cache(self, ref: str, ctx: dict[str, Any]) -> None:
        self._quotes[ref] = ctx
        self._quotes.move_to_end(ref)
        while len(self._quotes) > _MAX_CACHED_QUOTES:
            self._quotes.popitem(last=False)

    def _get_cached(self, quote_ref: str) -> dict[str, Any]:
        ctx = self._quotes.get(quote_ref)
        if ctx is None:
            raise ProviderError(
                f"unknown quote_ref {quote_ref!r}; call quote() first",
                provider=self.provider,  # type: ignore[attr-defined]
                capability=self.capability,
            )
        return ctx


class SquidBridgeAdapter(_BridgeAdapterBase):
    """:class:`BridgePort` over Squid ``POST /v2/route`` (any-chain -> Tempo etc)."""

    def __init__(self, client: SquidClient) -> None:
        super().__init__()
        self._client = client

    @property
    def provider(self) -> str:
        return "squid"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def quote(
        self,
        *,
        from_chain: str,
        to_chain: str,
        token: str,
        amount_minor: MinorUnits,
    ) -> ProviderResult:
        amount = _require_int_minor(amount_minor, provider=self.provider)
        # Cache the parameters; Squid's firm route + transactionRequest is bound
        # to the real from/to addresses, so the calldata is fetched in
        # build_execution where those addresses are known.  ``token`` is used as
        # both the source and destination token (USDC->USDC / *->pathUSD callers
        # may override to_token via metadata in a later iteration).
        ref = f"squid:{from_chain}:{to_chain}:{token}:{amount}"
        self._cache(
            ref,
            {
                "from_chain": str(from_chain),
                "to_chain": str(to_chain),
                "token": token,
                "amount": str(amount),
            },
        )
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=ref,
            status="quoted",
            raw={
                "from_chain": str(from_chain),
                "to_chain": str(to_chain),
                "token": token,
                "send_amount": str(amount),
                "quote_ref": ref,
                "note": "Squid binds the route to from/to addresses at build_execution",
            },
        )

    async def build_execution(
        self, *, quote_ref: str, sender_address: str, recipient_address: str
    ) -> ProviderResult:
        ctx = self._get_cached(quote_ref)
        try:
            route = await self._client.get_route(
                from_chain=str(ctx["from_chain"]),
                to_chain=str(ctx["to_chain"]),
                from_token=str(ctx["token"]),
                to_token=str(ctx["token"]),
                from_amount=str(ctx["amount"]),
                from_address=sender_address,
                to_address=recipient_address,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"squid_route_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=route.quote_id or quote_ref,
            status="ready",
            raw={
                "transaction": route.transaction,
                "allowance_spender": route.allowance_spender,
                "receive_amount": route.receive_amount,
                "receive_amount_min": route.receive_amount_min,
                # quoteId is mandatory for Squid Intents status tracking.
                "quote_id": route.quote_id,
                "sender": sender_address,
                "recipient": recipient_address,
            },
        )


class CctpBridgeAdapter(_BridgeAdapterBase):
    """:class:`BridgePort` over Circle CCTP v2 (native USDC burn/mint)."""

    def __init__(self, client: CctpClient) -> None:
        super().__init__()
        self._client = client

    @property
    def provider(self) -> str:
        return "cctp"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    def _finality(self) -> int:
        return CCTP_FINALITY_FAST if self._client.fast else CCTP_FINALITY_STANDARD

    async def quote(
        self,
        *,
        from_chain: str,
        to_chain: str,
        token: str,
        amount_minor: MinorUnits,
    ) -> ProviderResult:
        amount = _require_int_minor(amount_minor, provider=self.provider)
        try:
            source_domain = self._client.domain_for(from_chain)
            destination_domain = self._client.domain_for(to_chain)
        except ValueError as exc:
            raise ProviderError(
                str(exc), provider=self.provider, capability=self.capability
            ) from exc

        max_fee = 0
        bps_hundredths_str: str | None = None
        if self._client.fast:
            # Fast transfer carries an on-chain protocol fee; Standard is 0.
            try:
                bps = await self._client.get_min_fee_bps_hundredths(
                    source_domain=source_domain,
                    destination_domain=destination_domain,
                )
                bps_hundredths_str = str(bps)
                max_fee = self._client.compute_max_fee(amount_minor=amount, bps_hundredths=bps)
            except Exception as exc:  # noqa: BLE001 - normalized below
                raise ProviderError(
                    f"cctp_fee_failed: {exc}",
                    provider=self.provider,
                    capability=self.capability,
                    retryable=True,
                ) from exc

        # Recipient mints exactly (amount - max_fee) base units on Fast; on
        # Standard the recipient mints the full amount (fee 0).
        receive_amount = amount - max_fee
        ref = f"cctp:{source_domain}:{destination_domain}:{token}:{amount}:{self._finality()}"
        self._cache(
            ref,
            {
                "source_domain": source_domain,
                "destination_domain": destination_domain,
                "burn_token": token,
                "amount": amount,
                "max_fee": max_fee,
                "finality": self._finality(),
            },
        )
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=ref,
            status="quoted",
            raw={
                "source_domain": source_domain,
                "destination_domain": destination_domain,
                "send_amount": str(amount),
                "receive_amount": str(receive_amount),
                "max_fee": str(max_fee),
                "min_fee_bps_hundredths": bps_hundredths_str,
                "finality": self._finality(),
                "fast": self._client.fast,
                "quote_ref": ref,
            },
        )

    async def build_execution(
        self, *, quote_ref: str, sender_address: str, recipient_address: str
    ) -> ProviderResult:
        ctx = self._get_cached(quote_ref)
        try:
            calldata = self._client.build_deposit_for_burn_calldata(
                amount_minor=int(ctx["amount"]),
                destination_domain=int(ctx["destination_domain"]),
                mint_recipient=recipient_address,
                burn_token=str(ctx["burn_token"]),
                max_fee=int(ctx["max_fee"]),
                min_finality_threshold=int(ctx["finality"]),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"cctp_build_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=quote_ref,
            status="ready",
            raw={
                # The burn tx the CustodyPort signs + broadcasts on the source
                # chain.  Mint on the destination is permissionless via Iris.
                "transaction": {
                    "to": CCTP_TOKEN_MESSENGER_V2,
                    "data": calldata,
                    "value": "0",
                },
                "token_messenger": CCTP_TOKEN_MESSENGER_V2,
                "source_domain": ctx["source_domain"],
                "destination_domain": ctx["destination_domain"],
                "max_fee": str(ctx["max_fee"]),
                "min_finality_threshold": ctx["finality"],
                "sender": sender_address,
                "recipient": recipient_address,
            },
        )
