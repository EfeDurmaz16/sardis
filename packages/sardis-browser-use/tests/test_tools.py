"""Tests for sardis-browser-use tools."""
import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from sardis import SardisClient


def test_register_sardis_actions():
    """Test that actions are registered on the controller."""
    from sardis_browser_use.tools import register_sardis_actions

    controller = MagicMock()
    controller.action = MagicMock(side_effect=lambda desc: lambda fn: fn)

    client = SardisClient()
    wallet = client.wallets.create(name="test")
    os.environ["SARDIS_WALLET_ID"] = wallet.id

    actions = register_sardis_actions(controller)
    assert len(actions) == 3
    assert controller.action.call_count == 3


@pytest.mark.asyncio
async def test_sardis_pay_simulation():
    """Test payment in simulation mode."""
    from sardis_browser_use.tools import register_sardis_actions

    controller = MagicMock()
    controller.action = MagicMock(side_effect=lambda desc: lambda fn: fn)

    client = SardisClient()
    wallet = client.wallets.create(name="test", initial_balance=500, policy="Max $100/day")

    actions = register_sardis_actions(controller, wallet_id=wallet.id)
    pay_fn = actions[0]

    result = await pay_fn(amount=25.0, merchant="amazon.com", purpose="USB cable")
    assert "APPROVED" in result
    assert "$25" in result


@pytest.mark.asyncio
async def test_sardis_balance():
    """Test balance check."""
    from sardis_browser_use.tools import register_sardis_actions

    controller = MagicMock()
    controller.action = MagicMock(side_effect=lambda desc: lambda fn: fn)

    client = SardisClient()
    wallet = client.wallets.create(name="test", initial_balance=1000)

    actions = register_sardis_actions(controller, wallet_id=wallet.id)
    balance_fn = actions[1]

    result = await balance_fn(token="USDC")
    assert "Balance" in result
    assert "1000" in result


@pytest.mark.asyncio
async def test_sardis_policy_check():
    """Test policy pre-check."""
    from sardis_browser_use.tools import register_sardis_actions

    controller = MagicMock()
    controller.action = MagicMock(side_effect=lambda desc: lambda fn: fn)

    client = SardisClient()
    wallet = client.wallets.create(name="test", initial_balance=50, limit_total=100)

    actions = register_sardis_actions(controller, wallet_id=wallet.id)
    check_fn = actions[2]

    result = await check_fn(amount=30.0, merchant="shop.com")
    assert "WOULD BE ALLOWED" in result

    result = await check_fn(amount=200.0, merchant="shop.com")
    assert "WOULD BE BLOCKED" in result
