"""Smoke and tool-surface tests for sardis-langchain.

These tests do NOT make network calls. They verify that the package imports,
the toolkit instantiates, and each tool exposes the expected name/schema
surface that LangChain agents depend on.
"""
from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest


def test_package_imports():
    import sardis_langchain

    assert sardis_langchain.__version__ == "1.0.0"
    for name in (
        "SardisToolkit",
        "SardisPayTool",
        "SardisCheckBalanceTool",
        "SardisCheckPolicyTool",
        "SardisSetPolicyTool",
        "SardisListTransactionsTool",
        "SardisCallbackHandler",
    ):
        assert hasattr(sardis_langchain, name), f"missing export: {name}"


def test_toolkit_instantiates_with_fake_client():
    from sardis_langchain import SardisToolkit

    fake_client = MagicMock()
    toolkit = SardisToolkit(client=fake_client, wallet_id="wal_test_123")

    assert toolkit.wallet_id == "wal_test_123"
    assert toolkit.client is fake_client
    assert "wal_test_123" in repr(toolkit)


def test_get_tools_returns_expected_surface():
    from langchain_core.tools import BaseTool

    from sardis_langchain import SardisToolkit

    toolkit = SardisToolkit(client=MagicMock(), wallet_id="wal_x")
    tools = toolkit.get_tools()

    assert len(tools) == 5
    assert all(isinstance(t, BaseTool) for t in tools)

    names = {t.name for t in tools}
    assert names == {
        "sardis_pay",
        "sardis_check_balance",
        "sardis_check_policy",
        "sardis_set_policy",
        "sardis_list_transactions",
    }

    for tool in tools:
        assert tool.description
        assert tool.args_schema is not None


def test_get_payment_tools_subset():
    from sardis_langchain import SardisToolkit

    toolkit = SardisToolkit(client=MagicMock(), wallet_id="wal_x")
    tools = toolkit.get_payment_tools()

    names = {t.name for t in tools}
    assert names == {"sardis_pay", "sardis_check_balance", "sardis_check_policy"}


def test_pay_tool_rejects_invalid_amount_without_network():
    from sardis_langchain import SardisPayTool

    tool = SardisPayTool(client=MagicMock(), wallet_id="wal_x")
    result = json.loads(tool._run(to="acme.com", amount="not-a-number"))

    assert result["success"] is False
    assert "Invalid amount" in result["error"]


def test_pay_tool_without_wallet_id_fails_closed():
    from sardis_langchain import SardisPayTool

    tool = SardisPayTool(client=MagicMock(), wallet_id="")
    result = json.loads(tool._run(to="acme.com", amount="10.00"))

    assert result["success"] is False
    assert "wallet_id" in result["error"]


def test_pay_tool_builds_payload_and_returns_success():
    from sardis_langchain import SardisPayTool

    client = MagicMock()
    wallet = MagicMock()
    tx = MagicMock()
    tx.success = True
    tx.status = "completed"
    tx.tx_id = "tx_abc"
    tx.tx_hash = "0xdead"
    tx.amount = Decimal("25.00")
    tx.currency = "USDC"
    tx.to = "acme.com"
    tx.message = "ok"
    wallet.pay.return_value = tx
    client.wallets.get.return_value = wallet

    tool = SardisPayTool(client=client, wallet_id="wal_1")
    out = json.loads(tool._run(to="acme.com", amount="25.00", token="USDC", purpose="test"))

    client.wallets.get.assert_called_once_with("wal_1")
    wallet.pay.assert_called_once()
    kwargs = wallet.pay.call_args.kwargs
    assert kwargs["to"] == "acme.com"
    assert kwargs["amount"] == Decimal("25.00")
    assert kwargs["token"] == "USDC"

    assert out["success"] is True
    assert out["tx_id"] == "tx_abc"
    assert out["currency"] == "USDC"


def test_pay_tool_surfaces_policy_block_as_blocked_flag():
    from sardis_langchain import SardisPayTool

    client = MagicMock()
    client.wallets.get.side_effect = RuntimeError("Policy limit exceeded")

    tool = SardisPayTool(client=client, wallet_id="wal_1")
    out = json.loads(tool._run(to="acme.com", amount="500.00"))

    assert out["success"] is False
    assert out["blocked"] is True
    assert "Policy" in out["error"]


def test_check_policy_tool_allows_within_limits():
    from sardis_langchain import SardisCheckPolicyTool

    client = MagicMock()
    wallet = MagicMock()
    wallet.limit_per_tx = Decimal("100")
    wallet.balance = Decimal("500")
    wallet.remaining_limit.return_value = Decimal("400")
    wallet.is_active = True
    client.wallets.get.return_value = wallet

    tool = SardisCheckPolicyTool(client=client, wallet_id="wal_1")
    out = json.loads(tool._run(to="acme.com", amount="50"))

    assert out["success"] is True
    assert out["allowed"] is True
    assert all(c["passed"] for c in out["checks"])


def test_check_policy_tool_blocks_over_limit():
    from sardis_langchain import SardisCheckPolicyTool

    client = MagicMock()
    wallet = MagicMock()
    wallet.limit_per_tx = Decimal("100")
    wallet.balance = Decimal("500")
    wallet.remaining_limit.return_value = Decimal("400")
    wallet.is_active = True
    client.wallets.get.return_value = wallet

    tool = SardisCheckPolicyTool(client=client, wallet_id="wal_1")
    out = json.loads(tool._run(to="acme.com", amount="250"))

    assert out["success"] is True
    assert out["allowed"] is False
    failed = [c for c in out["checks"] if not c["passed"]]
    assert any("per-transaction" in c["reason"] for c in failed)
