"""Tests for on-chain USDC transfer verification in external wallet checkout.

Mocks RPC responses to verify correct behavior for:
- Valid transfer → paid
- Reverted transaction → 400
- Wrong recipient → 400
- Wrong amount (exact match required) → 400
- Transaction not found → 400
- Insufficient confirmations → 400
- No settlement address → 400 (mandatory verification)
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_api.services.onchain_verification import (
    TRANSFER_EVENT_TOPIC,
    verify_usdc_transfer,
)

# Base mainnet USDC address
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
MERCHANT_ADDR = "0x1234567890abcdef1234567890abcdef12345678"
TX_HASH = "0xabc123"


def _make_receipt(
    status: str = "0x1",
    to_address: str = MERCHANT_ADDR,
    amount_raw: int = 10_000_000,  # 10 USDC
    usdc_contract: str = USDC_BASE,
    block_number: str = "0x100",
) -> dict:
    """Build a mock eth_getTransactionReceipt response."""
    to_padded = "0x" + to_address.lower().replace("0x", "").zfill(64)
    from_padded = "0x" + "0" * 24 + "deadbeef" * 5  # arbitrary from
    amount_hex = hex(amount_raw)

    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "status": status,
            "blockNumber": block_number,
            "logs": [
                {
                    "address": usdc_contract,
                    "topics": [
                        TRANSFER_EVENT_TOPIC,
                        from_padded,
                        to_padded,
                    ],
                    "data": amount_hex,
                }
            ],
        },
    }


def _make_block_number_response(block_hex: str = "0x110") -> dict:
    """Build a mock eth_blockNumber response."""
    return {"jsonrpc": "2.0", "id": 2, "result": block_hex}


class TestVerifyUsdcTransfer:
    """Core verification logic tests."""

    @pytest.mark.asyncio
    async def test_valid_receipt_verifies(self):
        """Valid USDC transfer with correct recipient and amount."""
        mock_receipt_resp = MagicMock()
        mock_receipt_resp.json.return_value = _make_receipt()
        mock_block_resp = MagicMock()
        mock_block_resp.json.return_value = _make_block_number_response("0x110")  # 16 confirmations

        with patch("sardis_api.services.onchain_verification.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = [mock_receipt_resp, mock_block_resp]
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await verify_usdc_transfer(
                tx_hash=TX_HASH,
                expected_recipient=MERCHANT_ADDR,
                expected_amount=Decimal("10"),
                chain="base",
            )
            assert result.verified is True
            assert result.actual_amount == Decimal("10")
            assert result.block_number == 256

    @pytest.mark.asyncio
    async def test_reverted_tx_rejected(self):
        """Reverted transaction (status != 0x1) is rejected."""
        mock_receipt_resp = MagicMock()
        mock_receipt_resp.json.return_value = _make_receipt(status="0x0")
        mock_block_resp = MagicMock()
        mock_block_resp.json.return_value = _make_block_number_response()

        with patch("sardis_api.services.onchain_verification.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = [mock_receipt_resp, mock_block_resp]
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await verify_usdc_transfer(
                tx_hash=TX_HASH,
                expected_recipient=MERCHANT_ADDR,
                expected_amount=Decimal("10"),
                chain="base",
            )
            assert result.verified is False
            assert "reverted" in result.error.lower()

    @pytest.mark.asyncio
    async def test_wrong_recipient_rejected(self):
        """Transfer to wrong address is rejected."""
        wrong_addr = "0xdeaddeaddeaddeaddeaddeaddeaddeaddeaddead"
        mock_receipt_resp = MagicMock()
        mock_receipt_resp.json.return_value = _make_receipt(to_address=wrong_addr)
        mock_block_resp = MagicMock()
        mock_block_resp.json.return_value = _make_block_number_response()

        with patch("sardis_api.services.onchain_verification.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = [mock_receipt_resp, mock_block_resp]
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await verify_usdc_transfer(
                tx_hash=TX_HASH,
                expected_recipient=MERCHANT_ADDR,
                expected_amount=Decimal("10"),
                chain="base",
            )
            assert result.verified is False
            assert "Transfer" in (result.error or "")

    @pytest.mark.asyncio
    async def test_wrong_amount_rejected(self):
        """Transfer with wrong amount is rejected (exact match required)."""
        mock_receipt_resp = MagicMock()
        mock_receipt_resp.json.return_value = _make_receipt(amount_raw=5_000_000)  # 5 USDC
        mock_block_resp = MagicMock()
        mock_block_resp.json.return_value = _make_block_number_response()

        with patch("sardis_api.services.onchain_verification.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = [mock_receipt_resp, mock_block_resp]
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await verify_usdc_transfer(
                tx_hash=TX_HASH,
                expected_recipient=MERCHANT_ADDR,
                expected_amount=Decimal("10"),
                chain="base",
            )
            assert result.verified is False
            assert "does not match" in (result.error or "")

    @pytest.mark.asyncio
    async def test_overpayment_rejected(self):
        """Overpayment is also rejected (exact match required)."""
        mock_receipt_resp = MagicMock()
        mock_receipt_resp.json.return_value = _make_receipt(amount_raw=15_000_000)  # 15 USDC
        mock_block_resp = MagicMock()
        mock_block_resp.json.return_value = _make_block_number_response()

        with patch("sardis_api.services.onchain_verification.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = [mock_receipt_resp, mock_block_resp]
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await verify_usdc_transfer(
                tx_hash=TX_HASH,
                expected_recipient=MERCHANT_ADDR,
                expected_amount=Decimal("10"),
                chain="base",
            )
            assert result.verified is False
            assert "does not match" in (result.error or "")

    @pytest.mark.asyncio
    async def test_tx_not_found_rejected(self):
        """Transaction not yet mined (receipt is null) is rejected."""
        mock_receipt_resp = MagicMock()
        mock_receipt_resp.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": None}
        mock_block_resp = MagicMock()
        mock_block_resp.json.return_value = _make_block_number_response()

        with patch("sardis_api.services.onchain_verification.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = [mock_receipt_resp, mock_block_resp]
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await verify_usdc_transfer(
                tx_hash=TX_HASH,
                expected_recipient=MERCHANT_ADDR,
                expected_amount=Decimal("10"),
                chain="base",
            )
            assert result.verified is False
            assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_rpc_error_rejected(self):
        """RPC connection error is handled gracefully."""
        import httpx

        with patch("sardis_api.services.onchain_verification.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.ConnectError("connection refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await verify_usdc_transfer(
                tx_hash=TX_HASH,
                expected_recipient=MERCHANT_ADDR,
                expected_amount=Decimal("10"),
                chain="base",
            )
            assert result.verified is False
            assert "RPC error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_no_rpc_url_rejected(self):
        """Missing RPC URL for chain is rejected."""
        with patch.dict("os.environ", {}, clear=False):
            # Remove any RPC URL env vars
            env_clean = {k: v for k, v in __import__("os").environ.items()
                        if "RPC_URL" not in k}
            with patch.dict("os.environ", env_clean, clear=True):
                result = await verify_usdc_transfer(
                    tx_hash=TX_HASH,
                    expected_recipient=MERCHANT_ADDR,
                    expected_amount=Decimal("10"),
                    chain="nonexistent_chain",
                )
                assert result.verified is False
                assert "RPC URL" in (result.error or "")

    @pytest.mark.asyncio
    async def test_insufficient_confirmations_rejected(self):
        """Transaction with insufficient confirmations is rejected."""
        mock_receipt_resp = MagicMock()
        mock_receipt_resp.json.return_value = _make_receipt(block_number="0x100")  # block 256
        mock_block_resp = MagicMock()
        mock_block_resp.json.return_value = _make_block_number_response("0x100")  # latest also 256 = 0 confirmations

        with patch("sardis_api.services.onchain_verification.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = [mock_receipt_resp, mock_block_resp]
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await verify_usdc_transfer(
                tx_hash=TX_HASH,
                expected_recipient=MERCHANT_ADDR,
                expected_amount=Decimal("10"),
                chain="base",
                min_confirmations=1,
            )
            assert result.verified is False
            assert "confirmations" in (result.error or "").lower()
