"""Tests for Sardis AutoGPT blocks using SardisClient simulation mode."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from sardis_autogpt.blocks import (
    BLOCKS,
    SardisBalanceBlock,
    SardisBalanceBlockInput,
    SardisPayBlock,
    SardisPayBlockInput,
    SardisPolicyCheckBlock,
    SardisPolicyCheckBlockInput,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_payment_result(success: bool = True, tx_id: str = "tx_sim_001", amount: float = 10.0):
    result = MagicMock()
    result.success = success
    result.tx_id = tx_id
    result.amount = amount
    result.message = "Payment processed" if success else "Policy denied"
    return result


def _make_balance_result(balance: float = 500.0, remaining: float = 200.0):
    result = MagicMock()
    result.balance = balance
    result.remaining = remaining
    return result


# ---------------------------------------------------------------------------
# SardisPayBlock
# ---------------------------------------------------------------------------

class TestSardisPayBlock:
    def test_successful_payment(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result(success=True, tx_id="tx_abc")

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="wallet_123",
                amount=25.0,
                merchant="acme-corp",
                purpose="SaaS subscription",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert len(outputs) == 1
        out = outputs[0]
        assert out.status == "APPROVED"
        assert out.tx_id == "tx_abc"
        assert out.amount == 10.0
        assert out.merchant == "acme-corp"

    def test_blocked_payment(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result(success=False, tx_id="")

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="wallet_123",
                amount=9999.0,
                merchant="risky-merchant",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert len(outputs) == 1
        assert outputs[0].status == "BLOCKED"

    def test_missing_wallet_id(self):
        with patch("sardis_autogpt.blocks.SardisClient"), \
             patch("sardis_autogpt.blocks.os.getenv", return_value=None):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="",
                amount=10.0,
                merchant="test-merchant",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert len(outputs) == 1
        assert outputs[0].status == "ERROR"
        assert "wallet" in outputs[0].message.lower()

    def test_env_var_wallet_id(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result()

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client), \
             patch("sardis_autogpt.blocks.os.getenv", side_effect=lambda k: "env_wallet" if k == "SARDIS_WALLET_ID" else None):
            input_data = SardisPayBlockInput(amount=10.0, merchant="test")
            outputs = list(SardisPayBlock.run(input_data))

        mock_client.payments.send.assert_called_once()
        assert outputs[0].status == "APPROVED"


# ---------------------------------------------------------------------------
# SardisBalanceBlock
# ---------------------------------------------------------------------------

class TestSardisBalanceBlock:
    def test_returns_balance(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(balance=1000.0, remaining=400.0)

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisBalanceBlockInput(
                api_key="sk_test",
                wallet_id="wallet_123",
                token="USDC",
            )
            outputs = list(SardisBalanceBlock.run(input_data))

        assert len(outputs) == 1
        out = outputs[0]
        assert out.balance == 1000.0
        assert out.remaining == 400.0
        assert out.token == "USDC"

    def test_missing_wallet_id_returns_zeros(self):
        with patch("sardis_autogpt.blocks.SardisClient"), \
             patch("sardis_autogpt.blocks.os.getenv", return_value=None):
            input_data = SardisBalanceBlockInput(wallet_id="", token="USDC")
            outputs = list(SardisBalanceBlock.run(input_data))

        assert len(outputs) == 1
        assert outputs[0].balance == 0
        assert outputs[0].remaining == 0
        assert outputs[0].token == "USDC"

    def test_token_passed_to_client(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result()

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisBalanceBlockInput(
                api_key="sk_test",
                wallet_id="wallet_123",
                token="EURC",
            )
            list(SardisBalanceBlock.run(input_data))

        mock_client.wallets.get_balance.assert_called_once_with("wallet_123", token="EURC")


# ---------------------------------------------------------------------------
# SardisPolicyCheckBlock
# ---------------------------------------------------------------------------

class TestSardisPolicyCheckBlock:
    def test_allowed_when_within_limits(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(balance=500.0, remaining=300.0)

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPolicyCheckBlockInput(
                api_key="sk_test",
                wallet_id="wallet_123",
                amount=50.0,
                merchant="acme",
            )
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        assert len(outputs) == 1
        assert outputs[0].allowed is True
        assert "would be allowed" in outputs[0].reason

    def test_blocked_when_exceeds_remaining(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(balance=500.0, remaining=30.0)

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPolicyCheckBlockInput(
                api_key="sk_test",
                wallet_id="wallet_123",
                amount=100.0,
                merchant="acme",
            )
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        assert outputs[0].allowed is False
        assert "remaining limit" in outputs[0].reason

    def test_blocked_when_exceeds_balance(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(balance=20.0, remaining=5000.0)

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPolicyCheckBlockInput(
                api_key="sk_test",
                wallet_id="wallet_123",
                amount=100.0,
                merchant="acme",
            )
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        assert outputs[0].allowed is False
        assert "balance" in outputs[0].reason

    def test_missing_wallet_id(self):
        with patch("sardis_autogpt.blocks.SardisClient"), \
             patch("sardis_autogpt.blocks.os.getenv", return_value=None):
            input_data = SardisPolicyCheckBlockInput(wallet_id="", amount=10.0, merchant="test")
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        assert outputs[0].allowed is False
        assert "wallet" in outputs[0].reason.lower()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestBlockRegistry:
    def test_blocks_list_has_all_three(self):
        assert len(BLOCKS) == 3
        ids = {b.id for b in BLOCKS}
        assert "sardis-pay-block" in ids
        assert "sardis-balance-block" in ids
        assert "sardis-policy-check-block" in ids

    def test_each_block_has_required_attrs(self):
        for block_cls in BLOCKS:
            assert hasattr(block_cls, "id")
            assert hasattr(block_cls, "name")
            assert hasattr(block_cls, "description")
            assert hasattr(block_cls, "input_schema")
            assert hasattr(block_cls, "output_schema")
            assert hasattr(block_cls, "run")
            assert callable(block_cls.run)
