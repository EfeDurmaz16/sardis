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
    merchant_id: str | None = Field(default=None)
    merchant_category: str | None = Field(default=None)
    mcc_code: str | None = Field(default=None)
    scope: str | None = Field(default=None)
    definition: PolicyDefinitionModel | None = None


class SimulatePolicyResponse(BaseModel):
    """Simulation result."""
    intent_id: str
    would_succeed: bool
    failure_reasons: list[str] = Field(default_factory=list)
    policy_result: dict[str, Any] | None = None
    compliance_result: dict[str, Any] | None = None


def _build_regex_fallback_policy(parsed: dict[str, Any], agent_id: str):
    from sardis_v2_core.spending_policy import (
        MerchantRule,
        SpendingPolicy,
        TimeWindowLimit,
        TrustLevel,
    )

    policy = SpendingPolicy(
        agent_id=agent_id,
        trust_level=TrustLevel.MEDIUM,
    )

    for limit in parsed.get("spending_limits", []):
        vendor_pattern = limit.get("vendor_pattern") or "any"
        max_amount = Decimal(str(limit.get("max_amount", "0") or "0"))
        period = limit.get("period") or "daily"

        policy.merchant_rules.append(
            MerchantRule(
                rule_type="allow",
                merchant_id=vendor_pattern,
                max_per_tx=max_amount if period == "per_transaction" else None,
                daily_limit=max_amount if period == "daily" else None,
                reason=f"Regex policy: max {max_amount} {period}",
            )
        )

        if period == "per_transaction" and max_amount > 0:
            policy.limit_per_tx = min(policy.limit_per_tx, max_amount)
        if period == "daily" and max_amount > 0 and not policy.daily_limit:
            policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=max_amount)
        if period == "weekly" and max_amount > 0 and not policy.weekly_limit:
            policy.weekly_limit = TimeWindowLimit(window_type="weekly", limit_amount=max_amount)
        if period == "monthly" and max_amount > 0 and not policy.monthly_limit:
            policy.monthly_limit = TimeWindowLimit(window_type="monthly", limit_amount=max_amount)

    blocked = parsed.get("blocked_categories", []) or []
    for category in blocked:
        normalized = str(category).strip().lower()
        if normalized and normalized not in policy.blocked_merchant_categories:
            policy.blocked_merchant_categories.append(normalized)

    for override in parsed.get("category_limits", []):
        policy.merchant_rules.append(
            MerchantRule(
                rule_type="override",
                category=override["category"],
                max_per_tx=Decimal(str(override["max_per_tx"])),
                reason=f"Category override: {override['category']} max ${override['max_per_tx']}/tx",
            )
        )

    approval_threshold = parsed.get("requires_approval_above")
    if approval_threshold is not None:
        policy.require_preauth = True
        policy.approval_threshold = Decimal(str(approval_threshold))

    return policy


async def _compile_or_parse_policy(
    definition: PolicyDefinitionModel,
    *,
    agent_id: str,
):
    from sardis_v2_core.nl_policy_parser import create_policy_parser
    from sardis_v2_core.policy_dsl import PolicyDefinition, PolicyRule
    from sardis_v2_core.policy_dsl import compile_policy as dsl_compile

    natural_language_rules = [rule for rule in definition.rules if rule.type == "natural_language"]
    if natural_language_rules:
        nl_text = str(natural_language_rules[0].params.get("text", "")).strip()
        if not nl_text:
            raise ValueError("natural_language rule requires params.text")

        parser = create_policy_parser(use_llm=True)
        if hasattr(parser, "parse_and_convert"):
            return await parser.parse_and_convert(nl_text, agent_id)  # type: ignore[attr-defined]

        parsed = parser.parse(nl_text)  # type: ignore[attr-defined]
        return _build_regex_fallback_policy(parsed, agent_id)

    compiled_definition = PolicyDefinition(
        version=definition.version,
        rules=[PolicyRule(type=rule.type, params=rule.params) for rule in definition.rules],
        metadata=definition.metadata,
    )
    return dsl_compile(compiled_definition, agent_id)


def _step_result(step: dict[str, Any]) -> tuple[str, str | None]:
    details = step.get("details") or {}
    if details.get("requires_approval"):
        return "requires_approval", "Amount exceeds approval threshold"
    if step.get("passed", False):
        return "pass", None

    reason = details.get("reason")
    if reason is None and details.get("error"):
        reason = str(details["error"])
    return "fail", str(reason) if reason is not None else None


def _format_policy_result(*, verdict: str, reason: str, bundle: dict[str, Any]) -> dict[str, Any]:
    if verdict == "approved":
        normalized_verdict = "allowed"
    elif verdict == "escalated":
        normalized_verdict = "requires_approval"
    else:
        normalized_verdict = "denied"

    steps: list[dict[str, Any]] = []
    for step in bundle.get("steps", []):
        result, step_reason = _step_result(step)
        steps.append(
            {
                "step": step.get("step_name", "policy_check"),
                "result": result,
                "reason": step_reason,
            }
        )

    return {
        "verdict": normalized_verdict,
        "reason": reason,
        "decision_id": bundle.get("decision_id"),
        "evidence_hash": bundle.get("evidence_hash"),
        "steps": steps,
    }


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
    """Test a draft policy definition without using the live control plane."""
    from sardis_v2_core.policy_evidence import evaluate_with_evidence, export_evidence_bundle
    from sardis_v2_core.spending_policy import SpendingScope
    from sardis_v2_core.wallets import Wallet

    if body.definition is None:
        raise HTTPException(
            status_code=422,
            detail="Draft policy testing requires a definition. Use /api/v2/simulate for live policy dry runs.",
        )

    agent_id = body.agent_id or "draft_policy"
    try:
        policy = await _compile_or_parse_policy(body.definition, agent_id=agent_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    scope = SpendingScope.ALL
    if body.scope:
        try:
            scope = SpendingScope(body.scope)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid scope '{body.scope}': {e}")

    wallet = Wallet.new(agent_id=agent_id)
    (approved, reason), decision_log = await evaluate_with_evidence(
        policy,
        wallet,
        Decimal(body.amount),
        Decimal("0"),
        chain=body.chain,
        token=body.currency,
        merchant_id=body.merchant_id,
        merchant_category=body.merchant_category,
        mcc_code=body.mcc_code,
        scope=scope,
    )
    bundle = export_evidence_bundle(decision_log)
    policy_result = _format_policy_result(
        verdict=decision_log.final_verdict,
        reason=reason,
        bundle=bundle,
    )

    return SimulatePolicyResponse(
        intent_id=decision_log.decision_id,
        would_succeed=approved and reason == "OK",
        failure_reasons=[] if reason == "OK" else [f"Policy: {reason}"],
        policy_result=policy_result,
        compliance_result={
            "status": "not_evaluated",
            "reason": "draft_policy_test_only",
        },
    )
