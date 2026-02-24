from __future__ import annotations

from decimal import Decimal

import pytest

from sardis_v2_core.stripe_treasury import StripeTreasuryProvider, TransferStatus


class _FakeTopupAPI:
    @staticmethod
    def create(**kwargs):
        return {
            "id": "tu_test_123",
            "status": "succeeded",
            "currency": kwargs.get("currency", "usd"),
        }


class _FakeStripe:
    Topup = _FakeTopupAPI


@pytest.mark.asyncio
async def test_fund_issuing_balance_creates_topup():
    provider = StripeTreasuryProvider(
        stripe_secret_key="sk_test_123",
        financial_account_id="fa_123",
    )
    provider._stripe = _FakeStripe  # type: ignore[attr-defined]

    transfer = await provider.fund_issuing_balance(amount=Decimal("12.34"))

    assert transfer.id == "tu_test_123"
    assert transfer.amount == Decimal("12.34")
    assert transfer.status == TransferStatus.POSTED


@pytest.mark.asyncio
async def test_fund_issuing_balance_rejects_non_positive_amount():
    provider = StripeTreasuryProvider(
        stripe_secret_key="sk_test_123",
        financial_account_id="fa_123",
    )
    provider._stripe = _FakeStripe  # type: ignore[attr-defined]

    with pytest.raises(ValueError):
        await provider.fund_issuing_balance(amount=Decimal("0"))


@pytest.mark.asyncio
async def test_fund_issuing_balance_requires_stripe_sdk():
    provider = StripeTreasuryProvider(
        stripe_secret_key="sk_test_123",
        financial_account_id="fa_123",
    )
    provider._stripe = None  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError, match="Stripe SDK is not available"):
        await provider.fund_issuing_balance(amount=Decimal("1.00"))
