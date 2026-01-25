"""
Comprehensive tests for sardis_checkout.fraud module.

Tests cover:
- FraudCheckContext creation
- VelocityCheckProvider
- Fraud signal generation
- Risk level classification
- Rule-based detection
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_checkout.fraud import (
    FraudError,
    FraudCheckFailed,
    FraudDeclined,
    FraudCheckContext,
    FraudSignalProvider,
    VelocityCheckProvider,
)
from sardis_checkout.models import (
    FraudCheckResult,
    FraudDecision,
    FraudRiskLevel,
    FraudSignal,
)


class TestFraudError:
    """Tests for FraudError exception."""

    def test_base_fraud_error(self):
        """Should create base fraud error."""
        error = FraudError("Fraud check failed")
        assert "fraud" in str(error).lower() or "check" in str(error).lower()


class TestFraudCheckFailed:
    """Tests for FraudCheckFailed exception."""

    def test_check_failed_error(self):
        """Should create check failed error."""
        error = FraudCheckFailed("External service unavailable")
        assert isinstance(error, FraudError)


class TestFraudDeclined:
    """Tests for FraudDeclined exception."""

    def test_declined_error(self):
        """Should create declined error with check result."""
        check_result = Mock()
        check_result.decision = FraudDecision.DECLINE

        error = FraudDeclined("High fraud risk detected", check_result)

        assert error.check_result == check_result


class TestFraudCheckContext:
    """Tests for FraudCheckContext class."""

    def test_create_context(self):
        """Should create fraud check context."""
        context = FraudCheckContext(
            checkout_id="checkout_123",
            agent_id="agent_456",
            customer_id="cust_789",
            amount=Decimal("100.50"),
            currency="USD",
        )

        assert context.checkout_id == "checkout_123"
        assert context.agent_id == "agent_456"
        assert context.amount == Decimal("100.50")

    def test_context_with_all_fields(self):
        """Should create context with all optional fields."""
        context = FraudCheckContext(
            checkout_id="checkout_abc",
            agent_id="agent_xyz",
            customer_id="cust_123",
            customer_email="test@example.com",
            amount=Decimal("500"),
            currency="USD",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            device_fingerprint="fp_abc123",
            billing_country="US",
            card_country="US",
            card_bin="411111",
            is_new_customer=True,
            previous_checkouts=0,
            previous_successful_payments=0,
        )

        assert context.ip_address == "192.168.1.1"
        assert context.card_bin == "411111"
        assert context.is_new_customer is True

    def test_context_defaults(self):
        """Should have sensible defaults."""
        context = FraudCheckContext(
            checkout_id="c1",
            agent_id="a1",
        )

        assert context.amount == Decimal("0")
        assert context.currency == "USD"
        assert context.is_new_customer is True
        assert context.previous_checkouts == 0
        assert context.metadata == {}


class TestVelocityCheckProvider:
    """Tests for VelocityCheckProvider class."""

    @pytest.fixture
    def provider(self):
        """Create velocity check provider."""
        return VelocityCheckProvider(
            max_checkouts_per_ip_hour=5,
            max_checkouts_per_device_hour=3,
            max_amount_per_customer_day=Decimal("1000"),
        )

    def test_provider_name(self, provider):
        """Should have correct provider name."""
        assert provider.name == "velocity"

    @pytest.mark.asyncio
    async def test_no_signals_for_normal_activity(self, provider):
        """Should return no signals for normal activity."""
        context = FraudCheckContext(
            checkout_id="c1",
            agent_id="a1",
            ip_address="1.2.3.4",
            amount=Decimal("50"),
        )

        signals = await provider.get_signals(context)

        # First request should have no velocity signals
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_signals_for_high_ip_velocity(self, provider):
        """Should generate signal for high IP velocity."""
        ip = "192.168.1.100"

        # Generate many requests from same IP
        for i in range(10):
            context = FraudCheckContext(
                checkout_id=f"c_{i}",
                agent_id="a1",
                ip_address=ip,
                amount=Decimal("10"),
                timestamp=datetime.utcnow(),
            )
            await provider.get_signals(context)

        # Next request should trigger signal
        context = FraudCheckContext(
            checkout_id="c_final",
            agent_id="a1",
            ip_address=ip,
            amount=Decimal("10"),
            timestamp=datetime.utcnow(),
        )
        signals = await provider.get_signals(context)

        # Should have IP velocity signal
        ip_signals = [s for s in signals if "ip" in s.name.lower()]
        assert len(ip_signals) > 0

    @pytest.mark.asyncio
    async def test_signals_for_high_device_velocity(self, provider):
        """Should generate signal for high device velocity."""
        device_fp = "device_fingerprint_123"

        # Generate many requests from same device
        for i in range(6):
            context = FraudCheckContext(
                checkout_id=f"c_{i}",
                agent_id="a1",
                device_fingerprint=device_fp,
                amount=Decimal("10"),
                timestamp=datetime.utcnow(),
            )
            await provider.get_signals(context)

        # Next request should trigger signal
        context = FraudCheckContext(
            checkout_id="c_final",
            agent_id="a1",
            device_fingerprint=device_fp,
            amount=Decimal("10"),
            timestamp=datetime.utcnow(),
        )
        signals = await provider.get_signals(context)

        # Should have device velocity signal
        device_signals = [s for s in signals if "device" in s.name.lower()]
        assert len(device_signals) > 0

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self, provider):
        """Should cleanup old entries."""
        old_time = datetime.utcnow() - timedelta(hours=2)

        # Add old entry
        provider._ip_counts["old_ip"] = [old_time]

        # Process new context (triggers cleanup)
        context = FraudCheckContext(
            checkout_id="c1",
            agent_id="a1",
            ip_address="new_ip",
            timestamp=datetime.utcnow(),
        )
        await provider.get_signals(context)

        # Old entries should be cleaned
        assert "old_ip" not in provider._ip_counts or len(provider._ip_counts.get("old_ip", [])) == 0


class TestFraudSignal:
    """Tests for FraudSignal model."""

    def test_create_signal(self):
        """Should create fraud signal."""
        signal = FraudSignal(
            name="high_velocity_ip",
            provider="velocity",
            risk_score=75,
            description="Multiple checkouts from same IP",
            metadata={"ip": "1.2.3.4", "count": 10},
        )

        assert signal.name == "high_velocity_ip"
        assert signal.risk_score == 75
        assert signal.metadata["count"] == 10


class TestFraudCheckResult:
    """Tests for FraudCheckResult model."""

    def test_create_result(self):
        """Should create fraud check result."""
        result = FraudCheckResult(
            checkout_id="c1",
            decision=FraudDecision.ALLOW,
            risk_level=FraudRiskLevel.LOW,
            risk_score=15,
            signals=[],
        )

        assert result.decision == FraudDecision.ALLOW
        assert result.risk_level == FraudRiskLevel.LOW

    def test_result_with_signals(self):
        """Should include signals in result."""
        signals = [
            FraudSignal(
                name="signal_1",
                provider="test",
                risk_score=30,
            ),
            FraudSignal(
                name="signal_2",
                provider="test",
                risk_score=40,
            ),
        ]

        result = FraudCheckResult(
            checkout_id="c2",
            decision=FraudDecision.REVIEW,
            risk_level=FraudRiskLevel.MEDIUM,
            risk_score=50,
            signals=signals,
        )

        assert len(result.signals) == 2


class TestFraudDecision:
    """Tests for FraudDecision enum."""

    def test_decision_values(self):
        """Should have correct decision values."""
        assert FraudDecision.ALLOW.value == "allow"
        assert FraudDecision.REVIEW.value == "review"
        assert FraudDecision.DECLINE.value == "decline"


class TestFraudRiskLevel:
    """Tests for FraudRiskLevel enum."""

    def test_risk_level_values(self):
        """Should have correct risk level values."""
        assert FraudRiskLevel.LOW.value == "low"
        assert FraudRiskLevel.MEDIUM.value == "medium"
        assert FraudRiskLevel.HIGH.value == "high"
        assert FraudRiskLevel.CRITICAL.value == "critical"


class TestFraudIntegration:
    """Integration tests for fraud detection."""

    @pytest.mark.asyncio
    async def test_full_fraud_check_flow(self):
        """Should perform full fraud check flow."""
        provider = VelocityCheckProvider()

        # Normal checkout
        context = FraudCheckContext(
            checkout_id="normal_checkout",
            agent_id="agent_1",
            customer_id="customer_1",
            amount=Decimal("50"),
            ip_address="10.0.0.1",
        )

        signals = await provider.get_signals(context)

        # Should have no or low-risk signals for first checkout
        high_risk_signals = [s for s in signals if s.risk_score > 70]
        assert len(high_risk_signals) == 0


class TestFraudEdgeCases:
    """Edge case tests for fraud detection."""

    @pytest.mark.asyncio
    async def test_missing_ip_address(self):
        """Should handle missing IP address."""
        provider = VelocityCheckProvider()

        context = FraudCheckContext(
            checkout_id="no_ip",
            agent_id="a1",
            ip_address=None,
        )

        # Should not raise
        signals = await provider.get_signals(context)
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_missing_device_fingerprint(self):
        """Should handle missing device fingerprint."""
        provider = VelocityCheckProvider()

        context = FraudCheckContext(
            checkout_id="no_device",
            agent_id="a1",
            device_fingerprint=None,
        )

        # Should not raise
        signals = await provider.get_signals(context)
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_zero_amount(self):
        """Should handle zero amount."""
        provider = VelocityCheckProvider()

        context = FraudCheckContext(
            checkout_id="zero_amount",
            agent_id="a1",
            amount=Decimal("0"),
        )

        signals = await provider.get_signals(context)
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_very_large_amount(self):
        """Should handle very large amounts."""
        provider = VelocityCheckProvider(
            max_amount_per_customer_day=Decimal("100")
        )

        context = FraudCheckContext(
            checkout_id="large_amount",
            agent_id="a1",
            customer_id="cust_1",
            amount=Decimal("1000000"),
        )

        signals = await provider.get_signals(context)
        # May generate high-value signal
        assert isinstance(signals, list)
