"""Cards resource for Sardis SDK."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from ..models.card import Card, CardTransaction, SimulateCardPurchaseResponse
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    import builtins

    from ..client import TimeoutConfig


class AsyncCardsResource(AsyncBaseResource):
    async def issue(
        self,
        *,
        wallet_id: str,
        card_type: str = "multi_use",
        limit_per_tx: Decimal = Decimal("500.00"),
        limit_daily: Decimal = Decimal("2000.00"),
        limit_monthly: Decimal = Decimal("10000.00"),
        locked_merchant_id: str | None = None,
        funding_source: str = "stablecoin",
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        payload: dict[str, Any] = {
            "wallet_id": wallet_id,
            "card_type": card_type,
            "limit_per_tx": str(limit_per_tx),
            "limit_daily": str(limit_daily),
            "limit_monthly": str(limit_monthly),
            "locked_merchant_id": locked_merchant_id,
            "funding_source": funding_source,
        }
        data = await self._post("cards", payload, timeout=timeout)
        return Card.model_validate(data)

    async def list(
        self,
        wallet_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[Card]:
        params: dict[str, Any] = {}
        if wallet_id:
            params["wallet_id"] = wallet_id
        data = await self._get("cards", params=params or None, timeout=timeout)
        if isinstance(data, list):
            return [Card.model_validate(item) for item in data]
        return [Card.model_validate(item) for item in data.get("cards", [])]

    async def get(
        self,
        card_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        data = await self._get(f"cards/{card_id}", timeout=timeout)
        return Card.model_validate(data)

    async def freeze(
        self,
        card_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        data = await self._post(f"cards/{card_id}/freeze", {}, timeout=timeout)
        return Card.model_validate(data)

    async def unfreeze(
        self,
        card_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        data = await self._post(f"cards/{card_id}/unfreeze", {}, timeout=timeout)
        return Card.model_validate(data)

    async def cancel(
        self,
        card_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> None:
        await self._delete(f"cards/{card_id}", timeout=timeout)

    async def update_limits(
        self,
        card_id: str,
        *,
        limit_per_tx: Decimal | None = None,
        limit_daily: Decimal | None = None,
        limit_monthly: Decimal | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        payload: dict[str, Any] = {}
        if limit_per_tx is not None:
            payload["limit_per_tx"] = str(limit_per_tx)
        if limit_daily is not None:
            payload["limit_daily"] = str(limit_daily)
        if limit_monthly is not None:
            payload["limit_monthly"] = str(limit_monthly)
        data = await self._patch(f"cards/{card_id}/limits", payload, timeout=timeout)
        return Card.model_validate(data)

    async def transactions(
        self,
        card_id: str,
        limit: int = 50,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[CardTransaction]:
        data = await self._get(f"cards/{card_id}/transactions", params={"limit": limit}, timeout=timeout)
        if isinstance(data, list):
            return [CardTransaction.model_validate(item) for item in data]
        return [CardTransaction.model_validate(item) for item in data.get("transactions", [])]

    async def simulate_purchase(
        self,
        card_id: str,
        *,
        amount: Decimal,
        currency: str = "USD",
        merchant_name: str = "Demo Merchant",
        mcc_code: str = "5734",
        status: str = "approved",
        decline_reason: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> SimulateCardPurchaseResponse:
        payload = {
            "amount": str(amount),
            "currency": currency,
            "merchant_name": merchant_name,
            "mcc_code": mcc_code,
            "status": status,
            "decline_reason": decline_reason,
        }
        data = await self._post(f"cards/{card_id}/simulate-purchase", payload, timeout=timeout)
        return SimulateCardPurchaseResponse.model_validate(data)


class CardsResource(SyncBaseResource):
    def issue(
        self,
        *,
        wallet_id: str,
        card_type: str = "multi_use",
        limit_per_tx: Decimal = Decimal("500.00"),
        limit_daily: Decimal = Decimal("2000.00"),
        limit_monthly: Decimal = Decimal("10000.00"),
        locked_merchant_id: str | None = None,
        funding_source: str = "stablecoin",
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        payload: dict[str, Any] = {
            "wallet_id": wallet_id,
            "card_type": card_type,
            "limit_per_tx": str(limit_per_tx),
            "limit_daily": str(limit_daily),
            "limit_monthly": str(limit_monthly),
            "locked_merchant_id": locked_merchant_id,
            "funding_source": funding_source,
        }
        data = self._post("cards", payload, timeout=timeout)
        return Card.model_validate(data)

    def list(
        self,
        wallet_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[Card]:
        params: dict[str, Any] = {}
        if wallet_id:
            params["wallet_id"] = wallet_id
        data = self._get("cards", params=params or None, timeout=timeout)
        if isinstance(data, list):
            return [Card.model_validate(item) for item in data]
        return [Card.model_validate(item) for item in data.get("cards", [])]

    def get(
        self,
        card_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        data = self._get(f"cards/{card_id}", timeout=timeout)
        return Card.model_validate(data)

    def freeze(
        self,
        card_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        data = self._post(f"cards/{card_id}/freeze", {}, timeout=timeout)
        return Card.model_validate(data)

    def unfreeze(
        self,
        card_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        data = self._post(f"cards/{card_id}/unfreeze", {}, timeout=timeout)
        return Card.model_validate(data)

    def cancel(
        self,
        card_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> None:
        self._delete(f"cards/{card_id}", timeout=timeout)

    def update_limits(
        self,
        card_id: str,
        *,
        limit_per_tx: Decimal | None = None,
        limit_daily: Decimal | None = None,
        limit_monthly: Decimal | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> Card:
        payload: dict[str, Any] = {}
        if limit_per_tx is not None:
            payload["limit_per_tx"] = str(limit_per_tx)
        if limit_daily is not None:
            payload["limit_daily"] = str(limit_daily)
        if limit_monthly is not None:
            payload["limit_monthly"] = str(limit_monthly)
        data = self._patch(f"cards/{card_id}/limits", payload, timeout=timeout)
        return Card.model_validate(data)

    def transactions(
        self,
        card_id: str,
        limit: int = 50,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[CardTransaction]:
        data = self._get(f"cards/{card_id}/transactions", params={"limit": limit}, timeout=timeout)
        if isinstance(data, list):
            return [CardTransaction.model_validate(item) for item in data]
        return [CardTransaction.model_validate(item) for item in data.get("transactions", [])]

    def simulate_purchase(
        self,
        card_id: str,
        *,
        amount: Decimal,
        currency: str = "USD",
        merchant_name: str = "Demo Merchant",
        mcc_code: str = "5734",
        status: str = "approved",
        decline_reason: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> SimulateCardPurchaseResponse:
        payload = {
            "amount": str(amount),
            "currency": currency,
            "merchant_name": merchant_name,
            "mcc_code": mcc_code,
            "status": status,
            "decline_reason": decline_reason,
        }
        data = self._post(f"cards/{card_id}/simulate-purchase", payload, timeout=timeout)
        return SimulateCardPurchaseResponse.model_validate(data)

