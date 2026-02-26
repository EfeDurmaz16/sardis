"""
Confidence-Based Transaction Routing for Tiered Approvals

Routes transactions through graduated approval workflows based on confidence scoring.
High-confidence transactions auto-approve; low-confidence transactions require human review.

How confidence routing works:
────────────────────────────────
1. ConfidenceRouter.calculate_confidence() scores a transaction 0.0–1.0 based on:
   - Agent's historical behavior with this merchant
   - Transaction amount vs. budget capacity
   - Time-of-day and frequency patterns
   - KYA level and policy compliance history
   - Merchant familiarity and risk profile

2. Score maps to ConfidenceLevel:
   - 0.95+ → AUTO_APPROVE (instant execution)
   - 0.85–0.94 → MANAGER_APPROVAL (single approver, 1 hour timeout)
   - 0.70–0.84 → MULTI_SIG (2+ approvers, 24 hour timeout)
   - <0.70 → HUMAN_REWRITE (transaction rejected, requires redesign)

3. ApprovalWorkflow manages the approval lifecycle:
   - Tracks pending approvals per transaction
   - Enforces quorum for multi-sig transactions
   - Auto-expires stale approval requests
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any, TYPE_CHECKING
import math
import uuid

if TYPE_CHECKING:
    from .spending_policy import SpendingPolicy


class ConfidenceLevel(str, Enum):
    """Transaction confidence tier determining approval workflow."""
    AUTO_APPROVE = "auto_approve"
    MANAGER_APPROVAL = "manager_approval"
    MULTI_SIG = "multi_sig"
    HUMAN_REWRITE = "human_rewrite"


@dataclass(slots=True)
class ConfidenceThresholds:
    """
    Configurable thresholds for confidence-based routing.

    Adjust these to tune the risk tolerance of your deployment:
    - Raise auto_approve for faster execution (higher risk)
    - Lower multi_sig for stricter controls (slower execution)
    """
    auto_approve: float = 0.95
    manager: float = 0.85
    multi_sig: float = 0.70

    def get_level(self, score: float) -> ConfidenceLevel:
        """Map confidence score to approval level."""
        if score >= self.auto_approve:
            return ConfidenceLevel.AUTO_APPROVE
        elif score >= self.manager:
            return ConfidenceLevel.MANAGER_APPROVAL
        elif score >= self.multi_sig:
            return ConfidenceLevel.MULTI_SIG
        else:
            return ConfidenceLevel.HUMAN_REWRITE


@dataclass(slots=True)
class TransactionConfidence:
    """
    Confidence assessment for a single transaction.

    Returned by ConfidenceRouter.calculate_confidence() to inform routing decisions.
    """
    score: float  # 0.0–1.0, higher = more confident
    level: ConfidenceLevel
    factors: dict[str, float]  # Individual factor contributions
    recommendation: str
    transaction_id: str = field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:16]}")
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ApprovalRequest:
    """
    An active approval request for a transaction.

    Tracks approvers, votes, and expiration for pending transactions.
    """
    transaction_id: str
    agent_id: str
    amount: Decimal
    merchant_id: Optional[str]
    confidence: TransactionConfidence
    required_approvers: list[str]
    approvals: dict[str, datetime] = field(default_factory=dict)  # approver_id -> timestamp
    rejections: dict[str, tuple[datetime, str]] = field(default_factory=dict)  # approver_id -> (timestamp, reason)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    quorum: int = 1  # Number of approvals required

    def is_expired(self) -> bool:
        """Check if approval request has timed out."""
        return datetime.now(timezone.utc) > self.expires_at

    def is_approved(self) -> bool:
        """Check if quorum has been reached."""
        return len(self.approvals) >= self.quorum

    def is_rejected(self) -> bool:
        """Check if any approver has rejected."""
        return len(self.rejections) > 0

    def add_approval(self, approver_id: str) -> bool:
        """Record an approval vote. Returns True if quorum reached."""
        if approver_id not in self.required_approvers:
            return False
        if approver_id in self.approvals or approver_id in self.rejections:
            return False  # Already voted
        self.approvals[approver_id] = datetime.now(timezone.utc)
        return self.is_approved()

    def add_rejection(self, approver_id: str, reason: str) -> None:
        """Record a rejection vote."""
        if approver_id not in self.required_approvers:
            return
        if approver_id not in self.rejections:
            self.rejections[approver_id] = (datetime.now(timezone.utc), reason)


class ConfidenceRouter:
    """
    Calculate transaction confidence scores and route to appropriate approval workflows.

    Usage:
        router = ConfidenceRouter()
        confidence = router.calculate_confidence(
            agent_id="agent_123",
            transaction={"amount": 500, "merchant": "aws", ...},
            policy=spending_policy,
            history=transaction_history,
        )

        routing = router.route_transaction(confidence)
        # routing = {"approval_type": "auto_approve", "required_approvers": [], "timeout": 0}
    """

    def __init__(self, thresholds: Optional[ConfidenceThresholds] = None):
        """
        Initialize confidence router.

        Args:
            thresholds: Custom confidence thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or ConfidenceThresholds()

    @staticmethod
    def _build_history_stats(history: list[dict[str, Any]]) -> dict[str, Any]:
        """Build single-pass aggregates used by confidence factors."""
        merchant_counts: dict[str, int] = {}
        hour_counts: dict[int, int] = {}
        amount_count = 0
        amount_mean = 0.0
        amount_m2 = 0.0

        for tx in history:
            merchant = tx.get("merchant_id") or tx.get("merchant")
            if merchant:
                merchant_key = str(merchant)
                merchant_counts[merchant_key] = merchant_counts.get(merchant_key, 0) + 1

            tx_time = tx.get("timestamp")
            if isinstance(tx_time, str):
                tx_time = datetime.fromisoformat(tx_time.replace('Z', '+00:00'))
            if isinstance(tx_time, datetime):
                hour_counts[tx_time.hour] = hour_counts.get(tx_time.hour, 0) + 1

            tx_amount = tx.get("amount")
            if tx_amount is None:
                continue
            value = float(tx_amount)
            amount_count += 1
            delta = value - amount_mean
            amount_mean += delta / amount_count
            delta2 = value - amount_mean
            amount_m2 += delta * delta2

        std_dev = 0.0
        if amount_count > 1:
            variance = amount_m2 / (amount_count - 1)
            std_dev = math.sqrt(max(0.0, variance))
        elif amount_count == 1:
            std_dev = amount_mean * 0.5

        return {
            "merchant_counts": merchant_counts,
            "hour_counts": hour_counts,
            "amount_count": amount_count,
            "amount_mean": amount_mean,
            "amount_std_dev": std_dev,
        }

    def calculate_confidence(
        self,
        agent_id: str,
        transaction: dict[str, Any],
        policy: "SpendingPolicy",
        *,
        history: Optional[list[dict[str, Any]]] = None,
        kya_level: Optional[str] = None,
        violation_count: int = 0,
    ) -> TransactionConfidence:
        """
        Calculate confidence score for a transaction.

        Analyzes multiple factors to determine how much we trust this transaction
        to be legitimate and within the agent's expected behavior.

        Args:
            agent_id: Agent making the transaction
            transaction: Transaction details (amount, merchant, timestamp, etc.)
            policy: Agent's spending policy
            history: Recent transaction history (optional, improves accuracy)
            kya_level: Agent's KYA verification level (none/basic/verified/attested)
            violation_count: Number of recent policy violations

        Returns:
            TransactionConfidence with score, level, and routing recommendation
        """
        factors: dict[str, float] = {}

        # Extract transaction details
        amount = Decimal(str(transaction.get("amount", 0)))
        merchant_id = transaction.get("merchant_id") or transaction.get("merchant")
        timestamp = transaction.get("timestamp", datetime.now(timezone.utc))
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        history_stats = self._build_history_stats(history) if history else None

        # ── Factor 1: KYA Level (0.0–0.30 contribution) ──────────────────
        # Higher KYA = higher baseline confidence
        kya_scores = {"none": 0.0, "basic": 0.10, "verified": 0.20, "attested": 0.30}
        factors["kya_level"] = kya_scores.get(kya_level or "none", 0.0)

        # ── Factor 2: Budget Headroom (0.0–0.25 contribution) ────────────
        # More budget remaining = higher confidence
        remaining = float(policy.remaining_total())
        limit = float(policy.limit_total)
        if limit > 0:
            headroom_ratio = remaining / limit
            # Scale: 80%+ headroom = full score, <20% = zero score
            if headroom_ratio >= 0.8:
                factors["budget_headroom"] = 0.25
            elif headroom_ratio >= 0.5:
                factors["budget_headroom"] = 0.20
            elif headroom_ratio >= 0.2:
                factors["budget_headroom"] = 0.10
            else:
                factors["budget_headroom"] = 0.0
        else:
            factors["budget_headroom"] = 0.0

        # ── Factor 3: Merchant Familiarity (0.0–0.20 contribution) ───────
        # Repeat merchants = higher confidence
        if history_stats and merchant_id:
            merchant_count = history_stats["merchant_counts"].get(str(merchant_id), 0)
            if merchant_count >= 10:
                factors["merchant_familiarity"] = 0.20
            elif merchant_count >= 5:
                factors["merchant_familiarity"] = 0.15
            elif merchant_count >= 2:
                factors["merchant_familiarity"] = 0.10
            else:
                factors["merchant_familiarity"] = 0.0  # New merchant
        else:
            factors["merchant_familiarity"] = 0.05  # Unknown, slight penalty

        # ── Factor 4: Amount Normalcy (0.0–0.15 contribution) ────────────
        # Transaction amount within typical range = higher confidence
        if history_stats and history_stats["amount_count"] > 0:
            mean_amount = history_stats["amount_mean"]
            std_dev = history_stats["amount_std_dev"]
            # Z-score check
            if std_dev > 0:
                z_score = abs((float(amount) - mean_amount) / std_dev)
                if z_score <= 1.0:
                    factors["amount_normalcy"] = 0.15  # Within 1 std dev
                elif z_score <= 2.0:
                    factors["amount_normalcy"] = 0.10  # Within 2 std dev
                elif z_score <= 3.0:
                    factors["amount_normalcy"] = 0.05  # Within 3 std dev
                else:
                    factors["amount_normalcy"] = 0.0  # Outlier
            else:
                factors["amount_normalcy"] = 0.10  # No variance, moderate confidence
        else:
            factors["amount_normalcy"] = 0.05

        # ── Factor 5: Time-of-Day Pattern (0.0–0.05 contribution) ────────
        # Transactions during typical hours = higher confidence
        if history_stats:
            current_hour = timestamp.hour
            hour_counts = history_stats["hour_counts"]
            if current_hour in hour_counts and hour_counts[current_hour] >= 2:
                factors["time_pattern"] = 0.05  # Typical hour
            else:
                factors["time_pattern"] = 0.02  # Unusual hour
        else:
            factors["time_pattern"] = 0.03

        # ── Factor 6: Policy Compliance History (0.0–0.05 contribution) ──
        # No recent violations = higher confidence
        if violation_count == 0:
            factors["compliance_history"] = 0.05
        elif violation_count <= 2:
            factors["compliance_history"] = 0.02
        else:
            factors["compliance_history"] = 0.0

        # ── Calculate Total Score ─────────────────────────────────────────
        raw_score = sum(factors.values())
        # Confidence calibration curve:
        # router is typically called after deterministic policy/mandate guards,
        # so we map raw heuristic score through a sigmoid to avoid overly harsh
        # routing while preserving strict ordering across risk levels.
        total_score = 1.0 / (1.0 + math.exp(-5.0 * (raw_score + 0.03)))
        total_score = max(0.0, min(1.0, total_score))

        # ── Determine Confidence Level ────────────────────────────────────
        level = self.thresholds.get_level(total_score)

        # ── Generate Recommendation ───────────────────────────────────────
        if level == ConfidenceLevel.AUTO_APPROVE:
            recommendation = "High confidence - auto-approve and execute immediately"
        elif level == ConfidenceLevel.MANAGER_APPROVAL:
            recommendation = "Medium confidence - single manager approval required"
        elif level == ConfidenceLevel.MULTI_SIG:
            recommendation = "Low confidence - multi-signature approval required"
        else:
            recommendation = "Very low confidence - transaction should be redesigned"

        return TransactionConfidence(
            score=round(total_score, 3),
            level=level,
            factors=factors,
            recommendation=recommendation,
        )

    def route_transaction(self, confidence: TransactionConfidence) -> dict[str, Any]:
        """
        Determine approval workflow based on confidence level.

        Args:
            confidence: TransactionConfidence from calculate_confidence()

        Returns:
            Routing decision dict with:
                - approval_type: ConfidenceLevel enum value
                - required_approvers: List of approver IDs (empty for auto-approve)
                - timeout: Approval timeout in seconds (0 for auto-approve)
                - quorum: Number of approvals needed (1 for manager, 2+ for multi-sig)
        """
        if confidence.level == ConfidenceLevel.AUTO_APPROVE:
            return {
                "approval_type": confidence.level.value,
                "required_approvers": [],
                "timeout": 0,
                "quorum": 0,
            }
        elif confidence.level == ConfidenceLevel.MANAGER_APPROVAL:
            return {
                "approval_type": confidence.level.value,
                "required_approvers": ["manager_default"],  # Placeholder - caller should override
                "timeout": 3600,  # 1 hour
                "quorum": 1,
            }
        elif confidence.level == ConfidenceLevel.MULTI_SIG:
            return {
                "approval_type": confidence.level.value,
                "required_approvers": ["approver_1", "approver_2"],  # Placeholder - caller should override
                "timeout": 86400,  # 24 hours
                "quorum": 2,
            }
        else:  # HUMAN_REWRITE
            return {
                "approval_type": confidence.level.value,
                "required_approvers": [],
                "timeout": 0,
                "quorum": 0,
            }


class ApprovalWorkflow:
    """
    Manage approval lifecycle for transactions requiring human sign-off.

    Tracks pending approvals, enforces quorum rules, and handles timeouts.

    Usage:
        workflow = ApprovalWorkflow()

        # Request approval
        request_id = await workflow.request_approval(
            transaction_id="tx_abc123",
            approvers=["manager@company.com"],
            timeout=3600,
        )

        # Approver votes
        await workflow.approve("tx_abc123", "manager@company.com")

        # Check status
        status = await workflow.get_approval_status("tx_abc123")
    """

    def __init__(self):
        """Initialize approval workflow manager."""
        self._pending_approvals: dict[str, ApprovalRequest] = {}

    async def request_approval(
        self,
        transaction_id: str,
        agent_id: str,
        amount: Decimal,
        confidence: TransactionConfidence,
        approvers: list[str],
        timeout: int,
        quorum: int = 1,
        merchant_id: Optional[str] = None,
    ) -> str:
        """
        Create a new approval request.

        Args:
            transaction_id: Unique transaction identifier
            agent_id: Agent requesting the transaction
            amount: Transaction amount
            confidence: Confidence assessment
            approvers: List of approver identifiers
            timeout: Approval timeout in seconds
            quorum: Number of approvals required
            merchant_id: Target merchant (optional)

        Returns:
            Request ID (same as transaction_id)
        """
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout)

        request = ApprovalRequest(
            transaction_id=transaction_id,
            agent_id=agent_id,
            amount=amount,
            merchant_id=merchant_id,
            confidence=confidence,
            required_approvers=approvers,
            expires_at=expires_at,
            quorum=quorum,
        )

        self._pending_approvals[transaction_id] = request
        return transaction_id

    async def approve(self, transaction_id: str, approver_id: str) -> bool:
        """
        Record an approval vote.

        Args:
            transaction_id: Transaction to approve
            approver_id: Approver identifier

        Returns:
            True if quorum reached, False otherwise

        Raises:
            ValueError: If request not found or expired
        """
        request = self._pending_approvals.get(transaction_id)
        if not request:
            raise ValueError(f"Approval request not found: {transaction_id}")

        if request.is_expired():
            raise ValueError(f"Approval request expired: {transaction_id}")

        if request.is_rejected():
            raise ValueError(f"Approval request already rejected: {transaction_id}")

        quorum_reached = request.add_approval(approver_id)

        # Clean up if quorum reached
        if quorum_reached:
            # Keep in dict for status queries, but mark as completed
            # Caller should check is_approved() before execution
            pass

        return quorum_reached

    async def reject(self, transaction_id: str, approver_id: str, reason: str) -> bool:
        """
        Record a rejection vote.

        Args:
            transaction_id: Transaction to reject
            approver_id: Approver identifier
            reason: Rejection reason

        Returns:
            True (rejection always succeeds)

        Raises:
            ValueError: If request not found
        """
        request = self._pending_approvals.get(transaction_id)
        if not request:
            raise ValueError(f"Approval request not found: {transaction_id}")

        request.add_rejection(approver_id, reason)
        return True

    async def check_quorum(self, transaction_id: str) -> bool:
        """
        Check if approval quorum has been reached.

        Args:
            transaction_id: Transaction to check

        Returns:
            True if quorum reached, False otherwise
        """
        request = self._pending_approvals.get(transaction_id)
        if not request:
            return False

        return request.is_approved()

    async def get_approval_status(self, transaction_id: str) -> dict[str, Any]:
        """
        Get current status of an approval request.

        Args:
            transaction_id: Transaction to check

        Returns:
            Status dict with:
                - status: "pending" | "approved" | "rejected" | "expired" | "not_found"
                - approvals: List of approver IDs who approved
                - rejections: Dict of approver ID -> (timestamp, reason)
                - quorum_reached: bool
                - created_at: timestamp
                - expires_at: timestamp
        """
        request = self._pending_approvals.get(transaction_id)
        if not request:
            return {"status": "not_found", "transaction_id": transaction_id}

        if request.is_expired():
            status = "expired"
        elif request.is_rejected():
            status = "rejected"
        elif request.is_approved():
            status = "approved"
        else:
            status = "pending"

        return {
            "status": status,
            "transaction_id": transaction_id,
            "agent_id": request.agent_id,
            "amount": str(request.amount),
            "merchant_id": request.merchant_id,
            "approvals": list(request.approvals.keys()),
            "rejections": {
                approver: {"timestamp": ts.isoformat(), "reason": reason}
                for approver, (ts, reason) in request.rejections.items()
            },
            "quorum": request.quorum,
            "quorum_reached": request.is_approved(),
            "required_approvers": request.required_approvers,
            "created_at": request.created_at.isoformat(),
            "expires_at": request.expires_at.isoformat(),
            "confidence_score": request.confidence.score,
            "confidence_level": request.confidence.level.value,
        }

    def cleanup_expired(self) -> int:
        """
        Remove expired approval requests from memory.

        Returns:
            Number of requests cleaned up
        """
        expired = [
            tx_id for tx_id, req in self._pending_approvals.items()
            if req.is_expired()
        ]
        for tx_id in expired:
            del self._pending_approvals[tx_id]
        return len(expired)
