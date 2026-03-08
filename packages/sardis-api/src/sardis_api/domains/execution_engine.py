"""Execution Engine domain — chain execution.

Wraps the existing chain executor into the ControlPlane interface.
"""
from __future__ import annotations

import logging
from typing import Any

from sardis_v2_core.execution_intent import ExecutionIntent

logger = logging.getLogger(__name__)


class ExecutionEngineAdapter:
    """Adapts the existing chain_executor to the ControlPlane interface."""

    def __init__(self, chain_executor: Any = None) -> None:
        self._executor = chain_executor

    async def execute(self, intent: ExecutionIntent) -> dict[str, Any]:
        """Execute a payment on chain."""
        if self._executor is None:
            raise RuntimeError("Chain executor not configured")

        try:
            # Use real mandate if available, otherwise build minimal object
            mandate = intent.metadata.get("payment_mandate")
            if mandate is None:
                mandate = type("Mandate", (), {
                    "sender_wallet_id": intent.sender_wallet_id,
                    "sender_address": intent.sender_address,
                    "recipient_wallet_id": intent.recipient_wallet_id,
                    "recipient_address": intent.recipient_address,
                    "amount": intent.amount,
                    "currency": intent.currency,
                    "chain": intent.chain,
                    "mandate_id": intent.intent_id,
                    "agent_id": intent.agent_id,
                    "organization_id": intent.org_id,
                })()

            receipt = await self._executor.dispatch_payment(mandate)
            return {
                "tx_hash": getattr(receipt, "tx_hash", str(receipt)),
                "status": getattr(receipt, "status", "submitted"),
                "audit_anchor": getattr(receipt, "audit_anchor", None),
            }
        except Exception as e:
            logger.error("Chain execution failed: %s", e)
            raise
