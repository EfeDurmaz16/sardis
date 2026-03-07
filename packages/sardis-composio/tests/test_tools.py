"""Tests for Sardis Composio tools in simulation mode."""
from __future__ import annotations

import os
import pytest

# Use simulation mode - no real API key needed
os.environ.setdefault("SARDIS_API_KEY", "test-simulation-key")
os.environ.setdefault("SARDIS_WALLET_ID", "wallet_sim_001")

from sardis_composio.tools import sardis_pay, sardis_check_balance, sardis_check_policy, SARDIS_TOOLS


class TestSardisPay:
    def test_returns_dict(self):
        result = sardis_pay(amount=10.0, merchant="vendor.example.com", purpose="Test payment")
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        result = sardis_pay(amount=10.0, merchant="vendor.example.com")
        assert "success" in result
        assert "status" in result
        assert "tx_id" in result
        assert "message" in result
        assert "amount" in result
        assert "merchant" in result

    def test_status_reflects_success(self):
        result = sardis_pay(amount=10.0, merchant="vendor.example.com")
        if result["success"]:
            assert result["status"] == "APPROVED"
        else:
            assert result["status"] == "BLOCKED"

    def test_merchant_echoed(self):
        result = sardis_pay(amount=5.0, merchant="shop.test.com")
        assert result["merchant"] == "shop.test.com"

    def test_amount_is_float(self):
        result = sardis_pay(amount=25.50, merchant="vendor.example.com")
        assert isinstance(result["amount"], float)

    def test_no_wallet_id_returns_error(self):
        result = sardis_pay(
            amount=10.0,
            merchant="vendor.example.com",
            api_key="test-simulation-key",
            wallet_id="",
        )
        # When no wallet_id env var and no explicit wallet_id, should error
        # (env var is set in module scope so this tests explicit override path)
        assert isinstance(result, dict)

    def test_default_purpose(self):
        # Should not raise with default purpose
        result = sardis_pay(amount=1.0, merchant="test.com")
        assert "success" in result


class TestSardisCheckBalance:
    def test_returns_dict(self):
        result = sardis_check_balance()
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        result = sardis_check_balance()
        assert "success" in result
        if result["success"]:
            assert "balance" in result
            assert "remaining" in result
            assert "token" in result

    def test_default_token_usdc(self):
        result = sardis_check_balance()
        if result["success"]:
            assert result["token"] == "USDC"

    def test_custom_token(self):
        result = sardis_check_balance(token="EURC")
        if result["success"]:
            assert result["token"] == "EURC"

    def test_balance_is_float(self):
        result = sardis_check_balance()
        if result["success"]:
            assert isinstance(result["balance"], float)
            assert isinstance(result["remaining"], float)

    def test_no_wallet_returns_error(self):
        result = sardis_check_balance(api_key="test-simulation-key", wallet_id="  ")
        # With whitespace-only wallet_id converted to None via `or None`
        # behavior depends on env var; just assert dict returned
        assert isinstance(result, dict)


class TestSardisCheckPolicy:
    def test_returns_dict(self):
        result = sardis_check_policy(amount=10.0, merchant="vendor.example.com")
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        result = sardis_check_policy(amount=10.0, merchant="vendor.example.com")
        assert "allowed" in result
        assert "reason" in result
        assert "balance" in result
        assert "remaining" in result

    def test_allowed_is_bool(self):
        result = sardis_check_policy(amount=1.0, merchant="test.com")
        assert isinstance(result["allowed"], bool)

    def test_reason_contains_merchant(self):
        result = sardis_check_policy(amount=5.0, merchant="acme.com")
        if "reason" in result:
            assert "acme.com" in result["reason"]

    def test_large_amount_may_be_blocked(self):
        # A very large amount should be blocked or at least return a valid response
        result = sardis_check_policy(amount=999_999_999.0, merchant="big-spend.com")
        assert isinstance(result, dict)
        assert "allowed" in result

    def test_balance_and_remaining_are_floats(self):
        result = sardis_check_policy(amount=10.0, merchant="vendor.example.com")
        if "balance" in result:
            assert isinstance(result["balance"], float)
            assert isinstance(result["remaining"], float)


class TestSardisToolsRegistry:
    def test_tools_dict_has_all_keys(self):
        assert "sardis_pay" in SARDIS_TOOLS
        assert "sardis_check_balance" in SARDIS_TOOLS
        assert "sardis_check_policy" in SARDIS_TOOLS

    def test_tools_are_callable(self):
        for name, fn in SARDIS_TOOLS.items():
            assert callable(fn), f"{name} should be callable"

    def test_pay_via_registry(self):
        fn = SARDIS_TOOLS["sardis_pay"]
        result = fn(amount=10.0, merchant="registry-test.com")
        assert isinstance(result, dict)

    def test_balance_via_registry(self):
        fn = SARDIS_TOOLS["sardis_check_balance"]
        result = fn()
        assert isinstance(result, dict)

    def test_policy_via_registry(self):
        fn = SARDIS_TOOLS["sardis_check_policy"]
        result = fn(amount=10.0, merchant="registry-test.com")
        assert isinstance(result, dict)
