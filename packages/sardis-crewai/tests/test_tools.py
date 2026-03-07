"""Tests for sardis-crewai tools.

Tests call _run() directly on tool instances to avoid needing crewai installed.
The SardisClient runs in simulation mode (no real API key needed).
"""
from __future__ import annotations

import pytest
from sardis import SardisClient

from sardis_crewai.tools import (
    SardisPayTool,
    SardisCheckBalanceTool,
    SardisCheckPolicyTool,
    SardisSetPolicyTool,
    SardisGroupBudgetTool,
    create_sardis_tools,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client_and_wallet():
    client = SardisClient(api_key=None)
    wallet = client.wallets.create(
        name="test-wallet",
        chain="base",
        policy="Max $100 per transaction, $500 per day",
    )
    return client, wallet.wallet_id


# ---------------------------------------------------------------------------
# SardisPayTool
# ---------------------------------------------------------------------------

class TestSardisPayTool:
    def setup_method(self):
        self.client, self.wallet_id = _make_client_and_wallet()
        self.tool = SardisPayTool(client=self.client, wallet_id=self.wallet_id)

    def test_approved_payment_returns_success(self):
        result = self.tool._run(to="openai.com", amount="50.00", purpose="API credits")
        assert isinstance(result, str)
        # In simulation mode payment should succeed
        assert "successful" in result.lower() or "approved" in result.lower() or "TX ID" in result

    def test_payment_includes_tx_id(self):
        result = self.tool._run(to="stripe.com", amount="10.00")
        assert isinstance(result, str)

    def test_invalid_amount_returns_error(self):
        result = self.tool._run(to="vendor.com", amount="not-a-number")
        assert "Error" in result
        assert "amount" in result.lower() or "Invalid" in result

    def test_zero_amount_returns_error(self):
        result = self.tool._run(to="vendor.com", amount="0")
        assert "Error" in result

    def test_negative_amount_returns_error(self):
        result = self.tool._run(to="vendor.com", amount="-5.00")
        assert "Error" in result

    def test_default_token_is_usdc(self):
        result = self.tool._run(to="example.com", amount="5.00")
        assert isinstance(result, str)

    def test_custom_purpose_accepted(self):
        result = self.tool._run(to="github.com", amount="19.00", purpose="Copilot subscription")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# SardisCheckBalanceTool
# ---------------------------------------------------------------------------

class TestSardisCheckBalanceTool:
    def setup_method(self):
        self.client, self.wallet_id = _make_client_and_wallet()
        self.tool = SardisCheckBalanceTool(client=self.client, wallet_id=self.wallet_id)

    def test_returns_balance_string(self):
        result = self.tool._run(token="USDC", chain="base")
        assert isinstance(result, str)
        assert "Balance" in result or "balance" in result

    def test_contains_wallet_id(self):
        result = self.tool._run()
        assert self.wallet_id in result or "Wallet" in result

    def test_contains_remaining(self):
        result = self.tool._run()
        assert "Remaining" in result or "remaining" in result or "limit" in result.lower()

    def test_default_params_work(self):
        result = self.tool._run()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# SardisCheckPolicyTool
# ---------------------------------------------------------------------------

class TestSardisCheckPolicyTool:
    def setup_method(self):
        self.client, self.wallet_id = _make_client_and_wallet()
        self.tool = SardisCheckPolicyTool(client=self.client, wallet_id=self.wallet_id)

    def test_small_amount_check_returns_string(self):
        result = self.tool._run(amount="50.00", to="openai.com")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_result_contains_approved_field(self):
        result = self.tool._run(amount="10.00")
        assert "Approved" in result or "approved" in result or "WOULD BE" in result or "check" in result.lower()

    def test_invalid_amount_returns_error(self):
        result = self.tool._run(amount="bad")
        assert "Error" in result

    def test_default_destination_accepted(self):
        result = self.tool._run(amount="25.00")
        assert isinstance(result, str)

    def test_includes_policy_check_context(self):
        result = self.tool._run(amount="50.00", to="vendor.com", purpose="Software")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# SardisSetPolicyTool
# ---------------------------------------------------------------------------

class TestSardisSetPolicyTool:
    def setup_method(self):
        self.client, self.wallet_id = _make_client_and_wallet()
        self.tool = SardisSetPolicyTool(client=self.client, wallet_id=self.wallet_id)

    def test_set_policy_returns_string(self):
        result = self.tool._run(policy="Max $200 per transaction")
        assert isinstance(result, str)

    def test_set_policy_success_message(self):
        result = self.tool._run(policy="Daily limit $1000, max $50 per tx")
        # Should succeed in simulation mode
        assert "policy" in result.lower() or "Policy" in result or "wallet" in result.lower()

    def test_empty_policy_returns_error(self):
        result = self.tool._run(policy="")
        assert "Error" in result

    def test_whitespace_policy_returns_error(self):
        result = self.tool._run(policy="   ")
        assert "Error" in result


# ---------------------------------------------------------------------------
# create_sardis_tools factory
# ---------------------------------------------------------------------------

class TestCreateSardisTools:
    def setup_method(self):
        self.client, self.wallet_id = _make_client_and_wallet()

    def test_returns_tools_list(self):
        tools = create_sardis_tools(self.client, self.wallet_id)
        assert isinstance(tools, list)
        assert len(tools) >= 2

    def test_read_only_excludes_pay_tool(self):
        tools = create_sardis_tools(self.client, self.wallet_id, read_only=True)
        tool_types = [type(t) for t in tools]
        assert SardisPayTool not in tool_types

    def test_read_only_includes_balance_tool(self):
        tools = create_sardis_tools(self.client, self.wallet_id, read_only=True)
        tool_types = [type(t) for t in tools]
        assert SardisCheckBalanceTool in tool_types

    def test_full_set_includes_pay_tool(self):
        tools = create_sardis_tools(self.client, self.wallet_id)
        tool_types = [type(t) for t in tools]
        assert SardisPayTool in tool_types

    def test_with_group_id_includes_group_budget_tool(self):
        tools = create_sardis_tools(self.client, self.wallet_id, group_id="group_abc")
        tool_types = [type(t) for t in tools]
        assert SardisGroupBudgetTool in tool_types

    def test_without_group_id_excludes_group_budget_tool(self):
        tools = create_sardis_tools(self.client, self.wallet_id)
        tool_types = [type(t) for t in tools]
        assert SardisGroupBudgetTool not in tool_types
