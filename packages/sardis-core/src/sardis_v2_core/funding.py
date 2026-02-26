"""Provider-agnostic funding adapter contracts and Stripe adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import logging
from typing import Any, Literal, Protocol

import httpx

logger = logging.getLogger(__name__)


FundingRail = Literal["fiat", "stablecoin"]


@dataclass(frozen=True)
class FundingRequest:
    """Normalized funding request across fiat/stablecoin providers."""

    amount: Decimal
    currency: str = "USD"
    description: str = "Fund issuing balance"
    connected_account_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FundingResult:
    """Normalized funding response used by API routing and audit trails."""

    provider: str
    rail: FundingRail
    transfer_id: str
    amount: Decimal
    currency: str
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FundingAttempt:
    """Single provider attempt during a routed funding operation."""

    provider: str
    rail: FundingRail
    status: Literal["success", "failed"]
    error: str | None = None


class FundingAdapter(Protocol):
    """Adapter protocol for provider-specific funding implementations."""

    @property
    def provider(self) -> str:
        ...

    @property
    def rail(self) -> FundingRail:
        ...

    async def fund(self, request: FundingRequest) -> FundingResult:
        ...


class FundingRoutingError(RuntimeError):
    """Raised when all funding adapters fail."""

    def __init__(self, message: str, *, attempts: list[FundingAttempt]) -> None:
        super().__init__(message)
        self.attempts = attempts


async def execute_funding_with_failover(
    adapters: list[FundingAdapter],
    request: FundingRequest,
) -> tuple[FundingResult, list[FundingAttempt]]:
    """
    Execute funding in deterministic adapter order.

    Returns the first successful result and all attempt outcomes.
    Raises FundingRoutingError when all adapters fail.
    """
    if not adapters:
        raise FundingRoutingError("no_funding_adapters_configured", attempts=[])

    attempts: list[FundingAttempt] = []
    for adapter in adapters:
        try:
            result = await adapter.fund(request)
            attempts.append(
                FundingAttempt(
                    provider=str(getattr(result, "provider", getattr(adapter, "provider", "unknown"))),
                    rail=str(getattr(result, "rail", getattr(adapter, "rail", "fiat"))),  # type: ignore[arg-type]
                    status="success",
                )
            )
            return result, attempts
        except Exception as exc:
            attempts.append(
                FundingAttempt(
                    provider=str(getattr(adapter, "provider", "unknown")),
                    rail=str(getattr(adapter, "rail", "fiat")),  # type: ignore[arg-type]
                    status="failed",
                    error=str(exc),
                )
            )

    raise FundingRoutingError("all_funding_providers_failed", attempts=attempts)


class StripeIssuingFundingAdapter:
    """FundingAdapter implementation backed by Stripe Treasury top-ups."""

    def __init__(self, treasury_provider: Any) -> None:
        self._treasury = treasury_provider

    @property
    def provider(self) -> str:
        return "stripe"

    @property
    def rail(self) -> FundingRail:
        return "fiat"

    async def fund(self, request: FundingRequest) -> FundingResult:
        transfer = await self._treasury.fund_issuing_balance(
            amount=request.amount,
            description=request.description,
            connected_account_id=request.connected_account_id,
            metadata=request.metadata,
        )
        transfer_id = str(getattr(transfer, "id", "")) or "unknown"
        amount_value = Decimal(str(getattr(transfer, "amount", request.amount)))
        currency_value = str(getattr(transfer, "currency", request.currency)).upper()
        status_value = str(getattr(transfer, "status", "processing"))
        return FundingResult(
            provider=self.provider,
            rail=self.rail,
            transfer_id=transfer_id,
            amount=amount_value,
            currency=currency_value,
            status=status_value,
            metadata=request.metadata,
        )


class HttpTopupFundingAdapter:
    """HTTP adapter for provider top-up endpoints (Rain/Bridge/Coinbase custom lanes)."""

    def __init__(
        self,
        *,
        provider: str,
        rail: FundingRail,
        base_url: str,
        api_key: str,
        topup_path: str = "/v1/funding/topups",
        timeout_seconds: float = 20.0,
        auth_style: str = "bearer",
        api_secret: str = "",
        program_id: str = "",
    ) -> None:
        if not provider:
            raise ValueError("provider is required")
        if not base_url:
            raise ValueError(f"{provider}: base_url is required")
        if not api_key:
            raise ValueError(f"{provider}: api_key is required")
        self._provider = provider
        self._rail = rail
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._topup_path = topup_path
        self._timeout_seconds = timeout_seconds
        self._auth_style = (auth_style or "bearer").strip().lower()
        self._api_secret = api_secret
        self._program_id = program_id

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def rail(self) -> FundingRail:
        return self._rail

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "sardis-core/funding-http-adapter",
        }
        if self._auth_style == "x_api_key":
            headers["X-API-Key"] = self._api_key
        else:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if self._api_secret:
            headers["X-API-Secret"] = self._api_secret
        if self._program_id:
            headers["X-Program-Id"] = self._program_id
        return headers

    async def fund(self, request: FundingRequest) -> FundingResult:
        url = f"{self._base_url}/{self._topup_path.lstrip('/')}"
        payload: dict[str, Any] = {
            "amount": str(request.amount),
            "currency": request.currency.upper(),
            "description": request.description,
            "metadata": request.metadata,
        }
        if request.connected_account_id:
            payload["connected_account_id"] = request.connected_account_id

        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                headers=self._headers(),
                json=payload,
            )
        response.raise_for_status()
        body = response.json() if response.content else {}

        transfer_id = str(body.get("id") or body.get("transfer_id") or body.get("topup_id") or "unknown")
        amount_value = Decimal(str(body.get("amount") or request.amount))
        currency_value = str(body.get("currency") or request.currency).upper()
        status_value = str(body.get("status") or "processing")
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

        logger.info(
            "HTTP funding adapter success provider=%s transfer_id=%s status=%s",
            self._provider,
            transfer_id,
            status_value,
        )

        return FundingResult(
            provider=self._provider,
            rail=self._rail,
            transfer_id=transfer_id,
            amount=amount_value,
            currency=currency_value,
            status=status_value,
            metadata=metadata,
        )
