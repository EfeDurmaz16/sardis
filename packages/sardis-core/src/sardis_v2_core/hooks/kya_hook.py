"""KYA trust-scoring hook for PreExecutionPipeline.

Checks that the agent's trust score meets the minimum threshold required
for payment execution.  Extracted from ControlPlane's trust_scorer usage
(which feeds into KYA tier limits).

Usage::

    from sardis_v2_core.hooks import create_kya_hook

    hook = create_kya_hook(trust_scorer, min_trust=0.3)
    pipeline.add_hook(hook)
"""
from __future__ import annotations

import logging
from typing import Any

from ..pre_execution_pipeline import HookResult

logger = logging.getLogger("sardis.core.hooks.kya")


def create_kya_hook(
    trust_scorer: Any,
    min_trust: float = 0.3,
    fail_open: bool = True,
):
    """Factory: return an async hook that gates on KYA trust score.

    Args:
        trust_scorer: A ``TrustScorer`` (or compatible) instance whose
            ``calculate_trust(agent_id=..., agent_did=...)`` method returns
            a ``TrustScore`` with ``.overall`` (float) and ``.tier``
            attributes.
        min_trust: Minimum overall trust score required.  Intents from
            agents below this threshold are rejected.
        fail_open: When *True* (default, matching existing ControlPlane
            behavior), trust-scoring errors are logged but do not reject
            the intent.  When *False*, any error rejects.
    """

    async def kya_hook(intent: Any) -> HookResult:
        agent_id = getattr(intent, "agent_id", None) or ""
        metadata = getattr(intent, "metadata", {}) or {}
        agent_did = metadata.get("fides_did")

        if not agent_id:
            return HookResult(decision="skip", reason="no agent_id on intent")

        try:
            trust_score = await trust_scorer.calculate_trust(
                agent_id=agent_id,
                agent_did=agent_did,
            )
        except Exception as exc:
            if fail_open:
                logger.warning(
                    "KYA trust scoring failed for agent=%s: %s (non-blocking)",
                    agent_id, exc,
                )
                return HookResult(
                    decision="skip",
                    reason=f"KYA trust scoring unavailable: {exc}",
                )
            logger.error(
                "KYA trust scoring failed for agent=%s: %s (fail-closed)",
                agent_id, exc,
            )
            return HookResult(
                decision="reject",
                reason=f"KYA trust scoring unavailable: {exc}",
            )

        if trust_score.overall < min_trust:
            logger.warning(
                "KYA trust insufficient for agent=%s: %.2f < %.2f",
                agent_id, trust_score.overall, min_trust,
            )
            return HookResult(
                decision="reject",
                reason=f"trust_score_insufficient: {trust_score.overall:.2f} < {min_trust}",
                evidence={
                    "trust_score": trust_score.overall,
                    "trust_tier": trust_score.tier.value,
                    "min_required": min_trust,
                },
            )

        return HookResult(
            decision="approve",
            evidence={
                "trust_score": trust_score.overall,
                "trust_tier": trust_score.tier.value,
            },
        )

    kya_hook.__name__ = "kya_hook"
    return kya_hook
