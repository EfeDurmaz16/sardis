"""FIDES trust-gate hook for PreExecutionPipeline.

Checks the FIDES trust score for an agent's DID before allowing payment
execution.  Extracted from ControlPlane step 1.5a.

The hook is only active when the intent carries a ``fides_did`` in its
metadata.  If no DID is present the hook skips (non-blocking).

Usage::

    from sardis_v2_core.hooks import create_fides_hook

    hook = create_fides_hook(trust_scorer, min_trust=0.3)
    pipeline.add_hook(hook)
"""
from __future__ import annotations

import logging
from typing import Any

from ..pre_execution_pipeline import HookResult

logger = logging.getLogger("sardis.core.hooks.fides")


def create_fides_hook(
    trust_scorer: Any,
    min_trust: float = 0.3,
    fail_open: bool = True,
):
    """Factory: return an async hook that gates on FIDES trust score.

    This mirrors the FIDES trust gate in ControlPlane (step 1.5a) which
    requires both a ``trust_scorer`` *and* a ``fides_did`` on the intent
    metadata.

    Args:
        trust_scorer: A ``TrustScorer`` (or compatible) instance whose
            ``calculate_trust(agent_id=..., agent_did=...)`` method returns
            a ``TrustScore`` with ``.overall`` (float) and ``.tier``
            attributes.
        min_trust: Minimum overall trust score required.  Intents from
            agents below this threshold are rejected.
        fail_open: When *True* (default, matching existing ControlPlane
            behavior), FIDES errors are logged but do not reject the
            intent.  When *False*, any error rejects.
    """

    async def fides_hook(intent: Any) -> HookResult:
        metadata = getattr(intent, "metadata", {}) or {}
        fides_did = metadata.get("fides_did")
        agent_id = getattr(intent, "agent_id", None) or ""

        if not fides_did:
            # No FIDES DID -- nothing to check.
            return HookResult(decision="skip", reason="no fides_did in metadata")

        try:
            trust_score = await trust_scorer.calculate_trust(
                agent_id=agent_id,
                agent_did=fides_did,
            )
        except Exception as exc:
            if fail_open:
                logger.warning(
                    "FIDES trust check failed for agent=%s did=%s: %s (non-blocking)",
                    agent_id, fides_did, exc,
                )
                return HookResult(
                    decision="skip",
                    reason=f"FIDES trust check unavailable: {exc}",
                )
            logger.error(
                "FIDES trust check failed for agent=%s did=%s: %s (fail-closed)",
                agent_id, fides_did, exc,
            )
            return HookResult(
                decision="reject",
                reason=f"FIDES trust check unavailable: {exc}",
            )

        if trust_score.overall < min_trust:
            logger.warning(
                "FIDES trust insufficient for agent=%s: %.2f < %.2f",
                agent_id, trust_score.overall, min_trust,
            )
            return HookResult(
                decision="reject",
                reason=f"trust_score_insufficient: {trust_score.overall:.2f} < {min_trust}",
                evidence={
                    "trust_score": trust_score.overall,
                    "trust_tier": trust_score.tier.value,
                    "min_required": min_trust,
                    "fides_did": fides_did,
                },
            )

        return HookResult(
            decision="approve",
            evidence={
                "trust_score": trust_score.overall,
                "trust_tier": trust_score.tier.value,
                "fides_did": fides_did,
            },
        )

    fides_hook.__name__ = "fides_hook"
    return fides_hook
