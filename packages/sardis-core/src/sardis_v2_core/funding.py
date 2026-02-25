"""Provider-agnostic funding adapter contracts and Stripe adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Protocol


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
