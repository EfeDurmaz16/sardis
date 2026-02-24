"""Partner card issuer adapters (Rain / Bridge) with a shared HTTP abstraction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx

from .base import CardProvider
from ..models import Card, CardStatus, CardTransaction, CardType, FundingSource, TransactionStatus


def _to_decimal(value: Any, default: Decimal) -> Decimal:
    try:
        if value is None:
            return default
        return Decimal(str(value))
    except Exception:
        return default


def _to_iso_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_mapping(value: Any) -> dict[str, str]:
    """Parse endpoint/method maps from dict or JSON string."""
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            return {}
    return {}


@dataclass
class PartnerIssuerConfig:
    name: str
    base_url: str
    api_key: str
    api_secret: str = ""
    program_id: str = ""
    auth_style: str = "bearer"
    timeout_seconds: float = 20.0
    path_map: dict[str, str] | None = None
    method_map: dict[str, str] | None = None


class PartnerIssuerProvider(CardProvider):
    """Configurable HTTP provider for partner card issuers."""

    DEFAULT_PATHS = {
        "create_card": "/v1/cards",
        "get_card": "/v1/cards/{card_id}",
        "activate_card": "/v1/cards/{card_id}/activate",
        "freeze_card": "/v1/cards/{card_id}/freeze",
        "unfreeze_card": "/v1/cards/{card_id}/unfreeze",
        "cancel_card": "/v1/cards/{card_id}/cancel",
        "update_limits": "/v1/cards/{card_id}/limits",
        "fund_card": "/v1/cards/{card_id}/fund",
        "list_transactions": "/v1/cards/{card_id}/transactions",
        "get_transaction": "/v1/transactions/{tx_id}",
    }

    DEFAULT_METHODS = {
        "create_card": "POST",
        "get_card": "GET",
        "activate_card": "POST",
        "freeze_card": "POST",
        "unfreeze_card": "POST",
        "cancel_card": "POST",
        "update_limits": "PATCH",
        "fund_card": "POST",
        "list_transactions": "GET",
        "get_transaction": "GET",
    }

    def __init__(self, config: PartnerIssuerConfig) -> None:
        if not config.api_key:
            raise ValueError(f"{config.name}: api_key is required")
        self._config = config
        self._cards: dict[str, Card] = {}

        paths = dict(self.DEFAULT_PATHS)
        if config.path_map:
            paths.update(config.path_map)
        self._paths = paths

        methods = dict(self.DEFAULT_METHODS)
        if config.method_map:
            methods.update({k: str(v).upper() for k, v in config.method_map.items()})
        self._methods = methods

    @property
    def name(self) -> str:
        return self._config.name

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "sardis-cards/partner-issuers",
        }
        auth_style = (self._config.auth_style or "bearer").strip().lower()
        if auth_style == "x_api_key":
            headers["X-API-Key"] = self._config.api_key
        else:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        if self._config.api_secret:
            headers["X-API-Secret"] = self._config.api_secret
        if self._config.program_id:
            headers["X-Program-Id"] = self._config.program_id
        return headers

    async def _send(
        self,
        operation: str,
        *,
        path_params: Optional[dict[str, str]] = None,
        payload: Optional[dict[str, Any]] = None,
        query: Optional[dict[str, Any]] = None,
    ) -> Any:
        method = self._methods.get(operation, "GET")
        path_tmpl = self._paths.get(operation)
        if not path_tmpl:
            raise RuntimeError(f"{self.name}: missing endpoint mapping for operation={operation}")

        path = path_tmpl
        for key, value in (path_params or {}).items():
            path = path.replace("{" + key + "}", value)
        url = f"{self._config.base_url.rstrip('/')}/{path.lstrip('/')}"

        timeout = httpx.Timeout(self._config.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                json=payload,
                params=query,
            )
        response.raise_for_status()
        if not response.content:
            return {}
        if "application/json" not in response.headers.get("content-type", ""):
            return {}
        return response.json()

    @staticmethod
    def _parse_card_status(value: Any) -> CardStatus:
        raw = str(value or "pending").strip().lower()
        mapping = {
            "active": CardStatus.ACTIVE,
            "enabled": CardStatus.ACTIVE,
            "open": CardStatus.ACTIVE,
            "frozen": CardStatus.FROZEN,
            "paused": CardStatus.FROZEN,
            "inactive": CardStatus.PENDING,
            "pending": CardStatus.PENDING,
            "cancelled": CardStatus.CANCELLED,
            "canceled": CardStatus.CANCELLED,
            "closed": CardStatus.CANCELLED,
            "expired": CardStatus.EXPIRED,
        }
        return mapping.get(raw, CardStatus.PENDING)

    @staticmethod
    def _parse_card_type(value: Any) -> CardType:
        raw = str(value or "multi_use").strip().lower()
        mapping = {
            "single_use": CardType.SINGLE_USE,
            "single": CardType.SINGLE_USE,
            "merchant_locked": CardType.MERCHANT_LOCKED,
            "merchant": CardType.MERCHANT_LOCKED,
            "multi_use": CardType.MULTI_USE,
            "multi": CardType.MULTI_USE,
            "virtual": CardType.MULTI_USE,
        }
        return mapping.get(raw, CardType.MULTI_USE)

    @staticmethod
    def _parse_tx_status(value: Any) -> TransactionStatus:
        raw = str(value or "pending").strip().lower()
        mapping = {
            "pending": TransactionStatus.PENDING,
            "authorized": TransactionStatus.APPROVED,
            "approved": TransactionStatus.APPROVED,
            "declined": TransactionStatus.DECLINED,
            "denied": TransactionStatus.DECLINED,
            "reversed": TransactionStatus.REVERSED,
            "settled": TransactionStatus.SETTLED,
            "completed": TransactionStatus.SETTLED,
        }
        return mapping.get(raw, TransactionStatus.PENDING)

    def _to_card(
        self,
        raw: dict[str, Any],
        *,
        wallet_id: str = "",
        fallback_card: Optional[Card] = None,
    ) -> Card:
        limits = raw.get("limits") if isinstance(raw.get("limits"), dict) else {}
        provider_card_id = str(raw.get("id") or raw.get("card_id") or raw.get("token") or "")
        if not provider_card_id and fallback_card is not None:
            provider_card_id = fallback_card.provider_card_id
        if not provider_card_id:
            raise ValueError(f"{self.name}: card response is missing id/card_id/token")

        limit_per_tx = _to_decimal(
            raw.get("limit_per_tx")
            or limits.get("per_tx")
            or limits.get("per_transaction"),
            fallback_card.limit_per_tx if fallback_card else Decimal("500.00"),
        )
        limit_daily = _to_decimal(
            raw.get("limit_daily")
            or limits.get("daily"),
            fallback_card.limit_daily if fallback_card else Decimal("2000.00"),
        )
        limit_monthly = _to_decimal(
            raw.get("limit_monthly")
            or limits.get("monthly"),
            fallback_card.limit_monthly if fallback_card else Decimal("10000.00"),
        )

        card = Card(
            wallet_id=wallet_id or (fallback_card.wallet_id if fallback_card else str(raw.get("wallet_id") or "")),
            provider=self.name,
            provider_card_id=provider_card_id,
            card_number_last4=str(raw.get("last4") or raw.get("card_number_last4") or ""),
            expiry_month=int(raw.get("exp_month") or raw.get("expiry_month") or 0),
            expiry_year=int(raw.get("exp_year") or raw.get("expiry_year") or 0),
            card_type=self._parse_card_type(raw.get("card_type") or raw.get("type")),
            status=self._parse_card_status(raw.get("status") or raw.get("state")),
            funding_source=FundingSource.STABLECOIN,
            funded_amount=_to_decimal(raw.get("funded_amount"), fallback_card.funded_amount if fallback_card else Decimal("0")),
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
            created_at=fallback_card.created_at if fallback_card else _to_iso_now(),
            activated_at=fallback_card.activated_at if fallback_card else None,
            frozen_at=fallback_card.frozen_at if fallback_card else None,
            cancelled_at=fallback_card.cancelled_at if fallback_card else None,
        )
        self._cards[provider_card_id] = card
        return card

    def _to_transaction(self, raw: dict[str, Any]) -> CardTransaction:
        provider_tx_id = str(raw.get("id") or raw.get("transaction_id") or raw.get("token") or "")
        if not provider_tx_id:
            raise ValueError(f"{self.name}: transaction response is missing id/transaction_id/token")
        return CardTransaction(
            provider_tx_id=provider_tx_id,
            card_id=str(raw.get("card_id") or raw.get("card") or ""),
            amount=_to_decimal(raw.get("amount"), Decimal("0")),
            currency=str(raw.get("currency") or "USD").upper(),
            merchant_name=str(raw.get("merchant_name") or raw.get("merchant") or ""),
            merchant_category=str(raw.get("merchant_category") or raw.get("mcc") or ""),
            merchant_id=str(raw.get("merchant_id") or ""),
            status=self._parse_tx_status(raw.get("status")),
            decline_reason=raw.get("decline_reason"),
        )

    def _card_payload(
        self,
        *,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: Optional[str],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "wallet_id": wallet_id,
            "card_type": card_type.value,
            "limits": {
                "per_tx": str(limit_per_tx),
                "daily": str(limit_daily),
                "monthly": str(limit_monthly),
            },
            "metadata": {"managed_by": "sardis"},
        }
        if self._config.program_id:
            payload["program_id"] = self._config.program_id
        if locked_merchant_id:
            payload["locked_merchant_id"] = locked_merchant_id
        return payload

    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: Optional[str] = None,
    ) -> Card:
        response = await self._send(
            "create_card",
            payload=self._card_payload(
                wallet_id=wallet_id,
                card_type=card_type,
                limit_per_tx=limit_per_tx,
                limit_daily=limit_daily,
                limit_monthly=limit_monthly,
                locked_merchant_id=locked_merchant_id,
            ),
        )
        data = response if isinstance(response, dict) else {}
        card = self._to_card(data, wallet_id=wallet_id)
        card.limit_per_tx = limit_per_tx
        card.limit_daily = limit_daily
        card.limit_monthly = limit_monthly
        return card

    async def get_card(self, provider_card_id: str) -> Optional[Card]:
        response = await self._send("get_card", path_params={"card_id": provider_card_id})
        data = response if isinstance(response, dict) else {}
        if not data:
            return self._cards.get(provider_card_id)
        return self._to_card(data, fallback_card=self._cards.get(provider_card_id))

    async def activate_card(self, provider_card_id: str) -> Card:
        response = await self._send("activate_card", path_params={"card_id": provider_card_id})
        card = self._to_card(response if isinstance(response, dict) else {}, fallback_card=self._cards.get(provider_card_id))
        card.status = CardStatus.ACTIVE
        card.activated_at = _to_iso_now()
        self._cards[provider_card_id] = card
        return card

    async def freeze_card(self, provider_card_id: str) -> Card:
        response = await self._send("freeze_card", path_params={"card_id": provider_card_id})
        card = self._to_card(response if isinstance(response, dict) else {}, fallback_card=self._cards.get(provider_card_id))
        card.status = CardStatus.FROZEN
        card.frozen_at = _to_iso_now()
        self._cards[provider_card_id] = card
        return card

    async def unfreeze_card(self, provider_card_id: str) -> Card:
        response = await self._send("unfreeze_card", path_params={"card_id": provider_card_id})
        card = self._to_card(response if isinstance(response, dict) else {}, fallback_card=self._cards.get(provider_card_id))
        card.status = CardStatus.ACTIVE
        self._cards[provider_card_id] = card
        return card

    async def cancel_card(self, provider_card_id: str) -> Card:
        response = await self._send("cancel_card", path_params={"card_id": provider_card_id})
        card = self._to_card(response if isinstance(response, dict) else {}, fallback_card=self._cards.get(provider_card_id))
        card.status = CardStatus.CANCELLED
        card.cancelled_at = _to_iso_now()
        self._cards[provider_card_id] = card
        return card

    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None,
    ) -> Card:
        payload: dict[str, Any] = {"limits": {}}
        if limit_per_tx is not None:
            payload["limits"]["per_tx"] = str(limit_per_tx)
        if limit_daily is not None:
            payload["limits"]["daily"] = str(limit_daily)
        if limit_monthly is not None:
            payload["limits"]["monthly"] = str(limit_monthly)
        response = await self._send(
            "update_limits",
            path_params={"card_id": provider_card_id},
            payload=payload,
        )
        card = self._to_card(response if isinstance(response, dict) else {}, fallback_card=self._cards.get(provider_card_id))
        if limit_per_tx is not None:
            card.limit_per_tx = limit_per_tx
        if limit_daily is not None:
            card.limit_daily = limit_daily
        if limit_monthly is not None:
            card.limit_monthly = limit_monthly
        self._cards[provider_card_id] = card
        return card

    async def fund_card(
        self,
        provider_card_id: str,
        amount: Decimal,
    ) -> Card:
        response = await self._send(
            "fund_card",
            path_params={"card_id": provider_card_id},
            payload={"amount": str(amount), "currency": "USD"},
        )
        card = self._to_card(response if isinstance(response, dict) else {}, fallback_card=self._cards.get(provider_card_id))
        card.funded_amount = (self._cards.get(provider_card_id).funded_amount if self._cards.get(provider_card_id) else Decimal("0")) + amount
        card.last_funded_at = _to_iso_now()
        self._cards[provider_card_id] = card
        return card

    async def list_transactions(
        self,
        provider_card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        response = await self._send(
            "list_transactions",
            path_params={"card_id": provider_card_id},
            query={"limit": limit, "offset": offset},
        )
        if isinstance(response, list):
            rows = response
        elif isinstance(response, dict):
            rows = response.get("items") or response.get("data") or response.get("transactions") or []
        else:
            rows = []
        out: list[CardTransaction] = []
        for item in rows:
            if isinstance(item, dict):
                out.append(self._to_transaction(item))
        return out

    async def get_transaction(self, provider_tx_id: str) -> Optional[CardTransaction]:
        response = await self._send("get_transaction", path_params={"tx_id": provider_tx_id})
        if not isinstance(response, dict) or not response:
            return None
        return self._to_transaction(response)


class BridgeCardsProvider(PartnerIssuerProvider):
    """Bridge cards provider wrapper using the shared partner adapter."""

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str = "",
        base_url: str = "https://api.bridge.xyz",
        program_id: str = "",
        path_map: dict[str, str] | str | None = None,
        method_map: dict[str, str] | str | None = None,
    ) -> None:
        super().__init__(
            PartnerIssuerConfig(
                name="bridge_cards",
                base_url=base_url,
                api_key=api_key,
                api_secret=api_secret,
                program_id=program_id,
                auth_style="x_api_key",
                path_map=parse_mapping(path_map),
                method_map=parse_mapping(method_map),
            )
        )


class RainCardsProvider(PartnerIssuerProvider):
    """Rain cards provider wrapper using the shared partner adapter."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.rain.xyz",
        program_id: str = "",
        path_map: dict[str, str] | str | None = None,
        method_map: dict[str, str] | str | None = None,
    ) -> None:
        super().__init__(
            PartnerIssuerConfig(
                name="rain",
                base_url=base_url,
                api_key=api_key,
                program_id=program_id,
                auth_style="bearer",
                path_map=parse_mapping(path_map),
                method_map=parse_mapping(method_map),
            )
        )
