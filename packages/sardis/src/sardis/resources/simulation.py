"""Simulation resource for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from decimal import Decimal

    from ..client import TimeoutConfig


class AsyncSimulationResource(AsyncBaseResource):
    """Simulate policy checks and payment flows without real execution."""

    async def simulate(
        self,
        agent_id: str,
        amount: Decimal,
        *,
        currency: str = "USD",
        chain: str | None = None,
        merchant_id: str | None = None,
        mcc_code: str | None = None,
        source: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Simulate a payment against the agent's current policy.

        Args:
            agent_id: The agent whose policy to evaluate.
            amount: The payment amount.
            currency: Currency code (default "USD").
            chain: Optional chain to simulate on (e.g. "base", "polygon").
            merchant_id: Optional merchant identifier.
            mcc_code: Optional merchant category code.
            source: Optional origination source label.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "amount": str(amount),
            "currency": currency,
        }
        if chain:
            payload["chain"] = chain
        if merchant_id:
            payload["merchant_id"] = merchant_id
        if mcc_code:
            payload["mcc_code"] = mcc_code
        if source:
            payload["source"] = source
        return await self._post("simulation/run", payload, timeout=timeout)


class SimulationResource(SyncBaseResource):
    """Simulate policy checks and payment flows without real execution."""

    def simulate(
        self,
        agent_id: str,
        amount: Decimal,
        *,
        currency: str = "USD",
        chain: str | None = None,
        merchant_id: str | None = None,
        mcc_code: str | None = None,
        source: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Simulate a payment against the agent's current policy.

        Args:
            agent_id: The agent whose policy to evaluate.
            amount: The payment amount.
            currency: Currency code (default "USD").
            chain: Optional chain to simulate on (e.g. "base", "polygon").
            merchant_id: Optional merchant identifier.
            mcc_code: Optional merchant category code.
            source: Optional origination source label.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "amount": str(amount),
            "currency": currency,
        }
        if chain:
            payload["chain"] = chain
        if merchant_id:
            payload["merchant_id"] = merchant_id
        if mcc_code:
            payload["mcc_code"] = mcc_code
        if source:
            payload["source"] = source
        return self._post("simulation/run", payload, timeout=timeout)
