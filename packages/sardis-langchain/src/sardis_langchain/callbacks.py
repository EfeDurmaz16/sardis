"""
Optional callback handler for logging Sardis payment operations.

Attach this handler to a LangChain agent to get structured logging for every
tool invocation that touches Sardis.  Useful for audit trails, observability,
and debugging agent payment flows.

Usage::

    from sardis_langchain import SardisCallbackHandler

    handler = SardisCallbackHandler()
    executor = AgentExecutor(agent=agent, tools=tools, callbacks=[handler])
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("sardis_langchain")

# Tool names we care about
_SARDIS_TOOLS = frozenset({
    "sardis_pay",
    "sardis_check_balance",
    "sardis_check_policy",
    "sardis_set_policy",
    "sardis_list_transactions",
})


class SardisCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that logs Sardis tool invocations.

    Captures tool inputs and outputs for Sardis-specific tools.  Non-Sardis
    tool calls are silently ignored so this handler can be safely attached
    alongside other callbacks.

    Attributes:
        log_level: Python log level for tool invocations (default: INFO).
        records: In-memory list of structured event dicts (for programmatic access).
    """

    def __init__(self, log_level: int = logging.INFO) -> None:
        super().__init__()
        self.log_level = log_level
        self.records: list[dict[str, Any]] = []

    # -- Tool start -----------------------------------------------------------

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        inputs: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "")
        if tool_name not in _SARDIS_TOOLS:
            return

        record = {
            "event": "tool_start",
            "tool": tool_name,
            "input": input_str,
            "run_id": str(run_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.records.append(record)
        logger.log(self.log_level, "Sardis tool invoked: %s | input: %s", tool_name, input_str)

    # -- Tool end -------------------------------------------------------------

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        # Try to find the matching start record by run_id
        matching = [r for r in self.records if r.get("run_id") == str(run_id)]
        if not matching:
            return

        tool_name = matching[-1]["tool"]

        # Parse the output to extract success/failure
        parsed: dict[str, Any] = {}
        try:
            parsed = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            parsed = {"raw_output": output}

        record = {
            "event": "tool_end",
            "tool": tool_name,
            "success": parsed.get("success", None),
            "output": parsed,
            "run_id": str(run_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.records.append(record)

        if parsed.get("success") is False:
            logger.warning(
                "Sardis tool failed: %s | error: %s",
                tool_name,
                parsed.get("error", "unknown"),
            )
        else:
            logger.log(self.log_level, "Sardis tool completed: %s | success: %s", tool_name, True)

    # -- Tool error -----------------------------------------------------------

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        matching = [r for r in self.records if r.get("run_id") == str(run_id)]
        if not matching:
            return

        tool_name = matching[-1]["tool"]

        record = {
            "event": "tool_error",
            "tool": tool_name,
            "error": str(error),
            "run_id": str(run_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.records.append(record)
        logger.error("Sardis tool error: %s | %s", tool_name, error)

    # -- Convenience ----------------------------------------------------------

    def get_payment_records(self) -> list[dict[str, Any]]:
        """Return only records for sardis_pay invocations."""
        return [r for r in self.records if r.get("tool") == "sardis_pay"]

    def clear(self) -> None:
        """Clear all recorded events."""
        self.records.clear()
