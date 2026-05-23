"""Bridge ERC-8183 job actions to the ControlPlane.

Fund and settlement actions must flow through ControlPlane.submit() pipeline
(kill switch -> caps -> policy -> anomaly -> compliance -> execute -> ledger).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .erc8183_job import Job

from .control_plane import ControlPlane
from .execution_intent import (
    ExecutionIntent,
    ExecutionResult,
    IntentSource,
    SimulationResult,
)

logger = logging.getLogger(__name__)


class ERC8183PolicyDenied(Exception):
    """Raised when an ERC-8183 job action is denied by the control plane."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ERC8183PolicyGuard:
    """Bridges ERC-8183 job actions to the ControlPlane."""

    def __init__(self, control_plane: ControlPlane) -> None:
        self._control_plane = control_plane

    def _build_intent(
        self,
        job: Job,
        action: str,
        agent_id: str,
        org_id: str,
        wallet_id: str,
        *,
        dry_run: bool = False,
    ) -> ExecutionIntent:
        """Build an ExecutionIntent from an ERC-8183 job action."""
        return ExecutionIntent(
            source=IntentSource.ERC8183,
            amount=job.amount,
            currency=job.token,
            chain=job.chain,
            org_id=org_id,
            agent_id=agent_id,
            sender_wallet_id=wallet_id,
            metadata={
                "erc8183_job_id": job.id,
                "action": action,
                "dry_run": dry_run,
            },
        )

    async def evaluate_funding(
        self,
        job: Job,
        agent_id: str,
        org_id: str,
        wallet_id: str,
    ) -> tuple[bool, str]:
        """Simulate a funding action through the control plane.

        Returns:
            Tuple of (allowed, error_reason).
        """
        intent = self._build_intent(job, "fund", agent_id, org_id, wallet_id, dry_run=True)

        logger.info(
            "erc8183 policy guard: evaluating fund job=%s agent=%s amount=%s",
            job.id,
            agent_id,
            intent.amount,
        )

        result: SimulationResult = await self._control_plane.simulate(intent)

        if not result.would_succeed:
            reasons = "; ".join(result.failure_reasons) if result.failure_reasons else "denied"
            logger.warning(
                "erc8183 policy guard: denied job=%s reasons=%s",
                job.id,
                reasons,
            )
            return False, reasons

        return True, ""

    async def submit_funding(
        self,
        job: Job,
        agent_id: str,
        org_id: str,
        wallet_id: str,
    ) -> ExecutionResult:
        """Full funding submit through the control plane."""
        intent = self._build_intent(job, "fund", agent_id, org_id, wallet_id)

        logger.info(
            "erc8183 policy guard: submitting fund job=%s agent=%s amount=%s",
            job.id,
            agent_id,
            intent.amount,
        )

        result = await self._control_plane.submit(intent)

        if not result.success:
            logger.warning(
                "erc8183 policy guard: fund failed job=%s error=%s",
                job.id,
                result.error,
            )

        return result

    async def submit_settlement(
        self,
        job: Job,
        action: str,
        agent_id: str,
        org_id: str,
        wallet_id: str,
    ) -> ExecutionResult:
        """Submit settlement (release or refund) through the control plane."""
        intent = self._build_intent(job, action, agent_id, org_id, wallet_id)

        logger.info(
            "erc8183 policy guard: submitting %s job=%s agent=%s",
            action,
            job.id,
            agent_id,
        )

        result = await self._control_plane.submit(intent)

        if not result.success:
            logger.warning(
                "erc8183 policy guard: %s failed job=%s error=%s",
                action,
                job.id,
                result.error,
            )

        return result


__all__ = ["ERC8183PolicyGuard", "ERC8183PolicyDenied"]
