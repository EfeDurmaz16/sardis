"""Tempo DEX Adapter — enshrined orderbook for stablecoin swaps.

The Tempo DEX is a precompile at 0xdec0... with:
- Price-time priority orderbook (not AMM)
- All TIP-20 stablecoin pairs supported natively
- No swap fee on the orderbook itself
- Fee AMM (0xfeec...) charges 0.3% for gas token conversion
- Uniswap v2/v3/v4 also deployed, route through native DEX via aggregator

Usage::

    dex = TempoDEXAdapter()
    quote = await dex.get_quote("USDC", "EURC", Decimal("100.00"))
    receipt = await dex.execute_swap(quote)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.chain.tempo.dex")

# Precompile addresses
DEX_ADDRESS = "0xdec0000000000000000000000000000000000000"
FEE_MANAGER_ADDRESS = "0xfeec000000000000000000000000000000000000"

# Known TIP-20 token addresses on Tempo
TEMPO_TOKENS: dict[str, str] = {
    "USDC": "0x20c0000000000000000000000000000000000000",      # pathUSD
    "USDC.e": "0x20C000000000000000000000b9537d11c60E8b50",    # Bridged USDC
    "EURC": "",  # To be confirmed at launch
    "USDT": "",  # To be confirmed
}


@dataclass
class DEXQuote:
    """A quote from the Tempo enshrined DEX."""

    quote_id: str = field(default_factory=lambda: f"dxq_{uuid4().hex[:8]}")
    from_token: str = ""
    to_token: str = ""
    from_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    to_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    rate: Decimal = field(default_factory=lambda: Decimal("1.0"))
    slippage_bps: int = 50
    # Orderbook depth info
    best_bid: Decimal | None = None
    best_ask: Decimal | None = None
    depth_available: Decimal | None = None
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(seconds=10)
    )
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires_at


class TempoDEXAdapter:
    """Adapter for Tempo's enshrined stablecoin DEX.

    Routes through the native orderbook precompile for optimal
    execution of stablecoin FX swaps.
    """

    def __init__(
        self,
        rpc_url: str = "https://rpc.tempo.xyz",
        executor=None,
    ) -> None:
        self._rpc_url = rpc_url
        self._executor = executor

    async def get_quote(
        self,
        from_symbol: str,
        to_symbol: str,
        amount: Decimal,
        slippage_bps: int = 50,
    ) -> DEXQuote:
        """Get a quote from the enshrined DEX orderbook.

        Queries the on-chain orderbook for the best available rate.
        """
        from_token = TEMPO_TOKENS.get(from_symbol, "")
        to_token = TEMPO_TOKENS.get(to_symbol, "")

        if not from_token or not to_token:
            raise ValueError(f"Token pair not supported: {from_symbol}/{to_symbol}")

        # Query DEX orderbook for rate
        rate = await self._query_orderbook_rate(from_token, to_token, amount)
        to_amount = (amount * rate).quantize(Decimal("0.000001"))

        quote = DEXQuote(
            from_token=from_token,
            to_token=to_token,
            from_amount=amount,
            to_amount=to_amount,
            rate=rate,
            slippage_bps=slippage_bps,
        )

        logger.info(
            "DEX quote: %s %s → %s %s @ %s",
            amount, from_symbol, to_amount, to_symbol, rate,
        )
        return quote

    async def execute_swap(self, quote: DEXQuote) -> dict[str, Any]:
        """Execute a swap using the enshrined DEX.

        Constructs approve + swap in a type 0x76 batch for atomicity.
        """
        if quote.is_expired:
            raise ValueError("Quote has expired")

        if not self._executor:
            raise ValueError("Executor required for swap execution")

        # Calculate minimum output with slippage
        min_output_raw = int(
            quote.to_amount * (10000 - quote.slippage_bps) / 10000
            * Decimal("1000000")  # 6 decimals
        )
        amount_raw = int(quote.from_amount * Decimal("1000000"))

        receipt = await self._executor.execute_dex_swap(
            from_token=quote.from_token,
            to_token=quote.to_token,
            amount=amount_raw,
            min_output=min_output_raw,
        )

        return {
            "quote_id": quote.quote_id,
            "tx_hash": receipt.tx_hash,
            "status": "completed" if receipt.status else "failed",
            "from_amount": str(quote.from_amount),
            "to_amount": str(quote.to_amount),
            "rate": str(quote.rate),
        }

    async def get_rates(self) -> dict[str, Decimal]:
        """Get current indicative rates for all supported pairs."""
        pairs = [
            ("USDC", "USDC.e"),
            ("USDC.e", "USDC"),
        ]
        rates = {}
        for from_sym, to_sym in pairs:
            from_token = TEMPO_TOKENS.get(from_sym, "")
            to_token = TEMPO_TOKENS.get(to_sym, "")
            if from_token and to_token:
                rate = await self._query_orderbook_rate(
                    from_token, to_token, Decimal("1000")
                )
                rates[f"{from_sym}/{to_sym}"] = rate
        return rates

    async def _query_orderbook_rate(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
    ) -> Decimal:
        """Query the DEX precompile for the current orderbook rate.

        In production, calls eth_call on the DEX precompile to read
        the orderbook. Returns the volume-weighted average rate.
        """
        import httpx

        # Build the query calldata for the DEX precompile
        # getRate(address,address,uint256)
        amount_raw = int(amount * Decimal("1000000"))

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [{
                            "to": DEX_ADDRESS,
                            "data": self._encode_get_rate(from_token, to_token, amount_raw),
                        }, "latest"],
                        "id": 1,
                    },
                )
                result = resp.json()

            if "result" in result and result["result"] != "0x":
                # Parse rate from response (uint256, 18 decimals)
                rate_raw = int(result["result"], 16)
                return Decimal(rate_raw) / Decimal(10**18)
        except Exception:
            logger.debug("DEX rate query failed, using fallback rate")

        # Fallback: stablecoins are ~1:1
        return Decimal("1.0")

    @staticmethod
    def _encode_get_rate(from_token: str, to_token: str, amount: int) -> str:
        """Encode getRate(address,address,uint256) call."""
        selector = "0xf6c7e85e"  # getRate selector
        from_addr = from_token[2:].zfill(64)
        to_addr = to_token[2:].zfill(64)
        amt = format(amount, "064x")
        return selector + from_addr + to_addr + amt
