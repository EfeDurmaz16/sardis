"""Bridge x402 challenges to the ControlPlane.

Every x402 payment must flow through the existing ControlPlane.submit() pipeline
(kill switch -> caps -> policy -> anomaly -> compliance -> execute -> ledger).

This module converts x402 protocol objects into ExecutionIntents and delegates
all decision-making to the control plane. No duplicate policy logic.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sardis_protocol.x402 import X402Challenge
    from sardis_protocol.x402_settlement import X402Settlement

from .control_plane import ControlPlane
from .execution_intent import (
    ExecutionIntent,
    ExecutionResult,
    IntentSource,
    SimulationResult,
)

logger = logging.getLogger(__name__)


class X402PolicyDenied(Exception):
    """Raised when x402 payment is denied by the control plane."""

    def __init__(self, reason: str, remaining: str | None = None, reset_at: str | None = None):
        self.reason = reason
        self.remaining = remaining
        self.reset_at = reset_at
        parts = [reason]
        if remaining is not None:
            parts.append(f"Remaining: ${remaining}")
        if reset_at is not None:
            parts.append(f"Reset: {reset_at}")
        super().__init__(". ".join(parts))


class X402PolicyGuard:
    """Bridges x402 challenges to the ControlPlane."""

    def __init__(self, control_plane: ControlPlane) -> None:
        self._control_plane = control_plane

    def _build_intent(
        self,
        challenge: X402Challenge,
        agent_id: str,
        org_id: str,
        wallet_id: str,
        *,
        dry_run: bool = False,
    ) -> ExecutionIntent:
        """Build an ExecutionIntent from an x402 challenge."""
        # Convert atomic units to human-readable (USDC has 6 decimals)
        amount = Decimal(challenge.amount) / Decimal("1000000")

        return ExecutionIntent(
            source=IntentSource.X402,
            amount=amount,
            currency=challenge.currency,
            chain=challenge.network,
            org_id=org_id,
            agent_id=agent_id,
            sender_wallet_id=wallet_id,
            recipient_address=challenge.payee_address,
            metadata={
                "resource_uri": challenge.resource_uri,
                "x402_payment_id": challenge.payment_id,
                "dry_run": dry_run,
            },
        )

    async def evaluate(
        self,
        challenge: X402Challenge,
        agent_id: str,
        org_id: str,
        wallet_id: str,
    ) -> tuple[bool, str]:
        """Simulate an x402 payment through the control plane.

        Returns (allowed, error_reason).
        """
        intent = self._build_intent(challenge, agent_id, org_id, wallet_id, dry_run=True)

        logger.info(
            "x402 policy guard: evaluating challenge=%s agent=%s amount=%s",
            challenge.payment_id,
            agent_id,
            intent.amount,
        )

        result: SimulationResult = await self._control_plane.simulate(intent)

        if not result.would_succeed:
            reasons = "; ".join(result.failure_reasons) if result.failure_reasons else "denied"
            logger.warning(
                "x402 policy guard: denied challenge=%s reasons=%s",
                challenge.payment_id,
                reasons,
            )
            return False, reasons

        return True, ""

    async def submit(
        self,
        challenge: X402Challenge,
        agent_id: str,
        org_id: str,
        wallet_id: str,
    ) -> ExecutionResult:
        """Full submit through the control plane (executes on chain)."""
        intent = self._build_intent(challenge, agent_id, org_id, wallet_id)

        logger.info(
            "x402 policy guard: submitting challenge=%s agent=%s amount=%s",
            challenge.payment_id,
            agent_id,
            intent.amount,
        )

        result = await self._control_plane.submit(intent)

        if not result.success:
            logger.warning(
                "x402 policy guard: submit failed challenge=%s error=%s",
                challenge.payment_id,
                result.error,
            )

        return result

    async def record_spend(
        self,
        challenge: X402Challenge,
        settlement: X402Settlement,
    ) -> None:
        """Update policy state after settlement (ledger recording)."""
        logger.info(
            "x402 policy guard: recording spend challenge=%s status=%s tx=%s",
            challenge.payment_id,
            settlement.status.value if settlement.status else "unknown",
            settlement.tx_hash or "none",
        )


__all__ = [
    "X402PolicyGuard",
    "X402PolicyDenied",
]
