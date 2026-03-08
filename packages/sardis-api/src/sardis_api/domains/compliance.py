"""Compliance domain — KYC/AML/sanctions checking.

Wraps the existing compliance service into the ControlPlane interface.
"""
from __future__ import annotations

import logging
from typing import Any

from sardis_v2_core.execution_intent import ExecutionIntent

logger = logging.getLogger(__name__)


class ComplianceAdapter:
    """Adapts the existing compliance service to the ControlPlane interface."""

    def __init__(self, compliance: Any = None) -> None:
        self._compliance = compliance

    async def check(self, intent: ExecutionIntent) -> dict[str, Any]:
        """Run compliance preflight for an intent."""
        if self._compliance is None:
            return {"allowed": True, "reason": "no_compliance_service"}

        try:
            mandate = intent.metadata.get("payment_mandate")
            if mandate is None:
                return {"allowed": True, "reason": "no_mandate_for_compliance"}

            result = await self._compliance.preflight(mandate)
            return {
                "allowed": result.allowed,
                "reason": getattr(result, "reason", None),
            }
        except Exception as e:
            logger.warning("Compliance check error: %s", e)
            # Fail-closed: deny on compliance errors
            return {"allowed": False, "reason": f"Compliance check error: {e}"}
