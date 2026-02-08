"""Policy API endpoints with Natural Language parsing support."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from sardis_api.authz import require_principal
from sardis_api.authz import Principal
from sardis_v2_core import AgentRepository
from sardis_api.idempotency import get_idempotency_key, run_idempotent

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


# ============================================================================
# Dependencies
# ============================================================================

@dataclass
class PolicyDependencies:
    policy_store: any  # AsyncPolicyStore (in-memory or postgres)
    agent_repo: AgentRepository


def get_deps() -> PolicyDependencies:
    raise NotImplementedError("Dependency override required")


# ============================================================================
# Request/Response Models
# ============================================================================

class ParsePolicyRequest(BaseModel):
    """Request to parse a natural language policy."""

    natural_language: str = Field(
        ...,
        description="Natural language description of the spending policy",
        examples=[
            "Allow max $500 per day on AWS and OpenAI, block gambling",
            "Spend up to $100 per transaction, require approval over $500",
            "Only allow cloud services (AWS, GCP, Azure) with $1000 monthly limit",
        ],
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Agent ID to associate with the parsed policy",
    )


class SpendingLimitResponse(BaseModel):
    """A single spending limit."""

    vendor_pattern: str
    max_amount: float
    period: str
    currency: str = "USD"


class CategoryRestrictionsResponse(BaseModel):
    """Category-based restrictions."""

    allowed_categories: List[str] = []
    blocked_categories: List[str] = []


class TimeRestrictionsResponse(BaseModel):
    """Time-based restrictions."""

    allowed_hours_start: int = 0
    allowed_hours_end: int = 23
    allowed_days: List[str] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    timezone: str = "UTC"


class ParsedPolicyResponse(BaseModel):
    """Response containing the parsed policy."""

    name: str
    description: str
    spending_limits: List[SpendingLimitResponse] = []
    category_restrictions: Optional[CategoryRestrictionsResponse] = None
    time_restrictions: Optional[TimeRestrictionsResponse] = None
    requires_approval_above: Optional[float] = None
    global_daily_limit: Optional[float] = None
    global_monthly_limit: Optional[float] = None
    is_active: bool = True

    # The converted SpendingPolicy (if agent_id provided)
    policy_id: Optional[str] = None
    agent_id: Optional[str] = None

    # SECURITY: Warnings from post-LLM validation or regex fallback
    warnings: List[str] = Field(
        default_factory=list,
        description="Security or parsing warnings (e.g. injection detected, compound policy loss)",
    )


class CreatePolicyFromNLRequest(BaseModel):
    """Request to create a policy from natural language and apply it to an agent."""

    natural_language: str = Field(
        ...,
        description="Natural language description of the spending policy",
    )
    agent_id: str = Field(
        ...,
        description="Agent ID to apply the policy to",
    )
    confirm: bool = Field(
        default=False,
        description="If true, immediately apply the policy. If false, return preview only.",
    )


class PolicyPreviewResponse(BaseModel):
    """Preview of a policy before applying."""

    parsed: ParsedPolicyResponse
    warnings: List[str] = []
    requires_confirmation: bool = True
    confirmation_message: str = ""


class PolicyCheckRequest(BaseModel):
    """Request to evaluate a hypothetical purchase against an agent policy."""

    agent_id: str
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD")
    merchant_id: Optional[str] = None
    merchant_category: Optional[str] = Field(
        default=None,
        description="Optional category name (e.g., 'gambling'). Prefer mcc_code when available.",
    )
    mcc_code: Optional[str] = Field(
        default=None,
        description="4-digit MCC code (e.g., 7995 for gambling).",
    )


class PolicyCheckResponse(BaseModel):
    allowed: bool
    reason: str
    policy_id: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/parse", response_model=ParsedPolicyResponse)
async def parse_natural_language_policy(
    request: ParsePolicyRequest,
):
    """
    Parse a natural language policy into structured format.

    This endpoint uses AI to convert human-readable spending policies
    into structured rules that can be enforced by the payment system.

    **Examples:**
    - "Allow max $500 per day on AWS and OpenAI, block gambling"
    - "Spend up to $100 per transaction, require approval over $500"
    - "Only allow cloud services with $1000 monthly limit"

    **Returns:** Structured policy with spending limits, restrictions, and rules.
    """
    try:
        # Import here to handle optional dependency
        from sardis_v2_core.nl_policy_parser import (
            NLPolicyParser,
            RegexPolicyParser,
            HAS_INSTRUCTOR,
        )

        # Try LLM parser first, fall back to regex
        if HAS_INSTRUCTOR:
            try:
                parser = NLPolicyParser()
                extracted = await parser.parse(request.natural_language)

                # Collect post-LLM validation warnings
                parse_warnings = getattr(parser, "_last_warnings", []) or []

                # Convert to response model
                response = ParsedPolicyResponse(
                    name=extracted.name,
                    description=extracted.description,
                    spending_limits=[
                        SpendingLimitResponse(
                            vendor_pattern=sl.vendor_pattern,
                            max_amount=sl.max_amount,
                            period=sl.period,
                            currency=sl.currency,
                        )
                        for sl in extracted.spending_limits
                    ],
                    requires_approval_above=extracted.requires_approval_above,
                    global_daily_limit=extracted.global_daily_limit,
                    global_monthly_limit=extracted.global_monthly_limit,
                    is_active=extracted.is_active,
                    agent_id=request.agent_id,
                    warnings=parse_warnings,
                )

                # Add category restrictions if present
                if extracted.category_restrictions:
                    response.category_restrictions = CategoryRestrictionsResponse(
                        allowed_categories=extracted.category_restrictions.allowed_categories,
                        blocked_categories=extracted.category_restrictions.blocked_categories,
                    )

                # Add time restrictions if present
                if extracted.time_restrictions:
                    response.time_restrictions = TimeRestrictionsResponse(
                        allowed_hours_start=extracted.time_restrictions.allowed_hours_start,
                        allowed_hours_end=extracted.time_restrictions.allowed_hours_end,
                        allowed_days=extracted.time_restrictions.allowed_days,
                        timezone=extracted.time_restrictions.timezone,
                    )

                # If agent_id provided, also generate policy_id
                if request.agent_id:
                    policy = parser.to_spending_policy(extracted, request.agent_id)
                    response.policy_id = policy.policy_id

                return response

            except Exception as e:
                # SECURITY: Structured logging for LLM parser failures.
                # An attacker may craft input that intentionally crashes the LLM
                # parser to force the weaker regex fallback path.
                import hashlib
                input_hash = hashlib.sha256(
                    request.natural_language.encode()
                ).hexdigest()[:16]
                logger.warning(
                    "SECURITY: LLM parser failed, falling back to regex. "
                    "input_hash=%s input_len=%d error_type=%s error=%s",
                    input_hash,
                    len(request.natural_language),
                    type(e).__name__,
                    str(e)[:200],
                )
                # Fall through to regex parser

        # Fallback: Use regex parser
        regex_parser = RegexPolicyParser()
        parsed = regex_parser.parse(request.natural_language)

        # SECURITY: Surface regex parser warnings (e.g. compound policy loss)
        regex_warnings = parsed.get("warnings", [])
        regex_warnings.append("Used regex fallback parser (LLM unavailable). Results may be incomplete.")

        return ParsedPolicyResponse(
            name="Parsed Policy",
            description=request.natural_language,
            spending_limits=[
                SpendingLimitResponse(**sl)
                for sl in parsed.get("spending_limits", [])
            ],
            category_restrictions=CategoryRestrictionsResponse(
                blocked_categories=parsed.get("blocked_categories", []),
            ) if parsed.get("blocked_categories") else None,
            requires_approval_above=parsed.get("requires_approval_above"),
            agent_id=request.agent_id,
            warnings=regex_warnings,
        )

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Policy parsing not available: {e}",
        )


@router.post("/preview", response_model=PolicyPreviewResponse)
async def preview_policy_from_nl(
    request: CreatePolicyFromNLRequest,
):
    """
    Preview a policy from natural language before applying.

    This is a safety feature that shows what the AI understood from your
    natural language input, allowing you to confirm before applying.

    **Human-in-the-loop protection:**
    - Prevents misinterpretation (e.g., "$500" parsed as "$5000")
    - Shows blocked categories clearly
    - Highlights any unusual restrictions
    """
    # Parse the policy
    parsed = await parse_natural_language_policy(
        ParsePolicyRequest(
            natural_language=request.natural_language,
            agent_id=request.agent_id,
        )
    )

    # Generate warnings for potential issues
    warnings = []

    # Check for high limits
    for limit in parsed.spending_limits:
        if limit.max_amount > 10000:
            warnings.append(
                f"High spending limit detected: ${limit.max_amount} {limit.period} for {limit.vendor_pattern}"
            )

    if parsed.global_daily_limit and parsed.global_daily_limit > 10000:
        warnings.append(f"High global daily limit: ${parsed.global_daily_limit}")

    if parsed.global_monthly_limit and parsed.global_monthly_limit > 100000:
        warnings.append(f"High global monthly limit: ${parsed.global_monthly_limit}")

    # Check for missing blocks
    if not parsed.category_restrictions or not parsed.category_restrictions.blocked_categories:
        warnings.append("No blocked categories specified. Consider blocking 'gambling' and 'adult' categories.")

    # Generate confirmation message
    limit_summary = []
    for limit in parsed.spending_limits:
        limit_summary.append(f"${limit.max_amount} {limit.period} on {limit.vendor_pattern}")

    blocked = []
    if parsed.category_restrictions and parsed.category_restrictions.blocked_categories:
        blocked = parsed.category_restrictions.blocked_categories

    confirmation_message = (
        f"Policy Summary:\n"
        f"- Spending limits: {', '.join(limit_summary) if limit_summary else 'None specified'}\n"
        f"- Blocked categories: {', '.join(blocked) if blocked else 'None'}\n"
        f"- Requires approval above: ${parsed.requires_approval_above if parsed.requires_approval_above else 'N/A'}\n"
        f"\nDo you want to apply this policy to agent {request.agent_id}?"
    )

    return PolicyPreviewResponse(
        parsed=parsed,
        warnings=warnings,
        requires_confirmation=True,
        confirmation_message=confirmation_message,
    )


@router.post("/apply", response_model=dict)
async def apply_policy_from_nl(
    request: CreatePolicyFromNLRequest,
    http_request: Request,
    deps: PolicyDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Parse natural language and apply policy to an agent.

    **IMPORTANT:** Set `confirm: true` to actually apply the policy.
    Otherwise, use `/preview` first to see what will be applied.

    **Safety features:**
    - Requires explicit confirmation
    - Returns the applied policy for verification
    - Logs all policy changes for audit
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set 'confirm: true' or use /preview first.",
        )

    agent = await deps.agent_repo.get(request.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    idem_key = get_idempotency_key(http_request)
    if not idem_key:
        import hashlib
        idem_key = hashlib.sha256(f"{request.agent_id}:{request.natural_language}".encode()).hexdigest()

    async def _apply() -> tuple[int, object]:
        from sardis_v2_core.nl_policy_parser import create_policy_parser
        from sardis_v2_core.spending_policy import SpendingPolicy, TimeWindowLimit, MerchantRule, TrustLevel

        parser = create_policy_parser(use_llm=True)
        if hasattr(parser, "parse_and_convert"):
            policy = await parser.parse_and_convert(request.natural_language, request.agent_id)  # type: ignore[attr-defined]
        else:
            # Regex fallback: build a reasonable SpendingPolicy
            parsed = parser.parse(request.natural_language)  # type: ignore[attr-defined]
            policy = SpendingPolicy(
                agent_id=request.agent_id,
                trust_level=TrustLevel.MEDIUM,
            )

            for sl in parsed.get("spending_limits", []):
                vendor_pattern = sl.get("vendor_pattern") or "any"
                max_amount = Decimal(str(sl.get("max_amount", "0") or "0"))
                period = sl.get("period") or "daily"
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
                if period in ("daily", "weekly", "monthly") and max_amount > 0:
                    if period == "daily" and not policy.daily_limit:
                        policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=max_amount)
                    if period == "weekly" and not policy.weekly_limit:
                        policy.weekly_limit = TimeWindowLimit(window_type="weekly", limit_amount=max_amount)
                    if period == "monthly" and not policy.monthly_limit:
                        policy.monthly_limit = TimeWindowLimit(window_type="monthly", limit_amount=max_amount)

            blocked = parsed.get("blocked_categories", []) or []
            for cat in blocked:
                c = str(cat).strip().lower()
                if c and c not in policy.blocked_merchant_categories:
                    policy.blocked_merchant_categories.append(c)

        # In production, this would save to database
        await deps.policy_store.set_policy(request.agent_id, policy)

        logger.info(
            f"Policy applied: agent_id={request.agent_id}, "
            f"policy_id={policy.policy_id}, "
            f"limits={policy.limit_per_tx}/{policy.limit_total}"
        )

        return 200, {
            "success": True,
            "policy_id": policy.policy_id,
            "agent_id": policy.agent_id,
            "trust_level": policy.trust_level.value,
            "limit_per_tx": str(policy.limit_per_tx),
            "limit_total": str(policy.limit_total),
            "daily_limit": str(policy.daily_limit.limit_amount) if policy.daily_limit else None,
            "weekly_limit": str(policy.weekly_limit.limit_amount) if policy.weekly_limit else None,
            "monthly_limit": str(policy.monthly_limit.limit_amount) if policy.monthly_limit else None,
            "merchant_rules_count": len(policy.merchant_rules),
            "require_preauth": policy.require_preauth,
            "message": f"Policy {policy.policy_id} applied to agent {request.agent_id}",
        }
    try:
        return await run_idempotent(
            request=http_request,
            principal=principal,
            operation="policies.apply",
            key=str(idem_key),
            payload=request.model_dump(),
            fn=_apply,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Policy parsing not available: {e}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply policy: {str(e)}",
        )


@router.get("/examples", response_model=List[dict])
async def get_policy_examples():
    """
    Get example natural language policies.

    These examples demonstrate the supported policy syntax and can be
    used as templates for creating your own policies.
    """
    return [
        {
            "description": "Basic cloud spending policy",
            "natural_language": "Allow max $500 per day on AWS and OpenAI, block gambling",
            "use_case": "AI agent that needs to purchase cloud compute and API credits",
        },
        {
            "description": "Conservative spending with approval",
            "natural_language": "Spend up to $100 per transaction, require approval over $500, max $1000 monthly",
            "use_case": "Low-trust agent with spending oversight",
        },
        {
            "description": "Cloud-only policy",
            "natural_language": "Only allow cloud services (AWS, GCP, Azure, DigitalOcean, Vercel) with $2000 monthly limit",
            "use_case": "DevOps agent restricted to infrastructure spending",
        },
        {
            "description": "Business hours only",
            "natural_language": "Allow $200 daily during business hours (9am-5pm weekdays), block adult and gambling",
            "use_case": "Agent that should only operate during work hours",
        },
        {
            "description": "SaaS subscription manager",
            "natural_language": "Allow Slack, Notion, GitHub, Figma up to $50 each monthly, total cap $500",
            "use_case": "Agent managing team software subscriptions",
        },
        {
            "description": "AI API spending",
            "natural_language": "OpenAI and Anthropic only, max $1000 per month combined, $100 per transaction limit",
            "use_case": "Agent that uses LLM APIs for its operations",
        },
    ]


@router.get("/{agent_id}", response_model=dict)
async def get_active_policy(
    agent_id: str,
    deps: PolicyDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    agent = await deps.agent_repo.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    policy = await deps.policy_store.fetch_policy(agent_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No policy for agent")
    return {
        "agent_id": agent_id,
        "policy_id": policy.policy_id,
        "trust_level": policy.trust_level.value,
        "limit_per_tx": str(policy.limit_per_tx),
        "limit_total": str(policy.limit_total),
        "blocked_merchant_categories": policy.blocked_merchant_categories,
        "merchant_rules_count": len(policy.merchant_rules),
        "require_preauth": policy.require_preauth,
    }


@router.post("/check", response_model=PolicyCheckResponse)
async def check_policy(
    request: PolicyCheckRequest,
    deps: PolicyDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Evaluate a hypothetical purchase against the agent's active policy.

    For demo purposes, currency is treated as 1:1 with the policy's default currency.
    """
    agent = await deps.agent_repo.get(request.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    policy = await deps.policy_store.fetch_policy(request.agent_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No policy for agent")

    ok, reason = policy.validate_payment(
        amount=request.amount,
        fee=Decimal("0"),
        merchant_id=request.merchant_id,
        merchant_category=request.merchant_category,
        mcc_code=request.mcc_code,
    )
    return PolicyCheckResponse(allowed=ok, reason=reason, policy_id=policy.policy_id)
