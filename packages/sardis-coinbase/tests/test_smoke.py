from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
import pytest
from sardis_coinbase import CoinbaseCDPProvider, PaymentPolicyDenied, X402Client


class FakeCDPProvider:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_usdc(self, cdp_wallet_id: str, to_address: str, amount_usdc: Decimal) -> str:
        self.sent.append(
            {
                "cdp_wallet_id": cdp_wallet_id,
                "to_address": to_address,
                "amount_usdc": amount_usdc,
            }
        )
        return "0xpaid"


class FakeHTTPClient:
    def __init__(self, challenge: dict[str, Any]) -> None:
        self.challenge = challenge
        self.retried: list[dict[str, Any]] = []
        self.closed = False

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(402, json=self.challenge)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        self.retried.append({"method": method, "url": url, "kwargs": kwargs})
        return httpx.Response(200, json={"ok": True})

    async def aclose(self) -> None:
        self.closed = True


def test_public_import_surface() -> None:
    assert CoinbaseCDPProvider.__name__ == "CoinbaseCDPProvider"
    assert X402Client.__name__ == "X402Client"
    assert issubclass(PaymentPolicyDenied, Exception)


def test_cdp_provider_requires_optional_sdk_when_not_installed() -> None:
    with pytest.raises(ImportError, match=r"cdp-sdk is required"):
        CoinbaseCDPProvider("api-key-name", "private-key")


@pytest.mark.asyncio
async def test_x402_client_checks_policy_before_payment_and_retries() -> None:
    provider = FakeCDPProvider()

    async def allow_policy(**kwargs: Any) -> tuple[bool, str]:
        assert kwargs == {
            "amount": Decimal("1.25"),
            "merchant": "https://merchant.test/data",
            "payment_type": "x402",
        }
        return True, "allowed"

    client = X402Client(provider, "wallet-123", allow_policy)
    fake_http = FakeHTTPClient(
        {
            "amount": "1.25",
            "recipient": "0xmerchant",
            "network": "base-sepolia",
        }
    )
    client._http = fake_http

    response = await client.get("https://merchant.test/data", headers={"Accept": "application/json"})

    assert response.status_code == 200
    assert provider.sent == [
        {
            "cdp_wallet_id": "wallet-123",
            "to_address": "0xmerchant",
            "amount_usdc": Decimal("1.25"),
        }
    ]
    assert fake_http.retried == [
        {
            "method": "GET",
            "url": "https://merchant.test/data",
            "kwargs": {
                "headers": {
                    "Accept": "application/json",
                    "X-Payment": "txHash=0xpaid,network=base-sepolia",
                }
            },
        }
    ]

    await client.close()
    assert fake_http.closed is True


@pytest.mark.asyncio
async def test_x402_client_denies_before_sending_payment() -> None:
    provider = FakeCDPProvider()

    async def deny_policy(**kwargs: Any) -> tuple[bool, str]:
        return False, "merchant blocked"

    client = X402Client(provider, "wallet-123", deny_policy)
    client._http = FakeHTTPClient({"amount": "2", "recipient": "0xmerchant"})

    with pytest.raises(PaymentPolicyDenied, match="merchant blocked"):
        await client.get("https://merchant.test/data")

    assert provider.sent == []
