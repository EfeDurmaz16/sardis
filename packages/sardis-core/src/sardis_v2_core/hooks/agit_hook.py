"""AGIT policy-chain integrity hook for PreExecutionPipeline.

Verifies that the AGIT hash chain for an agent's spending policies has not
been tampered with.  Extracted from ControlPlane steps 1.25.

Usage::

    from sardis_v2_core.hooks import create_agit_hook

    hook = create_agit_hook(agit_engine, fail_open=False)
    pipeline.add_hook(hook)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..pre_execution_pipeline import HookResult

logger = logging.getLogger("sardis.core.hooks.agit")


def create_agit_hook(agit_engine: Any, fail_open: bool = False):
    """Factory: return an async hook that verifies the AGIT policy chain.

    Args:
        agit_engine: An ``AgitPolicyEngine`` (or compatible) instance whose
            ``verify_policy_chain(agent_id)`` method returns a
            ``PolicyChainVerification`` with ``.valid``, ``.broken_at``,
            ``.chain_length``, and ``.error`` attributes.
        fail_open: When *True*, AGIT errors are logged but do not reject
            the intent.  When *False* (default, safe), any error rejects.
    """

    async def agit_hook(intent: Any) -> HookResult:
        agent_id = getattr(intent, "agent_id", None) or ""
        if not agent_id:
            # No agent context -- nothing to verify.
            return HookResult(decision="skip", reason="no agent_id on intent")

        try:
            # AgitPolicyEngine.verify_policy_chain is synchronous.
            verification = await asyncio.to_thread(
                agit_engine.verify_policy_chain, agent_id,
            )
        except Exception as exc:
            if fail_open:
                logger.warning(
                    "AGIT chain check failed for agent=%s: %s (fail-open)",
                    agent_id, exc,
                )
                return HookResult(
                    decision="skip",
                    reason=f"AGIT unavailable (fail-open): {exc}",
                )
            logger.error(
                "AGIT chain check failed for agent=%s: %s (fail-closed)",
                agent_id, exc,
            )
            return HookResult(
                decision="reject",
                reason=f"AGIT policy verification unavailable: {exc}",
            )

        if not verification.valid:
            logger.warning(
                "AGIT policy chain tampered for agent=%s broken_at=%s",
                agent_id, verification.broken_at,
            )
            return HookResult(
                decision="reject",
                reason="policy_chain_tampered",
                evidence={
                    "broken_at": verification.broken_at,
                    "chain_length": verification.chain_length,
                    "error": verification.error,
                },
            )

        return HookResult(
            decision="approve",
            evidence={
                "agit": "valid",
                "chain_length": verification.chain_length,
            },
        )

    agit_hook.__name__ = "agit_hook"
    return agit_hook
