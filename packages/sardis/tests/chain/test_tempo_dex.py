"""Unit tests for Tempo DEX adapter (pytempo swap path).

Tests:
  - get_quote success with valid token pair
  - get_quote failure with unsupported pair
  - execute_swap with mocked pytempo
  - DEXQuote expiration
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis.chain.tempo.dex import (
    DEX_ADDRESS,
    TEMPO_TOKENS,
    TOKEN_DECIMALS,
    DEXQuote,
    TempoDEXAdapter,
)

# ── DEXQuote tests ───────────────────────────────────────────────────


class TestDEXQuote:
    def test_quote_not_expired_when_fresh(self):
        quote = DEXQuote(expires_at=datetime.now(UTC) + timedelta(seconds=10))
        assert quote.is_expired is False

    def test_quote_expired_when_past(self):
        quote = DEXQuote(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        assert quote.is_expired is True

    def test_from_amount_raw_conversion(self):
        quote = DEXQuote(from_amount=Decimal("100.000000"))
        assert quote.from_amount_raw == 100_000_000

    def test_min_output_raw_accounts_for_slippage(self):
        quote = DEXQuote(
            to_amount=Decimal("100.000000"),
            slippage_bps=50,  # 0.5%
        )
        # 100 * (10000 - 50) / 10000 = 99.5
        expected = int(Decimal("99.5") * Decimal(10**TOKEN_DECIMALS))
        assert quote.min_output_raw == expected

    def test_quote_id_prefix(self):
        quote = DEXQuote()
        assert quote.quote_id.startswith("dxq_")


# ── TempoDEXAdapter.get_quote tests ─────────────────────────────────


class TestGetQuote:
    @pytest.mark.asyncio
    async def test_get_quote_success(self):
        adapter = TempoDEXAdapter(rpc_url="https://rpc.tempo.xyz")
        # Mock the RPC call
        with patch.object(adapter, "_query_orderbook_rate", new_callable=AsyncMock) as mock_rate:
            mock_rate.return_value = Decimal("0.999500")
            quote = await adapter.get_quote("USDC", "USDC.e", Decimal("100"))

        assert quote.from_amount == Decimal("100")
        assert quote.rate == Decimal("0.999500")
        assert quote.from_token == TEMPO_TOKENS["USDC"]
        assert quote.to_token == TEMPO_TOKENS["USDC.e"]

    @pytest.mark.asyncio
    async def test_get_quote_unsupported_pair_raises(self):
        adapter = TempoDEXAdapter()
        with pytest.raises(ValueError, match="Token pair not supported"):
            await adapter.get_quote("BTC", "ETH", Decimal("1"))

    @pytest.mark.asyncio
    async def test_get_quote_uses_correct_tokens(self):
        adapter = TempoDEXAdapter()
        with patch.object(adapter, "_query_orderbook_rate", new_callable=AsyncMock) as mock_rate:
            mock_rate.return_value = Decimal("1.0")
            quote = await adapter.get_quote("USDC", "USDC.e", Decimal("50"))
        assert quote.from_token == TEMPO_TOKENS["USDC"]
        assert quote.to_token == TEMPO_TOKENS["USDC.e"]


# ── TempoDEXAdapter.execute_swap tests ───────────────────────────────


class TestExecuteSwap:
    @pytest.mark.asyncio
    async def test_expired_quote_raises(self):
        adapter = TempoDEXAdapter()
        quote = DEXQuote(
            from_token=TEMPO_TOKENS["USDC"],
            to_token=TEMPO_TOKENS["USDC.e"],
            from_amount=Decimal("100"),
            to_amount=Decimal("99.95"),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        with pytest.raises(ValueError, match="Quote has expired"):
            await adapter.execute_swap(quote)

    @pytest.mark.asyncio
    async def test_no_signing_key_raises(self):
        adapter = TempoDEXAdapter(private_key=None)
        quote = DEXQuote(
            from_token=TEMPO_TOKENS["USDC"],
            to_token=TEMPO_TOKENS["USDC.e"],
            from_amount=Decimal("100"),
            to_amount=Decimal("99.95"),
        )
        # Mock create_fx_signer to also fail
        with patch("sardis_chain.tempo.dex.create_fx_signer", side_effect=RuntimeError("no key")):
            with pytest.raises(ValueError, match="No Tempo signing key"):
                await adapter.execute_swap(quote)


# ── Encode helpers ───────────────────────────────────────────────────


class TestEncodeHelpers:
    def test_encode_get_rate(self):
        result = TempoDEXAdapter._encode_get_rate(
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
            1000000,
        )
        assert result.startswith("0xf6c7e85e")
        assert len(result) == 2 + 8 + 64 * 3  # 0x + selector + 3 params
