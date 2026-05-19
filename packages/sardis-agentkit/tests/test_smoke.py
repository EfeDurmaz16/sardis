from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import ValidationError
from sardis_agentkit import SardisActionProvider, sardis_action_provider
from sardis_agentkit.schemas import CheckBalanceSchema, SendPaymentSchema


class FakeHTTPClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def post(self, path: str, json: dict[str, Any]) -> httpx.Response:
        self.requests.append({"method": "POST", "path": path, "json": json})
        if path == "/api/v2/agents":
            return httpx.Response(
                200,
                json={"agent_id": "agent_123", "wallet_id": "wallet_123"},
                request=httpx.Request("POST", "https://api.test/api/v2/agents"),
            )
        if path == "/api/v2/policies":
            return httpx.Response(
                200,
                json={"policy_id": "policy_123"},
                request=httpx.Request("POST", "https://api.test/api/v2/policies"),
            )
        if path == "/api/v2/payments":
            return httpx.Response(
                403,
                json={"detail": "daily limit exceeded"},
                request=httpx.Request("POST", "https://api.test/api/v2/payments"),
            )
        raise AssertionError(f"unexpected POST path: {path}")

    def get(self, path: str) -> httpx.Response:
        self.requests.append({"method": "GET", "path": path})
        return httpx.Response(
            200,
            json={"balances": {"USDC": "25.00", "ETH": "0.01"}},
            request=httpx.Request("GET", f"https://api.test{path}"),
        )


def provider_with_fake_client() -> tuple[SardisActionProvider, FakeHTTPClient]:
    provider = sardis_action_provider(api_key="test-key", api_url="https://api.test/")
    fake_client = FakeHTTPClient()
    provider._client = fake_client
    return provider, fake_client


def test_public_import_surface_and_factory() -> None:
    provider = sardis_action_provider(api_key="test-key", api_url="https://api.test/")

    assert isinstance(provider, SardisActionProvider)
    assert provider._api_key == "test-key"
    assert provider._api_url == "https://api.test"
    assert provider.supports_network(object()) is True


def test_schemas_validate_required_payment_fields() -> None:
    payment = SendPaymentSchema(
        agent_id="agent_123",
        amount="25.50",
        recipient="0xmerchant",
    )

    assert payment.currency == "USDC"
    assert payment.memo == ""

    with pytest.raises(ValidationError):
        CheckBalanceSchema()


def test_create_agent_and_policy_actions_format_api_requests() -> None:
    provider, fake_client = provider_with_fake_client()

    created = provider.create_agent({"name": "Research Agent", "description": "buys data"})
    policy = provider.set_policy(
        {
            "agent_id": "agent_123",
            "policy_text": "Max 25 USDC per request",
        }
    )

    assert "agent_id=agent_123" in created
    assert "policy_id=policy_123" in policy
    assert fake_client.requests == [
        {
            "method": "POST",
            "path": "/api/v2/agents",
            "json": {"name": "Research Agent", "description": "buys data"},
        },
        {
            "method": "POST",
            "path": "/api/v2/policies",
            "json": {
                "agent_id": "agent_123",
                "policy_text": "Max 25 USDC per request",
            },
        },
    ]


def test_payment_action_reports_policy_block_without_success_claim() -> None:
    provider, fake_client = provider_with_fake_client()

    result = provider.send_payment(
        {
            "agent_id": "agent_123",
            "amount": "1000",
            "currency": "USDC",
            "recipient": "0xmerchant",
            "memo": "expensive data",
        }
    )

    assert result == "Payment BLOCKED by policy: daily limit exceeded"
    assert fake_client.requests == [
        {
            "method": "POST",
            "path": "/api/v2/payments",
            "json": {
                "agent_id": "agent_123",
                "amount": "1000",
                "currency": "USDC",
                "recipient": "0xmerchant",
                "memo": "expensive data",
            },
        }
    ]


def test_check_balance_formats_wallet_balances() -> None:
    provider, fake_client = provider_with_fake_client()

    result = provider.check_balance({"wallet_id": "wallet_123"})

    assert result == "Wallet wallet_123 balances:\n  USDC: 25.00\n  ETH: 0.01"
    assert fake_client.requests == [
        {"method": "GET", "path": "/api/v2/wallets/wallet_123/balance"}
    ]
