"""Policy DSL API — compile, validate, and simulate policy definitions.

Endpoints:
    POST /policies/simulate  — Dry-run a payment against a policy definition
    POST /policies/compile   — Compile DSL definition into SpendingPolicy
    POST /policies/validate  — Validate DSL rules without compiling
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request/Response Models ──────────────────────────────────────────


class PolicyRuleModel(BaseModel):
    """Single policy rule in DSL format."""
    type: str = Field(..., description="Rule type (e.g. 'limit_per_tx', 'scope')")
    params: dict[str, Any] = Field(default_factory=dict)


class PolicyDefinitionModel(BaseModel):
    """Complete policy definition."""
    version: str = Field(default="1.0")
    rules: list[PolicyRuleModel] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompileRequest(BaseModel):
    """Request to compile a policy definition."""
    definition: PolicyDefinitionModel
    agent_id: str = Field(..., description="Agent to attach policy to")


class CompileResponse(BaseModel):
    """Compiled policy result."""
    agent_id: str
    policy_id: str
    trust_level: str
    limit_per_tx: str
    limit_total: str
    allowed_scopes: list[str]
    blocked_categories: list[str]
    merchant_rules_count: int
    has_daily_limit: bool
    has_weekly_limit: bool
    has_monthly_limit: bool
    approval_threshold: str | None = None
    definition_hash: str


class ValidateRequest(BaseModel):
    """Request to validate a policy definition."""
    definition: PolicyDefinitionModel


class ValidateResponse(BaseModel):
    """Validation result."""
    valid: bool
    errors: list[str] = Field(default_factory=list)


class SimulatePolicyRequest(BaseModel):
    """Request to simulate a payment against a policy."""
    amount: str = Field(..., description="Payment amount")
    currency: str = Field(default="USDC")
    chain: str = Field(default="base")
    agent_id: str = Field(default="")
    definition: PolicyDefinitionModel | None = None


class SimulatePolicyResponse(BaseModel):
    """Simulation result."""
    intent_id: str
    would_succeed: bool
    failure_reasons: list[str] = Field(default_factory=list)
    policy_result: dict[str, Any] | None = None
    compliance_result: dict[str, Any] | None = None


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/validate", response_model=ValidateResponse)
async def validate_policy(
    body: ValidateRequest,
    principal: Principal = Depends(require_principal),
):
    """Validate a policy definition without compiling."""
    from sardis_v2_core.policy_dsl import PolicyDefinition, PolicyRule, validate_definition

    definition = PolicyDefinition(
        version=body.definition.version,
        rules=[PolicyRule(type=r.type, params=r.params) for r in body.definition.rules],
        metadata=body.definition.metadata,
    )

    errors = validate_definition(definition)
    return ValidateResponse(valid=len(errors) == 0, errors=errors)


@router.post("/compile", response_model=CompileResponse)
async def compile_policy(
    body: CompileRequest,
    principal: Principal = Depends(require_principal),
):
    """Compile a DSL definition into a SpendingPolicy."""
    from sardis_v2_core.policy_dsl import PolicyDefinition, PolicyRule
    from sardis_v2_core.policy_dsl import compile_policy as dsl_compile

    definition = PolicyDefinition(
        version=body.definition.version,
        rules=[PolicyRule(type=r.type, params=r.params) for r in body.definition.rules],
        metadata=body.definition.metadata,
    )

    try:
        policy = dsl_compile(definition, body.agent_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return CompileResponse(
        agent_id=policy.agent_id,
        policy_id=policy.policy_id,
        trust_level=policy.trust_level.value,
        limit_per_tx=str(policy.limit_per_tx),
        limit_total=str(policy.limit_total),
        allowed_scopes=[s.value for s in policy.allowed_scopes],
        blocked_categories=list(policy.blocked_merchant_categories),
        merchant_rules_count=len(policy.merchant_rules),
        has_daily_limit=policy.daily_limit is not None,
        has_weekly_limit=policy.weekly_limit is not None,
        has_monthly_limit=policy.monthly_limit is not None,
        approval_threshold=str(policy.approval_threshold) if policy.approval_threshold else None,
        definition_hash=definition.snapshot_hash(),
    )


@router.post("/simulate", response_model=SimulatePolicyResponse)
async def simulate_policy(
    body: SimulatePolicyRequest,
    principal: Principal = Depends(require_principal),
):
    """Simulate a payment against a policy definition (dry-run)."""
    from sardis_v2_core.control_plane import ControlPlane
    from sardis_v2_core.execution_intent import ExecutionIntent, IntentSource

    intent = ExecutionIntent(
        source=IntentSource.A2A,
        org_id=principal.organization_id,
        agent_id=body.agent_id,
        amount=Decimal(body.amount),
        currency=body.currency,
        chain=body.chain,
    )

    control_plane = ControlPlane()
    result = await control_plane.simulate(intent)

    return SimulatePolicyResponse(
        intent_id=result.intent_id,
        would_succeed=result.would_succeed,
        failure_reasons=result.failure_reasons,
        policy_result=result.policy_result,
        compliance_result=result.compliance_result,
    )
