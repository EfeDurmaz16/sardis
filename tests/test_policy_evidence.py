"""Tests for policy decision evidence — step-by-step audit trail of evaluate()."""
from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from sardis_v2_core.spending_policy import SpendingPolicy, TrustLevel, SpendingScope, TimeWindowLimit, MerchantRule
from sardis_v2_core.policy_evidence import (
    PolicyStepResult,
    PolicyDecisionLog,
    compute_evidence_hash,
    evaluate_with_evidence,
    export_evidence_bundle,
)


def _simple_policy(**kwargs) -> SpendingPolicy:
    defaults = dict(
        agent_id="agent_test",
        trust_level=TrustLevel.LOW,
        limit_per_tx=Decimal("500"),
        limit_total=Decimal("5000"),
    )
    defaults.update(kwargs)
    return SpendingPolicy(**defaults)


class FakeWallet:
    async def get_balance(self, chain, token, rpc):
        return Decimal("10000")


# ============ Evidence Hash Tests ============


def test_evidence_hash_determinism():
    steps = [
        PolicyStepResult(1, "amount_validation", True, {"amount": "100"}, 0.1),
        PolicyStepResult(2, "scope_check", True, {"scope": "all"}, 0.05),
    ]
    h1 = compute_evidence_hash(steps)
    h2 = compute_evidence_hash(steps)
    assert h1 == h2
    assert len(h1) == 64


def test_evidence_hash_changes_on_different_steps():
    steps1 = [PolicyStepResult(1, "amount_validation", True, {}, 0.1)]
    steps2 = [PolicyStepResult(1, "amount_validation", False, {}, 0.1)]
    assert compute_evidence_hash(steps1) != compute_evidence_hash(steps2)


# ============ evaluate_with_evidence Tests ============


@pytest.mark.asyncio
async def test_all_steps_pass():
    policy = _simple_policy()
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("1"),
        chain="base", token="USDC",
    )

    assert approved is True
    assert reason == "OK"
    assert evidence.final_verdict == "approved"
    assert len(evidence.steps) == 11  # All 11 steps
    assert all(s.passed for s in evidence.steps)
    assert evidence.evidence_hash
    assert evidence.decision_id.startswith("dec_")


@pytest.mark.asyncio
async def test_amount_validation_fails():
    policy = _simple_policy()
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("-10"), Decimal("0"),
        chain="base", token="USDC",
    )

    assert approved is False
    assert reason == "amount_must_be_positive"
    assert evidence.final_verdict == "denied"
    assert evidence.steps[0].step_name == "amount_validation"
    assert evidence.steps[0].passed is False


@pytest.mark.asyncio
async def test_per_tx_limit_fails():
    policy = _simple_policy(limit_per_tx=Decimal("100"))
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("200"), Decimal("0"),
        chain="base", token="USDC",
    )

    assert approved is False
    assert reason == "per_transaction_limit"
    # Steps 1-3 pass, step 4 fails
    assert evidence.steps[0].passed is True  # amount_validation
    assert evidence.steps[1].passed is True  # scope_check
    assert evidence.steps[2].passed is True  # mcc_check
    assert evidence.steps[3].passed is False  # per_tx_limit
    assert evidence.steps[3].step_name == "per_tx_limit"


@pytest.mark.asyncio
async def test_scope_check_fails():
    policy = _simple_policy(allowed_scopes=[SpendingScope.COMPUTE])
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC", scope=SpendingScope.RETAIL,
    )

    assert approved is False
    assert reason == "scope_not_allowed"
    assert evidence.steps[1].step_name == "scope_check"
    assert evidence.steps[1].passed is False


@pytest.mark.asyncio
async def test_total_limit_fails():
    policy = _simple_policy(spent_total=Decimal("4800"), limit_total=Decimal("5000"))
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("300"), Decimal("0"),
        chain="base", token="USDC",
    )

    assert approved is False
    assert reason == "total_limit_exceeded"


@pytest.mark.asyncio
async def test_goal_drift_fails():
    policy = _simple_policy(max_drift_score=Decimal("0.5"))
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC",
        drift_score=Decimal("0.8"),
    )

    assert approved is False
    assert reason == "goal_drift_exceeded"
    # Find the drift step
    drift_step = next(s for s in evidence.steps if s.step_name == "goal_drift")
    assert drift_step.passed is False


@pytest.mark.asyncio
async def test_approval_threshold_escalated():
    policy = _simple_policy(approval_threshold=Decimal("100"))
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("200"), Decimal("0"),
        chain="base", token="USDC",
    )

    assert approved is True
    assert reason == "requires_approval"
    assert evidence.final_verdict == "escalated"


@pytest.mark.asyncio
async def test_merchant_denied():
    policy = _simple_policy()
    policy.add_merchant_deny(merchant_id="bad_corp")
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC",
        merchant_id="bad_corp",
    )

    assert approved is False
    assert reason == "merchant_denied"


@pytest.mark.asyncio
async def test_time_window_limit_fails():
    policy = _simple_policy(
        daily_limit=TimeWindowLimit(window_type="daily", limit_amount=Decimal("100"), current_spent=Decimal("90")),
    )
    wallet = FakeWallet()

    (approved, reason), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("20"), Decimal("0"),
        chain="base", token="USDC",
    )

    assert approved is False
    assert reason == "time_window_limit"


@pytest.mark.asyncio
async def test_evidence_links_to_policy_version():
    policy = _simple_policy()
    wallet = FakeWallet()

    (_, _), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC",
        policy_version_id="pvr_abc123",
    )

    assert evidence.policy_version_id == "pvr_abc123"


@pytest.mark.asyncio
async def test_evidence_includes_mandate_id():
    policy = _simple_policy()
    wallet = FakeWallet()

    (_, _), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC",
        mandate_id="mandate_xyz",
    )

    assert evidence.mandate_id == "mandate_xyz"


@pytest.mark.asyncio
async def test_timing_instrumentation():
    """All steps should have duration_ms >= 0."""
    policy = _simple_policy()
    wallet = FakeWallet()

    (_, _), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC",
    )

    for step in evidence.steps:
        assert step.duration_ms >= 0


@pytest.mark.asyncio
async def test_group_hierarchy_recorded():
    policy = _simple_policy()
    wallet = FakeWallet()

    (_, _), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC",
        group_hierarchy=["grp_org", "grp_team"],
    )

    assert evidence.group_hierarchy_applied == ["grp_org", "grp_team"]


# ============ Export Tests ============


@pytest.mark.asyncio
async def test_export_format():
    policy = _simple_policy()
    wallet = FakeWallet()

    (_, _), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC",
        mandate_id="mandate_1",
    )

    bundle = export_evidence_bundle(evidence)

    assert "decision_id" in bundle
    assert "agent_id" in bundle
    assert "mandate_id" in bundle
    assert "timestamp" in bundle
    assert "final_verdict" in bundle
    assert "evidence_hash" in bundle
    assert "steps" in bundle
    assert isinstance(bundle["steps"], list)
    assert len(bundle["steps"]) == 11

    # Each step has required fields
    for step in bundle["steps"]:
        assert "step_number" in step
        assert "step_name" in step
        assert "passed" in step
        assert "details" in step
        assert "duration_ms" in step


@pytest.mark.asyncio
async def test_export_is_json_serializable():
    """Export bundle must be serializable to JSON without errors."""
    import json as _json

    policy = _simple_policy()
    wallet = FakeWallet()

    (_, _), evidence = await evaluate_with_evidence(
        policy, wallet, Decimal("50"), Decimal("0"),
        chain="base", token="USDC",
    )

    bundle = export_evidence_bundle(evidence)
    serialized = _json.dumps(bundle)
    assert isinstance(serialized, str)
    parsed = _json.loads(serialized)
    assert parsed["agent_id"] == "agent_test"
