"""Liquidity Router — chain-aware FX routing.

Routes stablecoin swaps through the optimal venue per chain:
- Tempo → enshrined DEX orderbook (best execution)
- Base → Uniswap V3/V4
- Other EVM → DEX aggregators (1inch, Paraswap)

Also routes cross-chain bridge transfers through ecosystem bridges:
- Relay (intent-based, lowest fees)
- Across (optimistic, fast)
- Squid, Bungee, LayerZero (fallbacks)
"""
from __future__ import annotations

import logging
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
    """Routes FX swaps and bridge transfers through optimal venues."""

    # Provider priority per chain
    CHAIN_PROVIDERS: dict[str, list[str]] = {
        "tempo": ["tempo_dex"],
        "base": ["uniswap_v3", "uniswap_v4"],
        "ethereum": ["uniswap_v3", "1inch"],
        "polygon": ["uniswap_v3", "paraswap"],
        "arbitrum": ["uniswap_v3", "1inch"],
        "optimism": ["uniswap_v3"],
    }

    # Bridge provider priority for chain pairs
    BRIDGE_PROVIDERS: dict[tuple[str, str], list[str]] = {
        ("tempo", "base"): ["relay", "across"],
        ("base", "tempo"): ["relay", "across"],
        ("tempo", "ethereum"): ["across", "relay"],
        ("base", "ethereum"): ["across", "relay", "cctp_v2"],
        ("ethereum", "base"): ["cctp_v2", "across", "relay"],
    }

    def __init__(
        self,
        tempo_dex=None,
        default_chain: str = "tempo",
    ) -> None:
        self._tempo_dex = tempo_dex
        self._default_chain = default_chain

    async def find_best_route(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        from_chain: str | None = None,
        to_chain: str | None = None,
    ) -> RouteResult:
        """Find the best execution route for a swap.

        If from_chain == to_chain: simple swap on the best DEX
        If from_chain != to_chain: bridge + optional swap
        """
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
        """Route a swap on the same chain."""
        providers = self.CHAIN_PROVIDERS.get(chain, ["uniswap_v3"])
        provider = providers[0]

        # Get rate from the best provider
        if provider == "tempo_dex" and self._tempo_dex:
            quote = await self._tempo_dex.get_quote(from_token, to_token, amount)
            return RouteResult(
                provider=provider,
                chain=chain,
                estimated_rate=quote.rate,
                estimated_fee_bps=0,  # Tempo DEX has no swap fee
                estimated_output=quote.to_amount,
                route_type="swap",
                steps=[{
                    "type": "swap",
                    "provider": provider,
                    "from": from_token,
                    "to": to_token,
                    "amount": str(amount),
                }],
            )

        # Fallback: indicative rate
        rate = Decimal("1.0") if from_token == to_token else Decimal("0.9999")
        return RouteResult(
            provider=provider,
            chain=chain,
            estimated_rate=rate,
            estimated_fee_bps=30 if provider != "tempo_dex" else 0,
            estimated_output=(amount * rate).quantize(Decimal("0.000001")),
            route_type="swap",
            steps=[{
                "type": "swap",
                "provider": provider,
                "from": from_token,
                "to": to_token,
                "amount": str(amount),
            }],
        )

    async def _route_cross_chain(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        src_chain: str,
        dst_chain: str,
    ) -> RouteResult:
        """Route a cross-chain transfer (bridge + optional swap)."""
        bridge_providers = self.BRIDGE_PROVIDERS.get(
            (src_chain, dst_chain),
            ["relay"],
        )
        bridge = bridge_providers[0]

        steps = []

        # If tokens differ, need swap on source chain first
        if from_token != to_token and from_token != "USDC":
            steps.append({
                "type": "swap",
                "chain": src_chain,
                "from": from_token,
                "to": "USDC",
                "amount": str(amount),
            })

        # Bridge
        steps.append({
            "type": "bridge",
            "provider": bridge,
            "from_chain": src_chain,
            "to_chain": dst_chain,
            "token": "USDC",
            "amount": str(amount),
        })

        # If destination token differs, swap on destination chain
        if to_token != "USDC":
            steps.append({
                "type": "swap",
                "chain": dst_chain,
                "from": "USDC",
                "to": to_token,
                "amount": str(amount),
            })

        route_type = "bridge" if len(steps) == 1 else "bridge+swap"
        fee_bps = {"relay": 5, "across": 8}.get(bridge, 10)

        return RouteResult(
            provider=bridge,
            chain=f"{src_chain}→{dst_chain}",
            estimated_rate=Decimal("1.0"),
            estimated_fee_bps=fee_bps,
            estimated_output=(amount * (10000 - fee_bps) / 10000).quantize(Decimal("0.000001")),
            route_type=route_type,
            steps=steps,
        )
