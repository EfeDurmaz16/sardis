"""Policy models for Sardis SDK."""
from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import SardisModel


class PolicySpendingLimit(SardisModel):
    vendor_pattern: str
    max_amount: float
    period: str
    currency: str = "USD"


class ParsedPolicy(SardisModel):
    name: str
    description: str
    spending_limits: list[PolicySpendingLimit] = Field(default_factory=list)
    requires_approval_above: float | None = None
    global_daily_limit: float | None = None
    global_monthly_limit: float | None = None
    is_active: bool = True
    policy_id: str | None = None
    agent_id: str | None = None
    # Additional fields may be returned by the API; they are ignored by default config.


class PolicyPreviewResponse(SardisModel):
    parsed: ParsedPolicy
    warnings: list[str] = Field(default_factory=list)
    requires_confirmation: bool = True
    confirmation_message: str = ""


class ApplyPolicyFromNLResponse(SardisModel):
    success: bool
    policy_id: str
    agent_id: str
    trust_level: str | None = None
    limit_per_tx: str | None = None
    limit_total: str | None = None
    merchant_rules_count: int | None = None
    message: str | None = None


class PolicyCheckResponse(SardisModel):
    allowed: bool
    reason: str
    policy_id: str | None = None


class PolicyExample(SardisModel):
    description: str
    natural_language: str
    use_case: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

