"""Langfuse LLM observability integration for Sardis.

Traces agent reasoning -> payment decision chains.

Setup:
    pip install langfuse

Environment variables:
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
    SARDIS_LANGFUSE_ENABLED=1 to enable
"""
from __future__ import annotations

import logging
import os
from functools import wraps
from typing import Any, Callable

_logger = logging.getLogger(__name__)
_langfuse = None
_enabled = False


def init_langfuse() -> None:
    """Initialize Langfuse client. No-op if not configured."""
    global _langfuse, _enabled

    if os.getenv("SARDIS_LANGFUSE_ENABLED", "").strip() not in ("1", "true", "yes"):
        return

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        _enabled = True
        _logger.info("Langfuse initialized")
    except ImportError:
        _logger.info("Langfuse not installed, LLM tracing disabled")
    except Exception as e:
        _logger.warning("Langfuse init failed: %s", e)


def trace_agent_action(action_name: str, agent_id: str | None = None) -> Callable:
    """Decorator to trace agent actions in Langfuse."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _enabled or _langfuse is None:
                return await func(*args, **kwargs)

            trace = _langfuse.trace(
                name=action_name,
                metadata={"agent_id": agent_id or kwargs.get("agent_id", "unknown"), "service": "sardis-api"},
            )
            try:
                result = await func(*args, **kwargs)
                trace.event(name="payment_decision", metadata={"decision": str(result)[:200]})
                return result
            except Exception as e:
                trace.event(name="error", metadata={"error": str(e)}, level="ERROR")
                raise
            finally:
                _langfuse.flush()
        return wrapper
    return decorator


def log_payment_decision(agent_id: str, amount: float, decision: str, reasoning: str | None = None) -> None:
    """Log a payment decision to Langfuse for audit trail."""
    if not _enabled or _langfuse is None:
        return
    _langfuse.trace(name="payment_decision", metadata={"agent_id": agent_id, "amount": amount, "decision": decision, "reasoning": reasoning})
    _langfuse.flush()
