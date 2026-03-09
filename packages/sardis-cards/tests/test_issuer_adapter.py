from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from sardis_cards.models import CardType
from sardis_cards.providers.issuer_adapter import IssuerAdapterShim, build_issuer_adapter


class _LegacyProvider:
    name = "legacy_provider"

    async def create_card(
        self,
        *,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        reuse_cardholder_id: str | None = None,
    ):
        return SimpleNamespace(
            provider="legacy_provider",
            provider_card_id="card_123",
            wallet_id=wallet_id,
            status="pending",
            card_type=card_type.value,
            limit_per_tx=str(limit_per_tx),
            limit_daily=str(limit_daily),
            limit_monthly=str(limit_monthly),
            reuse_cardholder_id=reuse_cardholder_id,
        )

    async def freeze_card(self, provider_card_id: str):
        return {"provider_card_id": provider_card_id, "status": "frozen"}

    async def unfreeze_card(self, provider_card_id: str):
        return {"provider_card_id": provider_card_id, "status": "active"}

    async def cancel_card(self, provider_card_id: str):
        return {"provider_card_id": provider_card_id, "status": "cancelled"}


@pytest.mark.asyncio
async def test_issuer_adapter_shim_maps_legacy_create_card():
    shim = IssuerAdapterShim(_LegacyProvider())
    cardholder = await shim.create_cardholder(wallet_id="wallet_1", cardholder_email="owner@example.com")
    card = await shim.create_virtual_card(
        wallet_id="wallet_1",
        cardholder_id=cardholder["cardholder_id"],
        limit_per_tx=Decimal("50"),
        limit_daily=Decimal("200"),
        limit_monthly=Decimal("1000"),
    )
    assert card["provider"] == "legacy_provider"
    assert card["provider_card_id"] == "card_123"
    assert card["reuse_cardholder_id"] == cardholder["cardholder_id"]


@pytest.mark.asyncio
async def test_issuer_adapter_shim_authorize_is_explicit_when_unsupported():
    shim = IssuerAdapterShim(_LegacyProvider())
    result = await shim.authorize(
        provider_card_id="card_123",
        amount=Decimal("10.25"),
        merchant_name="Test Merchant",
    )
    assert result["status"] == "unsupported"
    assert result["reason"] == "provider_authorization_not_exposed"


def test_build_issuer_adapter_wraps_legacy_provider():
    wrapped = build_issuer_adapter(_LegacyProvider())
    assert isinstance(wrapped, IssuerAdapterShim)

