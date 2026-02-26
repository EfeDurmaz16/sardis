from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from sardis_v2_core.funding import (
    FundingRequest,
    FundingResult,
    FundingRoutingError,
    HttpTopupFundingAdapter,
    StripeIssuingFundingAdapter,
    execute_funding_with_failover,
)


class _FakeTreasuryProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def fund_issuing_balance(
        self,
        *,
        amount: Decimal,
        description: str,
        connected_account_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> object:
        self.calls.append(
            {
                "amount": amount,
                "description": description,
                "connected_account_id": connected_account_id,
                "metadata": metadata,
            }
        )
        return SimpleNamespace(
            id="tu_test_42",
            amount=amount,
            currency="usd",
            status="posted",
        )


@pytest.mark.asyncio
async def test_stripe_issuing_funding_adapter_normalizes_result():
    treasury = _FakeTreasuryProvider()
    adapter = StripeIssuingFundingAdapter(treasury)

    result = await adapter.fund(
        FundingRequest(
            amount=Decimal("9.50"),
            description="Top-up",
            connected_account_id="acct_123",
            metadata={"org_id": "org_demo"},
        )
    )

    assert result.provider == "stripe"
    assert result.rail == "fiat"
    assert result.transfer_id == "tu_test_42"
    assert result.amount == Decimal("9.50")
    assert result.currency == "USD"
    assert result.status == "posted"
    assert treasury.calls[0]["connected_account_id"] == "acct_123"


class _FailingAdapter:
    provider = "lithic"
    rail = "fiat"

    async def fund(self, request: FundingRequest) -> FundingResult:
        raise RuntimeError("provider_down")


class _SuccessAdapter:
    provider = "stripe"
    rail = "fiat"

    async def fund(self, request: FundingRequest) -> FundingResult:
        return FundingResult(
            provider=self.provider,
            rail=self.rail,
            transfer_id="tu_ok",
            amount=request.amount,
            currency=request.currency,
            status="posted",
        )


@pytest.mark.asyncio
async def test_execute_funding_with_failover_uses_deterministic_order():
    request = FundingRequest(amount=Decimal("3.25"))
    result, attempts = await execute_funding_with_failover(
        [_FailingAdapter(), _SuccessAdapter()],
        request,
    )

    assert result.transfer_id == "tu_ok"
    assert len(attempts) == 2
    assert attempts[0].provider == "lithic"
    assert attempts[0].status == "failed"
    assert attempts[1].provider == "stripe"
    assert attempts[1].status == "success"


@pytest.mark.asyncio
async def test_execute_funding_with_failover_raises_when_all_fail():
    request = FundingRequest(amount=Decimal("1.00"))
    with pytest.raises(FundingRoutingError) as exc_info:
        await execute_funding_with_failover([_FailingAdapter()], request)
    assert exc_info.value.attempts
    assert exc_info.value.attempts[0].status == "failed"


class _FakeHttpClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, *, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers or {}, "json": json or {}})
        return self._response


@pytest.mark.asyncio
async def test_http_topup_funding_adapter_normalizes_json(monkeypatch):
    payload = {
        "id": "topup_900",
        "amount": "12.75",
        "currency": "usd",
        "status": "posted",
        "metadata": {"source": "test"},
    }
    response = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("POST", "https://api.rain.xyz/v1/funding/topups"),
    )
    fake = _FakeHttpClient(response)

    monkeypatch.setattr(
        "sardis_v2_core.funding.httpx.AsyncClient",
        lambda *args, **kwargs: fake,
    )

    adapter = HttpTopupFundingAdapter(
        provider="rain",
        rail="stablecoin",
        base_url="https://api.rain.xyz",
        api_key="rain_key",
        topup_path="/v1/funding/topups",
        program_id="rain_program",
    )

    result = await adapter.fund(
        FundingRequest(
            amount=Decimal("12.75"),
            currency="USD",
            description="Test topup",
            metadata={"org_id": "org_demo"},
        )
    )

    assert result.provider == "rain"
    assert result.rail == "stablecoin"
    assert result.transfer_id == "topup_900"
    assert result.amount == Decimal("12.75")
    assert result.currency == "USD"
    assert result.status == "posted"
    assert fake.calls
    assert fake.calls[0]["url"] == "https://api.rain.xyz/v1/funding/topups"
    assert fake.calls[0]["headers"]["X-Program-Id"] == "rain_program"


@pytest.mark.asyncio
async def test_http_topup_funding_adapter_surfaces_http_error(monkeypatch):
    response = httpx.Response(
        503,
        json={"error": "downstream unavailable"},
        request=httpx.Request("POST", "https://api.bridge.xyz/v1/funding/topups"),
    )
    fake = _FakeHttpClient(response)

    monkeypatch.setattr(
        "sardis_v2_core.funding.httpx.AsyncClient",
        lambda *args, **kwargs: fake,
    )

    adapter = HttpTopupFundingAdapter(
        provider="bridge",
        rail="fiat",
        base_url="https://api.bridge.xyz",
        api_key="bridge_key",
        auth_style="x_api_key",
    )

    with pytest.raises(httpx.HTTPStatusError):
        await adapter.fund(FundingRequest(amount=Decimal("1.00")))
