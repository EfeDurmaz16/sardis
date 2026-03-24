"""Unified payment endpoint — the simplest way to pay with Sardis.

POST /api/v2/pay
    → validates inputs
    → builds a mandate chain
    → calls PaymentOrchestrator.execute_chain()
    → returns a PaymentResult with status enum
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

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
    chain: str = Field(default="base", description="Target blockchain")
    mandate_id: str | None = Field(default=None, description="Spending mandate ID")


class PolicyExplanationResponse(BaseModel):
    allowed: bool
    summary: str
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    suggested_action: str | None = None
    reason_code: str | None = None


class PayResponse(BaseModel):
    status: PayStatus
    tx_hash: str | None = None
    ledger_tx_id: str | None = None
    chain: str | None = None
    message: str | None = None
    mandate_id: str | None = None
    policy_explanation: PolicyExplanationResponse | None = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PayResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a payment",
    description="Unified payment endpoint. Validates inputs, enforces policy, and executes on-chain.",
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

    # Build a minimal mandate chain for the orchestrator
    mandate_id = body.mandate_id or f"pay_{principal.subject_id}"

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
        chain=body.chain,
        token=body.currency,
    )
    chain = MandateChain(intent=intent, cart=cart, payment=payment)

    try:
        result = await deps.orchestrator.execute_chain(chain)
        return PayResponse(
            status=PayStatus.completed,
            tx_hash=result.chain_tx_hash,
            ledger_tx_id=result.ledger_tx_id,
            chain=result.chain,
            mandate_id=result.mandate_id,
        )
    except PolicyViolationError as exc:
        reason = getattr(exc, "rule_id", None) or "policy_violation"
        explanation = explain_denial(reason)
        return PayResponse(
            status=PayStatus.blocked,
            message=str(exc),
            mandate_id=mandate_id,
            policy_explanation=PolicyExplanationResponse(**explanation.to_dict()),
        )
    except MandateViolationError as exc:
        reason = getattr(exc, "error_code", None) or "mandate_violation"
        explanation = explain_denial(reason)
        return PayResponse(
            status=PayStatus.blocked,
            message=str(exc),
            mandate_id=mandate_id,
            policy_explanation=PolicyExplanationResponse(**explanation.to_dict()),
        )
    except KYAViolationError as exc:
        reason = getattr(exc, "reason", None) or "kya_violation"
        explanation = explain_denial(reason)
        return PayResponse(
            status=PayStatus.blocked,
            message=str(exc),
            mandate_id=mandate_id,
            policy_explanation=PolicyExplanationResponse(**explanation.to_dict()),
        )
    except ComplianceViolationError as exc:
        reason = getattr(exc, "rule_id", None) or "compliance_violation"
        explanation = explain_denial(reason)
        return PayResponse(
            status=PayStatus.blocked,
            message=str(exc),
            mandate_id=mandate_id,
            policy_explanation=PolicyExplanationResponse(**explanation.to_dict()),
        )
    except ChainExecutionError as exc:
        return PayResponse(
            status=PayStatus.failed,
            message=str(exc),
            mandate_id=mandate_id,
        )
    except Exception as exc:
        logger.exception("Unexpected error in /pay: %s", exc)
        return PayResponse(
            status=PayStatus.failed,
            message="Internal error",
            mandate_id=mandate_id,
        )
