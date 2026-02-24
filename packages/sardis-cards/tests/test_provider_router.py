from __future__ import annotations

from decimal import Decimal

import pytest

from sardis_cards.models import Card, CardType
from sardis_cards.providers.base import CardProvider
from sardis_cards.providers.router import CardProviderRouter


class FakeProvider(CardProvider):
    def __init__(self, name: str, fail_create: bool = False) -> None:
        self._name = name
        self._fail_create = fail_create
        self.cards: dict[str, Card] = {}
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: str | None = None,
    ) -> Card:
        self.calls.append("create_card")
        if self._fail_create:
            raise RuntimeError(f"{self.name} create failed")
        provider_card_id = f"{self.name}_card_{len(self.cards) + 1}"
        card = Card(
            wallet_id=wallet_id,
            provider=self.name,
            provider_card_id=provider_card_id,
            card_type=card_type,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
        )
        self.cards[provider_card_id] = card
        return card

    async def get_card(self, provider_card_id: str):
        self.calls.append("get_card")
        return self.cards.get(provider_card_id)

    async def activate_card(self, provider_card_id: str) -> Card:
        self.calls.append("activate_card")
        return self.cards[provider_card_id]

    async def freeze_card(self, provider_card_id: str) -> Card:
        self.calls.append("freeze_card")
        return self.cards[provider_card_id]

    async def unfreeze_card(self, provider_card_id: str) -> Card:
        self.calls.append("unfreeze_card")
        return self.cards[provider_card_id]

    async def cancel_card(self, provider_card_id: str) -> Card:
        self.calls.append("cancel_card")
        return self.cards[provider_card_id]

    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Decimal | None = None,
        limit_daily: Decimal | None = None,
        limit_monthly: Decimal | None = None,
    ) -> Card:
        self.calls.append("update_limits")
        return self.cards[provider_card_id]

    async def fund_card(self, provider_card_id: str, amount: Decimal) -> Card:
        self.calls.append("fund_card")
        return self.cards[provider_card_id]

    async def list_transactions(self, provider_card_id: str, limit: int = 50, offset: int = 0):
        self.calls.append("list_transactions")
        return []

    async def get_transaction(self, provider_tx_id: str):
        self.calls.append("get_transaction")
        return None


@pytest.mark.asyncio
async def test_create_card_falls_back_when_primary_fails():
    primary = FakeProvider("lithic", fail_create=True)
    fallback = FakeProvider("stripe_issuing")
    router = CardProviderRouter(primary=primary, fallback=fallback)

    card = await router.create_card(
        wallet_id="wallet_1",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("10"),
        limit_daily=Decimal("100"),
        limit_monthly=Decimal("1000"),
    )

    assert card.provider == "stripe_issuing"
    assert "create_card" in primary.calls
    assert "create_card" in fallback.calls


@pytest.mark.asyncio
async def test_existing_card_routes_to_primary_provider():
    primary = FakeProvider("lithic")
    fallback = FakeProvider("stripe_issuing")
    router = CardProviderRouter(primary=primary, fallback=fallback)

    created = await router.create_card(
        wallet_id="wallet_1",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("10"),
        limit_daily=Decimal("100"),
        limit_monthly=Decimal("1000"),
    )

    await router.freeze_card(created.provider_card_id)

    assert primary.calls.count("freeze_card") == 1
    assert fallback.calls.count("freeze_card") == 0


@pytest.mark.asyncio
async def test_probe_routes_unknown_card_to_fallback():
    primary = FakeProvider("lithic")
    fallback = FakeProvider("stripe_issuing")
    router = CardProviderRouter(primary=primary, fallback=fallback)

    fallback_card = await fallback.create_card(
        wallet_id="wallet_2",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("20"),
        limit_daily=Decimal("200"),
        limit_monthly=Decimal("2000"),
    )

    resolved = await router.get_card(fallback_card.provider_card_id)

    assert resolved is not None
    assert resolved.provider == "stripe_issuing"
