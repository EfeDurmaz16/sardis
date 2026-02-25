"""Adapter bridging sardis-api card router expectations with sardis-cards providers."""
from __future__ import annotations

from decimal import Decimal

from sardis_cards.models import CardType


class CardProviderCompatAdapter:
    """
    Bridge sardis-api's cards router interface with sardis-cards providers.

    The router expects:
      - create_card(card_id=..., wallet_id=..., card_type=str, limit_*: float) -> obj
      - fund_card(card_id=..., amount=float)
    While the provider expects:
      - create_card(wallet_id, card_type: CardType, limit_*: Decimal, ...)
      - fund_card(provider_card_id, amount: Decimal, ...)
    """

    def __init__(self, provider, repo):
        self._provider = provider
        self._repo = repo

    async def create_card(
        self,
        card_id: str,
        wallet_id: str,
        card_type: str,
        limit_per_tx: float,
        limit_daily: float,
        limit_monthly: float,
        locked_merchant_id: str | None = None,
    ):
        ct = {
            "single_use": CardType.SINGLE_USE,
            "multi_use": CardType.MULTI_USE,
            "merchant_locked": CardType.MERCHANT_LOCKED,
        }.get(card_type, CardType.MULTI_USE)
        return await self._provider.create_card(
            wallet_id=wallet_id,
            card_type=ct,
            limit_per_tx=Decimal(str(limit_per_tx)),
            limit_daily=Decimal(str(limit_daily)),
            limit_monthly=Decimal(str(limit_monthly)),
            locked_merchant_id=locked_merchant_id,
        )

    async def fund_card(self, card_id: str, amount: float):
        card = await self._repo.get_by_card_id(card_id)
        if not card or not card.get("provider_card_id"):
            raise RuntimeError("Card not found or missing provider_card_id")
        return await self._provider.fund_card(
            provider_card_id=card["provider_card_id"],
            amount=Decimal(str(amount)),
        )

    async def freeze_card(self, provider_card_id: str):
        return await self._provider.freeze_card(provider_card_id)

    async def unfreeze_card(self, provider_card_id: str):
        return await self._provider.unfreeze_card(provider_card_id)

    async def cancel_card(self, provider_card_id: str):
        return await self._provider.cancel_card(provider_card_id)

    async def update_limits(self, provider_card_id: str, **kwargs):
        return await self._provider.update_limits(provider_card_id, **kwargs)

    async def simulate_authorization(
        self,
        provider_card_id: str,
        amount_cents: int,
        merchant_descriptor: str = "Demo Merchant",
    ):
        if hasattr(self._provider, "simulate_authorization"):
            return await self._provider.simulate_authorization(
                provider_card_id=provider_card_id,
                amount_cents=amount_cents,
                merchant_descriptor=merchant_descriptor,
            )
        return None

    async def reveal_card_details(
        self,
        card_id: str,
        *,
        reason: str = "secure_checkout_executor",
    ) -> dict:
        """
        Resolve an internal card_id to provider_card_id and reveal details just-in-time.

        This method deliberately returns raw details only to trusted internal callers.
        It should never be exposed directly on public APIs.
        """
        card = await self._repo.get_by_card_id(card_id)
        if not card or not card.get("provider_card_id"):
            raise RuntimeError("Card not found or missing provider_card_id")

        provider_reveal = getattr(self._provider, "reveal_card_details", None)
        if not callable(provider_reveal):
            provider_name = str(getattr(self._provider, "name", "unknown"))
            raise RuntimeError(f"Provider does not support JIT reveal: {provider_name}")

        details = await provider_reveal(
            provider_card_id=card["provider_card_id"],
            reason=reason,
        )
        if not isinstance(details, dict):
            raise RuntimeError("Provider returned invalid card details payload")

        pan = str(details.get("pan") or "")
        if not pan:
            raise RuntimeError("Provider did not return PAN")

        exp_month = int(details.get("exp_month") or details.get("expiry_month") or 0)
        exp_year = int(details.get("exp_year") or details.get("expiry_year") or 0)
        cvv = str(details.get("cvv") or details.get("cvc") or "")
        return {
            "pan": pan,
            "cvv": cvv,
            "exp_month": exp_month,
            "exp_year": exp_year,
        }
