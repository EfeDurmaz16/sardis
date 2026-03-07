"""Policy Engine domain — spending policy evaluation.

Wraps the existing wallet policy validation into the ControlPlane interface.
"""
from __future__ import annotations

import logging
from typing import Any

from sardis_v2_core.execution_intent import ExecutionIntent

logger = logging.getLogger(__name__)


class PolicyEngineAdapter:
    """Adapts the existing wallet_manager policy check to the ControlPlane interface."""

    def __init__(self, wallet_manager: Any = None) -> None:
        self._wallet_manager = wallet_manager

    async def evaluate(self, intent: ExecutionIntent) -> dict[str, Any]:
        """Evaluate spending policies for an intent."""
        if self._wallet_manager is None:
            return {"allowed": True, "reason": "no_policy_engine"}

        try:
            # Use real mandate if available, otherwise build minimal object
            mandate = intent.metadata.get("payment_mandate")
            if mandate is None:
                mandate = type("Mandate", (), {
                    "sender_wallet_id": intent.sender_wallet_id,
                    "amount": intent.amount,
                    "currency": intent.currency,
                    "chain": intent.chain,
                    "agent_id": intent.agent_id,
                    "organization_id": intent.org_id,
                })()

            result = await self._wallet_manager.async_validate_policies(mandate)
            allowed = getattr(result, "allowed", True)
            reason = getattr(result, "reason", None)
            return {"allowed": allowed, "reason": reason}
        except Exception as e:
            logger.warning("Policy evaluation error: %s", e)
            return {"allowed": False, "reason": f"Policy evaluation error: {e}"}
