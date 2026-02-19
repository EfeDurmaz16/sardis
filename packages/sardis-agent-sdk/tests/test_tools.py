"""Tests for Sardis Agent SDK tool definitions and handlers."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from sardis import SardisClient

from sardis_agent_sdk import (
    SardisToolkit,
    SardisToolHandler,
    ALL_TOOLS,
    READ_ONLY_TOOLS,
    TOOL_NAMES,
    SARDIS_PAY_TOOL,
    SARDIS_CHECK_BALANCE_TOOL,
    SARDIS_CHECK_POLICY_TOOL,
    SARDIS_SET_POLICY_TOOL,
    SARDIS_LIST_TRANSACTIONS_TOOL,
    SARDIS_CREATE_HOLD_TOOL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sardis_client() -> SardisClient:
    return SardisClient(api_key="sk_test_demo")


@pytest.fixture()
def wallet(sardis_client: SardisClient):
    return sardis_client.wallets.create(
        name="test-agent",
        chain="base",
        initial_balance=1000,
        limit_per_tx=100,
        limit_total=5000,
    )


@pytest.fixture()
def handler(sardis_client: SardisClient, wallet) -> SardisToolHandler:
    return SardisToolHandler(client=sardis_client, wallet_id=wallet.id)


@pytest.fixture()
def toolkit(sardis_client: SardisClient, wallet) -> SardisToolkit:
    return SardisToolkit(client=sardis_client, wallet_id=wallet.id)


# ---------------------------------------------------------------------------
# Tool definition tests
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    """Verify tool definitions match the Anthropic tool_use schema."""

    def test_all_tools_count(self):
        assert len(ALL_TOOLS) == 6

    def test_read_only_tools_count(self):
        assert len(READ_ONLY_TOOLS) == 3

    def test_tool_names_set(self):
        assert TOOL_NAMES == {
            "sardis_pay",
            "sardis_check_balance",
            "sardis_check_policy",
            "sardis_set_policy",
            "sardis_list_transactions",
            "sardis_create_hold",
        }

    @pytest.mark.parametrize("tool", ALL_TOOLS)
    def test_tool_has_required_fields(self, tool: dict):
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
        assert "properties" in tool["input_schema"]

    def test_pay_tool_required_fields(self):
        assert SARDIS_PAY_TOOL["input_schema"]["required"] == ["to", "amount"]

    def test_check_balance_no_required_fields(self):
        assert SARDIS_CHECK_BALANCE_TOOL["input_schema"]["required"] == []

    def test_check_policy_required_fields(self):
        assert SARDIS_CHECK_POLICY_TOOL["input_schema"]["required"] == ["to", "amount"]

    def test_set_policy_required_fields(self):
        assert SARDIS_SET_POLICY_TOOL["input_schema"]["required"] == ["policy"]

    def test_list_transactions_no_required_fields(self):
        assert SARDIS_LIST_TRANSACTIONS_TOOL["input_schema"]["required"] == []

    def test_create_hold_required_fields(self):
        assert SARDIS_CREATE_HOLD_TOOL["input_schema"]["required"] == ["to", "amount"]


# ---------------------------------------------------------------------------
# Handler tests
# ---------------------------------------------------------------------------


class TestSardisToolHandler:
    """Test individual tool handlers."""

    def test_handle_pay_success(self, handler: SardisToolHandler):
        result = handler.handle("sardis_pay", {
            "to": "openai.com",
            "amount": "25.00",
            "token": "USDC",
            "purpose": "API credits",
        })
        assert result["status"] == "success"
        assert result["result"]["success"] is True
        assert result["result"]["amount"] == "25.00"
        assert result["result"]["to"] == "openai.com"

    def test_handle_pay_exceeds_limit(self, handler: SardisToolHandler):
        result = handler.handle("sardis_pay", {
            "to": "openai.com",
            "amount": "500.00",
        })
        assert result["status"] == "success"
        # Payment rejected by policy (exceeds per-tx limit of 100)
        assert result["result"]["success"] is False
        assert result["result"]["status"] == "rejected"

    def test_handle_check_balance(self, handler: SardisToolHandler):
        result = handler.handle("sardis_check_balance", {})
        assert result["status"] == "success"
        assert float(result["result"]["balance"]) == 1000.0
        assert float(result["result"]["limit_per_tx"]) == 100.0
        assert float(result["result"]["limit_total"]) == 5000.0

    def test_handle_check_policy_approved(self, handler: SardisToolHandler):
        result = handler.handle("sardis_check_policy", {
            "to": "openai.com",
            "amount": "50.00",
        })
        assert result["status"] == "success"
        assert result["result"]["approved"] is True

    def test_handle_check_policy_rejected(self, handler: SardisToolHandler):
        result = handler.handle("sardis_check_policy", {
            "to": "openai.com",
            "amount": "200.00",
        })
        assert result["status"] == "success"
        assert result["result"]["approved"] is False

    def test_handle_set_policy(self, handler: SardisToolHandler, wallet):
        result = handler.handle("sardis_set_policy", {
            "policy": "Max $50 per transaction, daily limit $200",
        })
        assert result["status"] == "success"
        assert result["result"]["limit_per_tx"] == "50"
        assert result["result"]["limit_total"] == "200"

    def test_handle_set_policy_with_overrides(self, handler: SardisToolHandler):
        result = handler.handle("sardis_set_policy", {
            "policy": "Max $50 per transaction",
            "max_per_tx": 75,
            "max_total": 300,
        })
        assert result["status"] == "success"
        # Explicit overrides win over natural language parse
        assert result["result"]["limit_per_tx"] == "75"
        assert result["result"]["limit_total"] == "300"

    def test_handle_list_transactions_empty(self, handler: SardisToolHandler):
        result = handler.handle("sardis_list_transactions", {"limit": 5})
        assert result["status"] == "success"
        assert result["result"]["count"] == 0
        assert result["result"]["transactions"] == []

    def test_handle_list_transactions_after_payment(self, handler: SardisToolHandler):
        handler.handle("sardis_pay", {"to": "openai.com", "amount": "10.00"})
        result = handler.handle("sardis_list_transactions", {})
        assert result["status"] == "success"
        assert result["result"]["count"] == 1
        tx = result["result"]["transactions"][0]
        assert tx["to"] == "openai.com"
        assert tx["amount"] == "10.00"

    def test_handle_create_hold(self, handler: SardisToolHandler):
        result = handler.handle("sardis_create_hold", {
            "to": "hotel.com",
            "amount": "50.00",
            "purpose": "Room deposit",
        })
        assert result["status"] == "success"
        assert result["result"]["status"] == "active"
        assert result["result"]["amount"] == "50.00"
        assert result["result"]["hold_id"] is not None

    def test_handle_create_hold_insufficient_funds(
        self, sardis_client: SardisClient
    ):
        wallet = sardis_client.wallets.create(
            name="low-balance",
            initial_balance=10,
            limit_per_tx=100,
            limit_total=1000,
        )
        handler = SardisToolHandler(client=sardis_client, wallet_id=wallet.id)
        result = handler.handle("sardis_create_hold", {
            "to": "hotel.com",
            "amount": "500.00",
        })
        assert result["status"] == "success"
        assert result["result"]["status"] == "rejected"

    def test_handle_unknown_tool(self, handler: SardisToolHandler):
        with pytest.raises(ValueError, match="Unknown tool"):
            handler.handle("nonexistent_tool", {})

    def test_process_tool_use_block(self, handler: SardisToolHandler):
        block = {
            "type": "tool_use",
            "id": "toolu_test123",
            "name": "sardis_check_balance",
            "input": {},
        }
        result = handler.process_tool_use_block(block)
        assert result["type"] == "tool_result"
        assert result["tool_use_id"] == "toolu_test123"
        assert "is_error" not in result
        content = json.loads(result["content"])
        assert float(content["balance"]) == 1000.0

    def test_process_tool_use_block_error(self, handler: SardisToolHandler):
        block = {
            "type": "tool_use",
            "id": "toolu_err456",
            "name": "sardis_pay",
            "input": {"to": "x", "amount": "not_a_number"},
        }
        result = handler.process_tool_use_block(block)
        assert result["type"] == "tool_result"
        assert result["tool_use_id"] == "toolu_err456"
        assert result["is_error"] is True

    def test_amount_parsing_strips_dollar_sign(self, handler: SardisToolHandler):
        result = handler.handle("sardis_pay", {
            "to": "openai.com",
            "amount": "$25.00",
        })
        assert result["status"] == "success"
        assert result["result"]["amount"] == "25.00"

    def test_amount_parsing_handles_commas(self, handler: SardisToolHandler):
        result = handler.handle("sardis_check_policy", {
            "to": "openai.com",
            "amount": "1,000.00",
        })
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Toolkit tests
# ---------------------------------------------------------------------------


class TestSardisToolkit:
    """Test the high-level SardisToolkit."""

    def test_get_tools_returns_all(self, toolkit: SardisToolkit):
        tools = toolkit.get_tools()
        assert len(tools) == 6

    def test_get_tools_read_only(self, sardis_client: SardisClient, wallet):
        toolkit = SardisToolkit(
            client=sardis_client,
            wallet_id=wallet.id,
            read_only=True,
        )
        tools = toolkit.get_tools()
        assert len(tools) == 3
        names = {t["name"] for t in tools}
        assert "sardis_pay" not in names
        assert "sardis_check_balance" in names

    def test_handle_tool_call_dict(self, toolkit: SardisToolkit):
        block = {
            "type": "tool_use",
            "id": "toolu_abc",
            "name": "sardis_check_balance",
            "input": {},
        }
        result = toolkit.handle_tool_call(block)
        assert result["type"] == "tool_result"
        assert result["tool_use_id"] == "toolu_abc"

    def test_handle_tool_call_object(self, toolkit: SardisToolkit):
        """Test with an object that mimics an Anthropic ToolUseBlock."""

        class FakeToolUseBlock:
            type = "tool_use"
            id = "toolu_obj789"
            name = "sardis_check_balance"
            input = {}

        result = toolkit.handle_tool_call(FakeToolUseBlock())
        assert result["type"] == "tool_result"
        assert result["tool_use_id"] == "toolu_obj789"

    def test_toolkit_returns_fresh_tool_copies(self, toolkit: SardisToolkit):
        """get_tools() should return copies, not references to module-level dicts."""
        tools1 = toolkit.get_tools()
        tools2 = toolkit.get_tools()
        assert tools1 is not tools2
