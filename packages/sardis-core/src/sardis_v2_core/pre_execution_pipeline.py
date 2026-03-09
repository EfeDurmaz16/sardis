"""Composable pre-execution pipeline for authorization hooks.

Before any payment intent reaches chain execution, it passes through an
ordered pipeline of async hooks (AGIT policy, KYA trust scoring, FIDES
identity, etc.).  The pipeline is fail-closed: a rejection or exception
in any hook short-circuits the remaining hooks and returns a reject
decision immediately.

Usage::

    from sardis_v2_core.pre_execution_pipeline import (
        HookResult,
        PreExecutionHook,
        PreExecutionPipeline,
    )

    async def spending_policy_hook(intent) -> HookResult:
        if intent.amount > limit:
            return HookResult(decision="reject", reason="over daily limit")
        return HookResult(decision="approve")

    pipeline = PreExecutionPipeline(hooks=[spending_policy_hook])
    result = await pipeline.evaluate(intent)
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
