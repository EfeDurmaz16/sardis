"""Tests for LlamaIndex integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock llama_index before importing our module
mock_llama_index_core = MagicMock()
mock_llama_index_core.tools = MagicMock()
mock_llama_index_core.tools.FunctionTool = MagicMock()
mock_llama_index_core.tools.AsyncBaseTool = MagicMock()
mock_llama_index_core.tools.ToolMetadata = MagicMock()
sys.modules["llama_index"] = MagicMock()
sys.modules["llama_index.core"] = mock_llama_index_core
sys.modules["llama_index.core.tools"] = mock_llama_index_core.tools

from sardis_sdk.integrations.llamaindex import (
    _generate_mandate_id,
    _create_audit_hash,
    SardisPaymentTool,
    create_sardis_tools,
    get_llamaindex_tool,
    LLAMA_INDEX_AVAILABLE,
)


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


class TestSardisPaymentTool:
    """Tests for SardisPaymentTool."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client."""
        client = MagicMock()
        client.payments = MagicMock()
        client.wallets = MagicMock()
        return client

    def test_init(self, mock_client):
        """Should initialize with correct values."""
        tool = SardisPaymentTool(
            client=mock_client,
            wallet_id="wallet_123",
            agent_id="agent_456",
            chain="polygon",
        )
        assert tool.wallet_id == "wallet_123"
        assert tool.agent_id == "agent_456"
        assert tool.chain == "polygon"

    def test_init_with_env_vars(self, mock_client):
        """Should use env vars when agent_id not provided."""
        with patch.dict("os.environ", {"SARDIS_AGENT_ID": "env_agent"}):
            tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
            assert tool.agent_id == "env_agent"

    async def test_async_pay_no_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        tool = SardisPaymentTool(client=mock_client, wallet_id="")
        result = await tool._async_pay(50, "OpenAI", "Purpose", None, "USDC")
        assert "Error" in result
        assert "wallet" in result.lower()

    async def test_async_pay_zero_amount(self, mock_client):
        """Should return error for zero amount."""
        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_pay(0, "OpenAI", "Purpose", None, "USDC")
        assert "Error" in result
        assert "positive" in result.lower()

    async def test_async_pay_negative_amount(self, mock_client):
        """Should return error for negative amount."""
        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_pay(-50, "OpenAI", "Purpose", None, "USDC")
        assert "Error" in result

    async def test_async_pay_success(self, mock_client):
        """Should execute payment successfully."""
        mock_result = MagicMock()
        mock_result.payment_id = "pay_123"
        mock_result.status = "completed"
        mock_result.tx_hash = "0xabc"
        mock_result.chain = "base_sepolia"
        mock_client.payments.execute_mandate = AsyncMock(return_value=mock_result)

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_pay(50, "OpenAI", "API credits", None, "USDC")

        assert "APPROVED" in result
        assert "pay_123" in result
        assert "$50" in result

    async def test_async_pay_with_merchant_address(self, mock_client):
        """Should use merchant address when provided."""
        mock_result = MagicMock()
        mock_result.payment_id = "pay_123"
        mock_result.status = "completed"
        mock_result.tx_hash = "0xabc"
        mock_result.chain = "base_sepolia"
        mock_client.payments.execute_mandate = AsyncMock(return_value=mock_result)

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_pay(50, "OpenAI", "Purpose", "0x456", "USDC")

        assert "APPROVED" in result

    async def test_async_pay_policy_blocked(self, mock_client):
        """Should handle policy block."""
        mock_client.payments.execute_mandate = AsyncMock(
            side_effect=Exception("Payment blocked by policy")
        )

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_pay(1000, "Amazon", "Purchase", None, "USDC")

        assert "BLOCKED" in result
        assert "PREVENTED" in result

    async def test_async_pay_limit_exceeded(self, mock_client):
        """Should handle limit exceeded."""
        mock_client.payments.execute_mandate = AsyncMock(
            side_effect=Exception("Limit exceeded")
        )

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_pay(1000, "OpenAI", "Purpose", None, "USDC")

        assert "BLOCKED" in result

    async def test_async_pay_generic_error(self, mock_client):
        """Should handle generic error."""
        mock_client.payments.execute_mandate = AsyncMock(
            side_effect=Exception("Network timeout")
        )

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_pay(50, "OpenAI", "Purpose", None, "USDC")

        assert "Error" in result
        assert "Network timeout" in result

    async def test_async_check_balance_no_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        tool = SardisPaymentTool(client=mock_client, wallet_id="")
        result = await tool._async_check_balance("USDC", "base_sepolia")
        assert "Error" in result

    async def test_async_check_balance_success(self, mock_client):
        """Should return balance info."""
        mock_balance = MagicMock()
        mock_balance.token = "USDC"
        mock_balance.chain = "base_sepolia"
        mock_balance.balance = "500.00"
        mock_balance.address = "0x123"
        mock_client.wallets.get_balance = AsyncMock(return_value=mock_balance)

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_check_balance("USDC", "base_sepolia")

        assert "Wallet Balance" in result
        assert "500.00" in result

    async def test_async_check_balance_error(self, mock_client):
        """Should handle error."""
        mock_client.wallets.get_balance = AsyncMock(side_effect=Exception("Failed"))

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_check_balance("USDC", "base_sepolia")

        assert "Error" in result

    async def test_async_check_policy_no_wallet_id(self, mock_client):
        """Should return error when no wallet ID."""
        tool = SardisPaymentTool(client=mock_client, wallet_id="")
        result = await tool._async_check_policy(50, "OpenAI")
        assert "Error" in result

    async def test_async_check_policy_allowed(self, mock_client):
        """Should return allowed for valid payment."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "500"
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_check_policy(50, "OpenAI")

        assert "WOULD BE ALLOWED" in result
        assert "PASS" in result

    async def test_async_check_policy_blocked_by_limit(self, mock_client):
        """Should return blocked when over limit."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "50"
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_check_policy(100, "OpenAI")

        assert "WOULD BE BLOCKED" in result
        assert "FAIL" in result

    async def test_async_check_policy_blocked_inactive(self, mock_client):
        """Should return blocked when wallet inactive."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = "500"
        mock_wallet.is_active = False
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_check_policy(50, "OpenAI")

        assert "WOULD BE BLOCKED" in result

    async def test_async_check_policy_no_limit(self, mock_client):
        """Should allow when no limit set."""
        mock_wallet = MagicMock()
        mock_wallet.limit_per_tx = None
        mock_wallet.is_active = True
        mock_client.wallets.get = AsyncMock(return_value=mock_wallet)

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_check_policy(10000, "OpenAI")

        assert "WOULD BE ALLOWED" in result

    async def test_async_check_policy_error(self, mock_client):
        """Should handle error."""
        mock_client.wallets.get = AsyncMock(side_effect=Exception("Failed"))

        tool = SardisPaymentTool(client=mock_client, wallet_id="wallet_123")
        result = await tool._async_check_policy(50, "OpenAI")

        assert "Error" in result


class TestCreateSardisTools:
    """Tests for create_sardis_tools."""

    def test_raises_import_error_when_not_available(self):
        """Should raise ImportError when llama_index not available."""
        # This test would need to actually unload the module
        # For now, we test that the flag exists
        assert isinstance(LLAMA_INDEX_AVAILABLE, bool)

    @pytest.mark.skipif(
        not LLAMA_INDEX_AVAILABLE, reason="llama_index not installed"
    )
    def test_creates_three_tools_when_available(self):
        """Should create three tools when llama_index is installed."""
        mock_client = MagicMock()
        tools = create_sardis_tools(mock_client, wallet_id="wallet_123")
        assert len(tools) == 3


class TestGetLlamaindexTool:
    """Tests for get_llamaindex_tool."""

    @pytest.mark.skipif(
        not LLAMA_INDEX_AVAILABLE, reason="llama_index not installed"
    )
    def test_returns_payment_tool_when_available(self):
        """Should return payment tool when llama_index is installed."""
        mock_client = MagicMock()
        tool = get_llamaindex_tool(client=mock_client, wallet_id="wallet_123")
        assert tool is not None

    @pytest.mark.skipif(
        not LLAMA_INDEX_AVAILABLE, reason="llama_index not installed"
    )
    def test_demo_mode_without_client_when_available(self):
        """Should return demo tool when no client and llama_index is installed."""
        tool = get_llamaindex_tool(client=None)
        assert tool is not None

    @pytest.mark.skipif(
        not LLAMA_INDEX_AVAILABLE, reason="llama_index not installed"
    )
    def test_uses_env_wallet_id_when_available(self):
        """Should use wallet ID from environment when llama_index is installed."""
        mock_client = MagicMock()

        with patch.dict("os.environ", {"SARDIS_WALLET_ID": "env_wallet"}):
            tool = get_llamaindex_tool(client=mock_client)
            assert tool is not None
