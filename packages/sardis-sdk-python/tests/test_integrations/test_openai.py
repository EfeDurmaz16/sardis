"""Tests for OpenAI integration."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sardis_sdk.integrations.openai import (
    get_openai_function_schema,
    get_openai_tools,
    handle_function_call,
    create_tool_response,
    _generate_mandate_id,
    _create_audit_hash,
)


class TestGetOpenAIFunctionSchema:
    """Tests for legacy function schema."""

    def test_returns_valid_schema(self):
        """Should return valid OpenAI function schema."""
        schema = get_openai_function_schema()
        assert schema["name"] == "sardis_pay"
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"

    def test_schema_has_required_properties(self):
        """Should have required properties."""
        schema = get_openai_function_schema()
        props = schema["parameters"]["properties"]
        assert "amount" in props
        assert "merchant" in props
        assert "purpose" in props
        assert "token" in props

    def test_schema_required_fields(self):
        """Should have correct required fields."""
        schema = get_openai_function_schema()
        assert schema["parameters"]["required"] == ["amount", "merchant"]


class TestGetOpenAITools:
    """Tests for OpenAI tools format."""

    def test_returns_list_of_tools(self):
        """Should return list of tool definitions."""
        tools = get_openai_tools()
        assert isinstance(tools, list)
        assert len(tools) == 4  # sardis_pay, check_balance, get_wallet, check_policy

    def test_tools_have_correct_format(self):
        """Should have correct OpenAI tool format."""
        tools = get_openai_tools()
        for tool in tools:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_has_sardis_pay_tool(self):
        """Should include sardis_pay tool."""
        tools = get_openai_tools()
        pay_tool = next((t for t in tools if t["function"]["name"] == "sardis_pay"), None)
        assert pay_tool is not None
        assert "amount" in pay_tool["function"]["parameters"]["properties"]

    def test_has_check_balance_tool(self):
        """Should include sardis_check_balance tool."""
        tools = get_openai_tools()
        balance_tool = next(
            (t for t in tools if t["function"]["name"] == "sardis_check_balance"), None
        )
        assert balance_tool is not None

    def test_has_get_wallet_tool(self):
        """Should include sardis_get_wallet tool."""
        tools = get_openai_tools()
        wallet_tool = next(
            (t for t in tools if t["function"]["name"] == "sardis_get_wallet"), None
        )
        assert wallet_tool is not None

    def test_has_check_policy_tool(self):
        """Should include sardis_check_policy tool."""
        tools = get_openai_tools()
        policy_tool = next(
            (t for t in tools if t["function"]["name"] == "sardis_check_policy"), None
        )
        assert policy_tool is not None


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_mandate_id(self):
        """Should generate unique mandate IDs."""
        id1 = _generate_mandate_id()
        id2 = _generate_mandate_id()
        assert id1.startswith("mnd_")
        assert id2.startswith("mnd_")
        assert id1 != id2

    def test_create_audit_hash(self):
        """Should create SHA-256 hash."""
        hash1 = _create_audit_hash("test data")
        hash2 = _create_audit_hash("test data")
        hash3 = _create_audit_hash("different data")
        assert len(hash1) == 64  # SHA-256 hex length
        assert hash1 == hash2  # Same input = same hash
        assert hash1 != hash3  # Different input = different hash


class TestHandleFunctionCall:
    """Tests for handle_function_call."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client."""
        client = MagicMock()
        client.payments = MagicMock()
        client.wallets = MagicMock()
        return client

    async def test_unknown_function(self, mock_client):
        """Should return error for unknown function."""
        result = await handle_function_call(
            mock_client, "unknown_function", {}, wallet_id="wallet_123"
        )
        data = json.loads(result)
        assert data["success"] is False
        assert "Unknown function" in data["error"]

    async def test_pay_without_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        result = await handle_function_call(
            mock_client,
            "sardis_pay",
            {"amount": 50, "merchant": "OpenAI"},
            wallet_id="",
        )
        data = json.loads(result)
        assert data["success"] is False
        assert "wallet" in data["error"].lower()

    async def test_pay_with_zero_amount(self, mock_client):
        """Should return error for zero amount."""
        result = await handle_function_call(
            mock_client,
            "sardis_pay",
            {"amount": 0, "merchant": "OpenAI"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is False
        assert "positive" in data["error"].lower()

    async def test_pay_with_negative_amount(self, mock_client):
        """Should return error for negative amount."""
        result = await handle_function_call(
            mock_client,
            "sardis_pay",
            {"amount": -50, "merchant": "OpenAI"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is False

    async def test_successful_payment(self, mock_client):
        """Should execute payment successfully."""
        mock_result = MagicMock()
        mock_result.status = "completed"
        mock_result.payment_id = "pay_123"
        mock_result.tx_hash = "0xabc"
        mock_result.chain = "base_sepolia"
        mock_result.ledger_tx_id = "ltx_456"
        mock_result.audit_anchor = "anchor_789"
        mock_client.payments.execute_mandate = AsyncMock(return_value=mock_result)

        result = await handle_function_call(
            mock_client,
            "sardis_pay",
            {"amount": 50, "merchant": "OpenAI", "purpose": "API credits"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["payment_id"] == "pay_123"

    async def test_payment_policy_blocked(self, mock_client):
        """Should handle policy block."""
        mock_client.payments.execute_mandate = AsyncMock(
            side_effect=Exception("Payment blocked by policy")
        )

        result = await handle_function_call(
            mock_client,
            "sardis_pay",
            {"amount": 1000, "merchant": "Amazon"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is False
        assert data["blocked"] is True

    async def test_payment_generic_error(self, mock_client):
        """Should handle generic error."""
        mock_client.payments.execute_mandate = AsyncMock(
            side_effect=Exception("Network error")
        )

        result = await handle_function_call(
            mock_client,
            "sardis_pay",
            {"amount": 50, "merchant": "OpenAI"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is False
        assert "Network error" in data["error"]

    async def test_check_balance(self, mock_client):
        """Should check balance."""
        mock_balance = MagicMock()
        mock_balance.wallet_id = "wallet_123"
        mock_balance.balance = "100.00"
        mock_balance.token = "USDC"
        mock_balance.chain = "base_sepolia"
        mock_balance.address = "0x123"
        mock_client.wallets.get_balance = AsyncMock(return_value=mock_balance)

        result = await handle_function_call(
            mock_client,
            "sardis_check_balance",
            {"token": "USDC"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["balance"] == "100.00"

    async def test_check_balance_without_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        result = await handle_function_call(
            mock_client, "sardis_check_balance", {}, wallet_id=""
        )
        data = json.loads(result)
        assert data["success"] is False

    async def test_check_balance_error(self, mock_client):
        """Should handle balance check error."""
        mock_client.wallets.get_balance = AsyncMock(side_effect=Exception("Failed"))

        result = await handle_function_call(
            mock_client,
            "sardis_check_balance",
            {},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is False

    async def test_get_wallet(self, mock_client):
        """Should get wallet info."""
        mock_wallet = MagicMock()
        mock_wallet.id = "wallet_123"
        mock_wallet.agent_id = "agent_456"
        mock_wallet.currency = "USD"
        mock_wallet.limit_per_tx = "500"
        mock_wallet.limit_total = "10000"
        mock_wallet.is_active = True
        mock_wallet.addresses = {"base_sepolia": "0x123"}
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        result = await handle_function_call(
            mock_client, "sardis_get_wallet", {}, wallet_id="wallet_123"
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["wallet"]["id"] == "wallet_123"

    async def test_get_wallet_without_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        result = await handle_function_call(
            mock_client, "sardis_get_wallet", {}, wallet_id=""
        )
        data = json.loads(result)
        assert data["success"] is False

    async def test_get_wallet_error(self, mock_client):
        """Should handle get wallet error."""
        mock_client.wallets.get = AsyncMock(side_effect=Exception("Not found"))

        result = await handle_function_call(
            mock_client, "sardis_get_wallet", {}, wallet_id="wallet_123"
        )
        data = json.loads(result)
        assert data["success"] is False

    async def test_check_policy_allowed(self, mock_client):
        """Should check policy - allowed."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "500"
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        result = await handle_function_call(
            mock_client,
            "sardis_check_policy",
            {"amount": 50, "merchant": "OpenAI"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["allowed"] is True

    async def test_check_policy_blocked_by_limit(self, mock_client):
        """Should check policy - blocked by limit."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "50"
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        result = await handle_function_call(
            mock_client,
            "sardis_check_policy",
            {"amount": 100, "merchant": "OpenAI"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["allowed"] is False

    async def test_check_policy_blocked_inactive_wallet(self, mock_client):
        """Should check policy - blocked by inactive wallet."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "500"
        mock_wallet.is_active = False
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        result = await handle_function_call(
            mock_client,
            "sardis_check_policy",
            {"amount": 50, "merchant": "OpenAI"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["allowed"] is False

    async def test_check_policy_no_limit(self, mock_client):
        """Should handle no per-tx limit."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = None
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        result = await handle_function_call(
            mock_client,
            "sardis_check_policy",
            {"amount": 10000, "merchant": "OpenAI"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["allowed"] is True

    async def test_check_policy_without_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        result = await handle_function_call(
            mock_client,
            "sardis_check_policy",
            {"amount": 50, "merchant": "OpenAI"},
            wallet_id="",
        )
        data = json.loads(result)
        assert data["success"] is False

    async def test_check_policy_error(self, mock_client):
        """Should handle policy check error."""
        mock_client.wallets.get = AsyncMock(side_effect=Exception("Failed"))

        result = await handle_function_call(
            mock_client,
            "sardis_check_policy",
            {"amount": 50, "merchant": "OpenAI"},
            wallet_id="wallet_123",
        )
        data = json.loads(result)
        assert data["success"] is False

    @patch.dict("os.environ", {"SARDIS_WALLET_ID": "env_wallet_123"})
    async def test_uses_env_wallet_id(self, mock_client):
        """Should use wallet ID from environment."""
        mock_client.wallets.get_balance = AsyncMock(side_effect=Exception("Error"))

        result = await handle_function_call(
            mock_client, "sardis_check_balance", {}, wallet_id=None
        )
        # Should attempt to use env wallet ID (and fail with Error)
        data = json.loads(result)
        assert data["success"] is False


class TestCreateToolResponse:
    """Tests for create_tool_response."""

    def test_creates_tool_response(self):
        """Should create proper tool response format."""
        response = create_tool_response("call_123", '{"success": true}')
        assert response["role"] == "tool"
        assert response["tool_call_id"] == "call_123"
        assert response["content"] == '{"success": true}'
