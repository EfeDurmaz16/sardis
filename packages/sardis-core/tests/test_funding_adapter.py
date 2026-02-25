from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from sardis_v2_core.funding import (
    FundingRequest,
    FundingResult,
    FundingRoutingError,
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
