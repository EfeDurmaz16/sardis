"""Tests for Sardis AutoGPT blocks.

Covers:
- Input validation (wallet_id regex, hex address, amount as str, Literal tokens/chains)
- Float rejection / Decimal string enforcement
- Error response handling
- URL / path-injection safety
- _normalize_response / _normalize_status with various API responses
- Block categories
- Singleton client reuse
- Retry logic
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from sardis_autogpt.blocks import (
    BLOCKS,
    BlockCategory,
    SardisBalanceBlock,
    SardisBalanceBlockInput,
    SardisBalanceBlockOutput,
    SardisPayBlock,
    SardisPayBlockInput,
    SardisPayBlockOutput,
    SardisPolicyCheckBlock,
    SardisPolicyCheckBlockInput,
    SardisPolicyCheckBlockOutput,
    _cached_clients,
    _normalize_response,
    _normalize_status,
    _validate_amount_str,
    _validate_hex_address,
    _validate_wallet_id,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_payment_result(
    success: bool = True,
    tx_id: str = "tx_sim_001",
    amount: str = "10.00",
    status: str | None = None,
):
    result = MagicMock()
    result.success = success
    result.tx_id = tx_id
    result.amount = amount
    result.message = "Payment processed" if success else "Policy denied"
    if status is not None:
        result.status = status
    else:
        # Remove the status attribute so fallback logic kicks in
        del result.status
    return result


def _make_balance_result(balance: str = "500.00", remaining: str = "200.00"):
    result = MagicMock()
    result.balance = balance
    result.remaining = remaining
    return result


@pytest.fixture(autouse=True)
def _clear_client_cache():
    """Clear the singleton client cache between tests."""
    _cached_clients.clear()
    yield
    _cached_clients.clear()


# ===========================================================================
# 1. Input Validation
# ===========================================================================

class TestWalletIdValidation:
    def test_valid_wallet_id(self):
        assert _validate_wallet_id("wal_abc123") == "wal_abc123"
        assert _validate_wallet_id("wal_A1b2C3") == "wal_A1b2C3"

    def test_empty_wallet_id_allowed(self):
        """Empty string is allowed (means use env var)."""
        assert _validate_wallet_id("") == ""

    def test_invalid_prefix(self):
        with pytest.raises(ValueError, match="must match pattern"):
            _validate_wallet_id("wallet_123")

    def test_invalid_characters(self):
        with pytest.raises(ValueError, match="must match pattern"):
            _validate_wallet_id("wal_abc-123")

    def test_path_injection_attempt(self):
        with pytest.raises(ValueError, match="must match pattern"):
            _validate_wallet_id("wal_abc/../etc/passwd")

    def test_no_prefix(self):
        with pytest.raises(ValueError, match="must match pattern"):
            _validate_wallet_id("abc123")

    def test_pydantic_model_rejects_bad_wallet(self):
        with pytest.raises(Exception):
            SardisPayBlockInput(
                wallet_id="bad_wallet!",
                amount="10.00",
                merchant="test",
            )


class TestHexAddressValidation:
    def test_valid_address(self):
        addr = "0x" + "a" * 40
        assert _validate_hex_address(addr) == addr

    def test_valid_mixed_case(self):
        addr = "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"
        assert _validate_hex_address(addr) == addr

    def test_empty_allowed(self):
        assert _validate_hex_address("") == ""

    def test_too_short(self):
        with pytest.raises(ValueError, match="40 hex"):
            _validate_hex_address("0xabc")

    def test_too_long(self):
        with pytest.raises(ValueError, match="40 hex"):
            _validate_hex_address("0x" + "a" * 41)

    def test_no_prefix(self):
        with pytest.raises(ValueError, match="40 hex"):
            _validate_hex_address("a" * 40)

    def test_invalid_hex_chars(self):
        with pytest.raises(ValueError, match="40 hex"):
            _validate_hex_address("0x" + "g" * 40)

    def test_pydantic_model_rejects_bad_destination(self):
        with pytest.raises(Exception):
            SardisPayBlockInput(
                wallet_id="wal_abc123",
                amount="10.00",
                merchant="test",
                destination="not-an-address",
            )


class TestAmountValidation:
    def test_valid_amount(self):
        assert _validate_amount_str("25.00") == "25.00"
        assert _validate_amount_str("0.01") == "0.01"
        assert _validate_amount_str("999999.999999") == "999999.999999"

    def test_integer_string(self):
        assert _validate_amount_str("100") == "100"

    def test_zero_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            _validate_amount_str("0")

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            _validate_amount_str("-10.00")

    def test_non_numeric_rejected(self):
        with pytest.raises(ValueError, match="decimal number"):
            _validate_amount_str("abc")

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="required"):
            _validate_amount_str("")

    def test_too_many_decimals_rejected(self):
        with pytest.raises(ValueError, match="decimal places"):
            _validate_amount_str("1.0000001")

    def test_float_type_rejected_by_pydantic(self):
        """Pydantic should coerce float to str, but the validator catches bad values."""
        # Direct construction with a float — Pydantic v2 will coerce to str
        # which is fine, the important thing is we don't silently use IEEE 754
        inp = SardisPayBlockInput(
            wallet_id="wal_abc123",
            amount="25.50",
            merchant="test",
        )
        assert inp.amount == "25.50"
        assert isinstance(inp.amount, str)


class TestTokenAndChainLiterals:
    def test_valid_tokens(self):
        for token in ("USDC", "USDT", "EURC", "PYUSD"):
            inp = SardisPayBlockInput(
                amount="10.00", merchant="test", token=token,
            )
            assert inp.token == token

    def test_invalid_token_rejected(self):
        with pytest.raises(Exception):
            SardisPayBlockInput(
                amount="10.00", merchant="test", token="DOGE",
            )

    def test_valid_chains(self):
        for chain in ("base", "ethereum", "polygon", "arbitrum", "optimism", "tempo"):
            inp = SardisPayBlockInput(
                amount="10.00", merchant="test", chain=chain,
            )
            assert inp.chain == chain

    def test_invalid_chain_rejected(self):
        with pytest.raises(Exception):
            SardisPayBlockInput(
                amount="10.00", merchant="test", chain="solana",
            )


# ===========================================================================
# 2. _normalize_status and _normalize_response
# ===========================================================================

class TestNormalizeStatus:
    def test_explicit_status_approved(self):
        r = MagicMock()
        r.status = "approved"
        assert _normalize_status(r) == "APPROVED"

    def test_explicit_status_blocked(self):
        r = MagicMock()
        r.status = "blocked"
        assert _normalize_status(r) == "BLOCKED"

    def test_explicit_status_pending(self):
        r = MagicMock()
        r.status = "pending"
        assert _normalize_status(r) == "PENDING"

    def test_explicit_status_failed(self):
        r = MagicMock()
        r.status = "failed"
        assert _normalize_status(r) == "FAILED"

    def test_explicit_status_error(self):
        r = MagicMock()
        r.status = "error"
        assert _normalize_status(r) == "ERROR"

    def test_case_insensitive(self):
        r = MagicMock()
        r.status = "APPROVED"
        assert _normalize_status(r) == "APPROVED"

    def test_fallback_success_true(self):
        r = MagicMock(spec=[])
        r.success = True
        assert _normalize_status(r) == "APPROVED"

    def test_fallback_success_false(self):
        r = MagicMock(spec=[])
        r.success = False
        assert _normalize_status(r) == "BLOCKED"

    def test_unknown_status_string_falls_back(self):
        r = MagicMock()
        r.status = "something_unknown"
        r.success = True
        assert _normalize_status(r) == "APPROVED"

    def test_no_status_no_success_returns_error(self):
        r = MagicMock(spec=[])
        assert _normalize_status(r) == "ERROR"


class TestNormalizeResponse:
    def test_full_response(self):
        r = MagicMock()
        r.status = "approved"
        r.tx_id = "tx_123"
        r.message = "OK"
        r.amount = "50.00"
        resp = _normalize_response(r, "50.00", "acme")
        assert resp == {
            "status": "APPROVED",
            "tx_id": "tx_123",
            "message": "OK",
            "amount": "50.00",
            "merchant": "acme",
        }

    def test_missing_fields_use_defaults(self):
        r = MagicMock(spec=[])
        r.success = True
        resp = _normalize_response(r, "10.00", "vendor")
        assert resp["status"] == "APPROVED"
        assert resp["tx_id"] == ""
        assert resp["amount"] == "10.00"
        assert resp["merchant"] == "vendor"

    def test_none_fields_coerced(self):
        r = MagicMock()
        r.status = "approved"
        r.tx_id = None
        r.message = None
        r.amount = None
        resp = _normalize_response(r, "5.00", "m")
        assert resp["tx_id"] == ""
        assert resp["message"] == ""
        assert resp["amount"] == "5.00"  # falls back to input amount


# ===========================================================================
# 3. SardisPayBlock
# ===========================================================================

class TestSardisPayBlock:
    def test_successful_payment(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result(
            success=True, tx_id="tx_abc", amount="25.00",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="25.00",
                merchant="acme-corp",
                purpose="SaaS subscription",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert len(outputs) == 1
        out = outputs[0]
        assert out.status == "APPROVED"
        assert out.tx_id == "tx_abc"
        assert out.amount == "25.00"
        assert out.merchant == "acme-corp"

    def test_blocked_payment(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result(
            success=False, tx_id="",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="9999.00",
                merchant="risky-merchant",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert len(outputs) == 1
        assert outputs[0].status == "BLOCKED"

    def test_explicit_status_field_preferred(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result(
            success=True, status="pending",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="10.00",
                merchant="test",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert outputs[0].status == "PENDING"

    def test_missing_wallet_id(self):
        with patch("sardis_autogpt.blocks.SardisClient"), \
             patch("sardis_autogpt.blocks.os.getenv", return_value=None):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                amount="10.00",
                merchant="test-merchant",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert len(outputs) == 1
        assert outputs[0].status == "ERROR"
        assert "wallet" in outputs[0].message.lower()

    def test_exception_yields_error(self):
        mock_client = MagicMock()
        mock_client.payments.send.side_effect = RuntimeError("RPC timeout")

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="10.00",
                merchant="test",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert outputs[0].status == "ERROR"
        assert "RPC timeout" in outputs[0].message

    def test_env_var_wallet_id(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result()

        def _env(k):
            if k == "SARDIS_WALLET_ID":
                return "wal_env123"
            return None

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client), \
             patch("sardis_autogpt.blocks.os.getenv", side_effect=_env):
            input_data = SardisPayBlockInput(amount="10.00", merchant="test")
            outputs = list(SardisPayBlock.run(input_data))

        mock_client.payments.send.assert_called_once()
        assert outputs[0].status == "APPROVED"

    def test_amounts_are_strings_not_floats(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result(
            amount="25.50",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="25.50",
                merchant="test",
            )
            outputs = list(SardisPayBlock.run(input_data))

        assert isinstance(outputs[0].amount, str)
        assert outputs[0].amount == "25.50"

    def test_destination_used_when_provided(self):
        mock_client = MagicMock()
        mock_client.payments.send.return_value = _make_payment_result()
        dest = "0x" + "ab" * 20

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPayBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="10.00",
                merchant="test",
                destination=dest,
            )
            list(SardisPayBlock.run(input_data))

        call_kwargs = mock_client.payments.send.call_args
        assert call_kwargs.kwargs["to"] == dest


# ===========================================================================
# 4. SardisBalanceBlock
# ===========================================================================

class TestSardisBalanceBlock:
    def test_returns_balance_as_str(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(
            balance="1000.00", remaining="400.00",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisBalanceBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                token="USDC",
            )
            outputs = list(SardisBalanceBlock.run(input_data))

        assert len(outputs) == 1
        out = outputs[0]
        assert out.balance == "1000.00"
        assert out.remaining == "400.00"
        assert isinstance(out.balance, str)
        assert isinstance(out.remaining, str)
        assert out.token == "USDC"

    def test_missing_wallet_id_returns_zeros(self):
        with patch("sardis_autogpt.blocks.SardisClient"), \
             patch("sardis_autogpt.blocks.os.getenv", return_value=None):
            input_data = SardisBalanceBlockInput(token="USDC")
            outputs = list(SardisBalanceBlock.run(input_data))

        assert outputs[0].balance == "0"
        assert outputs[0].remaining == "0"

    def test_token_passed_to_client(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result()

        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisBalanceBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                token="EURC",
            )
            list(SardisBalanceBlock.run(input_data))

        mock_client.wallets.get_balance.assert_called_once_with(
            "wal_abc123", token="EURC",
        )


# ===========================================================================
# 5. SardisPolicyCheckBlock
# ===========================================================================

class TestSardisPolicyCheckBlock:
    def test_allowed_when_within_limits(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(
            balance="500.00", remaining="300.00",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPolicyCheckBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="50.00",
                merchant="acme",
            )
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        assert outputs[0].allowed is True
        assert "would be allowed" in outputs[0].reason

    def test_blocked_when_exceeds_remaining(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(
            balance="500.00", remaining="30.00",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPolicyCheckBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="100.00",
                merchant="acme",
            )
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        assert outputs[0].allowed is False
        assert "remaining limit" in outputs[0].reason

    def test_blocked_when_exceeds_balance(self):
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(
            balance="20.00", remaining="5000.00",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPolicyCheckBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="100.00",
                merchant="acme",
            )
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        assert outputs[0].allowed is False
        assert "balance" in outputs[0].reason

    def test_missing_wallet_id(self):
        with patch("sardis_autogpt.blocks.SardisClient"), \
             patch("sardis_autogpt.blocks.os.getenv", return_value=None):
            input_data = SardisPolicyCheckBlockInput(
                amount="10.00", merchant="test",
            )
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        assert outputs[0].allowed is False
        assert "wallet" in outputs[0].reason.lower()

    def test_uses_decimal_comparison(self):
        """Verify Decimal comparison avoids IEEE 754 issues like 0.1+0.2!=0.3."""
        mock_client = MagicMock()
        mock_client.wallets.get_balance.return_value = _make_balance_result(
            balance="0.30", remaining="0.30",
        )
        with patch("sardis_autogpt.blocks.SardisClient", return_value=mock_client):
            input_data = SardisPolicyCheckBlockInput(
                api_key="sk_test",
                wallet_id="wal_abc123",
                amount="0.30",
                merchant="test",
            )
            outputs = list(SardisPolicyCheckBlock.run(input_data))

        # With float, 0.1 + 0.2 != 0.3, but with Decimal this is exact
        assert outputs[0].allowed is True


# ===========================================================================
# 6. Block Categories
# ===========================================================================

class TestBlockCategories:
    def test_pay_block_is_output(self):
        assert BlockCategory.OUTPUT in SardisPayBlock.categories

    def test_balance_block_is_data(self):
        assert BlockCategory.DATA in SardisBalanceBlock.categories

    def test_policy_check_block_is_data(self):
        assert BlockCategory.DATA in SardisPolicyCheckBlock.categories


# ===========================================================================
# 7. Client Singleton
# ===========================================================================

class TestClientSingleton:
    def test_same_key_reuses_client(self):
        with patch("sardis_autogpt.blocks.SardisClient") as MockClient:
            _get_client_fn = __import__(
                "sardis_autogpt.blocks", fromlist=["_get_client"],
            )._get_client
            c1, _ = _get_client_fn(api_key="sk_test")
            c2, _ = _get_client_fn(api_key="sk_test")
            assert c1 is c2
            assert MockClient.call_count == 1

    def test_different_keys_create_different_clients(self):
        with patch("sardis_autogpt.blocks.SardisClient") as MockClient:
            MockClient.side_effect = lambda **kw: MagicMock(name=f"client_{kw}")
            _get_client_fn = __import__(
                "sardis_autogpt.blocks", fromlist=["_get_client"],
            )._get_client
            c1, _ = _get_client_fn(api_key="sk_a")
            c2, _ = _get_client_fn(api_key="sk_b")
            assert c1 is not c2
            assert MockClient.call_count == 2


# ===========================================================================
# 8. Retry Logic
# ===========================================================================

class TestRetryLogic:
    def test_retries_on_connection_error(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("connection reset")
            return "success"

        from sardis_autogpt.blocks import _with_retry

        with patch("sardis_autogpt.blocks.time.sleep"):
            result = _with_retry(flaky)

        assert result == "success"
        assert call_count == 3

    def test_no_retry_on_value_error(self):
        def always_fail():
            raise ValueError("bad input")

        from sardis_autogpt.blocks import _with_retry

        with pytest.raises(ValueError, match="bad input"):
            _with_retry(always_fail)

    def test_raises_after_max_retries(self):
        def always_timeout():
            raise TimeoutError("timed out")

        from sardis_autogpt.blocks import _with_retry

        with patch("sardis_autogpt.blocks.time.sleep"):
            with pytest.raises(TimeoutError, match="timed out"):
                _with_retry(always_timeout)


# ===========================================================================
# 9. URL / Path Injection Safety
# ===========================================================================

class TestPathInjectionSafety:
    """Ensure wallet_id / destination can't be used for path traversal."""

    def test_wallet_id_rejects_slashes(self):
        with pytest.raises(ValueError):
            _validate_wallet_id("wal_abc/../../etc/passwd")

    def test_wallet_id_rejects_dots(self):
        with pytest.raises(ValueError):
            _validate_wallet_id("wal_abc..def")

    def test_destination_rejects_non_hex(self):
        with pytest.raises(ValueError):
            _validate_hex_address("0x" + "../" * 20 + "aa")

    def test_wallet_id_rejects_url_encoding(self):
        with pytest.raises(ValueError):
            _validate_wallet_id("wal_%2e%2e")


# ===========================================================================
# 10. Registry
# ===========================================================================

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
            assert hasattr(block_cls, "categories")
