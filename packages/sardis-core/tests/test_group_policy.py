"""Unit tests for GroupPolicyEvaluator."""
from __future__ import annotations

import pytest
from decimal import Decimal

from sardis_v2_core.agent_groups import (
    AgentGroupRepository,
    GroupSpendingLimits,
    GroupMerchantPolicy,
)
from sardis_v2_core.group_policy import (
    GroupPolicyEvaluator,
    InMemoryGroupSpendingTracker,
    GroupSpending,
)


@pytest.mark.asyncio
async def test_evaluator_allows_when_no_groups():
    repo = AgentGroupRepository()
    evaluator = GroupPolicyEvaluator(group_repo=repo)
    result = await evaluator.evaluate("agent_x", Decimal("100"), Decimal("1"))
    assert result.allowed is True


@pytest.mark.asyncio
async def test_evaluator_denies_over_per_tx():
    repo = AgentGroupRepository()
    group = await repo.create(
        name="Test",
        budget=GroupSpendingLimits(per_transaction=Decimal("10")),
    )
    await repo.add_agent(group.group_id, "agent_1")

    evaluator = GroupPolicyEvaluator(group_repo=repo)
    result = await evaluator.evaluate("agent_1", Decimal("10"), Decimal("1"))
    assert result.allowed is False
    assert "per_transaction" in result.reason


@pytest.mark.asyncio
async def test_evaluator_denies_over_total():
    repo = AgentGroupRepository()
    group = await repo.create(
        name="Total Cap",
        budget=GroupSpendingLimits(
            per_transaction=Decimal("1000"),
            daily=Decimal("10000"),
            monthly=Decimal("100000"),
            total=Decimal("50"),
        ),
    )
    await repo.add_agent(group.group_id, "agent_1")

    tracker = InMemoryGroupSpendingTracker()
    await tracker.record_spend(group.group_id, Decimal("40"))

    evaluator = GroupPolicyEvaluator(group_repo=repo, spending_tracker=tracker)
    result = await evaluator.evaluate("agent_1", Decimal("15"), Decimal("0"))
    assert result.allowed is False
    assert result.reason == "group_total_limit"


@pytest.mark.asyncio
async def test_evaluator_denies_over_monthly():
    repo = AgentGroupRepository()
    group = await repo.create(
        name="Monthly Cap",
        budget=GroupSpendingLimits(
            per_transaction=Decimal("1000"),
            daily=Decimal("10000"),
            monthly=Decimal("100"),
            total=Decimal("999999"),
        ),
    )
    await repo.add_agent(group.group_id, "agent_1")

    tracker = InMemoryGroupSpendingTracker()
    await tracker.record_spend(group.group_id, Decimal("90"))

    evaluator = GroupPolicyEvaluator(group_repo=repo, spending_tracker=tracker)
    result = await evaluator.evaluate("agent_1", Decimal("15"), Decimal("0"))
    assert result.allowed is False
    assert result.reason == "group_monthly_limit"


@pytest.mark.asyncio
async def test_evaluator_case_insensitive_merchant():
    repo = AgentGroupRepository()
    group = await repo.create(
        name="Case Test",
        merchant_policy=GroupMerchantPolicy(blocked_merchants=["BAD_MERCHANT"]),
    )
    await repo.add_agent(group.group_id, "agent_1")

    evaluator = GroupPolicyEvaluator(group_repo=repo)
    result = await evaluator.evaluate(
        "agent_1", Decimal("10"), Decimal("0"), merchant_id="bad_merchant"
    )
    assert result.allowed is False


@pytest.mark.asyncio
async def test_evaluator_category_allowlist():
    repo = AgentGroupRepository()
    group = await repo.create(
        name="Category Allowlist",
        merchant_policy=GroupMerchantPolicy(allowed_categories=["saas", "compute"]),
    )
    await repo.add_agent(group.group_id, "agent_1")

    evaluator = GroupPolicyEvaluator(group_repo=repo)

    # Allowed category
    result = await evaluator.evaluate(
        "agent_1", Decimal("10"), Decimal("0"),
        merchant_id="aws", merchant_category="compute",
    )
    assert result.allowed is True

    # Denied category
    result = await evaluator.evaluate(
        "agent_1", Decimal("10"), Decimal("0"),
        merchant_id="casino", merchant_category="gambling",
    )
    assert result.allowed is False
    assert result.reason == "group_category_not_allowed"


@pytest.mark.asyncio
async def test_in_memory_spending_tracker():
    tracker = InMemoryGroupSpendingTracker()

    s = await tracker.get_group_spending("grp_new")
    assert s.daily == Decimal("0")

    await tracker.record_spend("grp_new", Decimal("50"))
    s = await tracker.get_group_spending("grp_new")
    assert s.daily == Decimal("50")
    assert s.monthly == Decimal("50")
    assert s.total == Decimal("50")

    await tracker.record_spend("grp_new", Decimal("25"))
    s = await tracker.get_group_spending("grp_new")
    assert s.total == Decimal("75")


@pytest.mark.asyncio
async def test_evaluator_result_includes_group_info():
    repo = AgentGroupRepository()
    group = await repo.create(
        name="Named Group",
        budget=GroupSpendingLimits(per_transaction=Decimal("5")),
    )
    await repo.add_agent(group.group_id, "agent_1")

    evaluator = GroupPolicyEvaluator(group_repo=repo)
    result = await evaluator.evaluate("agent_1", Decimal("10"), Decimal("0"))
    assert result.allowed is False
    assert result.group_id == group.group_id
    assert result.group_name == "Named Group"
