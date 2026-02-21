"""Behavioral monitoring for detecting anomalous agent spending patterns.

Tracks spending patterns and detects deviations from established baselines.
"""

import asyncio
import math
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List


class AlertSeverity(str, Enum):
    """Severity levels for behavioral alerts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SensitivityLevel(str, Enum):
    """Sensitivity levels for anomaly detection."""

    RELAXED = "relaxed"  # 3.0 sigma threshold
    NORMAL = "normal"  # 2.5 sigma threshold
    STRICT = "strict"  # 2.0 sigma threshold
    PARANOID = "paranoid"  # 1.5 sigma threshold


@dataclass
class SpendingPattern:
    """Statistical profile of agent spending behavior."""

    total_transactions: int = 0
    total_amount: Decimal = Decimal("0")

    # Amount statistics
    mean_amount: Decimal = Decimal("0")
    std_dev_amount: Decimal = Decimal("0")
    min_amount: Decimal = Decimal("0")
    max_amount: Decimal = Decimal("0")

    # Time-based patterns (hour of day: 0-23)
    hourly_distribution: Dict[int, int] = field(default_factory=dict)

    # Merchant patterns
    merchant_frequencies: Dict[str, int] = field(default_factory=dict)

    # Token/chain patterns
    token_frequencies: Dict[str, int] = field(default_factory=dict)
    chain_frequencies: Dict[str, int] = field(default_factory=dict)

    # Recent transaction amounts (for running statistics)
    recent_amounts: List[Decimal] = field(default_factory=list)
    max_recent_history: int = 100  # Keep last 100 transactions

    last_updated: float = field(default_factory=time.time)


@dataclass
class BehavioralAlert:
    """Alert for detected behavioral anomaly."""

    agent_id: str
    severity: AlertSeverity
    anomaly_type: str
    description: str
    current_value: float | str
    expected_value: float | str
    deviation_score: float  # Number of standard deviations
    timestamp: float = field(default_factory=time.time)


@dataclass
class TransactionData:
    """Data for a transaction to monitor."""

    amount: Decimal
    merchant: str
    token: str
    chain: str
    timestamp: float = field(default_factory=time.time)


class BehavioralMonitor:
    """Monitor agent spending behavior and detect anomalies.

    Builds statistical profiles of normal behavior and alerts on deviations.

    Example:
        monitor = BehavioralMonitor(
            agent_id="agent-123",
            sensitivity=SensitivityLevel.NORMAL
        )

        # Record transactions
        await monitor.record_transaction(
            TransactionData(
                amount=Decimal("100.00"),
                merchant="Example Corp",
                token="USDC",
                chain="BASE"
            )
        )

        # Check for anomalies
        alerts = await monitor.check_transaction(
            TransactionData(
                amount=Decimal("10000.00"),  # Unusually large
                merchant="Example Corp",
                token="USDC",
                chain="BASE"
            )
        )

        if alerts:
            for alert in alerts:
                print(f"Alert: {alert.description}")
    """

    # Sigma thresholds by sensitivity level
    SIGMA_THRESHOLDS = {
        SensitivityLevel.RELAXED: 3.0,
        SensitivityLevel.NORMAL: 2.5,
        SensitivityLevel.STRICT: 2.0,
        SensitivityLevel.PARANOID: 1.5,
    }

    def __init__(
        self,
        agent_id: str,
        sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
        min_transactions_for_baseline: int = 10,
    ) -> None:
        """Initialize behavioral monitor for an agent.

        Args:
            agent_id: Unique identifier for the agent
            sensitivity: Sensitivity level for anomaly detection
            min_transactions_for_baseline: Minimum transactions before anomaly detection
        """
        self.agent_id = agent_id
        self.sensitivity = sensitivity
        self.min_transactions_for_baseline = min_transactions_for_baseline
        self.pattern = SpendingPattern()
        self._lock = asyncio.Lock()

    async def record_transaction(self, transaction: TransactionData) -> None:
        """Record a transaction and update behavioral profile.

        Args:
            transaction: Transaction data to record
        """
        async with self._lock:
            # Update transaction count and total
            self.pattern.total_transactions += 1
            self.pattern.total_amount += transaction.amount

            # Update recent amounts
            self.pattern.recent_amounts.append(transaction.amount)
            if len(self.pattern.recent_amounts) > self.pattern.max_recent_history:
                self.pattern.recent_amounts.pop(0)

            # Update amount statistics
            self._update_amount_statistics()

            # Update hourly distribution
            hour = int((transaction.timestamp % 86400) / 3600)  # Hour of day
            self.pattern.hourly_distribution[hour] = (
                self.pattern.hourly_distribution.get(hour, 0) + 1
            )

            # Update merchant frequencies
            self.pattern.merchant_frequencies[transaction.merchant] = (
                self.pattern.merchant_frequencies.get(transaction.merchant, 0) + 1
            )

            # Update token/chain frequencies
            self.pattern.token_frequencies[transaction.token] = (
                self.pattern.token_frequencies.get(transaction.token, 0) + 1
            )
            self.pattern.chain_frequencies[transaction.chain] = (
                self.pattern.chain_frequencies.get(transaction.chain, 0) + 1
            )

            self.pattern.last_updated = time.time()

    async def check_transaction(self, transaction: TransactionData) -> List[BehavioralAlert]:
        """Check a transaction for behavioral anomalies.

        Args:
            transaction: Transaction to check

        Returns:
            List of alerts if anomalies detected, empty list otherwise
        """
        async with self._lock:
            # Need minimum baseline before detecting anomalies
            if self.pattern.total_transactions < self.min_transactions_for_baseline:
                return []

            alerts: List[BehavioralAlert] = []
            sigma_threshold = self.SIGMA_THRESHOLDS[self.sensitivity]

            # Check amount anomaly
            if self.pattern.std_dev_amount > 0:
                amount_deviation = abs(
                    float(transaction.amount - self.pattern.mean_amount)
                ) / float(self.pattern.std_dev_amount)

                if amount_deviation > sigma_threshold:
                    severity = self._calculate_severity(amount_deviation, sigma_threshold)
                    alerts.append(
                        BehavioralAlert(
                            agent_id=self.agent_id,
                            severity=severity,
                            anomaly_type="amount_anomaly",
                            description=(
                                f"Transaction amount {transaction.amount} deviates significantly "
                                f"from typical amount {self.pattern.mean_amount}"
                            ),
                            current_value=float(transaction.amount),
                            expected_value=float(self.pattern.mean_amount),
                            deviation_score=amount_deviation,
                        )
                    )

            # Check time-of-day anomaly
            hour = int((transaction.timestamp % 86400) / 3600)
            typical_hourly_frequency = self.pattern.hourly_distribution.get(hour, 0)
            avg_hourly_frequency = self.pattern.total_transactions / 24

            if avg_hourly_frequency > 0:
                time_deviation = abs(typical_hourly_frequency - avg_hourly_frequency) / max(
                    avg_hourly_frequency, 1
                )

                # If this hour is significantly less active than average
                if (
                    typical_hourly_frequency < avg_hourly_frequency * 0.3
                    and time_deviation > 1.5
                ):
                    alerts.append(
                        BehavioralAlert(
                            agent_id=self.agent_id,
                            severity=AlertSeverity.LOW,
                            anomaly_type="time_anomaly",
                            description=(
                                f"Transaction at unusual time (hour {hour}). "
                                f"Typical frequency: {typical_hourly_frequency}, "
                                f"average: {avg_hourly_frequency:.1f}"
                            ),
                            current_value=hour,
                            expected_value=str(
                                sorted(
                                    self.pattern.hourly_distribution.items(),
                                    key=lambda x: x[1],
                                    reverse=True,
                                )[:3]
                            ),
                            deviation_score=time_deviation,
                        )
                    )

            # Check new merchant
            if transaction.merchant not in self.pattern.merchant_frequencies:
                # First time seeing this merchant
                if self.pattern.total_transactions > 50:  # Only alert after significant history
                    alerts.append(
                        BehavioralAlert(
                            agent_id=self.agent_id,
                            severity=AlertSeverity.MEDIUM,
                            anomaly_type="new_merchant",
                            description=f"First transaction with new merchant: {transaction.merchant}",
                            current_value=transaction.merchant,
                            expected_value=str(
                                sorted(
                                    self.pattern.merchant_frequencies.items(),
                                    key=lambda x: x[1],
                                    reverse=True,
                                )[:5]
                            ),
                            deviation_score=1.0,
                        )
                    )

            # Check new token/chain combination
            token_seen = transaction.token in self.pattern.token_frequencies
            chain_seen = transaction.chain in self.pattern.chain_frequencies

            if not token_seen or not chain_seen:
                if self.pattern.total_transactions > 20:
                    alerts.append(
                        BehavioralAlert(
                            agent_id=self.agent_id,
                            severity=AlertSeverity.MEDIUM,
                            anomaly_type="new_token_or_chain",
                            description=(
                                f"First transaction with {'token ' + transaction.token if not token_seen else ''}"
                                f"{' and ' if not token_seen and not chain_seen else ''}"
                                f"{'chain ' + transaction.chain if not chain_seen else ''}"
                            ),
                            current_value=f"{transaction.token}/{transaction.chain}",
                            expected_value=str(
                                list(self.pattern.token_frequencies.keys())[:5]
                            )
                            + " / "
                            + str(list(self.pattern.chain_frequencies.keys())[:5]),
                            deviation_score=1.0,
                        )
                    )

            return alerts

    def _update_amount_statistics(self) -> None:
        """Update running statistics for transaction amounts."""
        if not self.pattern.recent_amounts:
            return

        # Calculate mean
        total = sum(self.pattern.recent_amounts)
        count = len(self.pattern.recent_amounts)
        self.pattern.mean_amount = total / count

        # Calculate standard deviation
        if count > 1:
            variance = sum(
                (amount - self.pattern.mean_amount) ** 2
                for amount in self.pattern.recent_amounts
            ) / count
            self.pattern.std_dev_amount = Decimal(str(math.sqrt(float(variance))))
        else:
            self.pattern.std_dev_amount = Decimal("0")

        # Update min/max
        self.pattern.min_amount = min(self.pattern.recent_amounts)
        self.pattern.max_amount = max(self.pattern.recent_amounts)

    def _calculate_severity(self, deviation: float, threshold: float) -> AlertSeverity:
        """Calculate alert severity based on deviation.

        Args:
            deviation: Number of standard deviations
            threshold: Base threshold for this sensitivity level

        Returns:
            Alert severity
        """
        if deviation > threshold * 3:
            return AlertSeverity.CRITICAL
        elif deviation > threshold * 2:
            return AlertSeverity.HIGH
        elif deviation > threshold * 1.5:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    async def get_pattern(self) -> SpendingPattern:
        """Get current behavioral pattern.

        Returns:
            Current spending pattern
        """
        async with self._lock:
            return SpendingPattern(
                total_transactions=self.pattern.total_transactions,
                total_amount=self.pattern.total_amount,
                mean_amount=self.pattern.mean_amount,
                std_dev_amount=self.pattern.std_dev_amount,
                min_amount=self.pattern.min_amount,
                max_amount=self.pattern.max_amount,
                hourly_distribution=dict(self.pattern.hourly_distribution),
                merchant_frequencies=dict(self.pattern.merchant_frequencies),
                token_frequencies=dict(self.pattern.token_frequencies),
                chain_frequencies=dict(self.pattern.chain_frequencies),
                recent_amounts=list(self.pattern.recent_amounts),
                max_recent_history=self.pattern.max_recent_history,
                last_updated=self.pattern.last_updated,
            )

    async def reset(self) -> None:
        """Reset behavioral pattern to empty state."""
        async with self._lock:
            self.pattern = SpendingPattern()

    async def set_sensitivity(self, sensitivity: SensitivityLevel) -> None:
        """Update sensitivity level.

        Args:
            sensitivity: New sensitivity level
        """
        async with self._lock:
            self.sensitivity = sensitivity
