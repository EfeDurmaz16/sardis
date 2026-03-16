"""Composable pre-execution pipeline for authorization hooks.

Before any payment intent reaches chain execution, it passes through an
ordered pipeline of async hooks (AGIT policy, KYA trust scoring, FIDES
identity, mandate validation, etc.).  The pipeline is fail-closed: a
rejection or exception in any hook short-circuits the remaining hooks
and returns a reject decision immediately.

Usage::

    from sardis_v2_core.pre_execution_pipeline import (
        HookResult,
        PreExecutionHook,
        PreExecutionPipeline,
        make_mandate_validation_hook,
    )

    async def spending_policy_hook(intent) -> HookResult:
        if intent.amount > limit:
            return HookResult(decision="reject", reason="over daily limit")
        return HookResult(decision="approve")

    pipeline = PreExecutionPipeline(hooks=[spending_policy_hook])
    result = await pipeline.evaluate(intent)

    # Add mandate validation:
    mandate_hook = make_mandate_validation_hook(mandate_lookup)
    pipeline.add_hook(mandate_hook)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class HookResult:
    """Outcome of a single pre-execution hook evaluation."""

    decision: Literal["approve", "reject", "skip"]
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


# Type alias: a hook is an async callable that receives an intent and
# returns a HookResult.
PreExecutionHook = Callable[[Any], Coroutine[Any, Any, HookResult]]


class PreExecutionPipeline:
    """Ordered pipeline of async authorization hooks.

    Hooks are evaluated sequentially.  The first ``reject`` short-circuits
    and the pipeline returns immediately.  ``skip`` results are ignored;
    the pipeline continues to the next hook.  If all hooks approve (or
    skip), the pipeline returns an overall ``approve``.

    If a hook raises an exception the pipeline fails closed, returning a
    ``reject`` with the error message.
    """

    def __init__(self, hooks: list[PreExecutionHook] | None = None) -> None:
        self._hooks: list[PreExecutionHook] = list(hooks) if hooks else []

    def add_hook(self, hook: PreExecutionHook) -> None:
        """Append a hook to the end of the pipeline."""
        self._hooks.append(hook)

    async def evaluate(self, intent: Any) -> HookResult:
        """Run all hooks against *intent* and return the aggregate decision."""
        for hook in self._hooks:
            try:
                result = await hook(intent)
            except Exception as exc:  # noqa: BLE001
                return HookResult(
                    decision="reject",
                    reason=f"Hook error: {exc}",
                )
            if result.decision == "reject":
                return result
            # "skip" and "approve" both allow the pipeline to continue.
        return HookResult(decision="approve")


def make_mandate_validation_hook(
    mandate_lookup: Any,
) -> PreExecutionHook:
    """Create a pre-execution hook that validates payments against spending mandates.

    The returned hook:
    1. Looks up an active spending mandate for the intent's agent_id or wallet_id.
    2. If a mandate exists, validates: status is active, merchant within scope,
       amount within limits, rail permitted.
    3. If the mandate check fails, rejects the payment.
    4. If the mandate has an approval_threshold and amount exceeds it,
       rejects with a ``requires_approval`` evidence flag.
    5. Records ``mandate_id`` in the evidence dict for downstream use.
    6. If no mandate exists, skips (backward compatible).

    Args:
        mandate_lookup: An object implementing ``get_active_mandate(agent_id, wallet_id)``
            that returns a SpendingMandate or None.

    Returns:
        An async hook function suitable for ``PreExecutionPipeline.add_hook()``.
    """

    async def _mandate_validation_hook(intent: Any) -> HookResult:
        agent_id = getattr(intent, "agent_id", None) or getattr(intent, "from_agent", None)
        wallet_id = getattr(intent, "wallet_id", None) or getattr(intent, "subject", None)

        mandate = await mandate_lookup.get_active_mandate(
            agent_id=agent_id,
            wallet_id=wallet_id,
        )

        if mandate is None:
            # No mandate found — pass through for backward compatibility
            return HookResult(
                decision="skip",
                reason="no_active_mandate",
                evidence={"mandate_id": None},
            )

        from decimal import Decimal as _Dec

        amount = getattr(intent, "amount", None) or getattr(intent, "amount_minor", 0)
        merchant = getattr(intent, "merchant_id", None) or getattr(intent, "destination", None)
        rail = getattr(intent, "rail", None)
        chain = getattr(intent, "chain", None)
        token = getattr(intent, "token", None)

        check = mandate.check_payment(
            amount=_Dec(str(amount)),
            merchant=merchant,
            rail=rail,
            chain=chain,
            token=token,
        )

        if not check.approved:
            return HookResult(
                decision="reject",
                reason=check.reason,
                evidence={
                    "mandate_id": mandate.id,
                    "error_code": check.error_code,
                },
            )

        if check.requires_approval:
            return HookResult(
                decision="reject",
                reason=(
                    f"Payment of {amount} requires human approval "
                    f"(threshold: {mandate.approval_threshold})"
                ),
                evidence={
                    "mandate_id": mandate.id,
                    "requires_approval": True,
                    "approval_threshold": str(mandate.approval_threshold),
                },
            )

        return HookResult(
            decision="approve",
            reason="mandate_check_passed",
            evidence={
                "mandate_id": mandate.id,
                "mandate_version": check.mandate_version,
            },
        )

    return _mandate_validation_hook
