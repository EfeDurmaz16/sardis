"""Tests for drift → policy action integration."""
from __future__ import annotations

import pytest
from decimal import Decimal

from sardis_v2_core.goal_drift_detector import DriftAlert, DriftSeverity, DriftType
from sardis_v2_core.drift_policy_integrator import (
    DriftAction,
    DriftPolicyConfig,
    DriftPolicyIntegrator,
)
from sardis_v2_core.policy_store_memory import InMemoryPolicyStore
from sardis_v2_core.spending_policy import SpendingPolicy, TimeWindowLimit, create_default_policy


def _alert(
    agent_id: str = "agent_1",
    severity: DriftSeverity = DriftSeverity.LOW,
    drift_type: DriftType = DriftType.AMOUNT_ANOMALY,
    confidence: float = 0.9,
) -> DriftAlert:
    return DriftAlert(
        agent_id=agent_id,
        drift_type=drift_type,
        severity=severity,
        confidence=confidence,
        details={"test": True},
    )


def _make_integrator() -> tuple[DriftPolicyIntegrator, InMemoryPolicyStore]:
    """Create integrator + store pair sharing the same backing store."""
    store = InMemoryPolicyStore()
    integrator = DriftPolicyIntegrator(policy_store=store)
    return integrator, store


# ============ Action Mapping Tests ============


@pytest.mark.asyncio
async def test_low_severity_warn_only():
    integrator, _ = _make_integrator()
    alert = _alert(severity=DriftSeverity.LOW)

    result = await integrator.handle_drift_alert(None, alert)

    assert result.action == DriftAction.WARN
    assert result.policy_changed is False
    assert result.severity == "low"


@pytest.mark.asyncio
async def test_medium_severity_reduces_limits():
    integrator, store = _make_integrator()
    alert = _alert(agent_id="agent_reduce", severity=DriftSeverity.MEDIUM)

    policy = create_default_policy("agent_reduce")
    policy.limit_per_tx = Decimal("500")
    policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=Decimal("1000"))
    await store.set_policy("agent_reduce", policy)

    result = await integrator.handle_drift_alert(None, alert)

    assert result.action == DriftAction.REDUCE_LIMITS
    assert result.policy_changed is True
    assert result.details["reduce_factor"] == 0.5
    assert Decimal(result.details["new_per_tx"]) == Decimal("250.00")
    assert Decimal(result.details["new_daily"]) == Decimal("500.00")


@pytest.mark.asyncio
async def test_high_severity_requires_approval():
    integrator, store = _make_integrator()
    alert = _alert(agent_id="agent_approve", severity=DriftSeverity.HIGH)

    policy = create_default_policy("agent_approve")
    policy.approval_threshold = Decimal("100")
    await store.set_policy("agent_approve", policy)

    result = await integrator.handle_drift_alert(None, alert)

    assert result.action == DriftAction.REQUIRE_APPROVAL
    assert result.policy_changed is True
    assert result.details["new_threshold"] == "0"
    assert result.details["original_threshold"] == "100"


@pytest.mark.asyncio
async def test_critical_severity_freezes():
    integrator, store = _make_integrator()
    alert = _alert(agent_id="agent_freeze", severity=DriftSeverity.CRITICAL)

    policy = create_default_policy("agent_freeze")
    await store.set_policy("agent_freeze", policy)

    result = await integrator.handle_drift_alert(None, alert)

    assert result.action == DriftAction.FREEZE
    assert result.policy_changed is True
    assert result.details["frozen"] is True

    # Verify policy is actually frozen
    frozen_policy = await store.fetch_policy("agent_freeze")
    assert frozen_policy.limit_per_tx == Decimal("0")
    assert frozen_policy.limit_total == Decimal("0")


# ============ Custom Config Tests ============


@pytest.mark.asyncio
async def test_custom_config_mapping():
    """Custom config can remap severity -> action."""
    config = DriftPolicyConfig(
        low_severity_action=DriftAction.REDUCE_LIMITS,
        medium_severity_action=DriftAction.FREEZE,
        auto_reduce_factor=0.25,
    )
    integrator, store = _make_integrator()
    alert = _alert(agent_id="agent_custom", severity=DriftSeverity.LOW)

    policy = create_default_policy("agent_custom")
    policy.limit_per_tx = Decimal("1000")
    policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=Decimal("5000"))
    await store.set_policy("agent_custom", policy)

    result = await integrator.handle_drift_alert(None, alert, config)

    assert result.action == DriftAction.REDUCE_LIMITS
    assert Decimal(result.details["new_per_tx"]) == Decimal("250.00")


@pytest.mark.asyncio
async def test_custom_reduce_factor():
    config = DriftPolicyConfig(auto_reduce_factor=0.75)
    integrator, store = _make_integrator()
    alert = _alert(agent_id="agent_75", severity=DriftSeverity.MEDIUM)

    policy = create_default_policy("agent_75")
    policy.limit_per_tx = Decimal("400")
    policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=Decimal("1000"))
    await store.set_policy("agent_75", policy)

    result = await integrator.handle_drift_alert(None, alert, config)

    assert Decimal(result.details["new_per_tx"]) == Decimal("300.00")
    assert Decimal(result.details["new_daily"]) == Decimal("750.00")


# ============ Edge Cases ============


@pytest.mark.asyncio
async def test_no_policy_falls_back_to_default():
    """If no policy exists for the agent, falls back to default and reduces it."""
    integrator, _ = _make_integrator()
    alert = _alert(agent_id="agent_nonexistent", severity=DriftSeverity.MEDIUM)

    result = await integrator.handle_drift_alert(None, alert)

    # Falls back to default policy, then reduces
    assert result.action == DriftAction.REDUCE_LIMITS
    assert result.policy_changed is True
    assert Decimal(result.details["new_per_tx"]) == Decimal("25.00")  # default LOW $50 * 0.5


@pytest.mark.asyncio
async def test_reduce_no_daily_limit():
    """Reduce works even if daily_limit is not set."""
    integrator, store = _make_integrator()
    alert = _alert(agent_id="agent_no_daily", severity=DriftSeverity.MEDIUM)

    policy = SpendingPolicy(agent_id="agent_no_daily", limit_per_tx=Decimal("1000"))
    await store.set_policy("agent_no_daily", policy)

    result = await integrator.handle_drift_alert(None, alert)

    assert result.policy_changed is True
    assert Decimal(result.details["new_per_tx"]) == Decimal("500.00")
    assert result.details["new_daily"] is None


@pytest.mark.asyncio
async def test_warn_includes_alert_details():
    integrator, _ = _make_integrator()
    alert = _alert(
        severity=DriftSeverity.LOW,
        drift_type=DriftType.MERCHANT_SHIFT,
        confidence=0.85,
    )

    result = await integrator.handle_drift_alert(None, alert)

    assert result.details["drift_type"] == "merchant_shift"
    assert result.details["confidence"] == 0.85


# ============ Action -> Policy Verification ============


@pytest.mark.asyncio
async def test_reduced_limits_actually_enforce():
    """After REDUCE_LIMITS, the policy actually blocks higher amounts."""
    integrator, store = _make_integrator()

    policy = SpendingPolicy(
        agent_id="agent_verify",
        limit_per_tx=Decimal("500"),
        limit_total=Decimal("50000"),
        daily_limit=TimeWindowLimit(window_type="daily", limit_amount=Decimal("10000")),
    )
    await store.set_policy("agent_verify", policy)

    alert = _alert(agent_id="agent_verify", severity=DriftSeverity.MEDIUM)
    await integrator.handle_drift_alert(None, alert)

    reduced = await store.fetch_policy("agent_verify")
    assert reduced.limit_per_tx == Decimal("250.00")

    # $300 would have passed before, now it's denied
    ok, reason = reduced.validate_payment(Decimal("300"), Decimal("0"))
    assert ok is False
    assert reason == "per_transaction_limit"

    # $200 still passes
    ok, reason = reduced.validate_payment(Decimal("200"), Decimal("0"))
    assert ok is True


@pytest.mark.asyncio
async def test_require_approval_enforces():
    """After REQUIRE_APPROVAL, every tx needs human sign-off."""
    integrator, store = _make_integrator()

    policy = create_default_policy("agent_approval_test")
    policy.approval_threshold = Decimal("100")
    await store.set_policy("agent_approval_test", policy)

    alert = _alert(agent_id="agent_approval_test", severity=DriftSeverity.HIGH)
    await integrator.handle_drift_alert(None, alert)

    updated = await store.fetch_policy("agent_approval_test")
    assert updated.approval_threshold == Decimal("0")

    # Even $1 requires approval
    ok, reason = updated.validate_payment(Decimal("1"), Decimal("0"))
    assert ok is True
    assert reason == "requires_approval"


@pytest.mark.asyncio
async def test_freeze_blocks_all():
    """After FREEZE, no transactions can go through."""
    integrator, store = _make_integrator()

    policy = create_default_policy("agent_frozen_test")
    await store.set_policy("agent_frozen_test", policy)

    alert = _alert(agent_id="agent_frozen_test", severity=DriftSeverity.CRITICAL)
    await integrator.handle_drift_alert(None, alert)

    frozen = await store.fetch_policy("agent_frozen_test")

    # Even $0.01 is blocked
    ok, reason = frozen.validate_payment(Decimal("0.01"), Decimal("0"))
    assert ok is False
    assert reason == "per_transaction_limit"
