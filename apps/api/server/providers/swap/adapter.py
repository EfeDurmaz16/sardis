""":class:`SwapPort` adapters over the swap clients.

Three adapters, one per provider:

* :class:`LifiSwapAdapter`    — LI.FI pure-REST DEX/bridge aggregation; EVM +
  Solana; integrator-fee capture.  Non-custodial.
* :class:`ZeroExSwapAdapter`  — 0x Swap API v2 (allowance-holder), same-chain
  EVM best price; ``swapFeeBps`` capture.  Non-custodial.
* :class:`JupiterSwapAdapter` — Jupiter Solana best-price swap;
  ``platformFeeBps`` capture.  Non-custodial.

None of these authorizes, initiates, or settles money on its own.  Each only
*normalizes* the orchestrator's already-authorized instruction into the vendor
shape, returns a quote, and (via :meth:`build_execution`) hands back the
pre-shaped transaction the CustodyPort signs.  Money crosses the port boundary
as integer minor units and is converted to the vendors' base-unit string fields
with ``int``/``str`` only — never ``float``.

The :class:`SwapPort` protocol calls ``quote`` then ``build_execution`` by
``quote_ref`` alone, so each adapter keeps a small bounded in-memory cache of
quotes it issued, keyed by the reference it returned.  ``build_execution`` fails
closed when the ref is unknown rather than fabricating a transaction on a money
path.
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
    JupiterClient,
    LifiClient,
    SwapQuote,
    ZeroExClient,
)

#: Bound the per-adapter quote cache so a long-lived adapter cannot leak memory.
_MAX_CACHED_QUOTES = 256

#: Placeholder EVM address used only to satisfy LI.FI's required ``fromAddress``
#: at *indicative* quote time.  It is NOT authority-bearing: the firm,
#: taker-bound calldata is fetched in ``build_execution`` with the real taker.
ZERO_PLACEHOLDER_FROM = "0x0000000000000000000000000000000000000000"

#: Minimal chain-name -> EVM chain-id map for the chains Sardis swaps on.
#: Unknown names fail closed in the adapter rather than guessing a chain id on a
#: money path (the caller may pass a numeric chain id directly instead).
_EVM_CHAIN_IDS: dict[str, int] = {
    "ethereum": 1,
    "mainnet": 1,
    "optimism": 10,
    "bsc": 56,
    "polygon": 137,
    "base": 8453,
    "arbitrum": 42161,
    "linea": 59144,
    "tempo": 4217,
}


def _require_int_minor(amount_minor: MinorUnits, *, provider: str) -> int:
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ProviderError(
            "sell_amount_minor must be integer minor units (base units)",
            provider=provider,
            capability=ProviderCapability.SWAP,
        )
    if amount_minor <= 0:
        raise ProviderError(
            "sell_amount_minor must be positive",
            provider=provider,
            capability=ProviderCapability.SWAP,
        )
    return amount_minor


class _SwapAdapterBase:
    """Shared metadata + bounded quote cache for the swap adapters."""

    capability = ProviderCapability.SWAP

    def __init__(self) -> None:
        # ref -> SwapQuote, insertion-ordered LRU-ish (evict oldest).
        self._quotes: OrderedDict[str, SwapQuote] = OrderedDict()

    @property
    def custody_model(self) -> CustodyModel:
        # The swap client only returns a quote + an already-shaped transaction;
        # the user signs from their own wallet via the CustodyPort.  Sardis /
        # the provider never holds the funds.
        return CustodyModel.NON_CUSTODIAL

    def _cache(self, ref: str, quote: SwapQuote) -> None:
        self._quotes[ref] = quote
        self._quotes.move_to_end(ref)
        while len(self._quotes) > _MAX_CACHED_QUOTES:
            self._quotes.popitem(last=False)

    def _get_cached(self, quote_ref: str) -> SwapQuote:
        quote = self._quotes.get(quote_ref)
        if quote is None:
            raise ProviderError(
                f"unknown quote_ref {quote_ref!r}; call quote() first",
                provider=self.provider,  # type: ignore[attr-defined]
                capability=self.capability,
            )
        return quote

    def _quote_result(self, quote: SwapQuote, **extra: Any) -> ProviderResult:
        return ProviderResult(
            provider=self.provider,  # type: ignore[attr-defined]
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,  # type: ignore[attr-defined]
            reference=quote.quote_id or None,
            status="quoted",
            raw={
                "sell_amount": quote.sell_amount,
                "buy_amount": quote.buy_amount,
                "buy_amount_min": quote.buy_amount_min,
                "allowance_spender": quote.allowance_spender,
                **extra,
            },
        )


class LifiSwapAdapter(_SwapAdapterBase):
    """:class:`SwapPort` over LI.FI ``GET /v1/quote`` (EVM + Solana)."""

    def __init__(self, client: LifiClient) -> None:
        super().__init__()
        self._client = client

    @property
    def provider(self) -> str:
        return "lifi"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def quote(
        self,
        *,
        chain: str,
        sell_token: str,
        buy_token: str,
        sell_amount_minor: MinorUnits,
    ) -> ProviderResult:
        amount = _require_int_minor(sell_amount_minor, provider=self.provider)
        try:
            # LI.FI accepts chain id or chain key directly; same-chain swap uses
            # the same chain for from/to.  fromAddress is required by the API but
            # not authority-bearing — the orchestrator supplies the real taker
            # at build_execution; LI.FI re-quotes calldata against it there.
            quote = await self._client.get_quote(
                from_chain=chain,
                to_chain=chain,
                from_token=sell_token,
                to_token=buy_token,
                from_amount=str(amount),
                from_address=ZERO_PLACEHOLDER_FROM,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"lifi_quote_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        # Cache under a stable ref so build_execution can re-quote for the taker.
        ref = quote.quote_id or f"lifi:{chain}:{sell_token}:{buy_token}:{amount}"
        self._cache(
            ref,
            SwapQuote(
                quote_id=ref,
                sell_amount=quote.sell_amount,
                buy_amount=quote.buy_amount,
                buy_amount_min=quote.buy_amount_min,
                transaction=quote.transaction,
                allowance_spender=quote.allowance_spender,
                raw={
                    "chain": chain,
                    "sell_token": sell_token,
                    "buy_token": buy_token,
                    "sell_amount": str(amount),
                },
            ),
        )
        result = self._quote_result(quote, chain=chain, quote_ref=ref)
        return result

    async def build_execution(self, *, quote_ref: str, taker_address: str) -> ProviderResult:
        cached = self._get_cached(quote_ref)
        ctx = cached.raw
        try:
            # Re-quote against the real taker so the calldata is bound to them.
            fresh = await self._client.get_quote(
                from_chain=str(ctx["chain"]),
                to_chain=str(ctx["chain"]),
                from_token=str(ctx["sell_token"]),
                to_token=str(ctx["buy_token"]),
                from_amount=str(ctx["sell_amount"]),
                from_address=taker_address,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"lifi_build_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=quote_ref,
            status="ready",
            raw={
                "transaction": fresh.transaction,
                "allowance_spender": fresh.allowance_spender,
                "buy_amount_min": fresh.buy_amount_min,
                "taker": taker_address,
            },
        )


class ZeroExSwapAdapter(_SwapAdapterBase):
    """:class:`SwapPort` over 0x Swap API v2 (allowance-holder), same-chain EVM."""

    def __init__(self, client: ZeroExClient) -> None:
        super().__init__()
        self._client = client

    @property
    def provider(self) -> str:
        return "zerox"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    def _resolve_chain_id(self, chain: str) -> int:
        s = chain.strip().lower()
        if s.isdigit():
            return int(s)
        chain_id = _EVM_CHAIN_IDS.get(s)
        if chain_id is None:
            raise ProviderError(
                f"zerox: unknown chain {chain!r}; pass a numeric chain id",
                provider=self.provider,
                capability=self.capability,
            )
        return chain_id

    async def quote(
        self,
        *,
        chain: str,
        sell_token: str,
        buy_token: str,
        sell_amount_minor: MinorUnits,
    ) -> ProviderResult:
        amount = _require_int_minor(sell_amount_minor, provider=self.provider)
        chain_id = self._resolve_chain_id(chain)
        self._cache(
            f"{chain_id}:{sell_token}:{buy_token}:{amount}",
            SwapQuote(
                quote_id=f"{chain_id}:{sell_token}:{buy_token}:{amount}",
                sell_amount=str(amount),
                buy_amount="",
                buy_amount_min=None,
                raw={
                    "chain_id": chain_id,
                    "sell_token": sell_token,
                    "buy_token": buy_token,
                    "sell_amount": str(amount),
                },
            ),
        )
        # 0x v2 /quote requires a taker; for an indicative quote we still need
        # one, so the orchestrator must supply it via build_execution.  Here we
        # return the cached descriptor; the firm quote+calldata is fetched in
        # build_execution where the taker is known.
        ref = f"{chain_id}:{sell_token}:{buy_token}:{amount}"
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=ref,
            status="quoted",
            raw={
                "chain_id": chain_id,
                "sell_token": sell_token,
                "buy_token": buy_token,
                "sell_amount": str(amount),
                "quote_ref": ref,
                "note": "0x v2 requires taker; firm quote+calldata at build_execution",
            },
        )

    async def build_execution(self, *, quote_ref: str, taker_address: str) -> ProviderResult:
        cached = self._get_cached(quote_ref)
        ctx = cached.raw
        try:
            quote = await self._client.get_quote(
                chain_id=int(ctx["chain_id"]),
                sell_token=str(ctx["sell_token"]),
                buy_token=str(ctx["buy_token"]),
                sell_amount=str(ctx["sell_amount"]),
                taker=taker_address,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"zerox_quote_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=quote_ref,
            status="ready",
            raw={
                "transaction": quote.transaction,
                "allowance_spender": quote.allowance_spender,
                "buy_amount": quote.buy_amount,
                "buy_amount_min": quote.buy_amount_min,
                "taker": taker_address,
            },
        )


class JupiterSwapAdapter(_SwapAdapterBase):
    """:class:`SwapPort` over Jupiter (Solana) ``GET /swap/v1/quote`` + swap."""

    def __init__(self, client: JupiterClient) -> None:
        super().__init__()
        self._client = client

    @property
    def provider(self) -> str:
        return "jupiter"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def quote(
        self,
        *,
        chain: str,
        sell_token: str,
        buy_token: str,
        sell_amount_minor: MinorUnits,
    ) -> ProviderResult:
        # Jupiter is Solana-only; `chain` is accepted for port symmetry but must
        # be solana (fail closed otherwise rather than mis-routing).
        if chain.strip().lower() not in {"solana", "sol", "mainnet-beta"}:
            raise ProviderError(
                f"jupiter only swaps on solana, got chain={chain!r}",
                provider=self.provider,
                capability=self.capability,
            )
        amount = _require_int_minor(sell_amount_minor, provider=self.provider)
        try:
            quote = await self._client.get_quote(
                input_mint=sell_token,
                output_mint=buy_token,
                amount=str(amount),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"jupiter_quote_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        ref = quote.quote_id
        # Cache the raw Jupiter quote — build_swap requires the exact echo.
        self._cache(ref, quote)
        return self._quote_result(quote, chain="solana", quote_ref=ref)

    async def build_execution(self, *, quote_ref: str, taker_address: str) -> ProviderResult:
        cached = self._get_cached(quote_ref)
        try:
            swap = await self._client.build_swap(
                quote_response=cached.raw,
                user_public_key=taker_address,
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"jupiter_build_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=quote_ref,
            status="ready",
            raw={
                # Solana serialized transaction (base64) the wallet signs.
                "swap_transaction": swap.get("swapTransaction"),
                "last_valid_block_height": swap.get("lastValidBlockHeight"),
                "buy_amount_min": cached.buy_amount_min,
                "taker": taker_address,
            },
        )
