"""Policy models for Sardis SDK."""
from __future__ import annotations

from typing import Any, Optional

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
    requires_approval_above: Optional[float] = None
    global_daily_limit: Optional[float] = None
    global_monthly_limit: Optional[float] = None
    is_active: bool = True
    policy_id: Optional[str] = None
    agent_id: Optional[str] = None
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
    trust_level: Optional[str] = None
    limit_per_tx: Optional[str] = None
    limit_total: Optional[str] = None
    merchant_rules_count: Optional[int] = None
    message: Optional[str] = None


class PolicyCheckResponse(SardisModel):
    allowed: bool
    reason: str
    policy_id: Optional[str] = None


class PolicyExample(SardisModel):
    description: str
    natural_language: str
    use_case: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

