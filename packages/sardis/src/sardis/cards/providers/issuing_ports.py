"""Issuer adapter contracts for partner-agnostic card flows."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol


class IssuerAdapter(Protocol):
    """Unified contract for issuer integrations whose APIs evolve frequently."""

    @property
    def name(self) -> str:
        ...

    async def create_cardholder(
        self,
        *,
        wallet_id: str,
        cardholder_name: str | None = None,
        cardholder_email: str | None = None,
        cardholder_phone: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        ...

    async def create_virtual_card(
        self,
        *,
        wallet_id: str,
        cardholder_id: str,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        ...

    async def authorize(
        self,
        *,
        provider_card_id: str,
        amount: Decimal,
        merchant_name: str | None = None,
        mcc_code: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        ...

    async def freeze_card(self, provider_card_id: str) -> dict[str, Any]:
        ...

    async def unfreeze_card(self, provider_card_id: str) -> dict[str, Any]:
        ...

    async def cancel_card(self, provider_card_id: str) -> dict[str, Any]:
        ...

    async def normalize_webhook_event(
        self,
        *,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        ...
