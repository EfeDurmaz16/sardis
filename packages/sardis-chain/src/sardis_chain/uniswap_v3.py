"""Uniswap V3 adapter — direct on-chain stablecoin swaps on Base/Ethereum.

No API key needed — only an RPC endpoint (Alchemy via SARDIS_BASE_RPC_URL).

Uses:
- QuoterV2 for price quotes (eth_call, read-only, free)
- SwapRouter02 for execution (requires signer)

Stablecoin pool fee tiers:
- 100 bps (0.01%) — tightest spread, best for large stablecoin swaps
- 500 bps (0.05%) — more liquidity, good default

Usage::

    adapter = UniswapV3Adapter(rpc_url="https://base.g.alchemy.com/v2/KEY")
    quote = await adapter.get_quote(USDC_BASE, EURC_BASE, amount=100_000_000)
    result = await adapter.execute_swap(quote, private_key="0x...")
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.chain.uniswap_v3")

# Uniswap V3 contract addresses (same on all major EVM chains)
QUOTER_V2: dict[str, str] = {
    "base": "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",
    "ethereum": "0x61fFE014bA17989E743c0c7AE6D2Cc4B29d06C7c",
    "arbitrum": "0x61fFE014bA17989E743c0c7AE6D2Cc4B29d06C7c",
    "polygon": "0x61fFE014bA17989E743c0c7AE6D2Cc4B29d06C7c",
}

SWAP_ROUTER_02: dict[str, str] = {
    "base": "0x2626664c2603336E57B271c5C0b26F421741e481",
    "ethereum": "0x68b3465833fb72B5A828cCEBc9B6d7Cb6Dd44d61",
    "arbitrum": "0x68b3465833fb72B5A828cCEBc9B6d7Cb6Dd44d61",
    "polygon": "0x68b3465833fb72B5A828cCEBc9B6d7Cb6Dd44d61",
}

# Stablecoin token addresses on Base
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
EURC_BASE = "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42"

# ABI function selectors
QUOTE_EXACT_INPUT_SINGLE = "0xc6a5026a"  # quoteExactInputSingle((address,address,uint256,uint24,uint160))
EXACT_INPUT_SINGLE = "0x04e45aaf"  # exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))

# Default fee tier for stablecoins (0.05%)
DEFAULT_FEE_TIER = 500
TIGHT_FEE_TIER = 100  # 0.01% — best for large amounts


@dataclass
class UniswapQuote:
    """A quote from Uniswap V3."""
    quote_id: str = field(default_factory=lambda: f"uniq_{uuid4().hex[:8]}")
    token_in: str = ""
    token_out: str = ""
    amount_in: int = 0
    amount_out: int = 0
    fee_tier: int = DEFAULT_FEE_TIER
    sqrt_price_limit: int = 0
    chain: str = "base"
    rate: Decimal = field(default_factory=lambda: Decimal("1.0"))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(seconds=15)
    )

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires_at


class UniswapV3Adapter:
    """Direct on-chain Uniswap V3 swaps — no API key needed.

    Uses QuoterV2 (read-only) for quotes and SwapRouter02 for execution.
    Only requires an RPC URL (e.g., Alchemy on Base).
    """

    def __init__(
        self,
        rpc_url: str | None = None,
        chain: str = "base",
    ) -> None:
        self._rpc_url = rpc_url or os.getenv("SARDIS_BASE_RPC_URL", "")
        self._chain = chain
        self._quoter = QUOTER_V2.get(chain, "")
        self._router = SWAP_ROUTER_02.get(chain, "")

        if not self._rpc_url:
            logger.warning("No RPC URL for Uniswap V3 on %s", chain)

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        fee_tier: int = DEFAULT_FEE_TIER,
    ) -> UniswapQuote:
        """Get a quote from Uniswap V3 QuoterV2 via eth_call (free, no gas)."""
        if not self._quoter or not self._rpc_url:
            raise ValueError(f"Uniswap V3 not configured for {self._chain}")

        import httpx

        # Encode quoteExactInputSingle call
        calldata = self._encode_quote_exact_input_single(
            token_in, token_out, amount_in, fee_tier
        )

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self._rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [{"to": self._quoter, "data": calldata}, "latest"],
                    "id": 1,
                },
            )
            result = resp.json()

        if "error" in result:
            raise RuntimeError(f"QuoterV2 call failed: {result['error']}")

        # Decode: returns (uint256 amountOut, uint160 sqrtPriceX96After, uint32 initializedTicksCrossed, uint256 gasEstimate)
        data = result.get("result", "0x")
        if len(data) < 66:
            raise RuntimeError("QuoterV2 returned empty result — pool may not exist")

        amount_out = int(data[2:66], 16)

        rate = Decimal(amount_out) / Decimal(amount_in) if amount_in > 0 else Decimal("1.0")

        quote = UniswapQuote(
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            amount_out=amount_out,
            fee_tier=fee_tier,
            chain=self._chain,
            rate=rate,
        )

        logger.info(
            "Uniswap V3 quote: %d → %d (%s/%s, fee=%d, rate=%s)",
            amount_in, amount_out, token_in[:10], token_out[:10], fee_tier, rate,
        )
        return quote

    async def execute_swap(
        self,
        quote: UniswapQuote,
        private_key: str | None = None,
        recipient: str | None = None,
        slippage_bps: int = 50,
    ) -> dict[str, Any]:
        """Execute a swap on Uniswap V3 SwapRouter02.

        Signs the transaction and broadcasts via RPC. No API key needed.
        """
        if quote.is_expired:
            raise ValueError("Quote has expired")

        key = private_key or os.getenv("SARDIS_EOA_PRIVATE_KEY")
        if not key:
            raise ValueError("Private key required for swap execution")

        if not self._router or not self._rpc_url:
            raise ValueError(f"SwapRouter02 not configured for {self._chain}")

        from eth_account import Account
        import httpx

        account = Account.from_key(key)
        sender = account.address
        to = recipient or sender

        # Calculate minimum output with slippage
        min_out = int(quote.amount_out * (10000 - slippage_bps) / 10000)

        # Get nonce and gas
        async with httpx.AsyncClient(timeout=15) as client:
            nonce_resp = await client.post(self._rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_getTransactionCount",
                "params": [sender, "pending"], "id": 1,
            })
            gas_resp = await client.post(self._rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 2,
            })
            chain_resp = await client.post(self._rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 3,
            })

        nonce = int(nonce_resp.json()["result"], 16)
        gas_price = int(gas_resp.json()["result"], 16)
        chain_id = int(chain_resp.json()["result"], 16)

        # Build exactInputSingle calldata
        swap_data = self._encode_exact_input_single(
            quote.token_in, quote.token_out, quote.fee_tier,
            to, quote.amount_in, min_out,
        )

        # First: approve SwapRouter02 to spend token_in
        approve_data = self._encode_approve(self._router, quote.amount_in)

        # Sign and send approve tx
        approve_tx = {
            "to": quote.token_in,
            "data": "0x" + approve_data.hex(),
            "gas": 100_000,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": chain_id,
        }
        signed_approve = Account.sign_transaction(approve_tx, key)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_sendRawTransaction",
                "params": ["0x" + signed_approve.raw_transaction.hex()], "id": 1,
            })
            approve_result = resp.json()

        if "error" in approve_result:
            raise RuntimeError(f"Approve tx failed: {approve_result['error']}")

        # Sign and send swap tx
        swap_tx = {
            "to": self._router,
            "data": "0x" + swap_data.hex(),
            "gas": 300_000,
            "gasPrice": gas_price,
            "nonce": nonce + 1,
            "chainId": chain_id,
        }
        signed_swap = Account.sign_transaction(swap_tx, key)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_sendRawTransaction",
                "params": ["0x" + signed_swap.raw_transaction.hex()], "id": 1,
            })
            swap_result = resp.json()

        if "error" in swap_result:
            raise RuntimeError(f"Swap tx failed: {swap_result['error']}")

        tx_hash = swap_result.get("result", "")
        logger.info("Uniswap V3 swap submitted: %s", tx_hash)

        # Poll for receipt
        receipt = await self._wait_for_receipt(tx_hash)

        return {
            "quote_id": quote.quote_id,
            "tx_hash": tx_hash,
            "status": "completed" if receipt.get("status") else "failed",
            "amount_in": quote.amount_in,
            "amount_out": quote.amount_out,
            "rate": str(quote.rate),
            "chain": self._chain,
        }

    async def _wait_for_receipt(self, tx_hash: str, max_attempts: int = 30) -> dict:
        """Poll for transaction receipt."""
        import asyncio
        import httpx

        for _ in range(max_attempts):
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._rpc_url, json={
                    "jsonrpc": "2.0", "method": "eth_getTransactionReceipt",
                    "params": [tx_hash], "id": 1,
                })
                result = resp.json()

            receipt = result.get("result")
            if receipt:
                return {
                    "status": receipt.get("status") == "0x1",
                    "block_number": int(receipt.get("blockNumber", "0x0"), 16),
                }

            await asyncio.sleep(2)  # Base ~2s block time

        return {"status": False, "block_number": 0}

    # -- ABI encoding --

    @staticmethod
    def _encode_quote_exact_input_single(
        token_in: str, token_out: str, amount: int, fee: int
    ) -> str:
        """Encode QuoterV2.quoteExactInputSingle struct call."""
        # Struct: (address tokenIn, address tokenOut, uint256 amountIn, uint24 fee, uint160 sqrtPriceLimitX96)
        params = (
            token_in[2:].zfill(64)
            + token_out[2:].zfill(64)
            + format(amount, "064x")
            + format(fee, "064x")
            + "0" * 64  # sqrtPriceLimitX96 = 0 (no limit)
        )
        # Offset to tuple (0x20)
        return QUOTE_EXACT_INPUT_SINGLE + "0" * 62 + "20" + params

    @staticmethod
    def _encode_exact_input_single(
        token_in: str, token_out: str, fee: int,
        recipient: str, amount_in: int, amount_out_min: int,
    ) -> bytes:
        """Encode SwapRouter02.exactInputSingle struct call."""
        # Struct: (address tokenIn, address tokenOut, uint24 fee, address recipient,
        #          uint256 amountIn, uint256 amountOutMinimum, uint160 sqrtPriceLimitX96)
        selector = bytes.fromhex(EXACT_INPUT_SINGLE[2:])
        params = bytes.fromhex(
            token_in[2:].zfill(64)
            + token_out[2:].zfill(64)
            + format(fee, "064x")
            + recipient[2:].zfill(64)
            + format(amount_in, "064x")
            + format(amount_out_min, "064x")
            + "0" * 64  # sqrtPriceLimitX96 = 0
        )
        # Offset to tuple (0x20)
        return selector + bytes.fromhex("0" * 62 + "20") + params

    @staticmethod
    def _encode_approve(spender: str, amount: int) -> bytes:
        """Encode ERC-20 approve(address,uint256)."""
        selector = bytes.fromhex("095ea7b3")
        addr = bytes.fromhex(spender[2:].zfill(64))
        amt = amount.to_bytes(32, "big")
        return selector + addr + amt
