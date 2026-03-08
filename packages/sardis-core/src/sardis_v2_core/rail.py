"""
Rail abstraction for multi-rail payment execution.

The control plane (policy, approval, audit, evidence) is rail-agnostic.
Only the execution layer changes per rail. This module defines the
rail interface and routing logic.
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable
from datetime import datetime, timezone


class Rail(Enum):
    """Supported payment rails."""
    CRYPTO = "crypto"    # On-chain stablecoin transfers
    ACH = "ach"          # ACH bank transfers (future)
    WIRE = "wire"        # Wire transfers (future)
    CARD = "card"        # Virtual card payments
    DELEGATED_CARD = "delegated_card"  # Tokenized delegated card execution


@dataclass
class RailCapabilities:
    """What a rail can do."""
    rail: Rail
    supports_instant: bool
    supports_refund: bool
    supports_hold: bool
    min_amount: Decimal
    max_amount: Decimal
    settlement_time_seconds: int
    currencies: list[str]


@runtime_checkable
class RailExecutor(Protocol):
    """Interface for executing payments on a specific rail."""

    @property
    def rail(self) -> Rail: ...

    @property
    def capabilities(self) -> RailCapabilities: ...

    async def execute(
        self,
        *,
        amount: Decimal,
        currency: str,
        source: str,
        destination: str,
        metadata: dict[str, Any] | None = None,
    ) -> RailResult: ...

    async def estimate_fee(
        self,
        amount: Decimal,
        currency: str,
    ) -> Decimal: ...

    async def check_health(self) -> bool: ...


@dataclass
class RailResult:
    """Result of a rail execution."""
    success: bool
    rail: Rail
    tx_reference: str  # tx_hash for crypto, trace_id for ACH, etc.
    amount: Decimal
    currency: str
    fee: Decimal
    settlement_expected_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class RailRouter:
    """Selects optimal rail for a payment."""

    def __init__(self):
        self._executors: dict[Rail, RailExecutor] = {}

    def register(self, executor: RailExecutor) -> None:
        """Register a rail executor."""
        self._executors[executor.rail] = executor

    def get_executor(self, rail: Rail) -> RailExecutor:
        """Get executor for a specific rail."""
        if rail not in self._executors:
            raise ValueError(f"No executor registered for rail: {rail}")
        return self._executors[rail]

    def select_rail(
        self,
        amount: Decimal,
        currency: str,
        preferred_rail: Rail | None = None,
        instant_required: bool = False,
    ) -> Rail:
        """Select optimal rail based on constraints."""
        # If preferred rail specified and available, use it
        if preferred_rail and preferred_rail in self._executors:
            executor = self._executors[preferred_rail]
            caps = executor.capabilities
            if (
                caps.min_amount <= amount <= caps.max_amount
                and currency in caps.currencies
                and (not instant_required or caps.supports_instant)
            ):
                return preferred_rail

        # Find best available rail
        candidates = []
        for rail, executor in self._executors.items():
            caps = executor.capabilities
            if (
                caps.min_amount <= amount <= caps.max_amount
                and currency in caps.currencies
                and (not instant_required or caps.supports_instant)
            ):
                candidates.append((rail, caps))

        if not candidates:
            raise ValueError(f"No rail available for {amount} {currency}")

        # Prefer instant rails, then lowest settlement time
        candidates.sort(
            key=lambda x: (not x[1].supports_instant, x[1].settlement_time_seconds)
        )
        return candidates[0][0]

    async def execute(
        self,
        rail: Rail,
        *,
        amount: Decimal,
        currency: str,
        source: str,
        destination: str,
        metadata: dict[str, Any] | None = None,
    ) -> RailResult:
        """Execute payment on specified rail."""
        executor = self.get_executor(rail)
        return await executor.execute(
            amount=amount,
            currency=currency,
            source=source,
            destination=destination,
            metadata=metadata,
        )

    @property
    def available_rails(self) -> list[Rail]:
        return list(self._executors.keys())
