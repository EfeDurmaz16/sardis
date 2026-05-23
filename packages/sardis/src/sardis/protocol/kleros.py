"""Kleros decentralized dispute resolution integration.

Implements ERC-792 IArbitrable/IArbitrator interface patterns for
decentralized dispute resolution via Kleros Court. Provides:
- Dispute creation and lifecycle management
- Evidence submission (ERC-1497 Evidence Standard)
- Ruling tracking and appeal management
- Arbitration cost estimation
- Integration with Sardis escrow/refund pipeline

Kleros uses a Schelling-point based juror system where PNK token
holders adjudicate disputes. This module handles off-chain coordination
and on-chain interaction building.

Reference: https://kleros.io
ERC-792: https://eips.ethereum.org/EIPS/eip-792
ERC-1497: https://eips.ethereum.org/EIPS/eip-1497
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============ Enums ============


class DisputeStatus(str, Enum):
    """ERC-792 dispute lifecycle states."""
    WAITING = "waiting"          # Created, awaiting evidence period end
    EVIDENCE = "evidence"        # Evidence submission period
    COMMIT = "commit"            # Jurors committing votes (hidden)
    VOTE = "vote"                # Jurors revealing votes
    APPEAL = "appeal"            # Appeal period after ruling
    RESOLVED = "resolved"        # Final ruling executed
    CANCELLED = "cancelled"      # Dispute cancelled (settled)


class Ruling(int, Enum):
    """Standard ERC-792 rulings for payment disputes."""
    REFUSE_TO_RULE = 0   # Jurors abstained / tied
    CLAIMANT_WINS = 1    # Payer (buyer) wins — refund
    RESPONDENT_WINS = 2  # Payee (seller) wins — release


class EvidenceType(str, Enum):
    """Types of evidence that can be submitted."""
    DOCUMENT = "document"
    SCREENSHOT = "screenshot"
    TRANSACTION_PROOF = "transaction_proof"
    COMMUNICATION = "communication"
    EXPERT_REPORT = "expert_report"
    CONTRACT = "contract"
    DELIVERY_PROOF = "delivery_proof"
    OTHER = "other"


class CourtCategory(str, Enum):
    """Kleros court categories (subcourts)."""
    GENERAL = "general"
    ESCROW = "escrow"
    TOKEN_LISTING = "token_listing"
    TECHNICAL = "technical"
    MARKETING = "marketing"
    CURATION = "curation"


class DisputePartyRole(str, Enum):
    """Roles in a dispute."""
    CLAIMANT = "claimant"      # The party filing the dispute
    RESPONDENT = "respondent"  # The party being disputed against
    ARBITRATOR = "arbitrator"  # Kleros court / arbiter


# ============ Constants ============

# Kleros contract addresses (Arbitrum One mainnet)
KLEROS_ARBITRATOR_ADDRESS = "0x988b3A538b618C7A603e1c11Ab82Cd16dbE28069"
KLEROS_EVIDENCE_DISPLAY_URI = "https://resolve.kleros.io"

# Default configuration
DEFAULT_NUM_JURORS = 3
DEFAULT_EVIDENCE_PERIOD_DAYS = 7
DEFAULT_APPEAL_PERIOD_DAYS = 3
MIN_DISPUTE_AMOUNT_USD = Decimal("10")  # Minimum to justify arbitration cost

# Arbitration fee estimates (in ETH, approximate)
ARBITRATION_FEE_ESTIMATES: dict[CourtCategory, Decimal] = {
    CourtCategory.GENERAL: Decimal("0.03"),
    CourtCategory.ESCROW: Decimal("0.05"),
    CourtCategory.TECHNICAL: Decimal("0.10"),
    CourtCategory.TOKEN_LISTING: Decimal("0.04"),
    CourtCategory.MARKETING: Decimal("0.03"),
    CourtCategory.CURATION: Decimal("0.02"),
}


# ============ Data Classes ============


@dataclass
class Evidence:
    """Evidence submission per ERC-1497."""
    evidence_id: str
    dispute_id: str
    submitted_by: str  # party address or ID
    evidence_type: EvidenceType
    title: str
    description: str
    file_uri: str | None = None
    file_hash: str | None = None  # IPFS CID or SHA-256
    metadata: dict[str, Any] = field(default_factory=dict)
    submitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def evidence_uri(self) -> str:
        """Build ERC-1497 evidence URI (JSON object)."""
        return json.dumps({
            "name": self.title,
            "description": self.description,
            "fileURI": self.file_uri or "",
            "fileHash": self.file_hash or "",
            "fileTypeExtension": self.metadata.get("extension", ""),
        })


@dataclass
class DisputeParty:
    """A party in a dispute."""
    party_id: str
    role: DisputePartyRole
    address: str | None = None  # On-chain address
    name: str | None = None
    evidence_submitted: int = 0


@dataclass
class Dispute:
    """Kleros dispute record."""
    dispute_id: str
    escrow_id: str | None = None  # Linked Sardis escrow
    court: CourtCategory = CourtCategory.ESCROW
    status: DisputeStatus = DisputeStatus.WAITING
    claimant: DisputeParty | None = None
    respondent: DisputeParty | None = None

    # Amounts
    amount_usd: Decimal = Decimal("0")
    arbitration_fee_eth: Decimal = Decimal("0")

    # Configuration
    num_jurors: int = DEFAULT_NUM_JURORS
    evidence_period_end: datetime | None = None
    appeal_period_end: datetime | None = None

    # Ruling
    ruling: Ruling | None = None
    ruling_executed: bool = False
    ruling_timestamp: datetime | None = None

    # Appeal
    appeal_count: int = 0
    max_appeals: int = 3
    current_round: int = 1

    # Metadata
    reason: str = ""
    metadata_uri: str | None = None  # IPFS URI for dispute metadata
    on_chain_dispute_id: int | None = None  # Kleros on-chain ID
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Evidence
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.status not in (DisputeStatus.RESOLVED, DisputeStatus.CANCELLED)

    @property
    def is_appealable(self) -> bool:
        return (
            self.status == DisputeStatus.APPEAL
            and self.appeal_count < self.max_appeals
        )

    @property
    def can_submit_evidence(self) -> bool:
        return self.status in (DisputeStatus.WAITING, DisputeStatus.EVIDENCE)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)


@dataclass
class ArbitrationCostEstimate:
    """Estimated cost of arbitration."""
    court: CourtCategory
    num_jurors: int
    fee_eth: Decimal
    fee_usd_estimate: Decimal
    is_economical: bool  # Whether dispute amount justifies the cost


@dataclass
class DisputeRulingResult:
    """Result of a dispute ruling."""
    dispute_id: str
    ruling: Ruling
    ruling_description: str
    executed: bool = False
    appeal_possible: bool = False
    appeal_deadline: datetime | None = None

    @property
    def claimant_won(self) -> bool:
        return self.ruling == Ruling.CLAIMANT_WINS

    @property
    def respondent_won(self) -> bool:
        return self.ruling == Ruling.RESPONDENT_WINS

    @property
    def refused_to_rule(self) -> bool:
        return self.ruling == Ruling.REFUSE_TO_RULE


# ============ Calldata Builders ============


def build_create_dispute_calldata(
    num_jurors: int,
    subcourt_id: int,
    metadata_hash: bytes,
) -> bytes:
    """Build calldata for IArbitrator.createDispute(uint256, bytes).

    Args:
        num_jurors: Number of jurors requested
        subcourt_id: Kleros subcourt ID
        metadata_hash: Hash of dispute metadata (for MetaEvidence)

    Returns:
        ABI-encoded calldata bytes
    """
    # createDispute(uint256 _numberOfChoices, bytes _extraData)
    selector = bytes.fromhex("c13517e1")  # createDispute(uint256,bytes)
    choices = (2).to_bytes(32, "big")  # Always 2 choices for payment disputes
    # Extra data: subcourt ID + num jurors
    extra_data = subcourt_id.to_bytes(32, "big") + num_jurors.to_bytes(32, "big")
    # ABI encoding
    offset = (64).to_bytes(32, "big")  # offset to bytes
    length = len(extra_data).to_bytes(32, "big")
    padded = extra_data + b"\x00" * (32 - len(extra_data) % 32) if len(extra_data) % 32 else extra_data
    return selector + choices + offset + length + padded


def build_submit_evidence_calldata(
    dispute_id: int,
    evidence_uri: str,
) -> bytes:
    """Build calldata for IArbitrable.submitEvidence(uint256, string).

    Args:
        dispute_id: On-chain dispute ID
        evidence_uri: IPFS URI of evidence JSON

    Returns:
        ABI-encoded calldata bytes
    """
    selector = bytes.fromhex("5bb5e54b")  # submitEvidence(uint256,string)
    dispute_bytes = dispute_id.to_bytes(32, "big")
    uri_bytes = evidence_uri.encode("utf-8")
    offset = (64).to_bytes(32, "big")
    length = len(uri_bytes).to_bytes(32, "big")
    padding_len = (32 - len(uri_bytes) % 32) % 32
    padded = uri_bytes + b"\x00" * padding_len
    return selector + dispute_bytes + offset + length + padded


def build_appeal_calldata(dispute_id: int) -> bytes:
    """Build calldata for IArbitrator.appeal(uint256, bytes).

    Args:
        dispute_id: On-chain dispute ID

    Returns:
        ABI-encoded calldata bytes
    """
    selector = bytes.fromhex("44b22815")  # appeal(uint256,bytes)
    dispute_bytes = dispute_id.to_bytes(32, "big")
    # Empty extra data
    offset = (64).to_bytes(32, "big")
    length = (0).to_bytes(32, "big")
    return selector + dispute_bytes + offset + length


def build_rule_calldata(dispute_id: int, ruling: int) -> bytes:
    """Build calldata for IArbitrable.rule(uint256, uint256).

    Args:
        dispute_id: On-chain dispute ID
        ruling: Ruling value (0=refuse, 1=claimant, 2=respondent)

    Returns:
        ABI-encoded calldata bytes
    """
    selector = bytes.fromhex("311a6c56")  # rule(uint256,uint256)
    return selector + dispute_id.to_bytes(32, "big") + ruling.to_bytes(32, "big")


# ============ Service Class ============


class KlerosDisputeResolver:
    """Kleros dispute resolution service.

    Manages the lifecycle of disputes using Kleros Court as the
    decentralized arbitrator. Integrates with Sardis escrow for
    payment dispute resolution.
    """

    def __init__(
        self,
        arbitrator_address: str | None = None,
        default_court: CourtCategory = CourtCategory.ESCROW,
        eth_price_usd: Decimal = Decimal("3000"),
    ):
        self._arbitrator = arbitrator_address or os.getenv(
            "KLEROS_ARBITRATOR_ADDRESS", KLEROS_ARBITRATOR_ADDRESS
        )
        self._default_court = default_court
        self._eth_price_usd = eth_price_usd
        self._disputes: dict[str, Dispute] = {}

    def create_dispute(
        self,
        claimant_id: str,
        respondent_id: str,
        amount_usd: Decimal,
        reason: str,
        escrow_id: str | None = None,
        court: CourtCategory | None = None,
        num_jurors: int = DEFAULT_NUM_JURORS,
        claimant_address: str | None = None,
        respondent_address: str | None = None,
    ) -> Dispute:
        """Create a new dispute for Kleros arbitration.

        Args:
            claimant_id: ID of the party filing the dispute
            respondent_id: ID of the party being disputed against
            amount_usd: Disputed amount in USD
            reason: Human-readable dispute reason
            escrow_id: Optional linked Sardis escrow ID
            court: Kleros subcourt category
            num_jurors: Number of jurors (odd number recommended)
            claimant_address: On-chain address of claimant
            respondent_address: On-chain address of respondent
        """
        court = court or self._default_court
        fee = ARBITRATION_FEE_ESTIMATES.get(court, Decimal("0.05"))

        dispute = Dispute(
            dispute_id=f"disp_{uuid.uuid4().hex[:16]}",
            escrow_id=escrow_id,
            court=court,
            status=DisputeStatus.EVIDENCE,
            claimant=DisputeParty(
                party_id=claimant_id,
                role=DisputePartyRole.CLAIMANT,
                address=claimant_address,
            ),
            respondent=DisputeParty(
                party_id=respondent_id,
                role=DisputePartyRole.RESPONDENT,
                address=respondent_address,
            ),
            amount_usd=amount_usd,
            arbitration_fee_eth=fee * num_jurors,
            num_jurors=num_jurors,
            evidence_period_end=datetime.now(UTC) + timedelta(days=DEFAULT_EVIDENCE_PERIOD_DAYS),
            reason=reason,
        )

        self._disputes[dispute.dispute_id] = dispute
        logger.info(
            f"Created dispute {dispute.dispute_id}: {claimant_id} vs {respondent_id}, "
            f"${amount_usd}, court={court.value}"
        )
        return dispute

    def get_dispute(self, dispute_id: str) -> Dispute | None:
        """Get a dispute by ID."""
        return self._disputes.get(dispute_id)

    def submit_evidence(
        self,
        dispute_id: str,
        submitted_by: str,
        evidence_type: EvidenceType,
        title: str,
        description: str,
        file_uri: str | None = None,
        file_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Evidence:
        """Submit evidence to a dispute.

        Args:
            dispute_id: Dispute to submit evidence to
            submitted_by: ID of the submitting party
            evidence_type: Type of evidence
            title: Evidence title
            description: Evidence description
            file_uri: URI to evidence file (e.g., IPFS)
            file_hash: Hash of evidence file
            metadata: Additional metadata

        Raises:
            ValueError: If dispute not found or evidence period closed
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")
        if not dispute.can_submit_evidence:
            raise ValueError(
                f"Cannot submit evidence: dispute is in {dispute.status.value} state"
            )

        evidence = Evidence(
            evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
            dispute_id=dispute_id,
            submitted_by=submitted_by,
            evidence_type=evidence_type,
            title=title,
            description=description,
            file_uri=file_uri,
            file_hash=file_hash,
            metadata=metadata or {},
        )

        dispute.evidence.append(evidence)
        dispute.updated_at = datetime.now(UTC)

        # Update party evidence count
        if dispute.claimant and dispute.claimant.party_id == submitted_by:
            dispute.claimant.evidence_submitted += 1
        elif dispute.respondent and dispute.respondent.party_id == submitted_by:
            dispute.respondent.evidence_submitted += 1

        logger.info(
            f"Evidence {evidence.evidence_id} submitted to dispute {dispute_id} "
            f"by {submitted_by}: {title}"
        )
        return evidence

    def advance_to_voting(self, dispute_id: str) -> Dispute:
        """Close evidence period and advance to voting.

        Args:
            dispute_id: Dispute ID

        Raises:
            ValueError: If dispute not in evidence state
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")
        if dispute.status != DisputeStatus.EVIDENCE:
            raise ValueError(
                f"Cannot advance: dispute is in {dispute.status.value} state"
            )

        dispute.status = DisputeStatus.VOTE
        dispute.updated_at = datetime.now(UTC)
        logger.info(f"Dispute {dispute_id} advanced to voting")
        return dispute

    def submit_ruling(
        self,
        dispute_id: str,
        ruling: Ruling,
    ) -> DisputeRulingResult:
        """Submit a ruling for a dispute.

        Args:
            dispute_id: Dispute ID
            ruling: The ruling (0=refuse, 1=claimant, 2=respondent)

        Raises:
            ValueError: If dispute not in votable state
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")
        if dispute.status not in (DisputeStatus.VOTE, DisputeStatus.APPEAL):
            raise ValueError(
                f"Cannot rule: dispute is in {dispute.status.value} state"
            )

        dispute.ruling = ruling
        dispute.ruling_timestamp = datetime.now(UTC)
        dispute.status = DisputeStatus.APPEAL
        dispute.appeal_period_end = datetime.now(UTC) + timedelta(days=DEFAULT_APPEAL_PERIOD_DAYS)
        dispute.updated_at = datetime.now(UTC)

        descriptions = {
            Ruling.REFUSE_TO_RULE: "Jurors refused to rule / tied vote",
            Ruling.CLAIMANT_WINS: "Claimant wins — funds to be refunded",
            Ruling.RESPONDENT_WINS: "Respondent wins — funds to be released",
        }

        result = DisputeRulingResult(
            dispute_id=dispute_id,
            ruling=ruling,
            ruling_description=descriptions.get(ruling, "Unknown ruling"),
            executed=False,
            appeal_possible=dispute.is_appealable,
            appeal_deadline=dispute.appeal_period_end,
        )

        logger.info(
            f"Ruling for dispute {dispute_id}: {ruling.name} "
            f"(appeal possible: {result.appeal_possible})"
        )
        return result

    def appeal_ruling(self, dispute_id: str) -> Dispute:
        """Appeal a dispute ruling.

        Args:
            dispute_id: Dispute ID

        Raises:
            ValueError: If appeal not possible
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")
        if not dispute.is_appealable:
            raise ValueError(
                f"Cannot appeal: status={dispute.status.value}, "
                f"appeals={dispute.appeal_count}/{dispute.max_appeals}"
            )

        dispute.appeal_count += 1
        dispute.current_round += 1
        dispute.num_jurors = dispute.num_jurors * 2 + 1  # Double jurors + 1
        dispute.status = DisputeStatus.EVIDENCE  # Reopen evidence
        dispute.evidence_period_end = datetime.now(UTC) + timedelta(days=DEFAULT_EVIDENCE_PERIOD_DAYS)
        dispute.ruling = None
        dispute.updated_at = datetime.now(UTC)

        logger.info(
            f"Dispute {dispute_id} appealed (round {dispute.current_round}, "
            f"{dispute.num_jurors} jurors)"
        )
        return dispute

    def execute_ruling(self, dispute_id: str) -> DisputeRulingResult:
        """Execute the final ruling after appeal period expires.

        Args:
            dispute_id: Dispute ID

        Raises:
            ValueError: If no ruling or still in appeal period
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")
        if dispute.ruling is None:
            raise ValueError("No ruling to execute")
        if dispute.status != DisputeStatus.APPEAL:
            raise ValueError(
                f"Cannot execute: dispute is in {dispute.status.value} state"
            )

        dispute.status = DisputeStatus.RESOLVED
        dispute.ruling_executed = True
        dispute.updated_at = datetime.now(UTC)

        descriptions = {
            Ruling.REFUSE_TO_RULE: "Ruling executed: refused to rule — split funds",
            Ruling.CLAIMANT_WINS: "Ruling executed: claimant wins — refund initiated",
            Ruling.RESPONDENT_WINS: "Ruling executed: respondent wins — funds released",
        }

        result = DisputeRulingResult(
            dispute_id=dispute_id,
            ruling=dispute.ruling,
            ruling_description=descriptions.get(dispute.ruling, "Ruling executed"),
            executed=True,
            appeal_possible=False,
        )

        logger.info(f"Ruling executed for dispute {dispute_id}: {dispute.ruling.name}")
        return result

    def cancel_dispute(self, dispute_id: str, reason: str = "") -> Dispute:
        """Cancel a dispute (e.g., parties settled).

        Args:
            dispute_id: Dispute ID
            reason: Cancellation reason

        Raises:
            ValueError: If dispute already resolved
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")
        if dispute.status == DisputeStatus.RESOLVED:
            raise ValueError("Cannot cancel a resolved dispute")

        dispute.status = DisputeStatus.CANCELLED
        dispute.reason = reason or dispute.reason
        dispute.updated_at = datetime.now(UTC)
        logger.info(f"Dispute {dispute_id} cancelled: {reason}")
        return dispute

    def estimate_arbitration_cost(
        self,
        court: CourtCategory | None = None,
        num_jurors: int = DEFAULT_NUM_JURORS,
        dispute_amount_usd: Decimal = Decimal("0"),
    ) -> ArbitrationCostEstimate:
        """Estimate the cost of arbitration.

        Args:
            court: Subcourt category
            num_jurors: Number of jurors
            dispute_amount_usd: Amount being disputed (to check economics)
        """
        court = court or self._default_court
        base_fee = ARBITRATION_FEE_ESTIMATES.get(court, Decimal("0.05"))
        total_fee = base_fee * num_jurors
        fee_usd = total_fee * self._eth_price_usd

        is_economical = dispute_amount_usd >= fee_usd * 3  # 3x cost threshold

        return ArbitrationCostEstimate(
            court=court,
            num_jurors=num_jurors,
            fee_eth=total_fee,
            fee_usd_estimate=fee_usd,
            is_economical=is_economical,
        )

    def list_active_disputes(self) -> list[Dispute]:
        """List all active (unresolved) disputes."""
        return [d for d in self._disputes.values() if d.is_active]

    def list_disputes_for_escrow(self, escrow_id: str) -> list[Dispute]:
        """List disputes linked to a specific escrow."""
        return [d for d in self._disputes.values() if d.escrow_id == escrow_id]

    def get_dispute_calldata(self, dispute_id: str) -> bytes | None:
        """Get calldata to create this dispute on-chain.

        Returns None if dispute has no on-chain representation yet.
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return None

        subcourt_map: dict[CourtCategory, int] = {
            CourtCategory.GENERAL: 0,
            CourtCategory.ESCROW: 4,
            CourtCategory.TOKEN_LISTING: 2,
            CourtCategory.TECHNICAL: 1,
            CourtCategory.MARKETING: 5,
            CourtCategory.CURATION: 3,
        }
        subcourt_id = subcourt_map.get(dispute.court, 0)
        metadata = hashlib.sha256(dispute.reason.encode()).digest()
        return build_create_dispute_calldata(dispute.num_jurors, subcourt_id, metadata)


def create_dispute_resolver(
    arbitrator_address: str | None = None,
    default_court: CourtCategory = CourtCategory.ESCROW,
    eth_price_usd: Decimal = Decimal("3000"),
) -> KlerosDisputeResolver:
    """Factory function to create a KlerosDisputeResolver."""
    return KlerosDisputeResolver(
        arbitrator_address=arbitrator_address,
        default_court=default_court,
        eth_price_usd=eth_price_usd,
    )
