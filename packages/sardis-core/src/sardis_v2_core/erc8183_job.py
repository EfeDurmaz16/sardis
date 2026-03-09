"""ERC-8183 Agentic Commerce — Job lifecycle management.

Three-party job primitive for agent-to-agent commerce:
Client (creates/funds), Provider (delivers), Evaluator (approves/rejects).

Job States:
    OPEN -> FUNDED -> SUBMITTED -> COMPLETED
                               -> REJECTED
                   -> EXPIRED
         -> EXPIRED
    FUNDED -> DISPUTED -> COMPLETED | REJECTED
    SUBMITTED -> DISPUTED -> COMPLETED | REJECTED

Usage:
    from sardis_v2_core.erc8183_job import JobManager, JobState

    manager = JobManager()

    # 1. Create job
    job = await manager.create_job(
        client_agent_id="agent_client",
        provider_agent_id="agent_provider",
        evaluator_agent_id="agent_evaluator",
        amount=Decimal("500.00"),
        token="USDC",
        chain="base",
        deadline_hours=72,
        description="Generate market research report",
    )

    # 2. Fund job (after on-chain transaction)
    job = await manager.fund_job(job.id, tx_hash="0x...")

    # 3. Provider submits deliverable
    job = await manager.submit_deliverable(job.id, "ipfs://Qm...", "sha256:abc...")

    # 4. Evaluator approves/rejects
    job = await manager.evaluate_job(
        job.id,
        evaluator_agent_id="agent_evaluator",
        approved=True,
        reason="Quality meets requirements",
    )
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import uuid4

from .database import Database
from .exceptions import (
    SardisConflictError,
    SardisNotFoundError,
    SardisValidationError,
)

logger = logging.getLogger(__name__)


class JobState(str, Enum):
    """ERC-8183 job lifecycle states."""

    OPEN = "open"
    FUNDED = "funded"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    DISPUTED = "disputed"


# Valid state transitions (fail-closed: only explicit transitions allowed)
JOB_VALID_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.OPEN: {JobState.FUNDED, JobState.EXPIRED},
    JobState.FUNDED: {JobState.SUBMITTED, JobState.EXPIRED, JobState.DISPUTED},
    JobState.SUBMITTED: {JobState.COMPLETED, JobState.REJECTED, JobState.DISPUTED, JobState.EXPIRED},
    JobState.COMPLETED: set(),  # Terminal state
    JobState.REJECTED: set(),  # Terminal state
    JobState.EXPIRED: set(),  # Terminal state
    JobState.DISPUTED: {JobState.COMPLETED, JobState.REJECTED},
}


@dataclass(slots=True)
class Job:
    """ERC-8183 Job record — three-party escrow commerce primitive."""

    id: str
    client_agent_id: str
    provider_agent_id: str
    evaluator_agent_id: str
    amount: Decimal
    token: str
    chain: str
    state: JobState
    created_at: datetime
    deadline: datetime
    funded_at: datetime | None = None
    funding_tx_hash: str | None = None
    deliverable_uri: str | None = None
    deliverable_hash: str | None = None
    submitted_at: datetime | None = None
    evaluation_result: str | None = None  # "approved" | "rejected"
    evaluation_reason: str | None = None
    evaluated_at: datetime | None = None
    evaluation_tx_hash: str | None = None
    settlement_tx_hash: str | None = None
    settled_at: datetime | None = None
    onchain_job_id: int | None = None
    contract_address: str | None = None
    hook_contract_address: str | None = None
    description: str = ""
    metadata: dict = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_expired(self) -> bool:
        """Check if job has passed its deadline."""
        return datetime.now(UTC) > self.deadline

    def can_transition_to(self, new_state: JobState) -> bool:
        """Check if state transition is valid."""
        return new_state in JOB_VALID_TRANSITIONS.get(self.state, set())


class JobManager:
    """
    Manages ERC-8183 job lifecycle.

    Handles job creation, funding, deliverable submission, evaluation,
    disputes, and automatic expiration cleanup.
    """

    async def create_job(
        self,
        client_agent_id: str,
        provider_agent_id: str,
        evaluator_agent_id: str,
        amount: Decimal,
        token: str,
        chain: str,
        deadline_hours: int = 72,
        description: str = "",
        metadata: dict | None = None,
    ) -> Job:
        """
        Create a new ERC-8183 job between three parties.

        Args:
            client_agent_id: Agent that creates and funds the job
            provider_agent_id: Agent that delivers the work
            evaluator_agent_id: Agent that approves or rejects the deliverable
            amount: Payment amount in token units
            token: Token type (e.g. "USDC")
            chain: Blockchain network
            deadline_hours: Hours until job expires (default: 72)
            description: Human-readable job description
            metadata: Optional additional metadata

        Returns:
            Created Job instance

        Raises:
            SardisValidationError: If amount <= 0 or parties are not distinct
        """
        # Validation
        if amount <= 0:
            raise SardisValidationError("Job amount must be positive", field="amount")

        parties = {client_agent_id, provider_agent_id, evaluator_agent_id}
        if len(parties) < 3:
            raise SardisValidationError(
                "Client, provider, and evaluator must be three distinct agents"
            )

        job_id = f"job_{uuid4().hex[:16]}"
        now = datetime.now(UTC)
        deadline = now + timedelta(hours=deadline_hours)

        job = Job(
            id=job_id,
            client_agent_id=client_agent_id,
            provider_agent_id=provider_agent_id,
            evaluator_agent_id=evaluator_agent_id,
            amount=amount,
            token=token,
            chain=chain,
            state=JobState.OPEN,
            created_at=now,
            deadline=deadline,
            description=description,
            metadata=metadata or {},
        )

        # Persist to database
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO erc8183_jobs (
                    id, client_agent_id, provider_agent_id, evaluator_agent_id,
                    amount, token, chain, state, created_at, deadline,
                    description, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                job.id,
                job.client_agent_id,
                job.provider_agent_id,
                job.evaluator_agent_id,
                job.amount,
                job.token,
                job.chain,
                job.state.value,
                job.created_at,
                job.deadline,
                job.description,
                json.dumps(job.metadata),
            )

        logger.info(
            "erc8183 job created: id=%s client=%s provider=%s evaluator=%s amount=%s",
            job.id, client_agent_id, provider_agent_id, evaluator_agent_id, amount,
        )

        return job

    async def fund_job(self, job_id: str, tx_hash: str) -> Job:
        """
        Mark job as funded after on-chain transaction.

        Args:
            job_id: Job identifier
            tx_hash: On-chain funding transaction hash

        Returns:
            Updated Job instance

        Raises:
            SardisNotFoundError: If job not found
            SardisConflictError: If invalid state transition
        """
        job = await self.get_job(job_id)

        if not job.can_transition_to(JobState.FUNDED):
            raise SardisConflictError(
                f"Cannot fund job in state {job.state.value}"
            )

        now = datetime.now(UTC)

        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE erc8183_jobs
                SET state = $1, funded_at = $2, funding_tx_hash = $3, updated_at = $4
                WHERE id = $5
                """,
                JobState.FUNDED.value,
                now,
                tx_hash,
                now,
                job_id,
            )

        job.state = JobState.FUNDED
        job.funded_at = now
        job.funding_tx_hash = tx_hash
        job.updated_at = now

        logger.info("erc8183 job funded: id=%s tx=%s", job_id, tx_hash)

        return job

    async def submit_deliverable(
        self,
        job_id: str,
        deliverable_uri: str,
        deliverable_hash: str,
    ) -> Job:
        """
        Provider submits deliverable for evaluation.

        Args:
            job_id: Job identifier
            deliverable_uri: URI to deliverable (IPFS/HTTP)
            deliverable_hash: Content hash of the deliverable

        Returns:
            Updated Job instance

        Raises:
            SardisNotFoundError: If job not found
            SardisConflictError: If invalid state transition
        """
        job = await self.get_job(job_id)

        if not job.can_transition_to(JobState.SUBMITTED):
            raise SardisConflictError(
                f"Cannot submit deliverable for job in state {job.state.value}"
            )

        now = datetime.now(UTC)

        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE erc8183_jobs
                SET state = $1, deliverable_uri = $2, deliverable_hash = $3,
                    submitted_at = $4, updated_at = $5
                WHERE id = $6
                """,
                JobState.SUBMITTED.value,
                deliverable_uri,
                deliverable_hash,
                now,
                now,
                job_id,
            )

        job.state = JobState.SUBMITTED
        job.deliverable_uri = deliverable_uri
        job.deliverable_hash = deliverable_hash
        job.submitted_at = now
        job.updated_at = now

        logger.info("erc8183 job deliverable submitted: id=%s uri=%s", job_id, deliverable_uri)

        return job

    async def evaluate_job(
        self,
        job_id: str,
        evaluator_agent_id: str,
        approved: bool,
        reason: str = "",
        evidence_uri: str = "",
        trust_score: float | None = None,
    ) -> Job:
        """
        Evaluator approves or rejects the submitted deliverable.

        Args:
            job_id: Job identifier
            evaluator_agent_id: Evaluator agent ID (must match job's evaluator)
            approved: True to approve (COMPLETED), False to reject (REJECTED)
            reason: Evaluation reason
            evidence_uri: Optional URI to evaluation evidence
            trust_score: Optional trust score for the evaluation

        Returns:
            Updated Job instance

        Raises:
            SardisNotFoundError: If job not found
            SardisConflictError: If invalid state transition
            SardisValidationError: If evaluator does not match
        """
        job = await self.get_job(job_id)

        # Validate evaluator identity
        if job.evaluator_agent_id != evaluator_agent_id:
            raise SardisValidationError(
                "Only the designated evaluator can evaluate this job",
                field="evaluator_agent_id",
            )

        target_state = JobState.COMPLETED if approved else JobState.REJECTED
        if not job.can_transition_to(target_state):
            raise SardisConflictError(
                f"Cannot evaluate job in state {job.state.value}"
            )

        now = datetime.now(UTC)
        evaluation_result = "approved" if approved else "rejected"

        async with Database.transaction() as conn:
            # Update job state
            await conn.execute(
                """
                UPDATE erc8183_jobs
                SET state = $1, evaluation_result = $2, evaluation_reason = $3,
                    evaluated_at = $4, updated_at = $5
                WHERE id = $6
                """,
                target_state.value,
                evaluation_result,
                reason,
                now,
                now,
                job_id,
            )

            # Record evaluation in separate evaluations table
            eval_id = f"eval_{uuid4().hex[:16]}"
            await conn.execute(
                """
                INSERT INTO erc8183_evaluations (
                    id, job_id, evaluator_agent_id, result, reason,
                    evidence_uri, trust_score, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                eval_id,
                job_id,
                evaluator_agent_id,
                evaluation_result,
                reason,
                evidence_uri,
                trust_score,
                now,
            )

        job.state = target_state
        job.evaluation_result = evaluation_result
        job.evaluation_reason = reason
        job.evaluated_at = now
        job.updated_at = now

        logger.info(
            "erc8183 job evaluated: id=%s result=%s evaluator=%s",
            job_id, evaluation_result, evaluator_agent_id,
        )

        return job

    async def expire_job(self, job_id: str) -> Job:
        """
        Mark a single job as expired if past deadline.

        Args:
            job_id: Job identifier

        Returns:
            Updated Job instance

        Raises:
            SardisNotFoundError: If job not found
            SardisConflictError: If invalid state transition or not expired
        """
        job = await self.get_job(job_id)

        if not job.is_expired():
            raise SardisConflictError("Job has not reached its deadline yet")

        if not job.can_transition_to(JobState.EXPIRED):
            raise SardisConflictError(
                f"Cannot expire job in state {job.state.value}"
            )

        now = datetime.now(UTC)

        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE erc8183_jobs
                SET state = $1, updated_at = $2
                WHERE id = $3
                """,
                JobState.EXPIRED.value,
                now,
                job_id,
            )

        job.state = JobState.EXPIRED
        job.updated_at = now

        logger.info("erc8183 job expired: id=%s", job_id)

        return job

    async def dispute_job(self, job_id: str, reason: str) -> Job:
        """
        Open a dispute for a job.

        Args:
            job_id: Job identifier
            reason: Dispute reason

        Returns:
            Updated Job instance

        Raises:
            SardisNotFoundError: If job not found
            SardisConflictError: If invalid state transition
        """
        job = await self.get_job(job_id)

        if not job.can_transition_to(JobState.DISPUTED):
            raise SardisConflictError(
                f"Cannot dispute job in state {job.state.value}"
            )

        now = datetime.now(UTC)

        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE erc8183_jobs
                SET state = $1, updated_at = $2,
                    metadata = metadata || $3
                WHERE id = $4
                """,
                JobState.DISPUTED.value,
                now,
                json.dumps({"dispute_reason": reason, "disputed_at": now.isoformat()}),
                job_id,
            )

        job.state = JobState.DISPUTED
        job.metadata["dispute_reason"] = reason
        job.metadata["disputed_at"] = now.isoformat()
        job.updated_at = now

        logger.info("erc8183 job disputed: id=%s reason=%s", job_id, reason)

        return job

    async def get_job(self, job_id: str) -> Job:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job instance

        Raises:
            SardisNotFoundError: If job not found
        """
        async with Database.connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, client_agent_id, provider_agent_id, evaluator_agent_id,
                       amount, token, chain, state, created_at, deadline,
                       funded_at, funding_tx_hash, deliverable_uri, deliverable_hash,
                       submitted_at, evaluation_result, evaluation_reason,
                       evaluated_at, evaluation_tx_hash, settlement_tx_hash,
                       settled_at, onchain_job_id, contract_address,
                       hook_contract_address, description, metadata, updated_at
                FROM erc8183_jobs
                WHERE id = $1
                """,
                job_id,
            )

            if not row:
                raise SardisNotFoundError("Job", job_id)

            return self._row_to_job(row)

    async def list_jobs(
        self,
        agent_id: str,
        role: Literal["client", "provider", "evaluator", "any"] = "any",
        state: JobState | None = None,
    ) -> list[Job]:
        """
        List jobs for an agent.

        Args:
            agent_id: Agent identifier
            role: Filter by role (client, provider, evaluator, or any)
            state: Optional state filter

        Returns:
            List of Job instances
        """
        query_parts = [
            "SELECT id, client_agent_id, provider_agent_id, evaluator_agent_id,",
            "       amount, token, chain, state, created_at, deadline,",
            "       funded_at, funding_tx_hash, deliverable_uri, deliverable_hash,",
            "       submitted_at, evaluation_result, evaluation_reason,",
            "       evaluated_at, evaluation_tx_hash, settlement_tx_hash,",
            "       settled_at, onchain_job_id, contract_address,",
            "       hook_contract_address, description, metadata, updated_at",
            "FROM erc8183_jobs WHERE 1=1",
        ]
        params: list = []
        param_idx = 1

        # Role filter
        if role == "client":
            query_parts.append(f" AND client_agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1
        elif role == "provider":
            query_parts.append(f" AND provider_agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1
        elif role == "evaluator":
            query_parts.append(f" AND evaluator_agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1
        else:  # any
            query_parts.append(
                f" AND (client_agent_id = ${param_idx}"
                f" OR provider_agent_id = ${param_idx}"
                f" OR evaluator_agent_id = ${param_idx})"
            )
            params.append(agent_id)
            param_idx += 1

        # State filter
        if state:
            query_parts.append(f" AND state = ${param_idx}")
            params.append(state.value)
            param_idx += 1

        query_parts.append(" ORDER BY created_at DESC")
        query = " ".join(query_parts)

        async with Database.connection() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_job(row) for row in rows]

    async def check_expired_jobs(self) -> list[Job]:
        """
        Find and mark expired jobs in bulk.

        Returns:
            List of jobs that were marked as expired
        """
        now = datetime.now(UTC)

        async with Database.connection() as conn:
            rows = await conn.fetch(
                """
                UPDATE erc8183_jobs
                SET state = $1, updated_at = $2
                WHERE deadline < $3
                  AND state IN ($4, $5, $6)
                RETURNING id, client_agent_id, provider_agent_id, evaluator_agent_id,
                          amount, token, chain, state, created_at, deadline,
                          funded_at, funding_tx_hash, deliverable_uri, deliverable_hash,
                          submitted_at, evaluation_result, evaluation_reason,
                          evaluated_at, evaluation_tx_hash, settlement_tx_hash,
                          settled_at, onchain_job_id, contract_address,
                          hook_contract_address, description, metadata, updated_at
                """,
                JobState.EXPIRED.value,
                now,
                now,
                JobState.OPEN.value,
                JobState.FUNDED.value,
                JobState.SUBMITTED.value,
            )

            jobs = [self._row_to_job(row) for row in rows]

            if jobs:
                logger.info("erc8183 expired %d jobs", len(jobs))

            return jobs

    @staticmethod
    def _row_to_job(row) -> Job:
        """Convert database row to Job instance."""
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return Job(
            id=row["id"],
            client_agent_id=row["client_agent_id"],
            provider_agent_id=row["provider_agent_id"],
            evaluator_agent_id=row["evaluator_agent_id"],
            amount=row["amount"],
            token=row["token"],
            chain=row["chain"],
            state=JobState(row["state"]),
            created_at=row["created_at"],
            deadline=row["deadline"],
            funded_at=row.get("funded_at"),
            funding_tx_hash=row.get("funding_tx_hash"),
            deliverable_uri=row.get("deliverable_uri"),
            deliverable_hash=row.get("deliverable_hash"),
            submitted_at=row.get("submitted_at"),
            evaluation_result=row.get("evaluation_result"),
            evaluation_reason=row.get("evaluation_reason"),
            evaluated_at=row.get("evaluated_at"),
            evaluation_tx_hash=row.get("evaluation_tx_hash"),
            settlement_tx_hash=row.get("settlement_tx_hash"),
            settled_at=row.get("settled_at"),
            onchain_job_id=row.get("onchain_job_id"),
            contract_address=row.get("contract_address"),
            hook_contract_address=row.get("hook_contract_address"),
            description=row.get("description", ""),
            metadata=metadata or {},
            updated_at=row["updated_at"],
        )
