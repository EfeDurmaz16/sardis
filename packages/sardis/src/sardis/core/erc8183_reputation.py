"""ERC-8183 -> ERC-8004 reputation feedback.

Records job completion/rejection outcomes as ERC-8004 reputation entries.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .erc8183_job import Job

from .erc8004 import ERC8004Registry, ReputationEntry

logger = logging.getLogger(__name__)


class JobReputationService:
    """Records ERC-8183 job outcomes as ERC-8004 reputation."""

    def __init__(self, registry: ERC8004Registry) -> None:
        self._registry = registry

    async def record_completion(self, job: Job) -> None:
        """Record positive reputation for provider and evaluator after job completion."""
        now = int(time.time())

        # Provider gets high reputation for completing work
        await self._registry.submit_reputation(ReputationEntry(
            from_agent=job.client_agent_id,
            to_agent=job.provider_agent_id,
            score=800,
            category="job_completion",
            timestamp=now,
            transaction_hash=job.settlement_tx_hash or "",
        ))

        # Evaluator gets reputation for fair evaluation
        await self._registry.submit_reputation(ReputationEntry(
            from_agent=job.client_agent_id,
            to_agent=job.evaluator_agent_id,
            score=700,
            category="evaluation_accuracy",
            timestamp=now,
            transaction_hash=job.evaluation_tx_hash or "",
        ))

        logger.info(
            "erc8183 reputation: recorded completion for job=%s provider=%s",
            job.id,
            job.provider_agent_id,
        )

    async def record_rejection(self, job: Job) -> None:
        """Record negative reputation for provider, positive for evaluator after rejection."""
        now = int(time.time())

        # Provider gets low reputation for rejected work
        await self._registry.submit_reputation(ReputationEntry(
            from_agent=job.evaluator_agent_id,
            to_agent=job.provider_agent_id,
            score=200,
            category="job_rejection",
            timestamp=now,
            transaction_hash=job.evaluation_tx_hash or "",
        ))

        # Evaluator still gets positive reputation
        await self._registry.submit_reputation(ReputationEntry(
            from_agent=job.client_agent_id,
            to_agent=job.evaluator_agent_id,
            score=700,
            category="evaluation_accuracy",
            timestamp=now,
            transaction_hash=job.evaluation_tx_hash or "",
        ))

        logger.info(
            "erc8183 reputation: recorded rejection for job=%s provider=%s",
            job.id,
            job.provider_agent_id,
        )

    async def record_dispute(self, job: Job) -> None:
        """Flag dispute for review -- no automatic reputation change."""
        logger.info("erc8183 reputation: dispute flagged for job=%s", job.id)


__all__ = ["JobReputationService"]
