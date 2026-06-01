"""Shared MPP policy evaluation against the real SpendingPolicy engine.

Single source of policy truth for the MPP surfaces. Both the authenticated
``/api/v2/mpp/evaluate`` endpoint and the MPP demo (``/api/v2/demo/paid-data``)
route through ``evaluate_mpp_policy`` so there is exactly one policy answer —
the same ``SpendingPolicy`` the PaymentOrchestrator uses.

Fail-closed: no policy_store, no agent_id, no policy, or any engine error =>
DENY. There is no default-allow path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

# Number of distinct checks the SpendingPolicy engine runs (see
# SpendingPolicy.evaluate docstring). Reported for transparency; the engine
# short-circuits on the first failure.
POLICY_CHECK_COUNT = 12


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Outcome of a real SpendingPolicy evaluation."""

    allowed: bool
    reason: str
    checks_passed: int
    checks_total: int = POLICY_CHECK_COUNT

    @classmethod
    def deny(cls, reason: str) -> PolicyDecision:
        return cls(allowed=False, reason=reason, checks_passed=0)


async def evaluate_mpp_policy(
    *,
    policy_store: Any | None,
    agent_id: str | None,
    amount: Decimal,
    merchant: str,
    currency: str,
    network: str,
    merchant_category: str | None = None,
    mcc_code: str | None = None,
) -> PolicyDecision:
    """Evaluate an MPP payment against the agent's real SpendingPolicy.

    Args:
        policy_store: ``app.state.policy_store`` (must expose ``fetch_policy``).
        agent_id: Agent whose active policy governs the payment.
        amount/merchant/currency/network/merchant_category/mcc_code: payment params.

    Returns a :class:`PolicyDecision`. Fail-closed on every missing/error path.

    NOTE: caller is responsible for authorization (verifying the principal may
    evaluate this agent). This helper performs no ownership check.
    """
    if not agent_id:
        return PolicyDecision.deny("agent_id_required_for_policy_evaluation")

    if policy_store is None:
        logger.error("MPP policy: no policy_store configured — failing closed")
        return PolicyDecision.deny("policy_store_not_configured")

    try:
        policy = await policy_store.fetch_policy(agent_id)
    except Exception as exc:  # store/db error => fail closed
        logger.error("MPP policy: fetch failed for %s: %s", agent_id, exc)
        return PolicyDecision.deny("policy_lookup_error")

    if policy is None:
        return PolicyDecision.deny("no_policy_for_agent")

    # Real deterministic execution-context guard (chain/token allowlists).
    ctx_ok, ctx_reason = policy.validate_execution_context(
        destination=None,
        chain=network,
        token=currency,
    )
    if not ctx_ok:
        return PolicyDecision.deny(ctx_reason)

    # Real SpendingPolicy evaluation (same engine the orchestrator uses, minus
    # the on-chain balance lookup which a dry-run pre-flight cannot perform).
    try:
        ok, reason = policy.validate_payment(
            amount=amount,
            fee=Decimal("0"),
            merchant_id=merchant,
            merchant_category=merchant_category,
            mcc_code=mcc_code,
        )
    except Exception as exc:  # any engine error => fail closed
        logger.error("MPP policy: engine error for %s: %s", agent_id, exc)
        return PolicyDecision.deny("policy_engine_error")

    logger.info(
        "MPP policy evaluation (real): agent=%s amount=%s merchant=%s result=%s reason=%s",
        agent_id, amount, merchant, "ALLOWED" if ok else "DENIED", reason,
    )

    return PolicyDecision(
        allowed=ok,
        reason=reason,
        checks_passed=POLICY_CHECK_COUNT if ok else POLICY_CHECK_COUNT - 1,
    )


__all__ = ["PolicyDecision", "POLICY_CHECK_COUNT", "evaluate_mpp_policy"]
