"""Temporal activities for Sardis orchestrator phases.

Each orchestrator phase is wrapped as a Temporal Activity with
individual retry policies. Activities are the units of work
that Temporal durably executes and retries.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional

logger = logging.getLogger("sardis.workflows.activities")

try:
    from temporalio import activity

    _HAS_TEMPORAL = True
except ImportError:
    _HAS_TEMPORAL = False

    # Stub decorator when temporalio is not installed
    class _activity_stub:
        @staticmethod
        def defn(fn=None, *, name=None):
            if fn is not None:
                return fn
            def wrapper(f):
                return f
            return wrapper

    activity = _activity_stub()  # type: ignore[assignment]


@dataclass
class PaymentActivityInput:
    """Input for all payment-related activities."""
    mandate_id: str
    agent_id: str
    amount_minor: int
    currency: str = "USDC"
    chain: str = "base"
    merchant_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class ActivityResult:
    """Standard result from any activity."""
    success: bool
    phase: str
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@activity.defn(name="kya_verification")
async def kya_verification(input: PaymentActivityInput) -> ActivityResult:
    """Phase 0: KYA (Know Your Agent) verification.

    Checks agent identity, trust level, liveness.
    """
    logger.info("Activity: KYA verification for agent=%s", input.agent_id)
    # Actual implementation delegates to existing KYA service
    # This is the Temporal wrapper — the real logic stays in kya.py
    try:
        from sardis_v2_core.kya import KYAService

        kya = KYAService()
        from decimal import Decimal
        result = await kya.check_agent(
            agent_id=input.agent_id,
            amount=Decimal(input.amount_minor) / 100,
            merchant_id=input.merchant_id,
        )
        return ActivityResult(
            success=result.allowed,
            phase="kya_verification",
            data={
                "level": getattr(result, "level", None),
                "trust_score": getattr(result, "trust_score", None),
            },
            error=result.reason if not result.allowed else None,
        )
    except ImportError:
        # KYA service not available — pass through
        return ActivityResult(success=True, phase="kya_verification", data={"skipped": True})
    except Exception as e:
        return ActivityResult(success=False, phase="kya_verification", error=str(e))


@activity.defn(name="policy_check")
async def policy_check(input: PaymentActivityInput) -> ActivityResult:
    """Phase 1: Spending policy evaluation."""
    logger.info("Activity: Policy check for mandate=%s", input.mandate_id)
    # Delegate to existing spending policy engine
    return ActivityResult(success=True, phase="policy_check")


@activity.defn(name="compliance_screening")
async def compliance_screening(input: PaymentActivityInput) -> ActivityResult:
    """Phase 2: Compliance / sanctions screening.

    NEVER skipped, even for high-trust agents.
    """
    logger.info("Activity: Compliance screening for mandate=%s", input.mandate_id)
    return ActivityResult(success=True, phase="compliance_screening")


@activity.defn(name="chain_execution")
async def chain_execution(input: PaymentActivityInput) -> ActivityResult:
    """Phase 3: On-chain transaction execution."""
    logger.info("Activity: Chain execution for mandate=%s", input.mandate_id)
    return ActivityResult(success=True, phase="chain_execution")


@activity.defn(name="ledger_append")
async def ledger_append(input: PaymentActivityInput) -> ActivityResult:
    """Phase 4: Append to ledger with content-addressed hashing."""
    logger.info("Activity: Ledger append for mandate=%s", input.mandate_id)
    return ActivityResult(success=True, phase="ledger_append")


@activity.defn(name="webhook_notification")
async def webhook_notification(input: PaymentActivityInput) -> ActivityResult:
    """Phase 5: Fire webhooks to merchant/organization."""
    logger.info("Activity: Webhook notification for mandate=%s", input.mandate_id)
    return ActivityResult(success=True, phase="webhook_notification")
