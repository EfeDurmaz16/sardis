"""
Tests for LangChain Integration
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sardis_sdk import SardisClient
from sardis_sdk.integrations.langchain import (
    SardisTool,
    SardisPolicyCheckTool,
    SardisBalanceCheckTool,
    create_sardis_tools,
)


class TestSardisTool:
    """Tests for SardisTool."""

    def test_tool_has_correct_name(self, api_key, base_url):
        """Should have correct tool name."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisTool(client=client, wallet_id="wallet_123")

        assert tool.name == "sardis_pay"

    def test_tool_has_description(self, api_key, base_url):
        """Should have description."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisTool(client=client, wallet_id="wallet_123")

        assert len(tool.description) > 0
        assert "payment" in tool.description.lower()

    def test_tool_has_schema(self, api_key, base_url):
        """Should have args schema."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisTool(client=client, wallet_id="wallet_123")

        assert tool.args_schema is not None

    async def test_execute_payment_successfully(self, api_key, base_url, httpx_mock, mock_responses):
        """Should execute payment successfully."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/mandates/execute",
            method="POST",
            json={
                "payment_id": "pay_abc123",
                "status": "completed",
                "tx_hash": "0xabcdef",
                "chain": "base_sepolia",
                "audit_anchor": "anchor_789",
            },
        )

        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisTool(client=client, wallet_id="wallet_123", agent_id="agent_456")

        result = await tool._arun(
            amount=50,
            merchant="OpenAI",
            purpose="API credits",
        )

        assert "APPROVED" in result
        assert "OpenAI" in result
        assert "$50" in result

    async def test_return_error_when_no_client(self):
        """Should return error when client not initialized."""
        tool = SardisTool(wallet_id="wallet_123")

        result = await tool._arun(amount=50, merchant="Test")

        assert "Error" in result
        assert "not initialized" in result

    async def test_return_error_when_no_wallet_id(self, api_key, base_url):
        """Should return error when no wallet ID."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisTool(client=client)

        result = await tool._arun(amount=50, merchant="Test")

        assert "Error" in result
        assert "wallet ID" in result

    async def test_return_error_for_negative_amount(self, api_key, base_url):
        """Should return error for negative amount."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisTool(client=client, wallet_id="wallet_123")

        result = await tool._arun(amount=-50, merchant="Test")

        assert "Error" in result
        assert "positive" in result

    async def test_handle_policy_violation(self, api_key, base_url, httpx_mock):
        """Should handle policy violation."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/mandates/execute",
            method="POST",
            status_code=403,
            json={"error": "Payment blocked by policy: Amount exceeds limit"},
        )

        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisTool(client=client, wallet_id="wallet_123")

        result = await tool._arun(amount=10000, merchant="Expensive")

        assert "BLOCKED" in result


class TestSardisPolicyCheckTool:
    """Tests for SardisPolicyCheckTool."""

    def test_tool_has_correct_name(self, api_key, base_url):
        """Should have correct tool name."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisPolicyCheckTool(client=client, wallet_id="wallet_123")

        assert tool.name == "sardis_check_policy"

    async def test_check_policy_allowed(self, api_key, base_url, httpx_mock, mock_responses):
        """Should return allowed when policy passes."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/wallet_123",
            method="GET",
            json=mock_responses["wallet"],
        )

        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisPolicyCheckTool(client=client, wallet_id="wallet_123")

        result = await tool._arun(merchant="OpenAI", amount=50)

        assert "ALLOWED" in result

    async def test_check_policy_blocked(self, api_key, base_url, httpx_mock):
        """Should return blocked when amount exceeds limit."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/wallet_123",
            method="GET",
            json={
                "wallet_id": "wallet_123",
                "agent_id": "agent_001",
                "mpc_provider": "turnkey",
                "addresses": {},
                "currency": "USDC",
                "limit_per_tx": "100.00",
                "limit_total": "1000.00",
                "is_active": True,
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z",
            },
        )

        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisPolicyCheckTool(client=client, wallet_id="wallet_123")

        result = await tool._arun(merchant="Expensive", amount=500)

        assert "BLOCKED" in result


class TestSardisBalanceCheckTool:
    """Tests for SardisBalanceCheckTool."""

    def test_tool_has_correct_name(self, api_key, base_url):
        """Should have correct tool name."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisBalanceCheckTool(client=client, wallet_id="wallet_123")

        assert tool.name == "sardis_check_balance"

    async def test_check_balance_successfully(self, api_key, base_url, httpx_mock, mock_responses):
        """Should check balance successfully."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/wallet_123/balance?chain=base_sepolia&token=USDC",
            method="GET",
            json=mock_responses["balance"],
        )

        client = SardisClient(api_key=api_key, base_url=base_url)
        tool = SardisBalanceCheckTool(client=client, wallet_id="wallet_123")

        result = await tool._arun()

        assert "Balance" in result
        assert "1000.00" in result

    async def test_return_error_when_no_client(self):
        """Should return error when client not initialized."""
        tool = SardisBalanceCheckTool(wallet_id="wallet_123")

        result = await tool._arun()

        assert "Error" in result


class TestCreateSardisTools:
    """Tests for create_sardis_tools function."""

    def test_create_all_tools(self, api_key, base_url):
        """Should create all tools."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tools = create_sardis_tools(client, wallet_id="wallet_123")

        assert len(tools) == 3

        names = [t.name for t in tools]
        assert "sardis_pay" in names
        assert "sardis_check_policy" in names
        assert "sardis_check_balance" in names

    def test_pass_wallet_id_to_all_tools(self, api_key, base_url):
        """Should pass wallet ID to all tools."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tools = create_sardis_tools(client, wallet_id="my_wallet")

        for tool in tools:
            assert tool.wallet_id == "my_wallet"

    def test_pass_agent_id_to_payment_tool(self, api_key, base_url):
        """Should pass agent ID to payment tool."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tools = create_sardis_tools(client, wallet_id="wallet_123", agent_id="agent_456")

        payment_tool = next(t for t in tools if t.name == "sardis_pay")
        assert payment_tool.agent_id == "agent_456"

    def test_pass_chain_to_payment_tool(self, api_key, base_url):
        """Should pass chain to payment tool."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        tools = create_sardis_tools(
            client,
            wallet_id="wallet_123",
            chain="polygon",
        )

        payment_tool = next(t for t in tools if t.name == "sardis_pay")
        assert payment_tool.chain == "polygon"
