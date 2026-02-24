"""Card provider router for primary/fallback issuer failover."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from .base import CardProvider
from ..models import Card, CardTransaction, CardType


class CardProviderRouter(CardProvider):
    """
    Route card operations between primary and fallback providers.

    Behavior:
    - New card issuance uses primary first, then fallback on error.
    - Existing card operations resolve provider by provider_card_id.
    - Unknown cards are probed against primary then fallback.
    """

    def __init__(self, primary: CardProvider, fallback: Optional[CardProvider] = None) -> None:
        self.primary = primary
        self.fallback = fallback
        self._provider_by_card_id: dict[str, CardProvider] = {}

    @property
    def name(self) -> str:
        if self.fallback is None:
            return self.primary.name
        return f"router({self.primary.name}->{self.fallback.name})"

    def _register_card(self, card: Card, provider: CardProvider) -> None:
        if card.provider_card_id:
            self._provider_by_card_id[card.provider_card_id] = provider

    async def _resolve_provider(self, provider_card_id: str) -> CardProvider:
        resolved = self._provider_by_card_id.get(provider_card_id)
        if resolved is not None:
            return resolved

        for candidate in (self.primary, self.fallback):
            if candidate is None:
                continue
            try:
                card = await candidate.get_card(provider_card_id)
            except Exception:
                card = None
            if card:
                self._register_card(card, candidate)
                return candidate

        return self.primary

    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: Optional[str] = None,
    ) -> Card:
        last_error: Exception | None = None
        for provider in (self.primary, self.fallback):
            if provider is None:
                continue
            try:
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
            except Exception as exc:
                last_error = exc
                if provider is self.primary and self.fallback is not None:
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("No card provider available")

    async def get_card(self, provider_card_id: str) -> Optional[Card]:
        provider = await self._resolve_provider(provider_card_id)
        card = await provider.get_card(provider_card_id)
        if card:
            self._register_card(card, provider)
            return card
        if provider is self.primary and self.fallback is not None:
            card = await self.fallback.get_card(provider_card_id)
            if card:
                self._register_card(card, self.fallback)
            return card
        return None

    async def activate_card(self, provider_card_id: str) -> Card:
        provider = await self._resolve_provider(provider_card_id)
        card = await provider.activate_card(provider_card_id)
        self._register_card(card, provider)
        return card

    async def freeze_card(self, provider_card_id: str) -> Card:
        provider = await self._resolve_provider(provider_card_id)
        card = await provider.freeze_card(provider_card_id)
        self._register_card(card, provider)
        return card

    async def unfreeze_card(self, provider_card_id: str) -> Card:
        provider = await self._resolve_provider(provider_card_id)
        card = await provider.unfreeze_card(provider_card_id)
        self._register_card(card, provider)
        return card

    async def cancel_card(self, provider_card_id: str) -> Card:
        provider = await self._resolve_provider(provider_card_id)
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
        provider = await self._resolve_provider(provider_card_id)
        card = await provider.update_limits(
            provider_card_id=provider_card_id,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
        )
        self._register_card(card, provider)
        return card

    async def fund_card(self, provider_card_id: str, amount: Decimal) -> Card:
        provider = await self._resolve_provider(provider_card_id)
        card = await provider.fund_card(provider_card_id=provider_card_id, amount=amount)
        self._register_card(card, provider)
        return card

    async def list_transactions(
        self,
        provider_card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        provider = await self._resolve_provider(provider_card_id)
        return await provider.list_transactions(
            provider_card_id=provider_card_id,
            limit=limit,
            offset=offset,
        )

    async def get_transaction(self, provider_tx_id: str) -> Optional[CardTransaction]:
        tx = await self.primary.get_transaction(provider_tx_id)
        if tx is not None:
            return tx
        if self.fallback is not None:
            return await self.fallback.get_transaction(provider_tx_id)
        return None
