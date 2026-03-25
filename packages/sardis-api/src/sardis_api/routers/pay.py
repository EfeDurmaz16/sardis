"""Unified payment endpoint — the simplest way to pay with Sardis.

POST /api/v2/pay
    → validates inputs
    → auto-routes to cheapest chain (Phase 2) or uses explicit chain
    → builds a mandate chain
    → calls PaymentOrchestrator.execute_chain()
    → returns a PaymentResult with status enum + route metadata

Phase 2 additions:
    - `chain` is now optional — omit it to let Sardis pick the cheapest route
    - Auto-routing uses LiquidityRouter.find_best_route() across supported chains
    - Route selection: lowest (gas + bridge_fee + slippage)
    - Fallback: if best route fails, tries next cheapest
    - Response includes `route` field showing selected chain + provider
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sardis_v2_core.mandates import (
    CartMandate,
    IntentMandate,
    MandateChain,
    PaymentMandate,
)
from sardis_v2_core.orchestrator import (
    ChainExecutionError,
    ComplianceViolationError,
    KYAViolationError,
    MandateViolationError,
    PaymentOrchestrator,
    PolicyViolationError,
)
from sardis_v2_core.policy_explainer import explain_denial

from sardis_api.authz import Principal, require_principal

router = APIRouter()
logger = logging.getLogger(__name__)

# Chains to evaluate during auto-routing, ordered by preference.
# The router will quote all of them and pick the cheapest.
AUTO_ROUTE_CHAINS = ["base", "tempo", "ethereum", "arbitrum", "optimism"]


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@dataclass
class PayDependencies:
    orchestrator: PaymentOrchestrator


def get_deps() -> PayDependencies:
    raise NotImplementedError("Must be wired via dependency_overrides")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class PayStatus(str, Enum):
    pending = "pending"
    confirming = "confirming"
    completed = "completed"
    failed = "failed"
    blocked = "blocked"


class PayRequest(BaseModel):
    to: str = Field(..., description="Recipient address or merchant domain")
    amount: str = Field(..., description="Payment amount (e.g. '25.00')")
    currency: str = Field(default="USDC", description="Token / currency")
    chain: str | None = Field(
        default=None,
        description=(
            "Target blockchain. If omitted, Sardis auto-selects the "
            "cheapest route across supported chains."
        ),
    )
    mandate_id: str | None = Field(default=None, description="Spending mandate ID")


class PolicyExplanationResponse(BaseModel):
    allowed: bool
    summary: str
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    suggested_action: str | None = None
    reason_code: str | None = None


class RouteInfo(BaseModel):
    """Metadata about the route selected for this payment."""
    chain: str
    provider: str
    estimated_fee_bps: int = 0
    route_type: str = "direct"
    auto_routed: bool = False


class PayResponse(BaseModel):
    status: PayStatus
    tx_hash: str | None = None
    ledger_tx_id: str | None = None
    chain: str | None = None
    message: str | None = None
    mandate_id: str | None = None
    route: RouteInfo | None = None
    policy_explanation: PolicyExplanationResponse | None = None


# ---------------------------------------------------------------------------
# Auto-routing helpers
# ---------------------------------------------------------------------------


async def _find_best_chain(
    currency: str, amount: Decimal
) -> list[dict[str, Any]]:
    """Rank chains by total cost (gas + bridge fee + slippage).

    Returns a list of dicts sorted by estimated cost, each containing:
      - chain: str
      - provider: str
      - estimated_fee_bps: int
      - route_type: str
    """
    try:
        from sardis_chain.liquidity_router import LiquidityRouter

        router_instance = LiquidityRouter()
    except ImportError:
        logger.warning("LiquidityRouter not available — defaulting to base")
        return [{"chain": "base", "provider": "default", "estimated_fee_bps": 0, "route_type": "direct"}]

    candidates: list[dict[str, Any]] = []
    for chain in AUTO_ROUTE_CHAINS:
        try:
            route = await router_instance.find_best_route(
                from_token=currency,
                to_token=currency,
                amount=amount,
                from_chain=chain,
                to_chain=chain,
            )
            candidates.append({
                "chain": route.chain,
                "provider": route.provider,
                "estimated_fee_bps": route.estimated_fee_bps,
                "route_type": route.route_type,
            })
        except Exception as e:
            logger.debug("Auto-route quote failed for %s: %s", chain, e)

    if not candidates:
        # Absolute fallback
        candidates.append({
            "chain": "base",
            "provider": "fallback",
            "estimated_fee_bps": 0,
            "route_type": "direct",
        })

    # Sort by fee (lowest first)
    candidates.sort(key=lambda c: c["estimated_fee_bps"])
    return candidates


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PayResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a payment",
    description=(
        "Unified payment endpoint. Validates inputs, enforces policy, "
        "and executes on-chain. If `chain` is omitted, Sardis auto-selects "
        "the cheapest route across supported chains."
    ),
    tags=["pay"],
)
async def pay(
    body: PayRequest,
    principal: Principal = Depends(require_principal),
    deps: PayDependencies = Depends(get_deps),
) -> PayResponse:
    # Parse amount
    try:
        amount = Decimal(body.amount)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid amount: {body.amount!r}",
        )

    # ── Phase 2: resolve chain ──────────────────────────────────────
    # Iron rule: explicit chain always wins.
    auto_routed = body.chain is None
    if auto_routed:
        ranked_chains = await _find_best_chain(body.currency, amount)
    else:
        ranked_chains = [{
            "chain": body.chain,
            "provider": "explicit",
            "estimated_fee_bps": 0,
            "route_type": "direct",
        }]

    # Build a minimal mandate chain for the orchestrator
    mandate_id = body.mandate_id or f"pay_{principal.subject_id}"

    # Try each candidate chain in order (cheapest first).
    last_error: Exception | None = None
    for candidate in ranked_chains:
        selected_chain = candidate["chain"]

        intent = IntentMandate(
            mandate_id=f"intent_{mandate_id}",
            from_agent=principal.subject_id,
            to_merchant=body.to,
            amount_minor=int(amount * 100),
            currency=body.currency,
            purpose=f"sardis.pay to {body.to}",
        )
        cart = CartMandate(
            mandate_id=f"cart_{mandate_id}",
            items=[{
                "merchant": body.to,
                "amount_minor": int(amount * 100),
                "currency": body.currency,
            }],
            total_minor=int(amount * 100),
            currency=body.currency,
        )
        payment = PaymentMandate(
            mandate_id=mandate_id,
            from_agent=principal.subject_id,
            to_merchant=body.to,
            amount_minor=int(amount * 100),
            currency=body.currency,
            chain=selected_chain,
            token=body.currency,
        )
        chain = MandateChain(intent=intent, cart=cart, payment=payment)

        route_info = RouteInfo(
            chain=selected_chain,
            provider=candidate["provider"],
            estimated_fee_bps=candidate["estimated_fee_bps"],
            route_type=candidate["route_type"],
            auto_routed=auto_routed,
        )

        try:
            result = await deps.orchestrator.execute_chain(chain)
            return PayResponse(
                status=PayStatus.completed,
                tx_hash=result.chain_tx_hash,
                ledger_tx_id=result.ledger_tx_id,
                chain=result.chain or selected_chain,
                mandate_id=result.mandate_id,
                route=route_info,
            )
        except (PolicyViolationError, MandateViolationError, KYAViolationError, ComplianceViolationError) as exc:
            # Policy / compliance errors are not retryable on a different chain
            _reason_attr = {
                PolicyViolationError: "rule_id",
                MandateViolationError: "error_code",
                KYAViolationError: "reason",
                ComplianceViolationError: "rule_id",
            }
            default_code = type(exc).__name__.replace("Error", "").lower() + "_violation"
            reason = getattr(exc, _reason_attr.get(type(exc), "rule_id"), None) or default_code
            explanation = explain_denial(reason)
            return PayResponse(
                status=PayStatus.blocked,
                message=str(exc),
                mandate_id=mandate_id,
                route=route_info,
                policy_explanation=PolicyExplanationResponse(**explanation.to_dict()),
            )
        except ChainExecutionError as exc:
            last_error = exc
            if auto_routed:
                logger.warning(
                    "Chain execution failed on %s (provider=%s), trying next route: %s",
                    selected_chain, candidate["provider"], exc,
                )
                continue
            # Explicit chain — no fallback
            return PayResponse(
                status=PayStatus.failed,
                message=str(exc),
                mandate_id=mandate_id,
                route=route_info,
            )
        except Exception as exc:
            last_error = exc
            logger.exception("Unexpected error in /pay on chain %s: %s", selected_chain, exc)
            if auto_routed:
                continue
            return PayResponse(
                status=PayStatus.failed,
                message="Internal error",
                mandate_id=mandate_id,
                route=route_info,
            )

    # All candidates exhausted (auto-routing only reaches here)
    return PayResponse(
        status=PayStatus.failed,
        message=f"All routes exhausted. Last error: {last_error}" if last_error else "No viable route found",
        mandate_id=mandate_id,
    )
