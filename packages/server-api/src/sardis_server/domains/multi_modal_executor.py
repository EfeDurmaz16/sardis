"""Multi-modal execution adapter.

Sits between ControlPlane and executors — routes to the correct
sub-executor based on ExecutionModeRouter output.
"""
from __future__ import annotations

import logging
from typing import Any

from sardis_v2_core.execution_intent import ExecutionIntent
from sardis_v2_core.execution_mode import ExecutionMode, ExecutionModeRouter

logger = logging.getLogger(__name__)


class MultiModalExecutionAdapter:
    """ChainExecutor that dispatches to crypto or delegated sub-executor."""

    def __init__(
        self,
        crypto_executor=None,
        delegated_executor=None,
        mode_router: ExecutionModeRouter | None = None,
    ) -> None:
        self._crypto = crypto_executor
        self._delegated = delegated_executor
        self._router = mode_router

    async def execute(self, intent: ExecutionIntent) -> dict[str, Any]:
        # If router available and no explicit mode, resolve
        if self._router and not intent.execution_mode:
            selection = await self._router.resolve(intent)
            intent.execution_mode = selection.mode.value
            if selection.credential_id:
                intent.credential_id = selection.credential_id

        mode = intent.execution_mode or "native_crypto"

        if mode == ExecutionMode.DELEGATED_CARD.value:
            if self._delegated is None:
                raise RuntimeError("Delegated executor not configured")
            result = await self._delegated.execute(intent)
            result["execution_mode"] = "delegated_card"
            return result

        # Default: crypto execution
        if self._crypto is None:
            raise RuntimeError("Crypto executor not configured")
        result = await self._crypto.execute(intent)
        result["execution_mode"] = mode
        return result
