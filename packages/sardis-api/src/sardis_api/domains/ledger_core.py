"""Ledger Core domain — ledger recording and reconciliation.

Wraps the existing ledger into the ControlPlane interface.
"""
from __future__ import annotations

import logging
from typing import Any

from sardis_v2_core.execution_intent import ExecutionIntent

logger = logging.getLogger(__name__)


class LedgerCoreAdapter:
    """Adapts the existing ledger to the ControlPlane interface."""

    def __init__(self, ledger: Any = None) -> None:
        self._ledger = ledger

    async def record(self, intent: ExecutionIntent, tx_result: dict[str, Any]) -> str:
        """Record a payment in the ledger."""
        if self._ledger is None:
            return ""

        try:
            import inspect

            # Build a minimal mandate-like object for existing ledger
            mandate = type("Mandate", (), {
                "mandate_id": intent.intent_id,
                "sender_wallet_id": intent.sender_wallet_id,
                "recipient_wallet_id": intent.recipient_wallet_id,
                "amount": intent.amount,
                "currency": intent.currency,
                "chain": intent.chain,
                "agent_id": intent.agent_id,
                "organization_id": intent.org_id,
            })()

            chain_receipt = type("Receipt", (), tx_result)()

            if hasattr(self._ledger, "append_async"):
                maybe_tx = self._ledger.append_async(payment_mandate=mandate, chain_receipt=chain_receipt)
            else:
                maybe_tx = self._ledger.append(payment_mandate=mandate, chain_receipt=chain_receipt)

            tx = await maybe_tx if inspect.isawaitable(maybe_tx) else maybe_tx
            return getattr(tx, "tx_id", "") or ""

        except Exception as e:
            logger.warning("Ledger recording failed: %s", e)
            return ""
