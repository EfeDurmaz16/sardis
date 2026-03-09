"""Tests for sardis_openai_agents tools in simulation mode."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_client(balance=500.0, remaining=200.0, tx_success=True, tx_id="tx_abc123", tx_message=""):
    client = MagicMock()
    balance_result = MagicMock()
    balance_result.balance = balance
    balance_result.remaining = remaining
    client.wallets.get_balance.return_value = balance_result

    tx_result = MagicMock()
    tx_result.success = tx_success
    tx_result.tx_id = tx_id
    tx_result.message = tx_message
    client.payments.send.return_value = tx_result

    return client


@pytest.fixture(autouse=True)
def reset_module_state():
    """Reset module-level client state between tests."""
    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = None
    tools_mod._default_wallet_id = None
    yield
    tools_mod._default_client = None
    tools_mod._default_wallet_id = None


def test_sardis_pay_approved():
    mock_client = _make_mock_client(tx_success=True, tx_id="tx_001")

    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = mock_client
    tools_mod._default_wallet_id = "wid_test"

    result = tools_mod.sardis_pay(50.0, "acme.com", "Office supplies")
    assert "APPROVED" in result
    assert "50.0" in result
    assert "acme.com" in result
    assert "tx_001" in result


def test_sardis_pay_blocked():
    mock_client = _make_mock_client(tx_success=False, tx_message="Exceeds daily limit")

    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = mock_client
    tools_mod._default_wallet_id = "wid_test"

    result = tools_mod.sardis_pay(9999.0, "expensive.com")
    assert "BLOCKED by policy" in result
    assert "Exceeds daily limit" in result


def test_sardis_pay_no_wallet():
    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = _make_mock_client()
    tools_mod._default_wallet_id = None

    result = tools_mod.sardis_pay(10.0, "shop.com")
    assert "Error" in result
    assert "wallet ID" in result


def test_sardis_check_balance():
    mock_client = _make_mock_client(balance=1234.56, remaining=300.0)

    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = mock_client
    tools_mod._default_wallet_id = "wid_test"

    result = tools_mod.sardis_check_balance("USDC")
    assert "1234.56" in result
    assert "USDC" in result
    assert "300.0" in result


def test_sardis_check_balance_no_wallet():
    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = _make_mock_client()
    tools_mod._default_wallet_id = None

    result = tools_mod.sardis_check_balance()
    assert "Error" in result


def test_sardis_check_policy_allowed():
    mock_client = _make_mock_client(balance=500.0, remaining=200.0)

    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = mock_client
    tools_mod._default_wallet_id = "wid_test"

    result = tools_mod.sardis_check_policy(50.0, "store.com")
    assert "WOULD BE ALLOWED" in result


def test_sardis_check_policy_exceeds_remaining():
    mock_client = _make_mock_client(balance=500.0, remaining=100.0)

    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = mock_client
    tools_mod._default_wallet_id = "wid_test"

    result = tools_mod.sardis_check_policy(150.0, "store.com")
    assert "WOULD BE BLOCKED" in result
    assert "remaining limit" in result


def test_sardis_check_policy_exceeds_balance():
    mock_client = _make_mock_client(balance=50.0, remaining=200.0)

    import sardis_openai_agents.tools as tools_mod
    tools_mod._default_client = mock_client
    tools_mod._default_wallet_id = "wid_test"

    result = tools_mod.sardis_check_policy(100.0, "store.com")
    assert "WOULD BE BLOCKED" in result
    assert "balance" in result


def test_configure_sets_client():
    mock_sardis = MagicMock()
    mock_client_instance = _make_mock_client()
    mock_sardis.SardisClient.return_value = mock_client_instance

    with patch.dict(sys.modules, {"sardis": mock_sardis}):
        import sardis_openai_agents.tools as tools_mod

        tools_mod.configure(api_key="sk_test", wallet_id="wid_configured")
        assert tools_mod._default_wallet_id == "wid_configured"


def test_get_sardis_tools_returns_list():
    import sardis_openai_agents.tools as tools_mod
    tools = tools_mod.get_sardis_tools()
    assert isinstance(tools, list)
    assert len(tools) == 3


def test_init_exports():
    import sardis_openai_agents
    assert hasattr(sardis_openai_agents, "configure")
    assert hasattr(sardis_openai_agents, "get_sardis_tools")
    assert hasattr(sardis_openai_agents, "sardis_pay")
    assert hasattr(sardis_openai_agents, "sardis_check_balance")
    assert hasattr(sardis_openai_agents, "sardis_check_policy")
