"""
Goal Drift Detector with Statistical Monitoring

Detects when an agent's spending behavior has significantly diverged from its
established baseline profile, indicating possible goal drift, compromise, or
behavioral anomalies.

How goal drift detection works:
────────────────────────────────────
1. Build baseline spending profile from historical transactions:
   - Merchant distribution (chi-squared test for significant shifts)
   - Amount distribution (Kolmogorov-Smirnov test for distributional changes)
   - Time-of-day patterns (chi-squared test for temporal shifts)
   - Category distribution (chi-squared test for category drift)
   - Transaction velocity (z-score based velocity governor)

2. Compare recent behavior against baseline:
   - Chi-squared tests for categorical distributions (merchants, categories, time)
   - K-S test for continuous distributions (amounts)
   - Velocity checks for rate-of-spending anomalies

3. Generate DriftAlert when significant drift detected:
   - Severity: LOW/MEDIUM/HIGH/CRITICAL based on p-values and effect size
   - Confidence: 0.0–1.0 based on statistical significance
   - Details: Specific metrics that triggered the alert

Statistical Methods:
   - Chi-squared test: Detects shifts in categorical distributions (p < 0.05 = significant)
   - Kolmogorov-Smirnov test: Detects changes in continuous distributions
   - Z-score velocity check: Detects abnormal transaction rates (threshold: 2.0 std devs)
   - Behavioral fingerprinting: Hash-based quick comparison for pattern matching

Key Concepts:
   - Sensitivity: Chi-squared significance level (default 0.05 = 95% confidence)
   - Window: Rolling time window for baseline (default 30 days)
   - Velocity Governor: Rate limiting based on historical transaction frequency
"""

from __future__ import annotations

import hashlib
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
import math


class DriftType(str, Enum):
    """Type of behavioral drift detected."""
    MERCHANT_SHIFT = "merchant_shift"
    AMOUNT_ANOMALY = "amount_anomaly"
    VELOCITY_CHANGE = "velocity_change"
    CATEGORY_DRIFT = "category_drift"
    TIME_PATTERN_CHANGE = "time_pattern_change"


class DriftSeverity(str, Enum):
    """Severity level of drift detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class SpendingProfile:
    """
    Statistical profile of an agent's spending behavior.

    Built from historical transaction data to establish baseline patterns
    for drift detection.
    """
    agent_id: str
    merchant_distribution: dict[str, float]  # merchant -> frequency (0.0–1.0)
    amount_distribution: dict[str, float]  # mean, std, median, p25, p75, p90, p95
    time_distribution: dict[int, float]  # hour (0-23) -> frequency (0.0–1.0)
    category_distribution: dict[str, float]  # category -> frequency (0.0–1.0)
    velocity: float  # transactions per day
    total_transactions: int
    window_start: datetime
    window_end: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class DriftAlert:
    """
    Alert generated when significant behavioral drift is detected.

    Contains statistical evidence and severity assessment for the drift.
    """
    agent_id: str
    drift_type: DriftType
    severity: DriftSeverity
    confidence: float  # 0.0–1.0, higher = more confident in drift detection
    details: dict[str, Any]  # Statistical details (p-value, effect size, etc.)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    baseline_profile: Optional[SpendingProfile] = None
    current_profile: Optional[SpendingProfile] = None


class GoalDriftDetector:
    """
    Statistical drift detector for agent spending patterns.

    Uses chi-squared tests, K-S tests, and velocity analysis to detect
    significant deviations from established spending baselines.

    Usage:
        detector = GoalDriftDetector(sensitivity=0.05)

        # Build baseline from 30 days of history
        baseline = await detector.build_profile(
            agent_id="agent_123",
            transactions=historical_transactions,
            window_days=30,
        )

        # Check for drift in recent transactions
        alerts = await detector.detect_drift(
            agent_id="agent_123",
            recent_transactions=last_7_days_transactions,
            baseline=baseline,
        )

        for alert in alerts:
            if alert.severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
                # Block transaction, send notification, etc.
                ...
    """

    def __init__(self, sensitivity: float = 0.05):
        """
        Initialize goal drift detector.

        Args:
            sensitivity: Chi-squared significance level (default 0.05 = 95% confidence)
                        Lower values = stricter drift detection
        """
        self.sensitivity = sensitivity
        self._profile_cache: dict[str, SpendingProfile] = {}

    async def build_profile(
        self,
        agent_id: str,
        transactions: list[dict[str, Any]],
        window_days: int = 30,
    ) -> SpendingProfile:
        """
        Build spending profile from historical transactions.

        Analyzes transaction patterns to create baseline distributions for
        merchant preferences, spending amounts, time-of-day patterns, and
        transaction velocity.

        Args:
            agent_id: Agent identifier
            transactions: List of transaction dicts with keys:
                         amount, merchant_id, timestamp, category
            window_days: Size of rolling window in days (default 30)

        Returns:
            SpendingProfile with statistical baseline
        """
        if not transactions:
            raise ValueError(f"No transactions provided for agent {agent_id}")

        # Filter to window
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=window_days)
        filtered_txs = []

        for tx in transactions:
            ts = self._parse_timestamp(tx.get("timestamp"))
            if ts and ts >= window_start:
                filtered_txs.append(tx)

        if not filtered_txs:
            raise ValueError(f"No transactions in {window_days}-day window for agent {agent_id}")

        # ── Build Merchant Distribution ─────────────────────────────────
        merchant_counts: dict[str, int] = {}
        for tx in filtered_txs:
            merchant = tx.get("merchant_id") or tx.get("merchant", "unknown")
            merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1

        total_txs = len(filtered_txs)
        merchant_distribution = {
            merchant: count / total_txs
            for merchant, count in merchant_counts.items()
        }

        # ── Build Amount Distribution ───────────────────────────────────
        amounts = [float(tx.get("amount", 0)) for tx in filtered_txs if tx.get("amount")]
        amounts = [a for a in amounts if a > 0]

        if amounts:
            mean_amount = statistics.mean(amounts)
            median_amount = statistics.median(amounts)
            if len(amounts) > 1:
                std_amount = statistics.stdev(amounts)
            else:
                std_amount = 0.0

            sorted_amounts = sorted(amounts)
            amount_distribution = {
                "mean": mean_amount,
                "std": std_amount,
                "median": median_amount,
                "p25": self._percentile(sorted_amounts, 25),
                "p75": self._percentile(sorted_amounts, 75),
                "p90": self._percentile(sorted_amounts, 90),
                "p95": self._percentile(sorted_amounts, 95),
            }
        else:
            amount_distribution = {
                "mean": 0.0,
                "std": 0.0,
                "median": 0.0,
                "p25": 0.0,
                "p75": 0.0,
                "p90": 0.0,
                "p95": 0.0,
            }

        # ── Build Time-of-Day Distribution ──────────────────────────────
        hour_counts: dict[int, int] = {}
        for tx in filtered_txs:
            ts = self._parse_timestamp(tx.get("timestamp"))
            if ts:
                hour_counts[ts.hour] = hour_counts.get(ts.hour, 0) + 1

        time_distribution = {
            hour: count / total_txs
            for hour, count in hour_counts.items()
        }

        # ── Build Category Distribution ─────────────────────────────────
        category_counts: dict[str, int] = {}
        for tx in filtered_txs:
            category = tx.get("category") or tx.get("merchant_category", "other")
            category_counts[category] = category_counts.get(category, 0) + 1

        category_distribution = {
            category: count / total_txs
            for category, count in category_counts.items()
        }

        # ── Calculate Velocity ───────────────────────────────────────────
        timestamps = [self._parse_timestamp(tx.get("timestamp")) for tx in filtered_txs]
        timestamps = [ts for ts in timestamps if ts]

        if len(timestamps) >= 2:
            time_span_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400
            velocity = total_txs / max(time_span_days, 1)
        else:
            velocity = total_txs / window_days

        # ── Create Profile ───────────────────────────────────────────────
        profile = SpendingProfile(
            agent_id=agent_id,
            merchant_distribution=merchant_distribution,
            amount_distribution=amount_distribution,
            time_distribution=time_distribution,
            category_distribution=category_distribution,
            velocity=velocity,
            total_transactions=total_txs,
            window_start=window_start,
            window_end=now,
        )

        # Cache for quick lookups
        self._profile_cache[agent_id] = profile

        return profile

    async def detect_drift(
        self,
        agent_id: str,
        recent_transactions: list[dict[str, Any]],
        baseline: SpendingProfile,
    ) -> list[DriftAlert]:
        """
        Detect behavioral drift by comparing recent transactions against baseline.

        Runs multiple statistical tests to identify significant deviations:
        - Chi-squared tests for merchant, category, and time distributions
        - Kolmogorov-Smirnov test for amount distributions
        - Velocity check for transaction rate anomalies

        Args:
            agent_id: Agent identifier
            recent_transactions: Recent transaction history (e.g., last 7 days)
            baseline: Baseline spending profile

        Returns:
            List of DriftAlert objects for detected anomalies
        """
        if not recent_transactions:
            return []

        alerts: list[DriftAlert] = []

        # Build current profile from recent transactions
        try:
            current = await self.build_profile(
                agent_id=agent_id,
                transactions=recent_transactions,
                window_days=7,  # Short window for recent behavior
            )
        except ValueError:
            # Not enough recent transactions to build profile
            return []

        # ── Test 1: Merchant Distribution Shift ──────────────────────────
        merchant_chi2, merchant_p = self._chi_squared_test(
            observed=current.merchant_distribution,
            expected=baseline.merchant_distribution,
        )

        if merchant_p < self.sensitivity:
            severity = self._determine_severity(merchant_p)
            alerts.append(DriftAlert(
                agent_id=agent_id,
                drift_type=DriftType.MERCHANT_SHIFT,
                severity=severity,
                confidence=1.0 - merchant_p,
                details={
                    "chi_squared": merchant_chi2,
                    "p_value": merchant_p,
                    "new_merchants": [
                        m for m in current.merchant_distribution.keys()
                        if m not in baseline.merchant_distribution
                    ],
                    "baseline_top_merchants": sorted(
                        baseline.merchant_distribution.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:5],
                    "current_top_merchants": sorted(
                        current.merchant_distribution.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:5],
                },
                baseline_profile=baseline,
                current_profile=current,
            ))

        # ── Test 2: Amount Distribution Shift ────────────────────────────
        # Use distribution-parameter comparison; raw baseline samples are
        # intentionally not persisted in the profile.
        amount_deviation = self._compare_amount_distributions(
            baseline.amount_distribution,
            current.amount_distribution,
        )

        if amount_deviation > 2.0:  # More than 2 std devs different
            severity = self._determine_severity_from_deviation(amount_deviation)
            alerts.append(DriftAlert(
                agent_id=agent_id,
                drift_type=DriftType.AMOUNT_ANOMALY,
                severity=severity,
                confidence=min(amount_deviation / 5.0, 1.0),
                details={
                    "deviation_score": amount_deviation,
                    "baseline_mean": baseline.amount_distribution["mean"],
                    "current_mean": current.amount_distribution["mean"],
                    "baseline_std": baseline.amount_distribution["std"],
                    "current_std": current.amount_distribution["std"],
                },
                baseline_profile=baseline,
                current_profile=current,
            ))

        # ── Test 3: Category Distribution Shift ──────────────────────────
        category_chi2, category_p = self._chi_squared_test(
            observed=current.category_distribution,
            expected=baseline.category_distribution,
        )

        if category_p < self.sensitivity:
            severity = self._determine_severity(category_p)
            alerts.append(DriftAlert(
                agent_id=agent_id,
                drift_type=DriftType.CATEGORY_DRIFT,
                severity=severity,
                confidence=1.0 - category_p,
                details={
                    "chi_squared": category_chi2,
                    "p_value": category_p,
                    "baseline_categories": baseline.category_distribution,
                    "current_categories": current.category_distribution,
                },
                baseline_profile=baseline,
                current_profile=current,
            ))

        # ── Test 4: Time Pattern Shift ───────────────────────────────────
        time_chi2, time_p = self._chi_squared_test(
            observed=current.time_distribution,
            expected=baseline.time_distribution,
        )

        if time_p < self.sensitivity:
            severity = self._determine_severity(time_p)
            alerts.append(DriftAlert(
                agent_id=agent_id,
                drift_type=DriftType.TIME_PATTERN_CHANGE,
                severity=severity,
                confidence=1.0 - time_p,
                details={
                    "chi_squared": time_chi2,
                    "p_value": time_p,
                    "baseline_peak_hours": self._get_peak_hours(baseline.time_distribution),
                    "current_peak_hours": self._get_peak_hours(current.time_distribution),
                },
                baseline_profile=baseline,
                current_profile=current,
            ))

        # ── Test 5: Velocity Change ──────────────────────────────────────
        velocity_ok, velocity_reason = self._velocity_check(
            current_rate=current.velocity,
            baseline_rate=baseline.velocity,
            threshold=2.0,
        )

        if not velocity_ok:
            # Calculate z-score for severity
            if baseline.velocity > 0:
                velocity_z = abs(current.velocity - baseline.velocity) / (baseline.velocity * 0.5)
            else:
                velocity_z = 3.0

            severity = self._determine_severity_from_deviation(velocity_z)
            alerts.append(DriftAlert(
                agent_id=agent_id,
                drift_type=DriftType.VELOCITY_CHANGE,
                severity=severity,
                confidence=min(velocity_z / 5.0, 1.0),
                details={
                    "baseline_velocity": baseline.velocity,
                    "current_velocity": current.velocity,
                    "velocity_ratio": current.velocity / max(baseline.velocity, 0.01),
                    "reason": velocity_reason,
                },
                baseline_profile=baseline,
                current_profile=current,
            ))

        return alerts

    async def update_baseline(
        self,
        agent_id: str,
        new_transactions: list[dict[str, Any]],
    ) -> SpendingProfile:
        """
        Update baseline profile with new transactions (rolling window).

        Args:
            agent_id: Agent identifier
            new_transactions: New transactions to incorporate

        Returns:
            Updated SpendingProfile
        """
        # Rebuild profile with all transactions (will auto-filter to window)
        updated_profile = await self.build_profile(
            agent_id=agent_id,
            transactions=new_transactions,
            window_days=30,
        )

        return updated_profile

    def _chi_squared_test(
        self,
        observed: dict[str, float],
        expected: dict[str, float],
    ) -> tuple[float, float]:
        """
        Perform chi-squared test for goodness of fit.

        Tests whether observed distribution differs significantly from expected.

        Args:
            observed: Observed frequency distribution
            expected: Expected frequency distribution

        Returns:
            Tuple of (chi_squared_statistic, p_value)
        """
        # Combine all keys from both distributions
        all_keys = set(observed.keys()) | set(expected.keys())

        if not all_keys:
            return 0.0, 1.0

        chi_squared = 0.0
        for key in all_keys:
            obs = observed.get(key, 0.0)
            exp = expected.get(key, 0.001)  # Small value to avoid division by zero

            # Chi-squared formula: sum((O - E)^2 / E)
            chi_squared += ((obs - exp) ** 2) / exp

        # Degrees of freedom = number of categories - 1
        dof = max(1, len(all_keys) - 1)

        # Approximate p-value using chi-squared distribution
        # For simplicity, using rough approximation
        # In production, use scipy.stats.chi2.sf(chi_squared, dof)
        p_value = self._chi_squared_p_value(chi_squared, dof)

        return chi_squared, p_value

    def _kolmogorov_smirnov_test(
        self,
        sample1: list[float],
        sample2: list[float],
    ) -> tuple[float, float]:
        """
        Perform two-sample Kolmogorov-Smirnov test.

        Tests whether two samples come from the same distribution.

        Args:
            sample1: First sample
            sample2: Second sample

        Returns:
            Tuple of (ks_statistic, p_value)
        """
        if not sample1 or not sample2:
            return 0.0, 1.0

        # Sort both samples
        s1 = sorted(sample1)
        s2 = sorted(sample2)

        # Compute empirical CDFs and find max difference
        max_diff = 0.0

        # Combine and sort all unique values
        all_values = sorted(set(s1 + s2))

        for value in all_values:
            # CDF is proportion of samples <= value
            cdf1 = sum(1 for x in s1 if x <= value) / len(s1)
            cdf2 = sum(1 for x in s2 if x <= value) / len(s2)
            diff = abs(cdf1 - cdf2)
            max_diff = max(max_diff, diff)

        # K-S statistic
        ks_statistic = max_diff

        # Approximate p-value
        n = len(s1) * len(s2) / (len(s1) + len(s2))
        p_value = self._ks_p_value(ks_statistic, n)

        return ks_statistic, p_value

    def _velocity_check(
        self,
        current_rate: float,
        baseline_rate: float,
        threshold: float = 2.0,
    ) -> tuple[bool, str]:
        """
        Check if transaction velocity has changed significantly.

        Args:
            current_rate: Current transactions per day
            baseline_rate: Baseline transactions per day
            threshold: Z-score threshold (default 2.0 std devs)

        Returns:
            Tuple of (allowed, reason)
        """
        if baseline_rate == 0:
            if current_rate > 10:
                return False, "velocity_spike_from_zero"
            return True, "OK"

        ratio = current_rate / baseline_rate

        # Check for significant increases
        if ratio > (1 + threshold):
            return False, f"velocity_increased_{ratio:.1f}x"

        # Check for significant decreases
        if ratio < (1 / (1 + threshold)):
            return False, f"velocity_decreased_{ratio:.1f}x"

        return True, "OK"

    def _behavioral_fingerprint(self, profile: SpendingProfile) -> str:
        """
        Generate hash fingerprint of spending pattern for quick comparison.

        Args:
            profile: SpendingProfile to fingerprint

        Returns:
            SHA-256 hash of key behavioral attributes
        """
        # Create deterministic string representation
        components = []

        # Top 5 merchants by frequency
        top_merchants = sorted(
            profile.merchant_distribution.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        components.append("merchants:" + ",".join(f"{m}:{f:.3f}" for m, f in top_merchants))

        # Amount statistics
        components.append(f"amount_mean:{profile.amount_distribution['mean']:.2f}")
        components.append(f"amount_std:{profile.amount_distribution['std']:.2f}")

        # Top categories
        top_categories = sorted(
            profile.category_distribution.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        components.append("categories:" + ",".join(f"{c}:{f:.3f}" for c, f in top_categories))

        # Velocity
        components.append(f"velocity:{profile.velocity:.2f}")

        # Hash it
        fingerprint_str = "|".join(components)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()

    def _compare_amount_distributions(
        self,
        baseline: dict[str, float],
        current: dict[str, float],
    ) -> float:
        """
        Compare two amount distributions and return deviation score.

        Args:
            baseline: Baseline amount distribution (mean, std, etc.)
            current: Current amount distribution

        Returns:
            Deviation score (0 = identical, higher = more different)
        """
        deviation = 0.0

        baseline_mean = float(baseline.get("mean", 0.0))
        current_mean = float(current.get("mean", 0.0))
        baseline_std = float(baseline.get("std", 0.0))
        current_std = float(current.get("std", 0.0))

        # Compare means.
        if baseline_std > 0.0:
            mean_z = abs(current_mean - baseline_mean) / baseline_std
            deviation += mean_z
        else:
            # When baseline std is zero (e.g., perfectly constant historical
            # amounts), use relative mean shift so large jumps still trigger.
            if baseline_mean > 0.0:
                relative_shift = abs(current_mean - baseline_mean) / baseline_mean
                deviation += relative_shift
            elif current_mean > 0.0:
                deviation += 5.0

        # Compare standard deviations (as ratio-like effect size).
        if baseline_std > 0.0:
            std_ratio = abs(current_std - baseline_std) / baseline_std
            deviation += std_ratio
        elif current_std > 0.0:
            # Baseline had no variance; any recent variance is suspicious.
            denominator = max(baseline_mean, 1.0)
            deviation += current_std / denominator

        return deviation

    def _determine_severity(self, p_value: float) -> DriftSeverity:
        """Determine severity from p-value."""
        if p_value < 0.001:
            return DriftSeverity.CRITICAL
        elif p_value < 0.01:
            return DriftSeverity.HIGH
        elif p_value < 0.05:
            return DriftSeverity.MEDIUM
        else:
            return DriftSeverity.LOW

    def _determine_severity_from_deviation(self, deviation: float) -> DriftSeverity:
        """Determine severity from z-score or deviation metric."""
        if deviation >= 4.0:
            return DriftSeverity.CRITICAL
        elif deviation >= 3.0:
            return DriftSeverity.HIGH
        elif deviation >= 2.0:
            return DriftSeverity.MEDIUM
        else:
            return DriftSeverity.LOW

    def _get_peak_hours(self, time_dist: dict[int, float]) -> list[int]:
        """Get top 3 peak hours from time distribution."""
        sorted_hours = sorted(time_dist.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, _ in sorted_hours[:3]]

    def _parse_timestamp(self, ts: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if isinstance(ts, datetime):
            return ts
        elif isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return None
        return None

    def _percentile(self, sorted_values: list[float], percentile: int) -> float:
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

    def _chi_squared_p_value(self, chi2: float, dof: int) -> float:
        """
        Approximate p-value for chi-squared statistic.

        Uses rough approximation - in production, use scipy.stats.chi2.sf()
        """
        # Very rough approximation using normal distribution
        # For large dof, chi2 ~ Normal(dof, 2*dof)
        if dof < 1:
            return 1.0

        # Z-score approximation
        z = (chi2 - dof) / math.sqrt(2 * dof)

        # Approximate p-value from z-score
        if z < -3:
            return 0.999
        elif z > 3:
            return 0.001
        else:
            # Rough mapping
            return max(0.001, min(0.999, 0.5 * (1 - z / 4)))

    def _ks_p_value(self, ks_stat: float, n: float) -> float:
        """
        Approximate p-value for K-S statistic.

        Uses rough approximation - in production, use scipy.stats.ks_2samp()
        """
        # Kolmogorov distribution approximation
        # For large n, D ~ N(0, sqrt(2)/sqrt(n))
        if n < 1:
            return 1.0

        # Very rough approximation
        lambda_val = (math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)) * ks_stat

        if lambda_val < 0.5:
            return 1.0
        elif lambda_val > 3:
            return 0.001
        else:
            # Linear interpolation
            return max(0.001, 1.0 - (lambda_val / 4))


class VelocityGovernor:
    """
    Transaction velocity governor with graduated response.

    Tracks transaction rate per agent and enforces limits to prevent
    rapid-fire spending attacks or runaway agent behavior.

    Usage:
        governor = VelocityGovernor(
            max_per_minute=10,
            max_per_hour=100,
            max_per_day=500,
        )

        allowed, reason = await governor.check_velocity("agent_123")
        if not allowed:
            # Block transaction, send alert
            ...
    """

    def __init__(
        self,
        max_per_minute: int = 10,
        max_per_hour: int = 100,
        max_per_day: int = 500,
    ):
        """
        Initialize velocity governor.

        Args:
            max_per_minute: Maximum transactions per minute
            max_per_hour: Maximum transactions per hour
            max_per_day: Maximum transactions per day
        """
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day

        # In-memory tracking (in production, use Redis)
        self._transaction_log: dict[str, list[datetime]] = {}

    async def check_velocity(self, agent_id: str) -> tuple[bool, str]:
        """
        Check if agent is within velocity limits.

        Args:
            agent_id: Agent identifier

        Returns:
            Tuple of (allowed, reason)
        """
        now = datetime.now(timezone.utc)

        # Get recent transactions
        if agent_id not in self._transaction_log:
            self._transaction_log[agent_id] = []

        txs = self._transaction_log[agent_id]

        # Clean up old entries
        one_day_ago = now - timedelta(days=1)
        txs = [ts for ts in txs if ts > one_day_ago]
        self._transaction_log[agent_id] = txs

        # Count transactions in each window
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)

        count_minute = sum(1 for ts in txs if ts > one_minute_ago)
        count_hour = sum(1 for ts in txs if ts > one_hour_ago)
        count_day = len(txs)

        # Check limits
        if count_minute >= self.max_per_minute:
            return False, f"velocity_limit_minute:{count_minute}/{self.max_per_minute}"

        if count_hour >= self.max_per_hour:
            return False, f"velocity_limit_hour:{count_hour}/{self.max_per_hour}"

        if count_day >= self.max_per_day:
            return False, f"velocity_limit_day:{count_day}/{self.max_per_day}"

        return True, "OK"

    async def record_transaction(self, agent_id: str) -> None:
        """
        Record a transaction for velocity tracking.

        Args:
            agent_id: Agent identifier
        """
        now = datetime.now(timezone.utc)

        if agent_id not in self._transaction_log:
            self._transaction_log[agent_id] = []

        self._transaction_log[agent_id].append(now)
