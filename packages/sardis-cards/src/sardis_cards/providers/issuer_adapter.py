"""Provider-agnostic issuer adapter for keeping integrations warm before go-live."""

from __future__ import annotations

from decimal import Decimal
import hashlib
import inspect
from typing import Any, Iterable

from ..models import CardType
from .issuing_ports import IssuerAdapter

REQUIRED_ISSUER_METHODS: tuple[str, ...] = (
    "create_cardholder",
    "create_virtual_card",
    "authorize",
    "freeze_card",
    "unfreeze_card",
    "cancel_card",
    "normalize_webhook_event",
)


def _normalize_result(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "model_dump"):
        dumped = payload.model_dump()
        if isinstance(dumped, dict):
            return dumped
    if hasattr(payload, "__dict__"):
        return {
            key: value
            for key, value in vars(payload).items()
            if not key.startswith("_")
        }
    return {"value": payload}


def _has_methods(obj: Any, methods: Iterable[str]) -> bool:
    return all(callable(getattr(obj, name, None)) for name in methods)


class IssuerAdapterShim(IssuerAdapter):
    """Adapts legacy `CardProvider` implementations to the issuer adapter contract."""

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return str(getattr(self._provider, "name", "unknown"))

    async def create_cardholder(
        self,
        *,
        wallet_id: str,
        cardholder_name: str | None = None,
        cardholder_email: str | None = None,
        cardholder_phone: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        native = getattr(self._provider, "create_cardholder", None)
        if callable(native):
            result = await native(
                wallet_id=wallet_id,
                cardholder_name=cardholder_name,
                cardholder_email=cardholder_email,
                cardholder_phone=cardholder_phone,
                metadata=metadata,
            )
            payload = _normalize_result(result)
            payload.setdefault("provider", self.name)
            return payload

        seed = "|".join(
            [
                wallet_id,
                str(cardholder_name or ""),
                str(cardholder_email or ""),
                str(cardholder_phone or ""),
            ]
        )
        synthetic_id = f"ich_syn_{hashlib.sha256(seed.encode()).hexdigest()[:20]}"
        return {
            "provider": self.name,
            "cardholder_id": synthetic_id,
            "mode": "synthetic",
        }

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
        native = getattr(self._provider, "create_virtual_card", None)
        if callable(native):
            result = await native(
                wallet_id=wallet_id,
                cardholder_id=cardholder_id,
                limit_per_tx=limit_per_tx,
                limit_daily=limit_daily,
                limit_monthly=limit_monthly,
                locked_merchant_id=locked_merchant_id,
                metadata=metadata,
            )
            payload = _normalize_result(result)
            payload.setdefault("provider", self.name)
            return payload

        create_card = getattr(self._provider, "create_card", None)
        if not callable(create_card):
            raise RuntimeError("provider_missing_create_card")

        kwargs: dict[str, Any] = {
            "wallet_id": wallet_id,
            "card_type": CardType.MULTI_USE,
            "limit_per_tx": limit_per_tx,
            "limit_daily": limit_daily,
            "limit_monthly": limit_monthly,
            "locked_merchant_id": locked_merchant_id,
            "metadata": metadata,
            "reuse_cardholder_id": cardholder_id,
        }
        params = inspect.signature(create_card).parameters
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in params}

        card = await create_card(**filtered_kwargs)
        payload = _normalize_result(card)
        payload.setdefault("provider", self.name)
        payload.setdefault("provider_card_id", str(payload.get("provider_card_id") or payload.get("id") or ""))
        return payload

    async def authorize(
        self,
        *,
        provider_card_id: str,
        amount: Decimal,
        merchant_name: str | None = None,
        mcc_code: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        simulator = getattr(self._provider, "simulate_authorization", None)
        if callable(simulator):
            result = await simulator(
                provider_card_id=provider_card_id,
                amount_cents=int((amount * Decimal("100")).to_integral_value()),
                merchant_descriptor=merchant_name or "Sardis Authorization",
            )
            payload = _normalize_result(result)
            payload.setdefault("provider", self.name)
            payload.setdefault("status", "authorized")
            return payload

        return {
            "provider": self.name,
            "provider_card_id": provider_card_id,
            "amount": str(amount),
            "merchant_name": merchant_name,
            "mcc_code": mcc_code,
            "status": "unsupported",
            "reason": "provider_authorization_not_exposed",
        }

    async def freeze_card(self, provider_card_id: str) -> dict[str, Any]:
        result = await self._provider.freeze_card(provider_card_id)
        payload = _normalize_result(result)
        payload.setdefault("provider", self.name)
        return payload

    async def unfreeze_card(self, provider_card_id: str) -> dict[str, Any]:
        result = await self._provider.unfreeze_card(provider_card_id)
        payload = _normalize_result(result)
        payload.setdefault("provider", self.name)
        return payload

    async def cancel_card(self, provider_card_id: str) -> dict[str, Any]:
        result = await self._provider.cancel_card(provider_card_id)
        payload = _normalize_result(result)
        payload.setdefault("provider", self.name)
        return payload

    async def normalize_webhook_event(
        self,
        *,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        event_type = str(payload.get("type") or payload.get("event_type") or "unknown")
        card_id = str(
            payload.get("card_id")
            or payload.get("card_token")
            or payload.get("provider_card_id")
            or (payload.get("data", {}) or {}).get("card_id")
            or (payload.get("data", {}) or {}).get("card_token")
            or ""
        )
        event_id = str(
            payload.get("event_id")
            or payload.get("eventId")
            or payload.get("id")
            or hashlib.sha256(
                f"{event_type}:{card_id}:{headers.get('x-request-id', '')}".encode()
            ).hexdigest()
        )
        return {
            "provider": self.name,
            "event_id": event_id,
            "event_type": event_type,
            "provider_card_id": card_id,
            "raw": payload,
        }


def build_issuer_adapter(provider: Any) -> IssuerAdapter:
    """Return a provider-native issuer adapter when available, else wrap with a shim."""
    if _has_methods(provider, REQUIRED_ISSUER_METHODS):
        return provider  # type: ignore[return-value]
    return IssuerAdapterShim(provider)

