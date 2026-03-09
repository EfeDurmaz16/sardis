"""Structured JSON logging for payment events.

Provides a dedicated logger that emits JSON-structured payment event
records for observability and audit purposes.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

_logger = logging.getLogger("sardis.payments")


def log_payment_event(
    event_type: str,
    *,
    org_id: str = "",
    agent_id: str = "",
    amount: str = "",
    currency: str = "",
    chain: str = "",
    status: str = "",
    tx_hash: str = "",
    latency_ms: int = 0,
    error: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured payment event log entry."""
    record = {
        "event_type": event_type,
        "org_id": org_id,
        "agent_id": agent_id,
        "amount": amount,
        "currency": currency,
        "chain": chain,
        "status": status,
        "tx_hash": tx_hash,
        "latency_ms": latency_ms,
        "error": error,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if extra:
        record.update(extra)

    # Remove empty string values for cleaner output
    record = {k: v for k, v in record.items() if v != "" and v != 0}

    level = logging.WARNING if error else logging.INFO
    _logger.log(level, json.dumps(record, default=str))
