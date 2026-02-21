"""
Anomaly Detection for Sardis Spending Analytics

Statistical anomaly detection for transaction patterns without ML dependencies.
Uses z-score and percentile-based methods to identify unusual spending behavior.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from decimal import Decimal
import statistics

logger = logging.getLogger(__name__)


@dataclass
class BaselineStats:
    """Statistical baseline for normal spending patterns."""
    agent_id: str
    mean_amount: float
    median_amount: float
    std_dev: float
    percentile_75: float
    percentile_90: float
    percentile_95: float
    transaction_count: int
    total_volume: float
    avg_daily_transactions: float
    common_merchants: Dict[str, int]  # merchant -> transaction count
    last_updated: datetime


@dataclass
class AnomalyResult:
    """Result of anomaly detection analysis."""
    is_anomaly: bool
    confidence: float  # 0.0 to 1.0
    reason: str
    baseline_stats: Optional[BaselineStats] = None
    z_score: Optional[float] = None
    percentile: Optional[float] = None
    merchant_flags: List[str] = None

    def __post_init__(self):
        if self.merchant_flags is None:
            self.merchant_flags = []


class AnomalyDetector:
    """
    Statistical anomaly detector for spending patterns.

    Detects anomalies using:
    - Z-score analysis (transactions > 3 std devs from mean)
    - Percentile thresholds (transactions in top 5%)
    - Frequency analysis (unusual merchant patterns)
    - Velocity checks (rapid successive transactions)
    """

    # Thresholds
    Z_SCORE_THRESHOLD = 3.0  # Standard deviations
    HIGH_PERCENTILE_THRESHOLD = 95  # Top 5% of transactions
    MIN_TRANSACTIONS_FOR_BASELINE = 10  # Minimum history needed

    def __init__(self):
        """Initialize the anomaly detector."""
        self._baselines: Dict[str, BaselineStats] = {}

    def detect_spending_anomaly(
        self,
        agent_id: str,
        amount: float,
        merchant: str,
        transaction_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AnomalyResult:
        """
        Detect if a transaction is anomalous based on agent's spending patterns.

        Args:
            agent_id: Agent identifier
            amount: Transaction amount in USD
            merchant: Merchant name
            transaction_history: Recent transactions for the agent
                Each dict should have: amount, merchant, timestamp

        Returns:
            AnomalyResult with detection results
        """
        # If no history, we can't detect anomalies
        if not transaction_history or len(transaction_history) < self.MIN_TRANSACTIONS_FOR_BASELINE:
            return AnomalyResult(
                is_anomaly=False,
                confidence=0.0,
                reason="Insufficient transaction history for baseline",
            )

        # Calculate or get baseline stats
        baseline = self.get_agent_baseline(agent_id, transaction_history)

        # Run multiple detection methods
        z_score = self._calculate_z_score(amount, baseline)
        percentile = self._calculate_percentile(amount, transaction_history)
        merchant_flags = self._check_merchant_anomalies(merchant, baseline, transaction_history)

        # Determine if anomalous based on multiple signals
        is_anomaly = False
        reasons = []
        confidence = 0.0

        # Z-score check
        if abs(z_score) > self.Z_SCORE_THRESHOLD:
            is_anomaly = True
            reasons.append(f"Amount is {abs(z_score):.1f} standard deviations from mean")
            confidence = max(confidence, min(abs(z_score) / 5.0, 1.0))

        # Percentile check
        if percentile >= self.HIGH_PERCENTILE_THRESHOLD:
            is_anomaly = True
            reasons.append(f"Amount in top {100 - percentile:.1f}% of transactions")
            confidence = max(confidence, (percentile - 90) / 10.0)

        # Merchant checks
        if merchant_flags:
            is_anomaly = True
            reasons.extend(merchant_flags)
            confidence = max(confidence, 0.6)

        # First transaction with this merchant
        if merchant.lower() not in [m.lower() for m in baseline.common_merchants.keys()]:
            # Not necessarily anomalous, but worth noting
            if amount > baseline.percentile_90:
                reasons.append(f"First transaction with {merchant} is unusually large")
                confidence = max(confidence, 0.5)

        reason = "; ".join(reasons) if reasons else "Transaction within normal parameters"

        return AnomalyResult(
            is_anomaly=is_anomaly,
            confidence=round(confidence, 2),
            reason=reason,
            baseline_stats=baseline,
            z_score=round(z_score, 2),
            percentile=round(percentile, 1),
            merchant_flags=merchant_flags,
        )

    def get_agent_baseline(
        self,
        agent_id: str,
        transaction_history: List[Dict[str, Any]],
    ) -> BaselineStats:
        """
        Calculate baseline spending statistics for an agent.

        Args:
            agent_id: Agent identifier
            transaction_history: List of transaction dicts with amount, merchant, timestamp

        Returns:
            BaselineStats with statistical measures
        """
        # Check cache first
        if agent_id in self._baselines:
            baseline = self._baselines[agent_id]
            # Refresh if older than 1 hour
            if datetime.now(timezone.utc) - baseline.last_updated < timedelta(hours=1):
                return baseline

        # Extract amounts
        amounts = [float(tx.get("amount", 0)) for tx in transaction_history]
        amounts = [a for a in amounts if a > 0]  # Filter out invalid amounts

        if not amounts:
            raise ValueError(f"No valid transaction amounts found for agent {agent_id}")

        # Calculate statistics
        mean_amount = statistics.mean(amounts)
        median_amount = statistics.median(amounts)

        # Standard deviation (handle single value case)
        if len(amounts) > 1:
            std_dev = statistics.stdev(amounts)
        else:
            std_dev = 0.0

        # Percentiles
        sorted_amounts = sorted(amounts)
        percentile_75 = self._percentile(sorted_amounts, 75)
        percentile_90 = self._percentile(sorted_amounts, 90)
        percentile_95 = self._percentile(sorted_amounts, 95)

        # Merchant frequency
        merchant_counts: Dict[str, int] = {}
        for tx in transaction_history:
            merchant = tx.get("merchant", "unknown")
            merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1

        # Calculate daily transaction rate
        timestamps = [tx.get("timestamp") for tx in transaction_history if tx.get("timestamp")]
        if timestamps:
            # Convert to datetime if needed
            parsed_timestamps = []
            for ts in timestamps:
                if isinstance(ts, datetime):
                    parsed_timestamps.append(ts)
                elif isinstance(ts, str):
                    try:
                        parsed_timestamps.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
                    except:
                        continue

            if len(parsed_timestamps) >= 2:
                time_span = (max(parsed_timestamps) - min(parsed_timestamps)).total_seconds() / 86400
                avg_daily_transactions = len(transaction_history) / max(time_span, 1)
            else:
                avg_daily_transactions = len(transaction_history)
        else:
            avg_daily_transactions = len(transaction_history)

        baseline = BaselineStats(
            agent_id=agent_id,
            mean_amount=round(mean_amount, 2),
            median_amount=round(median_amount, 2),
            std_dev=round(std_dev, 2),
            percentile_75=round(percentile_75, 2),
            percentile_90=round(percentile_90, 2),
            percentile_95=round(percentile_95, 2),
            transaction_count=len(transaction_history),
            total_volume=round(sum(amounts), 2),
            avg_daily_transactions=round(avg_daily_transactions, 2),
            common_merchants=merchant_counts,
            last_updated=datetime.now(timezone.utc),
        )

        # Cache the baseline
        self._baselines[agent_id] = baseline

        return baseline

    def _calculate_z_score(self, amount: float, baseline: BaselineStats) -> float:
        """Calculate z-score for the transaction amount."""
        if baseline.std_dev == 0:
            return 0.0
        return (amount - baseline.mean_amount) / baseline.std_dev

    def _calculate_percentile(
        self,
        amount: float,
        transaction_history: List[Dict[str, Any]],
    ) -> float:
        """Calculate what percentile this amount falls into."""
        amounts = sorted([float(tx.get("amount", 0)) for tx in transaction_history if tx.get("amount", 0) > 0])

        if not amounts:
            return 50.0

        # Count how many transactions are below this amount
        below_count = sum(1 for a in amounts if a <= amount)
        percentile = (below_count / len(amounts)) * 100

        return percentile

    def _check_merchant_anomalies(
        self,
        merchant: str,
        baseline: BaselineStats,
        transaction_history: List[Dict[str, Any]],
    ) -> List[str]:
        """Check for merchant-related anomalies."""
        flags = []

        # Check if merchant is completely new
        merchant_lower = merchant.lower()
        baseline_merchants_lower = {m.lower(): count for m, count in baseline.common_merchants.items()}

        if merchant_lower not in baseline_merchants_lower:
            # New merchant - check if there's a pattern of one-off merchants
            merchant_counts = list(baseline.common_merchants.values())
            one_off_count = sum(1 for count in merchant_counts if count == 1)

            # If most merchants are one-offs, this might be normal
            if baseline.transaction_count > 20 and one_off_count / baseline.transaction_count < 0.3:
                flags.append(f"New merchant: {merchant}")

        # Check for rapid repeat transactions to same merchant
        recent_merchant_txs = [
            tx for tx in transaction_history[-10:]  # Last 10 transactions
            if tx.get("merchant", "").lower() == merchant_lower
        ]

        if len(recent_merchant_txs) >= 3:
            flags.append(f"Multiple recent transactions to {merchant}")

        return flags

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]
        if f < 0:
            return sorted_values[0]

        d0 = sorted_values[f] * (c - k)
        d1 = sorted_values[c] * (k - f)

        return d0 + d1

    def clear_baseline_cache(self, agent_id: Optional[str] = None) -> None:
        """
        Clear cached baseline statistics.

        Args:
            agent_id: If provided, clear only this agent's baseline.
                     If None, clear all baselines.
        """
        if agent_id:
            self._baselines.pop(agent_id, None)
        else:
            self._baselines.clear()
