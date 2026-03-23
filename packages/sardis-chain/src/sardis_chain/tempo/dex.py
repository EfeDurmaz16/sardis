"""Tempo DEX Adapter — enshrined orderbook for stablecoin swaps.

Uses pytempo (v0.4.0) typed contract helpers for production-grade
interaction with the Tempo StablecoinDEX precompile at 0xdec0...

Features:
- Price-time priority orderbook (not AMM)
- All TIP-20 stablecoin pairs supported natively
- No swap fee on the orderbook itself
- Atomic approve + swap in a single type 0x76 batch transaction
- No API key needed — only Tempo RPC

Usage::

    dex = TempoDEXAdapter(rpc_url="https://rpc.tempo.xyz")
    quote = await dex.get_quote("USDC", "USDC.e", Decimal("100.00"))
    result = await dex.execute_swap(quote, private_key="0x...")
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

# Known TIP-20 token addresses on Tempo (from pympp _defaults.py)
TEMPO_TOKENS: dict[str, str] = {
    "USDC": "0x20c0000000000000000000000000000000000000",      # pathUSD
    "USDC.e": "0x20C000000000000000000000b9537d11c60E8b50",    # Bridged USDC
    "EURC": "",  # To be confirmed at launch
    "USDT": "",  # To be confirmed
}

# Token decimals (all stablecoins are 6)
TOKEN_DECIMALS = 6


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

    @property
    def from_amount_raw(self) -> int:
        return int(self.from_amount * Decimal(10**TOKEN_DECIMALS))

    @property
    def min_output_raw(self) -> int:
        """Minimum output accounting for slippage."""
        adjusted = self.to_amount * (10000 - self.slippage_bps) / 10000
        return int(adjusted * Decimal(10**TOKEN_DECIMALS))


class TempoDEXAdapter:
    """Adapter for Tempo's enshrined stablecoin DEX.

    Uses pytempo.contracts.StablecoinDEX for typed, production-grade
    swap execution. No API key needed — only Tempo RPC.
    """

    def __init__(
        self,
        rpc_url: str = "https://rpc.tempo.xyz",
        chain_id: int = 4217,
        private_key: str | None = None,
    ) -> None:
        self._rpc_url = rpc_url
        self._chain_id = chain_id
        self._private_key = private_key

    async def get_quote(
        self,
        from_symbol: str,
        to_symbol: str,
        amount: Decimal,
        slippage_bps: int = 50,
    ) -> DEXQuote:
        """Get a quote from the enshrined DEX orderbook via eth_call."""
        from_token = TEMPO_TOKENS.get(from_symbol, "")
        to_token = TEMPO_TOKENS.get(to_symbol, "")

        if not from_token or not to_token:
            raise ValueError(f"Token pair not supported: {from_symbol}/{to_symbol}")

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

    async def execute_swap(
        self,
        quote: DEXQuote,
        private_key: str | None = None,
    ) -> dict[str, Any]:
        """Execute a swap using pytempo StablecoinDEX.

        Builds a type 0x76 batch transaction with:
        1. TIP20.approve(DEX, amount) — authorize DEX to spend input token
        2. StablecoinDEX.swap(token_in, amount_in, amount_out_min)

        Signs with the provided private key and broadcasts via RPC.
        """
        if quote.is_expired:
            raise ValueError("Quote has expired")

        key = private_key or self._private_key
        if not key:
            raise ValueError("Private key required for swap execution")

        try:
            from pytempo import TempoTransaction
            from pytempo.contracts import TIP20, StablecoinDEX
        except ImportError as e:
            raise RuntimeError(
                "pytempo is required for Tempo DEX swaps. Install: pip install pytempo"
            ) from e

        # Get on-chain tx params
        chain_id, nonce, gas_price = await self._get_tx_params(key)

        # Build atomic approve + swap batch
        tx = TempoTransaction.create(
            chain_id=chain_id,
            gas_limit=300_000,
            max_fee_per_gas=gas_price,
            max_priority_fee_per_gas=gas_price,
            nonce=nonce,
            fee_token=quote.from_token,  # Pay gas in the swap input token
            calls=(
                TIP20(quote.from_token).approve(
                    spender=StablecoinDEX.ADDRESS,
                    amount=quote.from_amount_raw,
                ),
                StablecoinDEX.swap(
                    token_in=quote.from_token,
                    amount_in=quote.from_amount_raw,
                    amount_out_min=quote.min_output_raw,
                ),
            ),
        )

        # Sign and broadcast
        signed = tx.sign(key)
        tx_hash = await self._broadcast(signed.encode())

        # Wait for receipt
        receipt = await self._wait_for_receipt(tx_hash)

        result = {
            "quote_id": quote.quote_id,
            "tx_hash": tx_hash,
            "status": "completed" if receipt.get("status") else "failed",
            "from_amount": str(quote.from_amount),
            "to_amount": str(quote.to_amount),
            "rate": str(quote.rate),
            "block_number": receipt.get("block_number", 0),
        }

        logger.info(
            "DEX swap %s: %s → %s (tx=%s, status=%s)",
            quote.quote_id, quote.from_amount, quote.to_amount,
            tx_hash, result["status"],
        )
        return result

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

    # -- RPC helpers (from pympp _rpc.py pattern) --

    async def _get_tx_params(self, private_key: str) -> tuple[int, int, int]:
        """Fetch chain_id, nonce, gas_price for building a transaction."""
        import asyncio
        import httpx

        from eth_account import Account
        address = Account.from_key(private_key).address

        async with httpx.AsyncClient(timeout=15) as client:
            chain_id_resp, nonce_resp, gas_resp = await asyncio.gather(
                client.post(self._rpc_url, json={
                    "jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1,
                }),
                client.post(self._rpc_url, json={
                    "jsonrpc": "2.0", "method": "eth_getTransactionCount",
                    "params": [address, "pending"], "id": 2,
                }),
                client.post(self._rpc_url, json={
                    "jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 3,
                }),
            )

        chain_id = int(chain_id_resp.json()["result"], 16)
        nonce = int(nonce_resp.json()["result"], 16)
        gas_price = int(gas_resp.json()["result"], 16)

        return chain_id, nonce, gas_price

    async def _broadcast(self, raw_tx: bytes) -> str:
        """Broadcast a signed transaction to Tempo RPC."""
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self._rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_sendRawTransaction",
                    "params": ["0x" + raw_tx.hex()],
                    "id": 1,
                },
            )
            result = resp.json()

        if "error" in result:
            raise RuntimeError(f"Broadcast failed: {result['error']}")

        tx_hash = result.get("result", "")
        logger.info("Broadcast tx: %s", tx_hash)
        return tx_hash

    async def _wait_for_receipt(self, tx_hash: str, max_attempts: int = 20) -> dict:
        """Poll for transaction receipt (Tempo has ~0.5s finality)."""
        import asyncio
        import httpx

        for _ in range(max_attempts):
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self._rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_getTransactionReceipt",
                        "params": [tx_hash],
                        "id": 1,
                    },
                )
                result = resp.json()

            receipt = result.get("result")
            if receipt:
                return {
                    "status": receipt.get("status") == "0x1",
                    "block_number": int(receipt.get("blockNumber", "0x0"), 16),
                    "gas_used": int(receipt.get("gasUsed", "0x0"), 16),
                }

            await asyncio.sleep(0.5)

        logger.warning("Timeout waiting for receipt: %s", tx_hash)
        return {"status": False, "block_number": 0, "gas_used": 0}

    async def _query_orderbook_rate(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
    ) -> Decimal:
        """Query the DEX precompile for the current orderbook rate."""
        import httpx

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
                rate_raw = int(result["result"], 16)
                return Decimal(rate_raw) / Decimal(10**18)
        except Exception:
            logger.debug("DEX rate query failed, using fallback rate")

        return Decimal("1.0")

    @staticmethod
    def _encode_get_rate(from_token: str, to_token: str, amount: int) -> str:
        """Encode getRate(address,address,uint256) call."""
        selector = "0xf6c7e85e"
        from_addr = from_token[2:].zfill(64)
        to_addr = to_token[2:].zfill(64)
        amt = format(amount, "064x")
        return selector + from_addr + to_addr + amt
