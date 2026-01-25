"""
Comprehensive tests for sardis_compliance.risk_scoring module.

Tests cover:
- Risk category and level enums
- RiskFactor calculations
- RiskAssessment creation and aggregation
- RiskConfig configuration
- TransactionVelocityMonitor
- Multi-factor risk scoring
- Geographic risk assessment
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch
import threading

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_compliance.risk_scoring import (
    RiskCategory,
    RiskLevel,
    RiskAction,
    RiskFactor,
    RiskAssessment,
    RiskConfig,
    TransactionVelocityMonitor,
)


class TestRiskCategory:
    """Tests for RiskCategory enum."""

    def test_category_values(self):
        """Should have correct category values."""
        assert RiskCategory.TRANSACTION.value == "transaction"
        assert RiskCategory.COUNTERPARTY.value == "counterparty"
        assert RiskCategory.GEOGRAPHIC.value == "geographic"
        assert RiskCategory.BEHAVIORAL.value == "behavioral"
        assert RiskCategory.REGULATORY.value == "regulatory"
        assert RiskCategory.SANCTIONS.value == "sanctions"
        assert RiskCategory.PEP.value == "pep"


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_level_values(self):
        """Should have correct level values."""
        assert RiskLevel.MINIMAL.value == "minimal"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestRiskAction:
    """Tests for RiskAction enum."""

    def test_action_values(self):
        """Should have correct action values."""
        assert RiskAction.APPROVE.value == "approve"
        assert RiskAction.REVIEW.value == "review"
        assert RiskAction.ENHANCED_DUE_DILIGENCE.value == "edd"
        assert RiskAction.BLOCK.value == "block"
        assert RiskAction.ESCALATE.value == "escalate"


class TestRiskFactor:
    """Tests for RiskFactor class."""

    def test_create_risk_factor(self):
        """Should create risk factor."""
        factor = RiskFactor(
            category=RiskCategory.TRANSACTION,
            name="high_value_transaction",
            score=75.0,
            weight=1.2,
            description="Transaction exceeds normal limits",
        )

        assert factor.category == RiskCategory.TRANSACTION
        assert factor.name == "high_value_transaction"
        assert factor.score == 75.0
        assert factor.weight == 1.2

    def test_weighted_score(self):
        """Should calculate weighted score correctly."""
        factor = RiskFactor(
            category=RiskCategory.SANCTIONS,
            name="partial_match",
            score=50.0,
            weight=2.0,
        )

        assert factor.weighted_score == 100.0  # 50 * 2.0, capped at 100

    def test_weighted_score_capped_at_100(self):
        """Should cap weighted score at 100."""
        factor = RiskFactor(
            category=RiskCategory.SANCTIONS,
            name="exact_match",
            score=80.0,
            weight=2.0,
        )

        # 80 * 2.0 = 160, but should be capped at 100
        assert factor.weighted_score == 100.0

    def test_default_weight(self):
        """Should have default weight of 1.0."""
        factor = RiskFactor(
            category=RiskCategory.BEHAVIORAL,
            name="unusual_pattern",
            score=30.0,
        )

        assert factor.weight == 1.0
        assert factor.weighted_score == 30.0


class TestRiskAssessment:
    """Tests for RiskAssessment class."""

    def test_create_assessment(self):
        """Should create risk assessment."""
        factors = [
            RiskFactor(RiskCategory.TRANSACTION, "high_amount", 40.0),
            RiskFactor(RiskCategory.GEOGRAPHIC, "high_risk_country", 60.0),
        ]

        assessment = RiskAssessment(
            subject_id="user_123",
            overall_score=50.0,
            risk_level=RiskLevel.MEDIUM,
            recommended_action=RiskAction.REVIEW,
            factors=factors,
        )

        assert assessment.subject_id == "user_123"
        assert assessment.overall_score == 50.0
        assert assessment.risk_level == RiskLevel.MEDIUM
        assert len(assessment.factors) == 2

    def test_by_category(self):
        """Should group factors by category."""
        factors = [
            RiskFactor(RiskCategory.TRANSACTION, "f1", 30.0),
            RiskFactor(RiskCategory.TRANSACTION, "f2", 40.0),
            RiskFactor(RiskCategory.GEOGRAPHIC, "f3", 50.0),
        ]

        assessment = RiskAssessment(
            subject_id="s1",
            overall_score=40.0,
            risk_level=RiskLevel.LOW,
            recommended_action=RiskAction.APPROVE,
            factors=factors,
        )

        by_cat = assessment.by_category
        assert len(by_cat[RiskCategory.TRANSACTION]) == 2
        assert len(by_cat[RiskCategory.GEOGRAPHIC]) == 1

    def test_highest_risk_factors(self):
        """Should return top 5 highest risk factors."""
        factors = [
            RiskFactor(RiskCategory.TRANSACTION, "f1", 30.0),
            RiskFactor(RiskCategory.GEOGRAPHIC, "f2", 80.0),
            RiskFactor(RiskCategory.SANCTIONS, "f3", 90.0, weight=2.0),
            RiskFactor(RiskCategory.BEHAVIORAL, "f4", 20.0),
            RiskFactor(RiskCategory.PEP, "f5", 70.0),
            RiskFactor(RiskCategory.COUNTERPARTY, "f6", 50.0),
        ]

        assessment = RiskAssessment(
            subject_id="s1",
            overall_score=60.0,
            risk_level=RiskLevel.MEDIUM,
            recommended_action=RiskAction.REVIEW,
            factors=factors,
        )

        highest = assessment.highest_risk_factors

        assert len(highest) == 5
        # First should be highest weighted score
        assert highest[0].name == "f3"  # 90 * 2.0 = 100 (capped)

    def test_to_dict(self):
        """Should convert to dictionary."""
        assessment = RiskAssessment(
            subject_id="s1",
            overall_score=45.0,
            risk_level=RiskLevel.LOW,
            recommended_action=RiskAction.APPROVE,
            factors=[
                RiskFactor(RiskCategory.TRANSACTION, "factor1", 45.0)
            ],
        )

        result = assessment.to_dict()

        assert result["subject_id"] == "s1"
        assert result["overall_score"] == 45.0
        assert result["risk_level"] == "low"
        assert result["recommended_action"] == "approve"
        assert len(result["factors"]) == 1
        assert "assessed_at" in result


class TestRiskConfig:
    """Tests for RiskConfig class."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = RiskConfig()

        assert config.high_value_threshold == Decimal("10000")
        assert config.velocity_window_hours == 24
        assert len(config.high_risk_countries) > 0

    def test_category_weights(self):
        """Should have category weights."""
        config = RiskConfig()

        assert config.category_weights[RiskCategory.SANCTIONS] == 2.0  # Highest
        assert config.category_weights[RiskCategory.PEP] == 1.5
        assert config.category_weights[RiskCategory.TRANSACTION] == 1.0

    def test_level_thresholds(self):
        """Should have level thresholds."""
        config = RiskConfig()

        assert config.level_thresholds[RiskLevel.MINIMAL] == 20
        assert config.level_thresholds[RiskLevel.LOW] == 40
        assert config.level_thresholds[RiskLevel.MEDIUM] == 60
        assert config.level_thresholds[RiskLevel.HIGH] == 80
        assert config.level_thresholds[RiskLevel.CRITICAL] == 100

    def test_action_thresholds(self):
        """Should have action thresholds."""
        config = RiskConfig()

        assert config.action_thresholds[RiskAction.APPROVE] == 30
        assert config.action_thresholds[RiskAction.BLOCK] == 85

    def test_high_risk_countries(self):
        """Should contain known high-risk countries."""
        config = RiskConfig()

        high_risk = config.high_risk_countries
        assert "KP" in high_risk  # North Korea
        assert "IR" in high_risk  # Iran
        assert "SY" in high_risk  # Syria

    def test_medium_risk_countries(self):
        """Should contain medium-risk countries."""
        config = RiskConfig()

        medium_risk = config.medium_risk_countries
        assert len(medium_risk) > 0


class TestTransactionVelocityMonitor:
    """Tests for TransactionVelocityMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create velocity monitor."""
        config = RiskConfig(
            velocity_window_hours=24,
            max_transactions_per_window=10,
            max_amount_per_window=Decimal("5000"),
        )
        return TransactionVelocityMonitor(config)

    def test_record_transaction(self, monitor):
        """Should record transactions."""
        monitor.record_transaction(
            subject_id="user_123",
            amount=Decimal("100"),
        )

        # Verify transaction was recorded
        assert "user_123" in monitor._transactions
        assert len(monitor._transactions["user_123"]) == 1

    def test_multiple_transactions(self, monitor):
        """Should track multiple transactions."""
        for i in range(5):
            monitor.record_transaction(
                subject_id="user_456",
                amount=Decimal("50"),
            )

        assert len(monitor._transactions["user_456"]) == 5

    def test_cleanup_old_transactions(self, monitor):
        """Should cleanup transactions outside window."""
        # Record old transaction
        old_time = datetime.now(timezone.utc) - timedelta(hours=50)
        monitor._transactions["user_789"] = [
            (old_time, Decimal("100"))
        ]

        # Record new transaction (triggers cleanup)
        monitor.record_transaction(
            subject_id="user_789",
            amount=Decimal("50"),
        )

        # Old transaction should be cleaned up
        transactions = monitor._transactions["user_789"]
        for ts, _ in transactions:
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            assert age_hours < 48  # Within 2x window

    def test_thread_safety(self, monitor):
        """Should handle concurrent access."""
        results = []

        def record_txs():
            for i in range(100):
                monitor.record_transaction(
                    subject_id="concurrent_user",
                    amount=Decimal("10"),
                )
            results.append(True)

        threads = [threading.Thread(target=record_txs) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should complete
        assert len(results) == 5
        # Should have 500 transactions
        assert len(monitor._transactions["concurrent_user"]) == 500


class TestRiskScoringIntegration:
    """Integration tests for risk scoring."""

    def test_assess_low_risk_transaction(self):
        """Should assess low-risk transaction correctly."""
        factors = [
            RiskFactor(RiskCategory.TRANSACTION, "normal_amount", 10.0),
            RiskFactor(RiskCategory.GEOGRAPHIC, "low_risk_country", 5.0),
        ]

        # Calculate overall score
        total_weighted = sum(f.weighted_score for f in factors)
        overall_score = total_weighted / len(factors)

        # Determine level based on score
        level = RiskLevel.MINIMAL if overall_score <= 20 else RiskLevel.LOW

        assessment = RiskAssessment(
            subject_id="user_low_risk",
            overall_score=overall_score,
            risk_level=level,
            recommended_action=RiskAction.APPROVE,
            factors=factors,
        )

        assert assessment.overall_score < 20
        assert assessment.risk_level == RiskLevel.MINIMAL

    def test_assess_high_risk_transaction(self):
        """Should assess high-risk transaction correctly."""
        factors = [
            RiskFactor(RiskCategory.SANCTIONS, "partial_match", 60.0, weight=2.0),
            RiskFactor(RiskCategory.GEOGRAPHIC, "sanctioned_country", 80.0),
            RiskFactor(RiskCategory.TRANSACTION, "large_amount", 50.0),
        ]

        # High weighted score should trigger high risk
        assessment = RiskAssessment(
            subject_id="user_high_risk",
            overall_score=75.0,
            risk_level=RiskLevel.HIGH,
            recommended_action=RiskAction.BLOCK,
            factors=factors,
        )

        assert assessment.risk_level == RiskLevel.HIGH
        assert assessment.recommended_action == RiskAction.BLOCK


class TestRiskScoringEdgeCases:
    """Edge case tests for risk scoring."""

    def test_zero_score_factor(self):
        """Should handle zero score factors."""
        factor = RiskFactor(
            category=RiskCategory.TRANSACTION,
            name="no_risk",
            score=0.0,
        )

        assert factor.weighted_score == 0.0

    def test_max_score_factor(self):
        """Should handle max score factors."""
        factor = RiskFactor(
            category=RiskCategory.SANCTIONS,
            name="exact_match",
            score=100.0,
            weight=1.0,
        )

        assert factor.weighted_score == 100.0

    def test_assessment_with_no_factors(self):
        """Should handle assessment with no factors."""
        assessment = RiskAssessment(
            subject_id="s1",
            overall_score=0.0,
            risk_level=RiskLevel.MINIMAL,
            recommended_action=RiskAction.APPROVE,
            factors=[],
        )

        assert assessment.by_category == {}
        assert assessment.highest_risk_factors == []

    def test_very_high_amount_transaction(self):
        """Should handle very high transaction amounts."""
        config = RiskConfig()

        # Amount 100x the threshold
        high_amount = config.high_value_threshold * 100

        factor = RiskFactor(
            category=RiskCategory.TRANSACTION,
            name="very_high_amount",
            score=100.0,
            description=f"Amount {high_amount} exceeds threshold",
        )

        assert factor.score == 100.0

    def test_assessment_metadata(self):
        """Should preserve metadata."""
        assessment = RiskAssessment(
            subject_id="s1",
            overall_score=50.0,
            risk_level=RiskLevel.MEDIUM,
            recommended_action=RiskAction.REVIEW,
            factors=[],
            metadata={"source": "automated", "version": "1.0"},
        )

        assert assessment.metadata["source"] == "automated"
        assert "source" in assessment.to_dict()["metadata"]
