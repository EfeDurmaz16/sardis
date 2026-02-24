"""Organization-aware card provider router."""

from __future__ import annotations

from decimal import Decimal
from typing import Awaitable, Callable, Optional

from .base import CardProvider
from ..models import Card, CardTransaction, CardType


WalletOrgResolver = Callable[[str], Awaitable[Optional[str]]]


class OrganizationCardProviderRouter(CardProvider):
    """Route card operations using org-specific providers with a default fallback."""

    def __init__(
        self,
        *,
        default_provider: CardProvider,
        providers_by_org: dict[str, CardProvider],
        wallet_org_resolver: WalletOrgResolver,
    ) -> None:
        self.default_provider = default_provider
        self.providers_by_org = providers_by_org
        self.wallet_org_resolver = wallet_org_resolver
        self._provider_by_card_id: dict[str, CardProvider] = {}

    @property
    def name(self) -> str:
        return f"org_router({self.default_provider.name})"

    async def resolve_provider_for_wallet(self, wallet_id: str) -> str:
        org_id = await self.wallet_org_resolver(wallet_id)
        if org_id and org_id in self.providers_by_org:
            return self.providers_by_org[org_id].name
        return self.default_provider.name

    def _register_card(self, card: Card, provider: CardProvider) -> None:
        if card.provider_card_id:
            self._provider_by_card_id[card.provider_card_id] = provider

    async def _provider_for_wallet(self, wallet_id: str) -> CardProvider:
        org_id = await self.wallet_org_resolver(wallet_id)
        if org_id and org_id in self.providers_by_org:
            return self.providers_by_org[org_id]
        return self.default_provider

    async def _resolve_provider_by_card(self, provider_card_id: str) -> CardProvider:
        known = self._provider_by_card_id.get(provider_card_id)
        if known is not None:
            return known

        candidates = [self.default_provider, *self.providers_by_org.values()]
        deduped: list[CardProvider] = []
        seen: set[int] = set()
        for candidate in candidates:
            marker = id(candidate)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(candidate)

        for candidate in deduped:
            try:
                card = await candidate.get_card(provider_card_id)
            except Exception:
                card = None
            if card:
                self._register_card(card, candidate)
                return candidate

        return self.default_provider

    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: Optional[str] = None,
    ) -> Card:
        provider = await self._provider_for_wallet(wallet_id)
        card = await provider.create_card(
            wallet_id=wallet_id,
            card_type=card_type,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
            locked_merchant_id=locked_merchant_id,
        )
        self._register_card(card, provider)
        return card

    async def get_card(self, provider_card_id: str) -> Optional[Card]:
        provider = await self._resolve_provider_by_card(provider_card_id)
        card = await provider.get_card(provider_card_id)
        if card:
            self._register_card(card, provider)
        return card

    async def activate_card(self, provider_card_id: str) -> Card:
        provider = await self._resolve_provider_by_card(provider_card_id)
        card = await provider.activate_card(provider_card_id)
        self._register_card(card, provider)
        return card

    async def freeze_card(self, provider_card_id: str) -> Card:
        provider = await self._resolve_provider_by_card(provider_card_id)
        card = await provider.freeze_card(provider_card_id)
        self._register_card(card, provider)
        return card

    async def unfreeze_card(self, provider_card_id: str) -> Card:
        provider = await self._resolve_provider_by_card(provider_card_id)
        card = await provider.unfreeze_card(provider_card_id)
        self._register_card(card, provider)
        return card

    async def cancel_card(self, provider_card_id: str) -> Card:
        provider = await self._resolve_provider_by_card(provider_card_id)
        card = await provider.cancel_card(provider_card_id)
        self._register_card(card, provider)
        return card

    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None,
    ) -> Card:
        provider = await self._resolve_provider_by_card(provider_card_id)
        card = await provider.update_limits(
            provider_card_id=provider_card_id,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
        )
        self._register_card(card, provider)
        return card

    async def fund_card(self, provider_card_id: str, amount: Decimal) -> Card:
        provider = await self._resolve_provider_by_card(provider_card_id)
        card = await provider.fund_card(provider_card_id=provider_card_id, amount=amount)
        self._register_card(card, provider)
        return card

    async def list_transactions(
        self,
        provider_card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        provider = await self._resolve_provider_by_card(provider_card_id)
        return await provider.list_transactions(
            provider_card_id=provider_card_id,
            limit=limit,
            offset=offset,
        )

    async def get_transaction(self, provider_tx_id: str) -> Optional[CardTransaction]:
        tx = await self.default_provider.get_transaction(provider_tx_id)
        if tx is not None:
            return tx
        candidates = [*self.providers_by_org.values()]
        deduped: list[CardProvider] = []
        seen: set[int] = set()
        for candidate in candidates:
            marker = id(candidate)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(candidate)
        for candidate in deduped:
            tx = await candidate.get_transaction(provider_tx_id)
            if tx is not None:
                return tx
        return None
