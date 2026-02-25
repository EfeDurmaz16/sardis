from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from sardis_v2_core.funding import FundingRequest, StripeIssuingFundingAdapter


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
