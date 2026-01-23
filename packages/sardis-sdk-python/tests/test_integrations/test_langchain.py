"""Tests for LangChain integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock langchain before importing our module
mock_base_tool = MagicMock()
mock_base_tool.BaseTool = type(
    "BaseTool",
    (),
    {
        "name": "",
        "description": "",
        "args_schema": None,
        "__init__": lambda self, **kwargs: None,
    },
)
sys.modules["langchain"] = MagicMock()
sys.modules["langchain.tools"] = mock_base_tool

from sardis_sdk.integrations.langchain import (
    PayInput,
    PolicyCheckInput,
    BalanceCheckInput,
    _generate_mandate_id,
    _create_audit_hash,
    SardisTool,
    SardisPolicyCheckTool,
    SardisBalanceCheckTool,
    create_sardis_tools,
)


class TestInputSchemas:
    """Tests for input schemas."""

    def test_pay_input_required_fields(self):
        """Should require amount and merchant."""
        pay_input = PayInput(amount=50.0, merchant="OpenAI")
        assert pay_input.amount == 50.0
        assert pay_input.merchant == "OpenAI"
        assert pay_input.purpose == "Service payment"
        assert pay_input.token == "USDC"

    def test_pay_input_all_fields(self):
        """Should accept all fields."""
        pay_input = PayInput(
            amount=100.0,
            merchant="AWS",
            merchant_address="0x123",
            purpose="Cloud compute",
            token="USDT",
        )
        assert pay_input.merchant_address == "0x123"
        assert pay_input.purpose == "Cloud compute"
        assert pay_input.token == "USDT"

    def test_policy_check_input(self):
        """Should create policy check input."""
        policy_input = PolicyCheckInput(merchant="OpenAI", amount=50.0)
        assert policy_input.merchant == "OpenAI"
        assert policy_input.amount == 50.0
        assert policy_input.purpose is None

    def test_balance_check_input(self):
        """Should create balance check input."""
        balance_input = BalanceCheckInput()
        assert balance_input.token == "USDC"
        assert balance_input.chain == "base_sepolia"

    def test_balance_check_input_custom(self):
        """Should accept custom values."""
        balance_input = BalanceCheckInput(token="USDT", chain="polygon")
        assert balance_input.token == "USDT"
        assert balance_input.chain == "polygon"


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
        """Should create consistent hashes."""
        hash1 = _create_audit_hash("test")
        hash2 = _create_audit_hash("test")
        hash3 = _create_audit_hash("different")
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64


class TestSardisTool:
    """Tests for SardisTool."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client."""
        client = MagicMock()
        client.payments = MagicMock()
        return client

    def test_tool_properties(self, mock_client):
        """Should have correct tool properties."""
        tool = SardisTool(client=mock_client, wallet_id="wallet_123")
        assert tool.name == "sardis_pay"
        assert "payment" in tool.description.lower()
        assert tool.wallet_id == "wallet_123"

    def test_tool_from_env(self, mock_client):
        """Should use env vars when not provided."""
        with patch.dict(
            "os.environ",
            {"SARDIS_WALLET_ID": "env_wallet", "SARDIS_AGENT_ID": "env_agent"},
        ):
            tool = SardisTool(client=mock_client)
            assert tool.wallet_id == "env_wallet"
            assert tool.agent_id == "env_agent"

    async def test_arun_no_client(self):
        """Should return error when no client."""
        tool = SardisTool(client=None, wallet_id="wallet_123")
        result = await tool._arun(50, "OpenAI")
        assert "Error" in result
        assert "not initialized" in result

    async def test_arun_no_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        tool = SardisTool(client=mock_client, wallet_id="")
        result = await tool._arun(50, "OpenAI")
        assert "Error" in result
        assert "wallet" in result.lower()

    async def test_arun_zero_amount(self, mock_client):
        """Should return error for zero amount."""
        tool = SardisTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun(0, "OpenAI")
        assert "Error" in result
        assert "positive" in result.lower()

    async def test_arun_negative_amount(self, mock_client):
        """Should return error for negative amount."""
        tool = SardisTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun(-50, "OpenAI")
        assert "Error" in result

    async def test_arun_success(self, mock_client):
        """Should execute payment successfully."""
        mock_result = MagicMock()
        mock_result.payment_id = "pay_123"
        mock_result.status = "completed"
        mock_result.tx_hash = "0xabc"
        mock_result.chain = "base_sepolia"
        mock_result.ledger_tx_id = "ltx_456"
        mock_client.payments.execute_mandate = AsyncMock(return_value=mock_result)

        tool = SardisTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun(50, "OpenAI", purpose="API credits")

        assert "APPROVED" in result
        assert "pay_123" in result
        assert "OpenAI" in result

    async def test_arun_policy_blocked(self, mock_client):
        """Should handle policy block."""
        mock_client.payments.execute_mandate = AsyncMock(
            side_effect=Exception("Payment blocked by policy limit")
        )

        tool = SardisTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun(1000, "Amazon")

        assert "BLOCKED" in result
        assert "PREVENTED" in result

    async def test_arun_generic_error(self, mock_client):
        """Should handle generic error."""
        mock_client.payments.execute_mandate = AsyncMock(
            side_effect=Exception("Network timeout")
        )

        tool = SardisTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun(50, "OpenAI")

        assert "Error" in result
        assert "Network timeout" in result


class TestSardisPolicyCheckTool:
    """Tests for SardisPolicyCheckTool."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client."""
        client = MagicMock()
        client.wallets = MagicMock()
        return client

    def test_tool_properties(self, mock_client):
        """Should have correct tool properties."""
        tool = SardisPolicyCheckTool(client=mock_client, wallet_id="wallet_123")
        assert tool.name == "sardis_check_policy"
        assert "policy" in tool.description.lower()

    async def test_arun_no_client(self):
        """Should return error when no client."""
        tool = SardisPolicyCheckTool(client=None, wallet_id="wallet_123")
        result = await tool._arun("OpenAI", 50)
        assert "Error" in result

    async def test_arun_no_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        tool = SardisPolicyCheckTool(client=mock_client, wallet_id="")
        result = await tool._arun("OpenAI", 50)
        assert "Error" in result

    async def test_arun_allowed(self, mock_client):
        """Should return allowed for valid payment."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "500"
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        tool = SardisPolicyCheckTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun("OpenAI", 50)

        assert "WOULD BE ALLOWED" in result
        assert "PASS" in result

    async def test_arun_blocked_by_limit(self, mock_client):
        """Should return blocked when over limit."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "50"
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        tool = SardisPolicyCheckTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun("OpenAI", 100)

        assert "WOULD BE BLOCKED" in result
        assert "FAIL" in result

    async def test_arun_blocked_inactive_wallet(self, mock_client):
        """Should return blocked when wallet inactive."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "500"
        mock_wallet.is_active = False
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        tool = SardisPolicyCheckTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun("OpenAI", 50)

        assert "WOULD BE BLOCKED" in result
        assert "disabled" in result or "FAIL" in result

    async def test_arun_no_limit(self, mock_client):
        """Should allow when no limit set."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = None
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        tool = SardisPolicyCheckTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun("OpenAI", 10000)

        assert "WOULD BE ALLOWED" in result

    async def test_arun_error(self, mock_client):
        """Should handle error."""
        mock_client.wallets.get = AsyncMock(side_effect=Exception("Failed"))

        tool = SardisPolicyCheckTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun("OpenAI", 50)

        assert "Error" in result


class TestSardisBalanceCheckTool:
    """Tests for SardisBalanceCheckTool."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client."""
        client = MagicMock()
        client.wallets = MagicMock()
        return client

    def test_tool_properties(self, mock_client):
        """Should have correct tool properties."""
        tool = SardisBalanceCheckTool(client=mock_client, wallet_id="wallet_123")
        assert tool.name == "sardis_check_balance"
        assert "balance" in tool.description.lower()

    async def test_arun_no_client(self):
        """Should return error when no client."""
        tool = SardisBalanceCheckTool(client=None, wallet_id="wallet_123")
        result = await tool._arun()
        assert "Error" in result

    async def test_arun_no_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        tool = SardisBalanceCheckTool(client=mock_client, wallet_id="")
        result = await tool._arun()
        assert "Error" in result

    async def test_arun_success(self, mock_client):
        """Should return balance info."""
        mock_balance = MagicMock()
        mock_balance.wallet_id = "wallet_123"
        mock_balance.token = "USDC"
        mock_balance.chain = "base_sepolia"
        mock_balance.balance = "500.00"
        mock_balance.address = "0x123"
        mock_client.wallets.get_balance = AsyncMock(return_value=mock_balance)

        tool = SardisBalanceCheckTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun()

        assert "Wallet Balance" in result
        assert "500.00" in result
        assert "USDC" in result

    async def test_arun_error(self, mock_client):
        """Should handle error."""
        mock_client.wallets.get_balance = AsyncMock(side_effect=Exception("Failed"))

        tool = SardisBalanceCheckTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._arun()

        assert "Error" in result


class TestCreateSardisTools:
    """Tests for create_sardis_tools."""

    def test_creates_three_tools(self):
        """Should create three tools."""
        mock_client = MagicMock()
        tools = create_sardis_tools(mock_client, wallet_id="wallet_123")

        assert len(tools) == 3
        tool_names = [t.name for t in tools]
        assert "sardis_pay" in tool_names
        assert "sardis_check_policy" in tool_names
        assert "sardis_check_balance" in tool_names

    def test_tools_have_correct_configuration(self):
        """Should configure tools with provided values."""
        mock_client = MagicMock()
        tools = create_sardis_tools(
            mock_client,
            wallet_id="wallet_123",
            agent_id="agent_456",
            chain="polygon",
        )

        pay_tool = tools[0]
        assert pay_tool.wallet_id == "wallet_123"
        assert pay_tool.agent_id == "agent_456"
        assert pay_tool.chain == "polygon"
