"""
Integration tests for framework integration packages.

Tests that the LangChain, CrewAI, ADK, and Anthropic Agent SDK packages
export correct interfaces and their tools/handlers work with mock data.
These tests do NOT require API keys or external services.
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# sardis-langchain integration tests
# ---------------------------------------------------------------------------

class TestLangChainIntegration:
    """Verify sardis-langchain package exports and tool structure."""

    def test_toolkit_import(self):
        from sardis_langchain import SardisToolkit
        assert SardisToolkit is not None

    def test_tool_imports(self):
        from sardis_langchain.tools import (
            SardisPayTool,
            SardisBalanceTool,
            SardisPolicyCheckTool,
            SardisSetPolicyTool,
            SardisTransactionsTool,
        )
        assert all([
            SardisPayTool,
            SardisBalanceTool,
            SardisPolicyCheckTool,
            SardisSetPolicyTool,
            SardisTransactionsTool,
        ])

    def test_callback_handler_import(self):
        from sardis_langchain.callbacks import SardisCallbackHandler
        assert SardisCallbackHandler is not None

    def test_toolkit_creates_tools(self):
        from sardis_langchain import SardisToolkit

        mock_client = MagicMock()
        toolkit = SardisToolkit(client=mock_client, wallet_id="test_wallet")
        tools = toolkit.get_tools()

        assert len(tools) == 5
        tool_names = {t.name for t in tools}
        assert "sardis_pay" in tool_names
        assert "sardis_check_balance" in tool_names

    def test_toolkit_read_only(self):
        from sardis_langchain import SardisToolkit

        mock_client = MagicMock()
        toolkit = SardisToolkit(client=mock_client, wallet_id="test_wallet", read_only=True)
        tools = toolkit.get_tools()

        # Read-only should not include pay or set_policy
        tool_names = {t.name for t in tools}
        assert "sardis_pay" not in tool_names
        assert "sardis_check_balance" in tool_names


# ---------------------------------------------------------------------------
# sardis-crewai integration tests
# ---------------------------------------------------------------------------

class TestCrewAIIntegration:
    """Verify sardis-crewai package exports and tool structure."""

    def test_tools_import(self):
        from sardis_crewai.tools import (
            SardisPayTool,
            SardisBalanceTool,
            SardisPolicyCheckTool,
            SardisSetPolicyTool,
            SardisTransactionsTool,
        )
        assert all([
            SardisPayTool,
            SardisBalanceTool,
            SardisPolicyCheckTool,
            SardisSetPolicyTool,
            SardisTransactionsTool,
        ])

    def test_create_sardis_tools(self):
        from sardis_crewai import create_sardis_tools

        mock_client = MagicMock()
        tools = create_sardis_tools(client=mock_client, wallet_id="test_wallet")

        assert len(tools) == 5

    def test_create_sardis_tools_read_only(self):
        from sardis_crewai import create_sardis_tools

        mock_client = MagicMock()
        tools = create_sardis_tools(client=mock_client, wallet_id="test_wallet", read_only=True)

        # Read-only should have fewer tools
        assert len(tools) < 5

    def test_agent_factories_import(self):
        from sardis_crewai.agents import (
            create_payment_agent,
            create_auditor_agent,
            create_treasury_agent,
        )
        assert all([create_payment_agent, create_auditor_agent, create_treasury_agent])

    def test_task_templates_import(self):
        from sardis_crewai.tasks import (
            create_purchase_task,
            create_audit_task,
            create_budget_review_task,
        )
        assert all([create_purchase_task, create_audit_task, create_budget_review_task])


# ---------------------------------------------------------------------------
# sardis-adk integration tests
# ---------------------------------------------------------------------------

class TestADKIntegration:
    """Verify sardis-adk package exports and tool functions."""

    def test_toolkit_import(self):
        from sardis_adk import SardisToolkit
        assert SardisToolkit is not None

    def test_tool_functions_import(self):
        from sardis_adk.tools import (
            sardis_pay,
            sardis_check_balance,
            sardis_check_policy,
            sardis_set_policy,
            sardis_list_transactions,
        )
        assert all([
            sardis_pay,
            sardis_check_balance,
            sardis_check_policy,
            sardis_set_policy,
            sardis_list_transactions,
        ])
        # All should be callable
        assert callable(sardis_pay)
        assert callable(sardis_check_balance)

    def test_configure_function(self):
        from sardis_adk.tools import configure
        assert callable(configure)

    def test_unconfigured_raises(self):
        """Tool functions should raise if not configured."""
        import sardis_adk.tools as tools
        # Reset state
        tools._client = None
        tools._wallet_id = None

        with pytest.raises(RuntimeError, match="not been configured"):
            tools.sardis_pay(to="test", amount="10")


# ---------------------------------------------------------------------------
# sardis-agent-sdk integration tests
# ---------------------------------------------------------------------------

class TestAgentSDKIntegration:
    """Verify sardis-agent-sdk package exports and tool definitions."""

    def test_toolkit_import(self):
        from sardis_agent_sdk import SardisToolkit
        assert SardisToolkit is not None

    def test_tool_definitions_import(self):
        from sardis_agent_sdk.tools import ALL_TOOLS, READ_ONLY_TOOLS, TOOL_NAMES
        assert len(ALL_TOOLS) == 6
        assert len(READ_ONLY_TOOLS) < len(ALL_TOOLS)
        assert len(TOOL_NAMES) == 6

    def test_tool_definitions_schema(self):
        """Each tool definition should have proper Anthropic tool_use schema."""
        from sardis_agent_sdk.tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool missing 'description': {tool}"
            assert "input_schema" in tool, f"Tool missing 'input_schema': {tool}"
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "properties" in schema

    def test_toolkit_get_tools(self):
        from sardis_agent_sdk import SardisToolkit

        mock_client = MagicMock()
        toolkit = SardisToolkit(client=mock_client, wallet_id="test_wallet")
        tools = toolkit.get_tools()

        assert len(tools) == 6

    def test_toolkit_read_only(self):
        from sardis_agent_sdk import SardisToolkit

        mock_client = MagicMock()
        toolkit = SardisToolkit(client=mock_client, wallet_id="test_wallet", read_only=True)
        tools = toolkit.get_tools()

        assert len(tools) < 6

    def test_handle_tool_call_dict(self):
        """Test handling a tool_use block as a dict."""
        from sardis_agent_sdk import SardisToolkit

        mock_client = MagicMock()
        mock_wallet = MagicMock()
        mock_wallet.balance = Decimal("1000")
        mock_wallet.limit_per_tx = Decimal("100")
        mock_wallet.limit_total = Decimal("1000")
        mock_wallet.spent_total = Decimal("0")
        mock_client.wallets.get_balance.return_value = MagicMock(
            wallet_id="test_wallet",
            balance=1000.0,
            token="USDC",
            chain="base",
            spent_total=0.0,
            limit_per_tx=100.0,
            limit_total=1000.0,
            remaining=1000.0,
        )

        toolkit = SardisToolkit(client=mock_client, wallet_id="test_wallet")

        result = toolkit.handle_tool_call({
            "type": "tool_use",
            "id": "call_123",
            "name": "sardis_check_balance",
            "input": {"token": "USDC"},
        })

        assert result["type"] == "tool_result"
        assert result["tool_use_id"] == "call_123"


# ---------------------------------------------------------------------------
# Cross-package: Policy consistency tests
# ---------------------------------------------------------------------------

class TestPolicyConsistency:
    """Verify policy checking works consistently across all framework integrations."""

    def test_policy_object_shared(self):
        """All packages should use the same core Policy class."""
        from sardis import Policy

        policy = Policy(max_per_tx=50, max_total=1000)

        # Under limit
        result = policy.check(amount=25, destination="openai.com", token="USDC")
        assert result.approved is True

        # Over limit
        result = policy.check(amount=100, destination="openai.com", token="USDC")
        assert result.approved is False
        assert "exceeds limit" in result.reason

    def test_policy_blocked_destination(self):
        from sardis import Policy

        policy = Policy(
            max_per_tx=500,
            blocked_destinations={"gambling.com", "adult:*"},
        )

        result = policy.check(amount=25, destination="gambling.com", token="USDC")
        assert result.approved is False
        assert "blocked" in result.reason.lower()

    def test_policy_approval_threshold(self):
        from sardis import Policy

        policy = Policy(max_per_tx=500, approval_threshold=100)

        # Under threshold - approved, no approval needed
        result = policy.check(amount=50, token="USDC")
        assert result.approved is True
        assert result.requires_approval is False

        # Over threshold - approved but needs human sign-off
        result = policy.check(amount=200, token="USDC")
        assert result.approved is True
        assert result.requires_approval is True


# ---------------------------------------------------------------------------
# Cross-package: EventBus integration tests
# ---------------------------------------------------------------------------

class TestEventBusIntegration:
    """Verify the EventBus system works with webhook event types."""

    def test_event_bus_import(self):
        from sardis_v2_core.event_bus import EventBus, get_default_bus
        assert EventBus is not None
        assert callable(get_default_bus)

    def test_event_types_comprehensive(self):
        """Verify all expected event categories exist."""
        from sardis_v2_core.webhooks import EventType

        # Policy events
        assert hasattr(EventType, "POLICY_CHECK_PASSED")
        assert hasattr(EventType, "POLICY_VIOLATION")

        # Spend events
        assert hasattr(EventType, "SPEND_RECORDED")
        assert hasattr(EventType, "SPEND_THRESHOLD_WARNING")

        # Approval events
        assert hasattr(EventType, "APPROVAL_REQUESTED")

    def test_event_bus_subscribe_and_emit(self):
        from sardis_v2_core.event_bus import EventBus
        from sardis_v2_core.webhooks import EventType, WebhookEvent

        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("policy.*", handler)
        bus.emit(WebhookEvent(
            event_type=EventType.POLICY_VIOLATION,
            data={"agent_id": "test", "amount": 100},
        ))

        assert len(received) == 1
        assert received[0].data["agent_id"] == "test"

    def test_event_bus_wildcard_all(self):
        from sardis_v2_core.event_bus import EventBus
        from sardis_v2_core.webhooks import EventType, WebhookEvent

        bus = EventBus()
        received = []

        bus.subscribe("*", lambda e: received.append(e))

        bus.emit(WebhookEvent(event_type=EventType.POLICY_VIOLATION, data={}))
        bus.emit(WebhookEvent(event_type=EventType.SPEND_RECORDED, data={}))

        assert len(received) == 2
