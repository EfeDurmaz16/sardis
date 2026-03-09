"""Agent group models for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from .base import SardisModel

if TYPE_CHECKING:
    from datetime import datetime


class GroupBudget(SardisModel):
    """Spending limits for an agent group."""

    per_transaction: str | None = None
    daily: str | None = None
    monthly: str | None = None
    total: str | None = None


class GroupMerchantPolicy(SardisModel):
    """Merchant policy for an agent group."""

    allowed_merchants: list[str] | None = None
    blocked_merchants: list[str] | None = None
    allowed_categories: list[str] | None = None
    blocked_categories: list[str] | None = None


class AgentGroup(SardisModel):
    """An agent group with shared budget and policies."""

    group_id: str = Field(alias="id")
    name: str
    owner_id: str | None = None
    budget: GroupBudget | None = None
    merchant_policy: GroupMerchantPolicy | None = None
    agent_ids: list[str] = Field(default_factory=list)
    metadata: dict | None = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreateGroupRequest(SardisModel):
    """Request to create a new agent group."""

    name: str
    budget: GroupBudget | None = None
    merchant_policy: GroupMerchantPolicy | None = None
    metadata: dict | None = None


class UpdateGroupRequest(SardisModel):
    """Request to update an agent group."""

    name: str | None = None
    budget: GroupBudget | None = None
    merchant_policy: GroupMerchantPolicy | None = None
    metadata: dict | None = None


# Aliases for consistency
GroupCreate = CreateGroupRequest
GroupUpdate = UpdateGroupRequest
