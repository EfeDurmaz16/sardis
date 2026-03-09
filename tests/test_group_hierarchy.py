"""Tests for group policy hierarchy — cascading org -> team -> agent policies."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sardis_v2_core.agent_groups import (
    AgentGroup,
    AgentGroupHierarchy,
    AgentGroupRepository,
    GroupMerchantPolicy,
    GroupSpendingLimits,
    merge_group_policies,
)

# ============ merge_group_policies unit tests ============


def _group(
    name: str,
    per_tx: str = "500.00",
    daily: str = "5000.00",
    monthly: str = "50000.00",
    total: str = "500000.00",
    allowed_merchants=None,
    blocked_merchants=None,
    allowed_categories=None,
    blocked_categories=None,
    **kwargs,
) -> AgentGroup:
    return AgentGroup.new(
        name=name,
        budget=GroupSpendingLimits(
            per_transaction=Decimal(per_tx),
            daily=Decimal(daily),
            monthly=Decimal(monthly),
            total=Decimal(total),
        ),
        merchant_policy=GroupMerchantPolicy(
            allowed_merchants=allowed_merchants,
            blocked_merchants=blocked_merchants or [],
            allowed_categories=allowed_categories,
            blocked_categories=blocked_categories or [],
        ),
        **kwargs,
    )


def test_merge_most_restrictive_limits():
    parent = _group("Org", per_tx="1000", daily="10000")
    child = _group("Team", per_tx="500", daily="20000")
    merged = merge_group_policies(child, parent)

    assert merged.budget.per_transaction == Decimal("500")  # child wins
    assert merged.budget.daily == Decimal("10000")  # parent wins


def test_merge_blocked_categories_union():
    parent = _group("Org", blocked_categories=["gambling"])
    child = _group("Team", blocked_categories=["adult"])
    merged = merge_group_policies(child, parent)

    assert "gambling" in merged.merchant_policy.blocked_categories
    assert "adult" in merged.merchant_policy.blocked_categories


def test_merge_blocked_merchants_union():
    parent = _group("Org", blocked_merchants=["bad_corp"])
    child = _group("Team", blocked_merchants=["evil_inc"])
    merged = merge_group_policies(child, parent)

    assert "bad_corp" in merged.merchant_policy.blocked_merchants
    assert "evil_inc" in merged.merchant_policy.blocked_merchants


def test_merge_allowed_merchants_intersection():
    parent = _group("Org", allowed_merchants=["aws", "gcp", "azure"])
    child = _group("Team", allowed_merchants=["aws", "gcp"])
    merged = merge_group_policies(child, parent)

    assert sorted(merged.merchant_policy.allowed_merchants) == ["aws", "gcp"]


def test_merge_allowed_merchants_parent_only():
    parent = _group("Org", allowed_merchants=["aws", "gcp"])
    child = _group("Team")  # allowed_merchants=None (no restriction)
    merged = merge_group_policies(child, parent)

    assert merged.merchant_policy.allowed_merchants == ["aws", "gcp"]


def test_merge_allowed_categories_intersection():
    parent = _group("Org", allowed_categories=["compute", "cloud", "saas"])
    child = _group("Team", allowed_categories=["compute", "cloud"])
    merged = merge_group_policies(child, parent)

    assert sorted(merged.merchant_policy.allowed_categories) == ["cloud", "compute"]


def test_merge_preserves_child_identity():
    parent = _group("Org")
    child = _group("Team")
    merged = merge_group_policies(child, parent)

    assert merged.group_id == child.group_id
    assert merged.name == child.name


# ============ Hierarchy resolution tests (repo-backed) ============


@pytest.mark.asyncio
async def test_three_level_hierarchy():
    """org -> team -> agent: effective policy is most restrictive across all."""
    repo = AgentGroupRepository()

    org = await repo.create(
        name="Org",
        budget=GroupSpendingLimits(
            per_transaction=Decimal("10000"),
            daily=Decimal("100000"),
        ),
        merchant_policy=GroupMerchantPolicy(blocked_categories=["gambling"]),
    )
    team = await repo.create(
        name="Team",
        budget=GroupSpendingLimits(
            per_transaction=Decimal("1000"),
            daily=Decimal("50000"),
        ),
        merchant_policy=GroupMerchantPolicy(blocked_categories=["adult"]),
    )
    await repo.set_parent(team.group_id, org.group_id)
    await repo.add_agent(team.group_id, "agent_1")

    hierarchy = AgentGroupHierarchy(repo)
    effective = await hierarchy.resolve_effective_policy("agent_1")

    assert effective is not None
    assert effective.budget.per_transaction == Decimal("1000")  # team wins
    assert effective.budget.daily == Decimal("50000")  # team wins
    # Both blocked categories merged
    assert "gambling" in effective.merchant_policy.blocked_categories
    assert "adult" in effective.merchant_policy.blocked_categories


@pytest.mark.asyncio
async def test_cycle_detection():
    """Setting A->B->C->A as parent should raise ValueError."""
    repo = AgentGroupRepository()

    a = await repo.create(name="A")
    b = await repo.create(name="B")
    c = await repo.create(name="C")

    await repo.set_parent(b.group_id, a.group_id)
    await repo.set_parent(c.group_id, b.group_id)

    with pytest.raises(ValueError, match="Cycle detected"):
        await repo.set_parent(a.group_id, c.group_id)


@pytest.mark.asyncio
async def test_self_cycle_detection():
    """Setting a group as its own parent should raise ValueError."""
    repo = AgentGroupRepository()
    g = await repo.create(name="Self")

    with pytest.raises(ValueError, match="Cycle detected"):
        await repo.set_parent(g.group_id, g.group_id)


@pytest.mark.asyncio
async def test_orphan_agent_returns_none():
    """Agent with no group returns None from hierarchy resolution."""
    repo = AgentGroupRepository()
    hierarchy = AgentGroupHierarchy(repo)

    result = await hierarchy.resolve_effective_policy("agent_solo")
    assert result is None


@pytest.mark.asyncio
async def test_get_ancestors():
    """Ancestors returns chain from group to root (exclusive of self)."""
    repo = AgentGroupRepository()

    root = await repo.create(name="Root")
    mid = await repo.create(name="Mid")
    leaf = await repo.create(name="Leaf")

    await repo.set_parent(mid.group_id, root.group_id)
    await repo.set_parent(leaf.group_id, mid.group_id)

    hierarchy = AgentGroupHierarchy(repo)
    ancestors = await hierarchy.get_ancestors(leaf.group_id)

    assert len(ancestors) == 2
    assert ancestors[0].group_id == mid.group_id
    assert ancestors[1].group_id == root.group_id


@pytest.mark.asyncio
async def test_hierarchy_path_updated_on_set_parent():
    repo = AgentGroupRepository()

    root = await repo.create(name="Root")
    child = await repo.create(name="Child")

    updated = await repo.set_parent(child.group_id, root.group_id)
    assert updated is not None
    assert updated.parent_group_id == root.group_id
    assert updated.hierarchy_path == [root.group_id]


@pytest.mark.asyncio
async def test_set_parent_to_none():
    repo = AgentGroupRepository()

    root = await repo.create(name="Root")
    child = await repo.create(name="Child")
    await repo.set_parent(child.group_id, root.group_id)

    updated = await repo.set_parent(child.group_id, None)
    assert updated is not None
    assert updated.parent_group_id is None
    assert updated.hierarchy_path == []


@pytest.mark.asyncio
async def test_set_parent_nonexistent():
    repo = AgentGroupRepository()
    g = await repo.create(name="Group")

    with pytest.raises(ValueError, match="not found"):
        await repo.set_parent(g.group_id, "grp_nonexistent")


@pytest.mark.asyncio
async def test_effective_policy_root_limits_cap():
    """Effective policy cannot exceed root limits regardless of child settings."""
    repo = AgentGroupRepository()

    root = await repo.create(
        name="Root",
        budget=GroupSpendingLimits(per_transaction=Decimal("100")),
    )
    child = await repo.create(
        name="Child",
        budget=GroupSpendingLimits(per_transaction=Decimal("999")),
    )
    await repo.set_parent(child.group_id, root.group_id)
    await repo.add_agent(child.group_id, "agent_1")

    hierarchy = AgentGroupHierarchy(repo)
    effective = await hierarchy.resolve_effective_policy("agent_1")

    assert effective is not None
    # Root's $100 caps the child's $999
    assert effective.budget.per_transaction == Decimal("100")
