from __future__ import annotations

from decimal import Decimal
from typing import Optional

import httpx
import pytest

from sardis_cards.models import Card, CardStatus, CardType
from sardis_cards.providers.base import CardProvider
from sardis_cards.providers.partner_issuers import BridgeCardsProvider, RainCardsProvider
from sardis_cards.providers.router import CardProviderRouter


class _FakeProvider(CardProvider):
    def __init__(self, name: str, *, fail_create: bool = False) -> None:
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
        locked_merchant_id: Optional[str] = None,
    ) -> Card:
        self.calls.append("create_card")
        if self._fail_create:
            raise RuntimeError(f"{self._name}_create_failed")
        provider_card_id = f"{self._name}_card_{len(self.cards) + 1}"
        card = Card(
            wallet_id=wallet_id,
            provider=self._name,
            provider_card_id=provider_card_id,
            card_type=card_type,
            status=CardStatus.PENDING,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
            locked_merchant_id=locked_merchant_id,
        )
        self.cards[provider_card_id] = card
        return card

    async def get_card(self, provider_card_id: str) -> Optional[Card]:
        self.calls.append("get_card")
        return self.cards.get(provider_card_id)

    async def activate_card(self, provider_card_id: str) -> Card:
        self.calls.append("activate_card")
        card = self.cards[provider_card_id]
        card.status = CardStatus.ACTIVE
        return card

    async def freeze_card(self, provider_card_id: str) -> Card:
        self.calls.append("freeze_card")
        card = self.cards[provider_card_id]
        card.status = CardStatus.FROZEN
        return card

    async def unfreeze_card(self, provider_card_id: str) -> Card:
        self.calls.append("unfreeze_card")
        card = self.cards[provider_card_id]
        card.status = CardStatus.ACTIVE
        return card

    async def cancel_card(self, provider_card_id: str) -> Card:
        self.calls.append("cancel_card")
        card = self.cards[provider_card_id]
        card.status = CardStatus.CANCELLED
        return card

    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None,
    ) -> Card:
        self.calls.append("update_limits")
        card = self.cards[provider_card_id]
        if limit_per_tx is not None:
            card.limit_per_tx = limit_per_tx
        if limit_daily is not None:
            card.limit_daily = limit_daily
        if limit_monthly is not None:
            card.limit_monthly = limit_monthly
        return card

    async def fund_card(self, provider_card_id: str, amount: Decimal) -> Card:
        self.calls.append("fund_card")
        card = self.cards[provider_card_id]
        card.funded_amount += amount
        return card

    async def list_transactions(self, provider_card_id: str, limit: int = 50, offset: int = 0):
        self.calls.append("list_transactions")
        return []

    async def get_transaction(self, provider_tx_id: str):
        self.calls.append("get_transaction")
        return None


def _make_partner_provider(provider: str):
    if provider == "rain":
        return RainCardsProvider(api_key="rain_test_key", program_id="rain_program")
    if provider == "bridge_cards":
        return BridgeCardsProvider(api_key="bridge_test_key", api_secret="bridge_secret")
    raise ValueError(f"unknown provider={provider}")


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["rain", "bridge_cards"])
async def test_partner_provider_contract_freeze_rotate(provider_name: str):
    provider = _make_partner_provider(provider_name)
    state: dict[str, dict[str, str]] = {}

    async def fake_send(operation: str, *, path_params=None, payload=None, query=None):
        card_id = (path_params or {}).get("card_id")
        if operation == "create_card":
            cid = f"{provider_name}_card_1"
            state[cid] = {"status": "pending", "funded_amount": "0.00"}
            return {
                "id": cid,
                "status": "pending",
                "limits": {"per_tx": "50", "daily": "200", "monthly": "1000"},
                "last4": "4242",
                "exp_month": 12,
                "exp_year": 2030,
                "type": "virtual",
            }
        if operation == "activate_card":
            state[card_id]["status"] = "active"
            return {"id": card_id, "status": "active"}
        if operation == "freeze_card":
            state[card_id]["status"] = "paused"
            return {"id": card_id, "status": "paused"}
        if operation == "unfreeze_card":
            state[card_id]["status"] = "active"
            return {"id": card_id, "status": "active"}
        if operation == "cancel_card":
            state[card_id]["status"] = "cancelled"
            return {"id": card_id, "status": "cancelled"}
        if operation == "fund_card":
            current = Decimal(state[card_id]["funded_amount"])
            state[card_id]["funded_amount"] = str(current + Decimal(payload["amount"]))
            return {"id": card_id, "status": state[card_id]["status"], "funded_amount": state[card_id]["funded_amount"]}
        if operation == "get_card":
            if card_id not in state:
                return {}
            return {"id": card_id, "status": state[card_id]["status"], "funded_amount": state[card_id]["funded_amount"]}
        return {}

    provider._send = fake_send  # type: ignore[method-assign]

    created = await provider.create_card(
        wallet_id="wallet_contract",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("50"),
        limit_daily=Decimal("200"),
        limit_monthly=Decimal("1000"),
    )
    assert created.provider == provider_name
    assert created.status == CardStatus.PENDING

    activated = await provider.activate_card(created.provider_card_id)
    assert activated.status == CardStatus.ACTIVE

    frozen = await provider.freeze_card(created.provider_card_id)
    assert frozen.status == CardStatus.FROZEN

    unfrozen = await provider.unfreeze_card(created.provider_card_id)
    assert unfrozen.status == CardStatus.ACTIVE

    funded = await provider.fund_card(created.provider_card_id, Decimal("20.25"))
    assert funded.funded_amount >= Decimal("20.25")
    assert funded.last_funded_at is not None

    cancelled = await provider.cancel_card(created.provider_card_id)
    assert cancelled.status == CardStatus.CANCELLED


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["rain", "bridge_cards"])
async def test_partner_provider_contract_surfaces_timeout(provider_name: str):
    provider = _make_partner_provider(provider_name)

    async def timeout_send(*args, **kwargs):
        raise httpx.ReadTimeout("provider timeout")

    provider._send = timeout_send  # type: ignore[method-assign]

    with pytest.raises(httpx.ReadTimeout):
        await provider.list_transactions("card_timeout")


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["rain", "bridge_cards"])
async def test_partner_provider_contract_funding_failure(provider_name: str):
    provider = _make_partner_provider(provider_name)

    async def fake_send(operation: str, *, path_params=None, payload=None, query=None):
        if operation == "create_card":
            return {
                "id": f"{provider_name}_fund_fail_1",
                "status": "active",
                "limits": {"per_tx": "40", "daily": "100", "monthly": "500"},
                "last4": "1001",
                "exp_month": 1,
                "exp_year": 2031,
                "type": "virtual",
            }
        if operation == "fund_card":
            raise RuntimeError("funding_downstream_failed")
        return {"id": (path_params or {}).get("card_id", "unknown"), "status": "active"}

    provider._send = fake_send  # type: ignore[method-assign]

    card = await provider.create_card(
        wallet_id="wallet_contract",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("40"),
        limit_daily=Decimal("100"),
        limit_monthly=Decimal("500"),
    )
    with pytest.raises(RuntimeError, match="funding_downstream_failed"):
        await provider.fund_card(card.provider_card_id, Decimal("5.00"))


@pytest.mark.asyncio
async def test_stripe_lithic_router_contract_failover():
    primary = _FakeProvider("lithic", fail_create=True)
    fallback = _FakeProvider("stripe_issuing")
    router = CardProviderRouter(primary=primary, fallback=fallback)

    created = await router.create_card(
        wallet_id="wallet_router",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("20"),
        limit_daily=Decimal("100"),
        limit_monthly=Decimal("500"),
    )
    assert created.provider == "stripe_issuing"
    assert primary.calls.count("create_card") == 1
    assert fallback.calls.count("create_card") == 1

    await router.freeze_card(created.provider_card_id)
    assert fallback.calls.count("freeze_card") == 1
    assert primary.calls.count("freeze_card") == 0
