"""Tests for agent groups and group policy evaluation."""
from __future__ import annotations

import pytest
from decimal import Decimal

from sardis_v2_core.agent_groups import (
    AgentGroup,
    AgentGroupRepository,
    GroupSpendingLimits,
    GroupMerchantPolicy,
)
from sardis_v2_core.group_policy import (
    GroupPolicyEvaluator,
    GroupPolicyResult,
    InMemoryGroupSpendingTracker,
)


# ============ Repository CRUD Tests ============


@pytest.mark.asyncio
async def test_create_group():
    repo = AgentGroupRepository()
    group = await repo.create(name="Engineering", owner_id="org_1")
    assert group.name == "Engineering"
    assert group.owner_id == "org_1"
    assert group.group_id.startswith("grp_")
    assert group.agent_ids == []


@pytest.mark.asyncio
async def test_get_group():
    repo = AgentGroupRepository()
    created = await repo.create(name="Marketing", owner_id="org_1")
    fetched = await repo.get(created.group_id)
    assert fetched is not None
    assert fetched.group_id == created.group_id
    assert fetched.name == "Marketing"


@pytest.mark.asyncio
async def test_get_nonexistent_group():
    repo = AgentGroupRepository()
    result = await repo.get("grp_nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_groups():
    repo = AgentGroupRepository()
    await repo.create(name="Group A", owner_id="org_1")
    await repo.create(name="Group B", owner_id="org_1")
    await repo.create(name="Group C", owner_id="org_2")

    all_groups = await repo.list()
    assert len(all_groups) == 3

    org1_groups = await repo.list(owner_id="org_1")
    assert len(org1_groups) == 2

    limited = await repo.list(limit=1)
    assert len(limited) == 1


@pytest.mark.asyncio
async def test_update_group():
    repo = AgentGroupRepository()
    group = await repo.create(name="Old Name", owner_id="org_1")
    updated = await repo.update(group.group_id, name="New Name")
    assert updated is not None
    assert updated.name == "New Name"


@pytest.mark.asyncio
async def test_delete_group():
    repo = AgentGroupRepository()
    group = await repo.create(name="Temp", owner_id="org_1")
    assert await repo.delete(group.group_id) is True
    assert await repo.get(group.group_id) is None
    assert await repo.delete(group.group_id) is False


@pytest.mark.asyncio
async def test_add_remove_agent():
    repo = AgentGroupRepository()
    group = await repo.create(name="Team", owner_id="org_1")

    updated = await repo.add_agent(group.group_id, "agent_1")
    assert updated is not None
    assert "agent_1" in updated.agent_ids

    # Adding same agent is idempotent
    updated = await repo.add_agent(group.group_id, "agent_1")
    assert updated.agent_ids.count("agent_1") == 1

    updated = await repo.remove_agent(group.group_id, "agent_1")
    assert "agent_1" not in updated.agent_ids


@pytest.mark.asyncio
async def test_get_groups_for_agent():
    repo = AgentGroupRepository()
    g1 = await repo.create(name="Group 1", owner_id="org_1")
    g2 = await repo.create(name="Group 2", owner_id="org_1")
    await repo.create(name="Group 3", owner_id="org_1")

    await repo.add_agent(g1.group_id, "agent_x")
    await repo.add_agent(g2.group_id, "agent_x")

    groups = await repo.get_groups_for_agent("agent_x")
    assert len(groups) == 2
    group_ids = {g.group_id for g in groups}
    assert g1.group_id in group_ids
    assert g2.group_id in group_ids


# ============ Group Policy Evaluation Tests ============


@pytest.mark.asyncio
async def test_no_group_membership_allows():
    repo = AgentGroupRepository()
    evaluator = GroupPolicyEvaluator(group_repo=repo)

    result = await evaluator.evaluate(
        agent_id="agent_solo",
        amount=Decimal("100"),
        fee=Decimal("1"),
    )
    assert result.allowed is True
    assert result.reason == "no_group_membership"


@pytest.mark.asyncio
async def test_group_per_transaction_limit():
    repo = AgentGroupRepository()
    budget = GroupSpendingLimits(per_transaction=Decimal("50"))
    group = await repo.create(name="Low Limit", budget=budget)
    await repo.add_agent(group.group_id, "agent_1")

    evaluator = GroupPolicyEvaluator(group_repo=repo)

    # Under limit
    result = await evaluator.evaluate(
        agent_id="agent_1",
        amount=Decimal("40"),
        fee=Decimal("1"),
    )
    assert result.allowed is True

    # Over limit (amount + fee > per_transaction)
    result = await evaluator.evaluate(
        agent_id="agent_1",
        amount=Decimal("50"),
        fee=Decimal("1"),
    )
    assert result.allowed is False
    assert result.reason == "group_per_transaction_limit"


@pytest.mark.asyncio
async def test_group_daily_limit():
    repo = AgentGroupRepository()
    budget = GroupSpendingLimits(
        per_transaction=Decimal("1000"),
        daily=Decimal("100"),
    )
    group = await repo.create(name="Daily Cap", budget=budget)
    await repo.add_agent(group.group_id, "agent_1")

    tracker = InMemoryGroupSpendingTracker()
    evaluator = GroupPolicyEvaluator(group_repo=repo, spending_tracker=tracker)

    # Record some spending
    await tracker.record_spend(group.group_id, Decimal("80"))

    # This would exceed daily
    result = await evaluator.evaluate(
        agent_id="agent_1",
        amount=Decimal("25"),
        fee=Decimal("0"),
    )
    assert result.allowed is False
    assert result.reason == "group_daily_limit"


@pytest.mark.asyncio
async def test_group_merchant_blocked():
    repo = AgentGroupRepository()
    policy = GroupMerchantPolicy(blocked_merchants=["bad_merchant"])
    group = await repo.create(name="Strict", merchant_policy=policy)
    await repo.add_agent(group.group_id, "agent_1")

    evaluator = GroupPolicyEvaluator(group_repo=repo)

    result = await evaluator.evaluate(
        agent_id="agent_1",
        amount=Decimal("10"),
        fee=Decimal("0"),
        merchant_id="bad_merchant",
    )
    assert result.allowed is False
    assert result.reason == "group_merchant_blocked"

    # Good merchant should be allowed
    result = await evaluator.evaluate(
        agent_id="agent_1",
        amount=Decimal("10"),
        fee=Decimal("0"),
        merchant_id="good_merchant",
    )
    assert result.allowed is True


@pytest.mark.asyncio
async def test_group_merchant_allowlist():
    repo = AgentGroupRepository()
    policy = GroupMerchantPolicy(allowed_merchants=["approved_vendor"])
    group = await repo.create(name="Allowlist", merchant_policy=policy)
    await repo.add_agent(group.group_id, "agent_1")

    evaluator = GroupPolicyEvaluator(group_repo=repo)

    # Allowed merchant
    result = await evaluator.evaluate(
        agent_id="agent_1",
        amount=Decimal("10"),
        fee=Decimal("0"),
        merchant_id="approved_vendor",
    )
    assert result.allowed is True

    # Unknown merchant denied
    result = await evaluator.evaluate(
        agent_id="agent_1",
        amount=Decimal("10"),
        fee=Decimal("0"),
        merchant_id="random_vendor",
    )
    assert result.allowed is False
    assert result.reason == "group_merchant_not_allowed"


@pytest.mark.asyncio
async def test_group_category_blocked():
    repo = AgentGroupRepository()
    policy = GroupMerchantPolicy(blocked_categories=["gambling"])
    group = await repo.create(name="No Gambling", merchant_policy=policy)
    await repo.add_agent(group.group_id, "agent_1")

    evaluator = GroupPolicyEvaluator(group_repo=repo)

    result = await evaluator.evaluate(
        agent_id="agent_1",
        amount=Decimal("10"),
        fee=Decimal("0"),
        merchant_id="casino_xyz",
        merchant_category="gambling",
    )
    assert result.allowed is False
    assert result.reason == "group_category_blocked"


@pytest.mark.asyncio
async def test_multi_group_most_restrictive():
    """Agent in multiple groups — most restrictive limit wins."""
    repo = AgentGroupRepository()

    # Group A: generous
    g_a = await repo.create(
        name="Generous",
        budget=GroupSpendingLimits(per_transaction=Decimal("1000")),
    )
    # Group B: strict
    g_b = await repo.create(
        name="Strict",
        budget=GroupSpendingLimits(per_transaction=Decimal("50")),
    )

    await repo.add_agent(g_a.group_id, "agent_multi")
    await repo.add_agent(g_b.group_id, "agent_multi")

    evaluator = GroupPolicyEvaluator(group_repo=repo)

    # $60 exceeds Group B's per-tx limit
    result = await evaluator.evaluate(
        agent_id="agent_multi",
        amount=Decimal("60"),
        fee=Decimal("0"),
    )
    assert result.allowed is False
    assert result.group_name == "Strict"


@pytest.mark.asyncio
async def test_backwards_compatibility_no_groups():
    """Agents without groups work exactly as before."""
    repo = AgentGroupRepository()
    evaluator = GroupPolicyEvaluator(group_repo=repo)

    result = await evaluator.evaluate(
        agent_id="agent_legacy",
        amount=Decimal("999999"),
        fee=Decimal("0"),
    )
    assert result.allowed is True
    assert result.reason == "no_group_membership"


@pytest.mark.asyncio
async def test_record_spend_updates_all_groups():
    repo = AgentGroupRepository()
    g1 = await repo.create(name="G1", budget=GroupSpendingLimits(daily=Decimal("200")))
    g2 = await repo.create(name="G2", budget=GroupSpendingLimits(daily=Decimal("200")))
    await repo.add_agent(g1.group_id, "agent_shared")
    await repo.add_agent(g2.group_id, "agent_shared")

    tracker = InMemoryGroupSpendingTracker()
    evaluator = GroupPolicyEvaluator(group_repo=repo, spending_tracker=tracker)

    await evaluator.record_spend("agent_shared", Decimal("100"))

    s1 = await tracker.get_group_spending(g1.group_id)
    s2 = await tracker.get_group_spending(g2.group_id)
    assert s1.daily == Decimal("100")
    assert s2.daily == Decimal("100")
