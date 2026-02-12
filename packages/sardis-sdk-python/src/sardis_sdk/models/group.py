"""Agent group models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import Field

from .base import SardisModel


class GroupBudget(SardisModel):
    """Spending limits for an agent group."""

    per_transaction: Optional[str] = None
    daily: Optional[str] = None
    monthly: Optional[str] = None
    total: Optional[str] = None


class GroupMerchantPolicy(SardisModel):
    """Merchant policy for an agent group."""

    allowed_merchants: Optional[List[str]] = None
    blocked_merchants: Optional[List[str]] = None
    allowed_categories: Optional[List[str]] = None
    blocked_categories: Optional[List[str]] = None


class AgentGroup(SardisModel):
    """An agent group with shared budget and policies."""

    group_id: str = Field(alias="id")
    name: str
    owner_id: Optional[str] = None
    budget: Optional[GroupBudget] = None
    merchant_policy: Optional[GroupMerchantPolicy] = None
    agent_ids: List[str] = Field(default_factory=list)
    metadata: Optional[dict] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreateGroupRequest(SardisModel):
    """Request to create a new agent group."""

    name: str
    budget: Optional[GroupBudget] = None
    merchant_policy: Optional[GroupMerchantPolicy] = None
    metadata: Optional[dict] = None


class UpdateGroupRequest(SardisModel):
    """Request to update an agent group."""

    name: Optional[str] = None
    budget: Optional[GroupBudget] = None
    merchant_policy: Optional[GroupMerchantPolicy] = None
    metadata: Optional[dict] = None


# Aliases for consistency
GroupCreate = CreateGroupRequest
GroupUpdate = UpdateGroupRequest
