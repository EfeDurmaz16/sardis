"""Liquidity Router — chain-aware FX routing with native-first priority.

Routes stablecoin swaps through the optimal venue per chain:
- Tempo → pytempo StablecoinDEX (enshrined orderbook, no API key)
- Base → Uniswap V3 direct (no API key, only RPC)
- Optional fallbacks → CDPSwap, 1inch (if API keys configured)

Also routes cross-chain bridge transfers:
- Relay (intent-based, free API, lowest fees)
- Across (optimistic, free API for quotes)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

logger = logging.getLogger("sardis.chain.liquidity_router")


@dataclass
class RouteResult:
    """Result of a liquidity routing decision."""
    provider: str
    chain: str
    estimated_rate: Decimal = field(default_factory=lambda: Decimal("1.0"))
    estimated_fee_bps: int = 0
    estimated_output: Decimal = field(default_factory=lambda: Decimal("0"))
    route_type: str = "swap"  # swap, bridge, bridge+swap
    steps: list[dict[str, Any]] = field(default_factory=list)


class LiquidityRouter:
    """Routes FX swaps through optimal venues — native/on-chain first.

    Priority (no API key needed for primary path):
      tempo:    pytempo StablecoinDEX [free]
      base:     Uniswap V3 direct [free] → CDPSwap [if key] → 1inch [if key]
      ethereum: Uniswap V3 direct [free] → CDPSwap [if key]
      polygon:  CDPSwap [if key] → indicative rate
      arbitrum: CDPSwap [if key] → indicative rate
    """

    BRIDGE_PROVIDERS: dict[tuple[str, str], list[str]] = {
        ("tempo", "base"): ["relay", "across"],
        ("base", "tempo"): ["relay", "across"],
        ("tempo", "ethereum"): ["across", "relay"],
        ("base", "ethereum"): ["across", "relay"],
        ("ethereum", "base"): ["across", "relay"],
    }

    def __init__(
        self,
        tempo_dex=None,
        default_chain: str = "tempo",
    ) -> None:
        self._tempo_dex = tempo_dex
        self._default_chain = default_chain

        # Lazy-init adapters — only when first needed
        self._uniswap: Any = None
        self._cdp_swap: Any = None

    def _get_uniswap(self, chain: str = "base"):
        """Lazy-init Uniswap V3 adapter (no API key needed)."""
        if self._uniswap is None:
            rpc = os.getenv("SARDIS_BASE_RPC_URL", "")
            if rpc:
                try:
                    from sardis_chain.uniswap_v3 import UniswapV3Adapter
                    self._uniswap = UniswapV3Adapter(rpc_url=rpc, chain=chain)
                except ImportError:
                    pass
        return self._uniswap

    def _get_cdp_swap(self):
        """Lazy-init CDPSwap (needs CDP_API_KEY)."""
        if self._cdp_swap is None:
            cdp_key = os.getenv("CDP_API_KEY", "")
            if cdp_key:
                try:
                    from sardis_chain.cdp_swap import CDPSwapClient
                    self._cdp_swap = CDPSwapClient(api_key=cdp_key)
                except ImportError:
                    pass
        return self._cdp_swap

    async def find_best_route(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        from_chain: str | None = None,
        to_chain: str | None = None,
    ) -> RouteResult:
        """Find the best execution route for a swap."""
        src_chain = from_chain or self._default_chain
        dst_chain = to_chain or src_chain

        if src_chain == dst_chain:
            return await self._route_same_chain(from_token, to_token, amount, src_chain)
        else:
            return await self._route_cross_chain(
                from_token, to_token, amount, src_chain, dst_chain
            )

    async def _route_same_chain(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        chain: str,
    ) -> RouteResult:
        """Route a swap on the same chain — try native adapters first."""

        # 1. Tempo → pytempo StablecoinDEX (free)
        if chain in ("tempo", "tempo_testnet") and self._tempo_dex:
            try:
                quote = await self._tempo_dex.get_quote(from_token, to_token, amount)
                return RouteResult(
                    provider="tempo_dex",
                    chain=chain,
                    estimated_rate=quote.rate,
                    estimated_fee_bps=0,
                    estimated_output=quote.to_amount,
                    route_type="swap",
                    steps=[{"type": "swap", "provider": "tempo_dex",
                            "from": from_token, "to": to_token, "amount": str(amount)}],
                )
            except Exception as e:
                logger.warning("Tempo DEX quote failed: %s", e)

        # 2. Base/Ethereum → Uniswap V3 (free, only needs RPC)
        if chain in ("base", "ethereum", "arbitrum", "optimism"):
            uni = self._get_uniswap(chain)
            if uni:
                try:
                    # Resolve token addresses for this chain
                    in_addr = self._resolve_token_address(from_token, chain)
                    out_addr = self._resolve_token_address(to_token, chain)

                    if in_addr and out_addr:
                        amount_raw = int(amount * Decimal("1000000"))
                        quote = await uni.get_quote(in_addr, out_addr, amount_raw)
                        output = Decimal(quote.amount_out) / Decimal("1000000")
                        return RouteResult(
                            provider="uniswap_v3",
                            chain=chain,
                            estimated_rate=quote.rate,
                            estimated_fee_bps=quote.fee_tier // 100,
                            estimated_output=output.quantize(Decimal("0.000001")),
                            route_type="swap",
                            steps=[{"type": "swap", "provider": "uniswap_v3",
                                    "from": from_token, "to": to_token, "amount": str(amount)}],
                        )
                except Exception as e:
                    logger.warning("Uniswap V3 quote failed on %s: %s", chain, e)

        # 3. CDPSwap fallback (needs CDP_API_KEY)
        cdp = self._get_cdp_swap()
        if cdp:
            try:
                quote = await cdp.get_quote(
                    from_token=from_token, to_token=to_token,
                    amount=amount, chain=chain,
                )
                return RouteResult(
                    provider="cdp_swap",
                    chain=chain,
                    estimated_rate=quote.exchange_rate,
                    estimated_fee_bps=10,
                    estimated_output=quote.to_amount,
                    route_type="swap",
                    steps=[{"type": "swap", "provider": "cdp_swap",
                            "from": from_token, "to": to_token, "amount": str(amount)}],
                )
            except Exception as e:
                logger.warning("CDPSwap quote failed: %s", e)

        # 4. Fallback: indicative rate (no real execution possible)
        rate = Decimal("1.0") if from_token == to_token else Decimal("0.9999")
        logger.warning(
            "No real adapter available for %s on %s — returning indicative rate",
            f"{from_token}/{to_token}", chain,
        )
        return RouteResult(
            provider="indicative",
            chain=chain,
            estimated_rate=rate,
            estimated_fee_bps=0,
            estimated_output=(amount * rate).quantize(Decimal("0.000001")),
            route_type="swap",
            steps=[{"type": "swap", "provider": "indicative",
                    "from": from_token, "to": to_token, "amount": str(amount)}],
        )

    async def _route_cross_chain(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        src_chain: str,
        dst_chain: str,
    ) -> RouteResult:
        """Route cross-chain — try Relay first (free API), then Across."""
        bridge_providers = self.BRIDGE_PROVIDERS.get(
            (src_chain, dst_chain), ["relay"]
        )

        # Try each bridge provider
        for provider_name in bridge_providers:
            try:
                if provider_name == "relay":
                    from sardis_chain.bridges.relay import RelayBridgeAdapter
                    adapter = RelayBridgeAdapter()
                    quote = await adapter.quote(src_chain, dst_chain, from_token, amount)
                    fee = getattr(quote, "total_fee", Decimal("0"))
                    return RouteResult(
                        provider="relay",
                        chain=f"{src_chain}→{dst_chain}",
                        estimated_rate=Decimal("1.0"),
                        estimated_fee_bps=int(fee / amount * 10000) if amount else 5,
                        estimated_output=amount - fee,
                        route_type="bridge",
                        steps=[{"type": "bridge", "provider": "relay",
                                "from_chain": src_chain, "to_chain": dst_chain,
                                "token": from_token, "amount": str(amount)}],
                    )
                elif provider_name == "across":
                    from sardis_chain.bridges.across import AcrossBridgeAdapter
                    adapter = AcrossBridgeAdapter()
                    quote = await adapter.quote(src_chain, dst_chain, from_token, amount)
                    return RouteResult(
                        provider="across",
                        chain=f"{src_chain}→{dst_chain}",
                        estimated_rate=Decimal("1.0"),
                        estimated_fee_bps=int(quote.total_fee / amount * 10000) if amount else 8,
                        estimated_output=quote.output_amount,
                        route_type="bridge",
                        steps=[{"type": "bridge", "provider": "across",
                                "from_chain": src_chain, "to_chain": dst_chain,
                                "token": from_token, "amount": str(amount)}],
                    )
            except Exception as e:
                logger.warning("Bridge %s failed for %s→%s: %s", provider_name, src_chain, dst_chain, e)

        # All bridges failed
        fee_bps = 10
        return RouteResult(
            provider="indicative",
            chain=f"{src_chain}→{dst_chain}",
            estimated_rate=Decimal("1.0"),
            estimated_fee_bps=fee_bps,
            estimated_output=(amount * (10000 - fee_bps) / 10000).quantize(Decimal("0.000001")),
            route_type="bridge",
            steps=[{"type": "bridge", "provider": "indicative",
                    "from_chain": src_chain, "to_chain": dst_chain,
                    "token": from_token, "amount": str(amount)}],
        )

    @staticmethod
    def _resolve_token_address(symbol: str, chain: str) -> str | None:
        """Resolve a token symbol to its contract address on a chain."""
        try:
            from sardis_v2_core.tokens import TOKEN_REGISTRY, TokenType
            for token_type in TokenType:
                if token_type.value == symbol:
                    meta = TOKEN_REGISTRY.get(token_type)
                    if meta:
                        return meta.contract_addresses.get(chain)
        except (ImportError, ValueError):
            pass
        # If symbol looks like an address, return it directly
        if symbol.startswith("0x") and len(symbol) == 42:
            return symbol
        return None
