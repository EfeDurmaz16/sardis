from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sardis_openai.handler import SardisToolHandler


def _tool_call(name: str, arguments: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        )
    )


@pytest.mark.asyncio
async def test_check_policy_uses_wallet_agent_and_canonical_policy_check() -> None:
    class _Wallets:
        async def get(self, wallet_id: str) -> SimpleNamespace:
            assert wallet_id == "wallet_123"
            return SimpleNamespace(agent_id="agent_123")

    class _Policies:
        async def check(self, **kwargs: object) -> SimpleNamespace:
            assert kwargs["agent_id"] == "agent_123"
            assert str(kwargs["amount"]) == "25.00"
            assert kwargs["currency"] == "USD"
            assert kwargs["merchant_id"] == "aws"
            return SimpleNamespace(allowed=True, reason="ALLOWED", policy_id="pol_123")

    handler = SardisToolHandler(api_key="sk_test", wallet_id="wallet_123")
    handler._client = SimpleNamespace(wallets=_Wallets(), policies=_Policies())

    result = json.loads(
        await handler.handle(
            _tool_call(
                "sardis_check_policy",
                {"wallet_id": "wallet_123", "amount": "25.00", "vendor": "aws"},
            )
        )
    )

    assert result["allowed"] is True
    assert result["agent_id"] == "agent_123"
    assert result["policy_id"] == "pol_123"


@pytest.mark.asyncio
async def test_check_balance_uses_get_balance_resource() -> None:
    class _Wallets:
        async def get_balance(self, wallet_id: str) -> SimpleNamespace:
            assert wallet_id == "wallet_123"
            return SimpleNamespace(balance="42.00", token="USDC", chain="base", address="0xabc")

    handler = SardisToolHandler(api_key="sk_test", wallet_id="wallet_123")
    handler._client = SimpleNamespace(wallets=_Wallets())

    result = json.loads(
        await handler.handle(_tool_call("sardis_check_balance", {"wallet_id": "wallet_123"}))
    )

    assert result == {
        "wallet_id": "wallet_123",
        "balance": "42.00",
        "token": "USDC",
        "chain": "base",
        "address": "0xabc",
    }


@pytest.mark.asyncio
async def test_spending_summary_returns_truthful_unavailable_error() -> None:
    handler = SardisToolHandler(api_key="sk_test", agent_id="agent_123")

    result = json.loads(
        await handler.handle(
            _tool_call("sardis_get_spending_summary", {"agent_id": "agent_123", "period": "month"})
        )
    )

    assert "does not expose a spending.summary resource" in result["error"]
    assert result["agent_id"] == "agent_123"
