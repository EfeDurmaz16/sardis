"""Dispute Protocol — evidence-based dispute resolution.

Supports a 7-state dispute lifecycle:
  FILED → EVIDENCE_COLLECTION → UNDER_REVIEW → RESOLVED_*

Three possible outcomes:
  - RESOLVED_REFUND: Full refund to payer
  - RESOLVED_RELEASE: Full release to merchant
  - RESOLVED_SPLIT: Split between parties (custom ratio)

Usage::

    protocol = DisputeProtocol(pool)
    dispute = await protocol.file_dispute(
        escrow_hold_id="esc_abc123",
        filed_by="agent_procurement",
        reason="Service not delivered as described",
    )
    await protocol.submit_evidence(
        dispute.dispute_id,
        submitted_by="agent_procurement",
        evidence_type="screenshot",
        content={"url": "https://..."},
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.dispute")


class DisputeStatus(str, Enum):
    """Lifecycle states for a dispute."""
    FILED = "filed"                          # Dispute submitted
    EVIDENCE_COLLECTION = "evidence_collection"  # Both parties submitting evidence
    UNDER_REVIEW = "under_review"            # Under arbitration review
    RESOLVED_REFUND = "resolved_refund"      # Resolved: full refund
    RESOLVED_RELEASE = "resolved_release"    # Resolved: release to merchant
    RESOLVED_SPLIT = "resolved_split"        # Resolved: split
    WITHDRAWN = "withdrawn"                  # Withdrawn by filer


class DisputeReason(str, Enum):
    """Standard dispute reason codes."""
    NOT_DELIVERED = "not_delivered"
    NOT_AS_DESCRIBED = "not_as_described"
    UNAUTHORIZED = "unauthorized"
    DUPLICATE = "duplicate"
    SERVICE_QUALITY = "service_quality"
    OVERCHARGE = "overcharge"
    OTHER = "other"


DISPUTE_VALID_TRANSITIONS: dict[tuple[str, str], str] = {
    (DisputeStatus.FILED, DisputeStatus.EVIDENCE_COLLECTION): "open_evidence",
    (DisputeStatus.FILED, DisputeStatus.WITHDRAWN): "withdraw",
    (DisputeStatus.EVIDENCE_COLLECTION, DisputeStatus.UNDER_REVIEW): "close_evidence",
    (DisputeStatus.EVIDENCE_COLLECTION, DisputeStatus.WITHDRAWN): "withdraw",
    (DisputeStatus.UNDER_REVIEW, DisputeStatus.RESOLVED_REFUND): "resolve_refund",
    (DisputeStatus.UNDER_REVIEW, DisputeStatus.RESOLVED_RELEASE): "resolve_release",
    (DisputeStatus.UNDER_REVIEW, DisputeStatus.RESOLVED_SPLIT): "resolve_split",
}

# Default deadlines
EVIDENCE_DEADLINE_HOURS = 72
REVIEW_DEADLINE_HOURS = 48


@dataclass
class DisputeEvidence:
    """A piece of evidence submitted by either party."""

    evidence_id: str = field(default_factory=lambda: f"evi_{uuid4().hex[:12]}")
    dispute_id: str = ""
    submitted_by: str = ""
    party: str = ""  # "payer" or "merchant"
    evidence_type: str = ""  # screenshot, receipt, log, communication, other
    content: dict[str, Any] = field(default_factory=dict)
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DisputeResolution:
    """The outcome of a dispute resolution."""

    resolution_id: str = field(default_factory=lambda: f"res_{uuid4().hex[:12]}")
    dispute_id: str = ""
    outcome: DisputeStatus = DisputeStatus.RESOLVED_RELEASE
    resolved_by: str = ""  # arbitrator ID or "auto"

    # Split details (for RESOLVED_SPLIT)
    payer_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    merchant_amount: Decimal = field(default_factory=lambda: Decimal("0"))

    reasoning: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Dispute:
    """A payment dispute."""

    dispute_id: str = field(default_factory=lambda: f"dsp_{uuid4().hex[:12]}")
    escrow_hold_id: str = ""
    payment_object_id: str = ""

    # Parties
    payer_id: str = ""
    merchant_id: str = ""
    filed_by: str = ""

    # Details
    reason: DisputeReason = DisputeReason.OTHER
    description: str | None = None
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"

    # Lifecycle
    status: DisputeStatus = DisputeStatus.FILED
    evidence_deadline: datetime | None = None
    review_deadline: datetime | None = None

    # Evidence
    evidence_count: int = 0
    payer_evidence_count: int = 0
    merchant_evidence_count: int = 0

    # Resolution
    resolution: DisputeResolution | None = None
    resolved_at: datetime | None = None

    # Audit
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            DisputeStatus.RESOLVED_REFUND,
            DisputeStatus.RESOLVED_RELEASE,
            DisputeStatus.RESOLVED_SPLIT,
            DisputeStatus.WITHDRAWN,
        )


class DisputeProtocol:
    """Manages the dispute lifecycle."""

    def __init__(self, pool) -> None:
        self._pool = pool

    async def file_dispute(
        self,
        escrow_hold_id: str,
        payment_object_id: str,
        payer_id: str,
        merchant_id: str,
        filed_by: str,
        reason: DisputeReason,
        description: str | None = None,
        amount: Decimal = Decimal("0"),
        currency: str = "USDC",
    ) -> Dispute:
        """File a new dispute."""
        dispute = Dispute(
            escrow_hold_id=escrow_hold_id,
            payment_object_id=payment_object_id,
            payer_id=payer_id,
            merchant_id=merchant_id,
            filed_by=filed_by,
            reason=reason,
            description=description,
            amount=amount,
            currency=currency,
            evidence_deadline=datetime.now(UTC) + timedelta(hours=EVIDENCE_DEADLINE_HOURS),
        )

        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO disputes
                   (dispute_id, escrow_hold_id, payment_object_id,
                    payer_id, merchant_id, filed_by,
                    reason, description, amount, currency,
                    status, evidence_deadline, metadata)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
                dispute.dispute_id, dispute.escrow_hold_id,
                dispute.payment_object_id, dispute.payer_id,
                dispute.merchant_id, dispute.filed_by,
                dispute.reason.value, dispute.description,
                dispute.amount, dispute.currency,
                dispute.status.value, dispute.evidence_deadline,
                dispute.metadata,
            )

        logger.info("Dispute filed: %s on escrow %s", dispute.dispute_id, escrow_hold_id)
        return dispute

    async def submit_evidence(
        self,
        dispute_id: str,
        submitted_by: str,
        party: str,
        evidence_type: str,
        content: dict[str, Any],
        description: str | None = None,
    ) -> DisputeEvidence:
        """Submit evidence for a dispute."""
        evidence = DisputeEvidence(
            dispute_id=dispute_id,
            submitted_by=submitted_by,
            party=party,
            evidence_type=evidence_type,
            content=content,
            description=description,
        )

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Verify dispute is in evidence collection phase
                row = await conn.fetchrow(
                    "SELECT status, evidence_deadline FROM disputes WHERE dispute_id = $1 FOR UPDATE NOWAIT",
                    dispute_id,
                )
                if not row:
                    raise ValueError(f"Dispute {dispute_id} not found")
                if row["status"] not in ("filed", "evidence_collection"):
                    raise ValueError(f"Cannot submit evidence: dispute is {row['status']}")
                if row["evidence_deadline"] and datetime.now(UTC) > row["evidence_deadline"]:
                    raise ValueError("Evidence deadline has passed")

                await conn.execute(
                    """INSERT INTO dispute_evidence
                       (evidence_id, dispute_id, submitted_by, party,
                        evidence_type, content, description)
                       VALUES ($1,$2,$3,$4,$5,$6,$7)""",
                    evidence.evidence_id, dispute_id, submitted_by,
                    party, evidence_type, content, description,
                )

                # Update counters and transition to evidence_collection if needed
                counter_col = "payer_evidence_count" if party == "payer" else "merchant_evidence_count"
                await conn.execute(
                    f"""UPDATE disputes
                        SET status = 'evidence_collection',
                            evidence_count = evidence_count + 1,
                            {counter_col} = {counter_col} + 1,
                            updated_at = now()
                        WHERE dispute_id = $1""",
                    dispute_id,
                )

        logger.info("Evidence %s submitted for dispute %s", evidence.evidence_id, dispute_id)
        return evidence

    async def resolve(
        self,
        dispute_id: str,
        outcome: DisputeStatus,
        resolved_by: str,
        payer_amount: Decimal = Decimal("0"),
        merchant_amount: Decimal = Decimal("0"),
        reasoning: str | None = None,
    ) -> DisputeResolution:
        """Resolve a dispute with one of three outcomes."""
        if outcome not in (
            DisputeStatus.RESOLVED_REFUND,
            DisputeStatus.RESOLVED_RELEASE,
            DisputeStatus.RESOLVED_SPLIT,
        ):
            raise ValueError(f"Invalid resolution outcome: {outcome}")

        resolution = DisputeResolution(
            dispute_id=dispute_id,
            outcome=outcome,
            resolved_by=resolved_by,
            payer_amount=payer_amount,
            merchant_amount=merchant_amount,
            reasoning=reasoning,
        )

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT status FROM disputes WHERE dispute_id = $1 FOR UPDATE NOWAIT",
                    dispute_id,
                )
                if not row:
                    raise ValueError(f"Dispute {dispute_id} not found")
                if row["status"] not in ("evidence_collection", "under_review"):
                    raise ValueError(f"Cannot resolve: dispute is {row['status']}")

                await conn.execute(
                    """UPDATE disputes
                       SET status = $1, resolved_at = now(), updated_at = now()
                       WHERE dispute_id = $2""",
                    outcome.value, dispute_id,
                )

                await conn.execute(
                    """INSERT INTO dispute_resolutions
                       (resolution_id, dispute_id, outcome, resolved_by,
                        payer_amount, merchant_amount, reasoning)
                       VALUES ($1,$2,$3,$4,$5,$6,$7)""",
                    resolution.resolution_id, dispute_id, outcome.value,
                    resolved_by, payer_amount, merchant_amount, reasoning,
                )

        logger.info("Dispute %s resolved: %s", dispute_id, outcome.value)
        return resolution
