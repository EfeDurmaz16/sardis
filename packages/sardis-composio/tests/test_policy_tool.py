from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from sardis_composio import tools


class _Policies:
    def check(self, **kwargs: object) -> SimpleNamespace:
        assert kwargs["agent_id"] == "agent_123"
        assert kwargs["amount"] == Decimal("25.0")
        assert kwargs["currency"] == "USD"
        assert kwargs["merchant_id"] == "aws"
        return SimpleNamespace(allowed=True, reason="ALLOWED", policy_id="pol_123")


class _Wallets:
    def get(self, wallet_id: str) -> SimpleNamespace:
        assert wallet_id == "wallet_123"
        return SimpleNamespace(agent_id="agent_123")

    def get_balance(self, wallet_id: str) -> SimpleNamespace:
        assert wallet_id == "wallet_123"
        return SimpleNamespace(balance="50.00", remaining="50.00")


def test_sardis_check_policy_uses_canonical_policy_check(monkeypatch) -> None:
    monkeypatch.setattr(
        tools,
        "_get_client",
        lambda api_key=None, wallet_id=None: (
            SimpleNamespace(wallets=_Wallets(), policies=_Policies()),
            "wallet_123",
        ),
    )

    result = tools.sardis_check_policy(amount=25.0, merchant="aws")

    assert result["allowed"] is True
    assert result["policy_id"] == "pol_123"
    assert result["agent_id"] == "agent_123"
    assert result["balance"] == 50.0
    assert result["remaining"] == 50.0
