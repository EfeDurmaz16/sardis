"""Unit tests for goal drift detection."""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sardis_v2_core.goal_drift_detector import (
    GoalDriftDetector,
    DriftType,
    DriftSeverity,
    VelocityGovernor,
)


class TestGoalDriftDetector:
    """Test behavioral drift detection."""

    @pytest.mark.asyncio
    async def test_build_profile_from_transactions(self):
        """Test building spending profile from transaction history."""
        detector = GoalDriftDetector()

        now = datetime.now(timezone.utc)
        transactions = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=i),
                "category": "infrastructure",
            }
            for i in range(10)
        ]

        profile = await detector.build_profile(
            agent_id="agent-123",
            transactions=transactions,
            window_days=30,
        )

        assert profile.agent_id == "agent-123"
        assert "aws" in profile.merchant_distribution
        assert profile.total_transactions == 10
        assert profile.amount_distribution["mean"] == 100.0

    @pytest.mark.asyncio
    async def test_merchant_shift_detection(self):
        """Test detecting shift in merchant preferences."""
        detector = GoalDriftDetector(sensitivity=0.05)

        now = datetime.now(timezone.utc)

        # Baseline: all AWS transactions
        baseline_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=30 - i),
                "category": "infrastructure",
            }
            for i in range(20)
        ]

        baseline = await detector.build_profile("agent-123", baseline_txs, window_days=30)

        # Recent: all new merchant
        recent_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "unknown_merchant",
                "timestamp": now - timedelta(days=i),
                "category": "infrastructure",
            }
            for i in range(10)
        ]

        alerts = await detector.detect_drift(
            agent_id="agent-123",
            recent_transactions=recent_txs,
            baseline=baseline,
        )

        # Should detect merchant shift
        merchant_alerts = [a for a in alerts if a.drift_type == DriftType.MERCHANT_SHIFT]
        assert len(merchant_alerts) > 0
        assert merchant_alerts[0].severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]

    @pytest.mark.asyncio
    async def test_amount_anomaly_detection(self):
        """Test detecting abnormal transaction amounts."""
        detector = GoalDriftDetector(sensitivity=0.05)

        now = datetime.now(timezone.utc)

        # Baseline: consistent $50 transactions
        baseline_txs = [
            {
                "amount": Decimal("50"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=30 - i),
                "category": "infrastructure",
            }
            for i in range(30)
        ]

        baseline = await detector.build_profile("agent-123", baseline_txs, window_days=30)

        # Recent: much larger amounts
        recent_txs = [
            {
                "amount": Decimal("1000"),  # 20x larger
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=i),
                "category": "infrastructure",
            }
            for i in range(10)
        ]

        alerts = await detector.detect_drift(
            agent_id="agent-123",
            recent_transactions=recent_txs,
            baseline=baseline,
        )

        # Should detect amount anomaly
        amount_alerts = [a for a in alerts if a.drift_type == DriftType.AMOUNT_ANOMALY]
        assert len(amount_alerts) > 0

    @pytest.mark.asyncio
    async def test_velocity_change_detection(self):
        """Test detecting changes in transaction velocity."""
        detector = GoalDriftDetector(sensitivity=0.05)

        now = datetime.now(timezone.utc)

        # Baseline: 1 transaction per day
        baseline_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=30 - i),
                "category": "infrastructure",
            }
            for i in range(30)
        ]

        baseline = await detector.build_profile("agent-123", baseline_txs, window_days=30)

        # Recent: 10 transactions per day (10x spike)
        recent_txs = []
        for day in range(7):
            for hour in range(10):
                recent_txs.append({
                    "amount": Decimal("100"),
                    "merchant_id": "aws",
                    "timestamp": now - timedelta(days=day, hours=hour),
                    "category": "infrastructure",
                })

        alerts = await detector.detect_drift(
            agent_id="agent-123",
            recent_transactions=recent_txs,
            baseline=baseline,
        )

        # Should detect velocity change
        velocity_alerts = [a for a in alerts if a.drift_type == DriftType.VELOCITY_CHANGE]
        assert len(velocity_alerts) > 0

    @pytest.mark.asyncio
    async def test_category_drift_detection(self):
        """Test detecting changes in spending categories."""
        detector = GoalDriftDetector(sensitivity=0.05)

        now = datetime.now(timezone.utc)

        # Baseline: all infrastructure
        baseline_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=30 - i),
                "category": "infrastructure",
            }
            for i in range(20)
        ]

        baseline = await detector.build_profile("agent-123", baseline_txs, window_days=30)

        # Recent: all marketing
        recent_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "google_ads",
                "timestamp": now - timedelta(days=i),
                "category": "marketing",
            }
            for i in range(10)
        ]

        alerts = await detector.detect_drift(
            agent_id="agent-123",
            recent_transactions=recent_txs,
            baseline=baseline,
        )

        # Should detect category drift
        category_alerts = [a for a in alerts if a.drift_type == DriftType.CATEGORY_DRIFT]
        assert len(category_alerts) > 0

    @pytest.mark.asyncio
    async def test_time_pattern_change_detection(self):
        """Test detecting changes in time-of-day patterns."""
        detector = GoalDriftDetector(sensitivity=0.05)

        now = datetime.now(timezone.utc)

        # Baseline: all during business hours (9-17)
        baseline_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": (now - timedelta(days=30 - i)).replace(hour=10),
                "category": "infrastructure",
            }
            for i in range(20)
        ]

        baseline = await detector.build_profile("agent-123", baseline_txs, window_days=30)

        # Recent: all at night (2-4 AM)
        recent_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": (now - timedelta(days=i)).replace(hour=3),
                "category": "infrastructure",
            }
            for i in range(10)
        ]

        alerts = await detector.detect_drift(
            agent_id="agent-123",
            recent_transactions=recent_txs,
            baseline=baseline,
        )

        # Should detect time pattern change
        time_alerts = [a for a in alerts if a.drift_type == DriftType.TIME_PATTERN_CHANGE]
        assert len(time_alerts) > 0

    @pytest.mark.asyncio
    async def test_no_drift_on_normal_behavior(self):
        """Test no alerts for consistent behavior."""
        detector = GoalDriftDetector(sensitivity=0.05)

        now = datetime.now(timezone.utc)

        # Baseline transactions
        baseline_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=30 - i),
                "category": "infrastructure",
            }
            for i in range(30)
        ]

        baseline = await detector.build_profile("agent-123", baseline_txs, window_days=30)

        # Recent: same pattern
        recent_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=i),
                "category": "infrastructure",
            }
            for i in range(7)
        ]

        alerts = await detector.detect_drift(
            agent_id="agent-123",
            recent_transactions=recent_txs,
            baseline=baseline,
        )

        # Should have minimal or no alerts for normal behavior
        # (Some statistical tests might still trigger at low p-values)
        assert len(alerts) <= 1

    @pytest.mark.asyncio
    async def test_update_baseline(self):
        """Test updating baseline profile with new transactions."""
        detector = GoalDriftDetector()

        now = datetime.now(timezone.utc)

        initial_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=40 - i),
                "category": "infrastructure",
            }
            for i in range(20)
        ]

        new_txs = initial_txs + [
            {
                "amount": Decimal("150"),
                "merchant_id": "gcp",
                "timestamp": now - timedelta(days=i),
                "category": "infrastructure",
            }
            for i in range(10)
        ]

        updated_profile = await detector.update_baseline(
            agent_id="agent-123",
            new_transactions=new_txs,
        )

        # Should include both AWS and GCP
        assert "aws" in updated_profile.merchant_distribution
        assert "gcp" in updated_profile.merchant_distribution

    @pytest.mark.asyncio
    async def test_empty_recent_transactions(self):
        """Test drift detection with no recent transactions."""
        detector = GoalDriftDetector()

        now = datetime.now(timezone.utc)

        baseline_txs = [
            {
                "amount": Decimal("100"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=30 - i),
                "category": "infrastructure",
            }
            for i in range(20)
        ]

        baseline = await detector.build_profile("agent-123", baseline_txs, window_days=30)

        alerts = await detector.detect_drift(
            agent_id="agent-123",
            recent_transactions=[],
            baseline=baseline,
        )

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_severity_levels(self):
        """Test different severity levels based on drift magnitude."""
        detector = GoalDriftDetector(sensitivity=0.05)

        now = datetime.now(timezone.utc)

        baseline_txs = [
            {
                "amount": Decimal("50"),
                "merchant_id": "aws",
                "timestamp": now - timedelta(days=30 - i),
                "category": "infrastructure",
            }
            for i in range(30)
        ]

        baseline = await detector.build_profile("agent-123", baseline_txs, window_days=30)

        # Extreme drift: completely different merchant
        extreme_txs = [
            {
                "amount": Decimal("50"),
                "merchant_id": "totally_new_merchant",
                "timestamp": now - timedelta(days=i),
                "category": "unknown",
            }
            for i in range(15)
        ]

        alerts = await detector.detect_drift(
            agent_id="agent-123",
            recent_transactions=extreme_txs,
            baseline=baseline,
        )

        # Should have high or critical severity alerts
        high_severity = [a for a in alerts if a.severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]]
        assert len(high_severity) > 0


class TestVelocityGovernor:
    """Test transaction velocity limiting."""

    @pytest.mark.asyncio
    async def test_velocity_check_within_limits(self):
        """Test velocity check passes when within limits."""
        governor = VelocityGovernor(
            max_per_minute=10,
            max_per_hour=100,
            max_per_day=500,
        )

        # Record a few transactions
        for _ in range(3):
            await governor.record_transaction("agent-123")

        # Should pass
        allowed, reason = await governor.check_velocity("agent-123")
        assert allowed is True
        assert reason == "OK"

    @pytest.mark.asyncio
    async def test_velocity_limit_per_minute(self):
        """Test velocity limit per minute."""
        governor = VelocityGovernor(max_per_minute=5)

        # Record 5 transactions
        for _ in range(5):
            await governor.record_transaction("agent-123")

        # 6th should fail
        allowed, reason = await governor.check_velocity("agent-123")
        assert allowed is False
        assert "velocity_limit_minute" in reason

    @pytest.mark.asyncio
    async def test_velocity_limit_per_hour(self):
        """Test velocity limit per hour."""
        governor = VelocityGovernor(
            max_per_minute=100,  # High minute limit
            max_per_hour=10,
        )

        # Record 10 transactions
        for _ in range(10):
            await governor.record_transaction("agent-123")

        # 11th should fail hour limit
        allowed, reason = await governor.check_velocity("agent-123")
        assert allowed is False
        assert "velocity_limit_hour" in reason

    @pytest.mark.asyncio
    async def test_velocity_limit_per_day(self):
        """Test velocity limit per day."""
        governor = VelocityGovernor(
            max_per_minute=1000,
            max_per_hour=1000,
            max_per_day=20,
        )

        # Record 20 transactions
        for _ in range(20):
            await governor.record_transaction("agent-123")

        # 21st should fail day limit
        allowed, reason = await governor.check_velocity("agent-123")
        assert allowed is False
        assert "velocity_limit_day" in reason

    @pytest.mark.asyncio
    async def test_velocity_governor_independent_agents(self):
        """Test different agents have independent velocity limits."""
        governor = VelocityGovernor(max_per_minute=2)

        # Agent 1 uses up limit
        await governor.record_transaction("agent-1")
        await governor.record_transaction("agent-1")

        # Agent 1 should be at limit
        allowed, _ = await governor.check_velocity("agent-1")
        assert allowed is False

        # Agent 2 should still have capacity
        allowed, reason = await governor.check_velocity("agent-2")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_velocity_new_agent(self):
        """Test velocity check for agent with no history."""
        governor = VelocityGovernor()

        allowed, reason = await governor.check_velocity("new-agent")
        assert allowed is True
        assert reason == "OK"
