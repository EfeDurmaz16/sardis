from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from sardis_v2_core.cpn_funding_adapter import CircleCPNFundingAdapter
from sardis_v2_core.funding import FundingRequest


class _FakeHttpClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method: str, url: str, *, headers=None, json=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers or {},
                "json": json or {},
            }
        )
        return self._response


@pytest.mark.asyncio
async def test_circle_cpn_funding_adapter_normalizes_result(monkeypatch):
    response = httpx.Response(
        200,
        json={
            "payment_id": "cpn_pay_123",
            "amount": "42.50",
            "currency": "usd",
            "status": "queued",
            "metadata": {"source": "test"},
        },
        request=httpx.Request("POST", "https://api.circle.com/v1/cpn/payments"),
    )
    fake = _FakeHttpClient(response)
    monkeypatch.setattr(
        "sardis_v2_core.cpn_funding_adapter.httpx.AsyncClient",
        lambda *args, **kwargs: fake,
    )

    adapter = CircleCPNFundingAdapter(
        api_key="cpn_key",
        base_url="https://api.circle.com",
        payout_path="/v1/cpn/payments",
        status_path="/v1/cpn/payments/{payment_id}",
    )

    result = await adapter.fund(
        FundingRequest(
            amount=Decimal("42.50"),
            currency="USD",
            description="Topup",
            metadata={"org_id": "org_demo"},
        )
    )

    assert result.provider == "circle_cpn"
    assert result.rail == "fiat"
    assert result.transfer_id == "cpn_pay_123"
    assert result.amount == Decimal("42.50")
    assert result.currency == "USD"
    assert result.status == "queued"
    assert fake.calls[0]["url"] == "https://api.circle.com/v1/cpn/payments"


@pytest.mark.asyncio
async def test_circle_cpn_status_replaces_payment_id(monkeypatch):
    response = httpx.Response(
        200,
        json={
            "id": "cpn_pay_456",
            "status": "settled",
        },
        request=httpx.Request("GET", "https://api.circle.com/v1/cpn/payments/cpn_pay_456"),
    )
    fake = _FakeHttpClient(response)
    monkeypatch.setattr(
        "sardis_v2_core.cpn_funding_adapter.httpx.AsyncClient",
        lambda *args, **kwargs: fake,
    )

    adapter = CircleCPNFundingAdapter(
        api_key="cpn_key",
        base_url="https://api.circle.com",
        payout_path="/v1/cpn/payments",
        status_path="/v1/cpn/payments/{payment_id}",
    )

    status = await adapter.status("cpn_pay_456")
    assert status["id"] == "cpn_pay_456"
    assert status["status"] == "settled"
    assert fake.calls[0]["url"] == "https://api.circle.com/v1/cpn/payments/cpn_pay_456"
