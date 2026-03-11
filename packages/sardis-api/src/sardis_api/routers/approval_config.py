"""Approval routing configuration — approver groups, quorum, SLA, escalation.

Allows operators to configure approval workflows without code changes.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import require_principal

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_principal)])

# In-memory config store (replace with DB in production)
_approval_config: dict = {
    "approver_groups": [
        {"id": "finance", "name": "Finance Team", "members": ["finance@company.com"], "is_fallback": False},
        {"id": "leadership", "name": "Leadership", "members": ["cto@company.com"], "is_fallback": True},
    ],
    "routing_rules": [
        {
            "id": "high-value",
            "name": "High Value Payments",
            "condition": "amount > 1000",
            "approver_group": "finance",
            "quorum": 1,
            "distinct_reviewers": True,
            "sla_hours": 4,
            "escalation_hours": 8,
            "escalation_group": "leadership",
        },
        {
            "id": "critical",
            "name": "Critical Payments",
            "condition": "amount > 5000 OR urgency == 'critical'",
            "approver_group": "leadership",
            "quorum": 2,
            "distinct_reviewers": True,
            "sla_hours": 2,
            "escalation_hours": 4,
            "escalation_group": None,
        },
    ],
    "defaults": {
        "default_approver_group": "finance",
        "default_quorum": 1,
        "default_sla_hours": 24,
        "auto_expire_hours": 168,
        "require_distinct_reviewers": False,
    },
}


class ApproverGroup(BaseModel):
    id: str
    name: str
    members: list[str]
    is_fallback: bool = False


class RoutingRule(BaseModel):
    id: str
    name: str
    condition: str
    approver_group: str
    quorum: int = Field(default=1, ge=1)
    distinct_reviewers: bool = False
    sla_hours: int = Field(default=24, ge=1)
    escalation_hours: int | None = None
    escalation_group: str | None = None


class ApprovalDefaults(BaseModel):
    default_approver_group: str
    default_quorum: int = 1
    default_sla_hours: int = 24
    auto_expire_hours: int = 168
    require_distinct_reviewers: bool = False


class ApprovalConfigResponse(BaseModel):
    approver_groups: list[ApproverGroup]
    routing_rules: list[RoutingRule]
    defaults: ApprovalDefaults


@router.get("/", response_model=ApprovalConfigResponse)
async def get_approval_config() -> ApprovalConfigResponse:
    """Get the current approval routing configuration."""
    return ApprovalConfigResponse(**_approval_config)


@router.put("/groups", response_model=list[ApproverGroup])
async def update_approver_groups(groups: list[ApproverGroup]) -> list[ApproverGroup]:
    """Replace all approver groups."""
    _approval_config["approver_groups"] = [g.model_dump() for g in groups]
    logger.info("Approver groups updated: %d groups", len(groups))
    return groups


@router.put("/rules", response_model=list[RoutingRule])
async def update_routing_rules(rules: list[RoutingRule]) -> list[RoutingRule]:
    """Replace all routing rules."""
    # Validate that all referenced approver groups exist
    group_ids = {g["id"] for g in _approval_config["approver_groups"]}
    for rule in rules:
        if rule.approver_group not in group_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Rule '{rule.id}' references unknown approver group '{rule.approver_group}'",
            )
        if rule.escalation_group and rule.escalation_group not in group_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Rule '{rule.id}' references unknown escalation group '{rule.escalation_group}'",
            )
    _approval_config["routing_rules"] = [r.model_dump() for r in rules]
    logger.info("Routing rules updated: %d rules", len(rules))
    return rules


@router.put("/defaults", response_model=ApprovalDefaults)
async def update_defaults(defaults: ApprovalDefaults) -> ApprovalDefaults:
    """Update default approval settings."""
    group_ids = {g["id"] for g in _approval_config["approver_groups"]}
    if defaults.default_approver_group not in group_ids:
        raise HTTPException(
            status_code=422,
            detail=f"Default approver group '{defaults.default_approver_group}' does not exist",
        )
    _approval_config["defaults"] = defaults.model_dump()
    logger.info("Approval defaults updated")
    return defaults
