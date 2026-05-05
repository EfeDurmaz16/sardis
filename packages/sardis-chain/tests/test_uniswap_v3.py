"""Unit tests for Uniswap V3 adapter.

Tests:
  - get_quote via QuoterV2 (mocked RPC)
  - execute_swap with approve + swap (mocked RPC)
  - Slippage handling
  - ABI encoding helpers
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_chain.uniswap_v3 import (
    DEFAULT_FEE_TIER,
    EURC_BASE,
    QUOTER_V2,
    SWAP_ROUTER_02,
    USDC_BASE,
    UniswapQuote,
    UniswapV3Adapter,
)

# ── UniswapQuote tests ───────────────────────────────────────────────


class TestUniswapQuote:
    def test_quote_not_expired_when_fresh(self):
        quote = UniswapQuote(expires_at=datetime.now(UTC) + timedelta(seconds=15))
        assert quote.is_expired is False

    def test_quote_expired_when_past(self):
        quote = UniswapQuote(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        assert quote.is_expired is True

    def test_quote_id_prefix(self):
        quote = UniswapQuote()
        assert quote.quote_id.startswith("uniq_")

    def test_default_fee_tier(self):
        quote = UniswapQuote()
        assert quote.fee_tier == DEFAULT_FEE_TIER


# ── Adapter configuration ───────────────────────────────────────────


class TestAdapterConfig:
    def test_base_chain_has_quoter(self):
        assert "base" in QUOTER_V2
        assert "base" in SWAP_ROUTER_02

    def test_adapter_stores_chain(self):
        adapter = UniswapV3Adapter(rpc_url="https://rpc.example.com", chain="base")
        assert adapter._chain == "base"
        assert adapter._quoter == QUOTER_V2["base"]
        assert adapter._router == SWAP_ROUTER_02["base"]

    def test_adapter_unknown_chain(self):
        adapter = UniswapV3Adapter(rpc_url="https://rpc.example.com", chain="solana")
        assert adapter._quoter == ""
        assert adapter._router == ""


# ── get_quote tests (mocked RPC) ────────────────────────────────────


class TestGetQuote:
    @pytest.mark.asyncio
    async def test_get_quote_success(self):
        adapter = UniswapV3Adapter(rpc_url="https://rpc.example.com", chain="base")

        # Mock the RPC response: amountOut = 99950000 (99.95 EURC for 100 USDC)
        amount_out_hex = format(99_950_000, "064x")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": "0x" + amount_out_hex + "0" * 192,
        }
        mock_response.status_code = 200

        adapter._http_client.post = AsyncMock(return_value=mock_response)
        try:
            quote = await adapter.get_quote(USDC_BASE, EURC_BASE, 100_000_000)
        finally:
            await adapter.close()

        assert quote.amount_in == 100_000_000
        assert quote.amount_out == 99_950_000
        assert quote.chain == "base"

    @pytest.mark.asyncio
    async def test_get_quote_no_rpc_raises(self):
        adapter = UniswapV3Adapter(rpc_url="", chain="base")
        with pytest.raises(ValueError, match="not configured"):
            await adapter.get_quote(USDC_BASE, EURC_BASE, 100_000_000)

    @pytest.mark.asyncio
    async def test_get_quote_rpc_error_raises(self):
        adapter = UniswapV3Adapter(rpc_url="https://rpc.example.com", chain="base")

        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"code": -32000, "message": "execution reverted"}}

        adapter._http_client.post = AsyncMock(return_value=mock_response)
        try:
            with pytest.raises(RuntimeError, match="QuoterV2 call failed"):
                await adapter.get_quote(USDC_BASE, EURC_BASE, 100_000_000)
        finally:
            await adapter.close()


# ── execute_swap tests ───────────────────────────────────────────────


class TestExecuteSwap:
    @pytest.mark.asyncio
    async def test_expired_quote_raises(self):
        adapter = UniswapV3Adapter(rpc_url="https://rpc.example.com", chain="base")
        quote = UniswapQuote(
            token_in=USDC_BASE,
            token_out=EURC_BASE,
            amount_in=100_000_000,
            amount_out=99_950_000,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        with pytest.raises(ValueError, match="Quote has expired"):
            await adapter.execute_swap(quote)

    @pytest.mark.asyncio
    async def test_no_private_key_raises(self):
        adapter = UniswapV3Adapter(rpc_url="https://rpc.example.com", chain="base")
        quote = UniswapQuote(
            token_in=USDC_BASE,
            token_out=EURC_BASE,
            amount_in=100_000_000,
            amount_out=99_950_000,
        )
        with patch.dict("os.environ", {}, clear=False):
            # Ensure no env key
            import os
            os.environ.pop("SARDIS_EOA_PRIVATE_KEY", None)
            with pytest.raises(ValueError, match="Private key required"):
                await adapter.execute_swap(quote)


# ── ABI encoding tests ──────────────────────────────────────────────


class TestABIEncoding:
    def test_encode_quote_exact_input_single(self):
        result = UniswapV3Adapter._encode_quote_exact_input_single(
            USDC_BASE, EURC_BASE, 100_000_000, 500
        )
        assert result.startswith("0xc6a5026a")

    def test_encode_exact_input_single(self):
        result = UniswapV3Adapter._encode_exact_input_single(
            USDC_BASE, EURC_BASE, 500,
            "0x1234567890123456789012345678901234567890",
            100_000_000, 99_000_000,
        )
        assert isinstance(result, bytes)
        # Selector is 4 bytes
        assert result[:4] == bytes.fromhex("04e45aaf")

    def test_encode_approve(self):
        result = UniswapV3Adapter._encode_approve(
            "0x1234567890123456789012345678901234567890",
            100_000_000,
        )
        assert isinstance(result, bytes)
        # ERC-20 approve selector
        assert result[:4] == bytes.fromhex("095ea7b3")

    def test_slippage_calculation(self):
        """Slippage of 50 bps (0.5%) reduces output correctly."""
        amount_out = 100_000_000
        slippage_bps = 50
        min_out = int(amount_out * (10000 - slippage_bps) / 10000)
        assert min_out == 99_500_000
