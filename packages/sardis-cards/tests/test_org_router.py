from __future__ import annotations

from decimal import Decimal

import pytest

from sardis_cards.models import Card, CardType
from sardis_cards.providers.base import CardProvider
from sardis_cards.providers.org_router import OrganizationCardProviderRouter


class FakeProvider(CardProvider):
    def __init__(self, name: str) -> None:
        self._name = name
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
async def test_org_router_uses_org_specific_provider_for_card_creation():
    default_provider = FakeProvider("lithic")
    org_provider = FakeProvider("rain")

    async def resolve_wallet_org(wallet_id: str) -> str | None:
        return "org_special" if wallet_id == "wallet_special" else "org_default"

    router = OrganizationCardProviderRouter(
        default_provider=default_provider,
        providers_by_org={"org_special": org_provider},
        wallet_org_resolver=resolve_wallet_org,
    )

    special = await router.create_card(
        wallet_id="wallet_special",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("10"),
        limit_daily=Decimal("100"),
        limit_monthly=Decimal("1000"),
    )
    regular = await router.create_card(
        wallet_id="wallet_regular",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("10"),
        limit_daily=Decimal("100"),
        limit_monthly=Decimal("1000"),
    )

    assert special.provider == "rain"
    assert regular.provider == "lithic"
    assert default_provider.calls.count("create_card") == 1
    assert org_provider.calls.count("create_card") == 1


@pytest.mark.asyncio
async def test_org_router_routes_existing_card_ops_by_provider_card_id():
    default_provider = FakeProvider("lithic")
    org_provider = FakeProvider("bridge_cards")

    async def resolve_wallet_org(wallet_id: str) -> str | None:
        return "org_bridge" if wallet_id == "wallet_bridge" else None

    router = OrganizationCardProviderRouter(
        default_provider=default_provider,
        providers_by_org={"org_bridge": org_provider},
        wallet_org_resolver=resolve_wallet_org,
    )

    bridge_card = await router.create_card(
        wallet_id="wallet_bridge",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("20"),
        limit_daily=Decimal("200"),
        limit_monthly=Decimal("2000"),
    )

    await router.freeze_card(bridge_card.provider_card_id)

    assert org_provider.calls.count("freeze_card") == 1
    assert default_provider.calls.count("freeze_card") == 0


@pytest.mark.asyncio
async def test_org_router_resolve_provider_for_wallet():
    default_provider = FakeProvider("lithic")
    org_provider = FakeProvider("stripe_issuing")

    async def resolve_wallet_org(wallet_id: str) -> str | None:
        return "org_stripe" if wallet_id.startswith("wallet_s") else None

    router = OrganizationCardProviderRouter(
        default_provider=default_provider,
        providers_by_org={"org_stripe": org_provider},
        wallet_org_resolver=resolve_wallet_org,
    )

    assert await router.resolve_provider_for_wallet("wallet_special") == "stripe_issuing"
    assert await router.resolve_provider_for_wallet("wallet_default") == "lithic"
