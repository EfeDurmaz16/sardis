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
