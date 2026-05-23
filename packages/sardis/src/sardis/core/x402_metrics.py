"""x402 self-monitoring metrics (veneur pattern).

Emits structured metric events for observability.
Counters and histograms for challenge, verification, settlement, and error flows.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class X402MetricsCollector:
    """Collects x402 protocol metrics for monitoring dashboards.

    Follows the veneur self-monitoring pattern: every subsystem
    emits metrics about its own health.
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}

    def _inc(self, name: str, tags: dict[str, str] | None = None, value: int = 1) -> None:
        key = f"{name}:{_serialize_tags(tags)}" if tags else name
        self._counters[key] = self._counters.get(key, 0) + value
        logger.debug("x402 metric counter %s=%d tags=%s", name, self._counters[key], tags)

    def _observe(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        key = f"{name}:{_serialize_tags(tags)}" if tags else name
        self._histograms.setdefault(key, []).append(value)
        logger.debug("x402 metric histogram %s=%.4f tags=%s", name, value, tags)

    def challenge_generated(self, network: str, currency: str) -> None:
        self._inc("x402.challenge.generated", {"network": network, "currency": currency})

    def payment_verified(self, network: str, success: bool) -> None:
        self._inc("x402.payment.verified", {"network": network, "success": str(success).lower()})

    def settlement_completed(self, network: str, source: str, duration_ms: float) -> None:
        self._inc("x402.settlement.completed", {"network": network, "source": source})
        self._observe("x402.settlement.duration_ms", duration_ms, {"network": network})

    def payment_failed(self, network: str, reason: str) -> None:
        self._inc("x402.payment.failed", {"network": network, "reason": reason})

    def dry_run_executed(self, network: str) -> None:
        self._inc("x402.dry_run.executed", {"network": network})

    def negotiator_selected(self, network: str, scheme: str) -> None:
        self._inc("x402.negotiator.selected", {"network": network, "scheme": scheme})

    def policy_check(self, allowed: bool, source: str) -> None:
        self._inc("x402.policy.check", {"allowed": str(allowed).lower(), "source": source})

    def get_counter(self, name: str) -> int:
        """Get counter value (for testing)."""
        total = 0
        for key, val in self._counters.items():
            if key == name or key.startswith(f"{name}:"):
                total += val
        return total

    def get_histogram(self, name: str) -> list[float]:
        """Get histogram values (for testing)."""
        values: list[float] = []
        for key, vals in self._histograms.items():
            if key == name or key.startswith(f"{name}:"):
                values.extend(vals)
        return values

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self._counters.clear()
        self._histograms.clear()


def _serialize_tags(tags: dict[str, str] | None) -> str:
    if not tags:
        return ""
    return ",".join(f"{k}={v}" for k, v in sorted(tags.items()))


# Module-level singleton
_collector: X402MetricsCollector | None = None


def get_x402_metrics() -> X402MetricsCollector:
    global _collector
    if _collector is None:
        _collector = X402MetricsCollector()
    return _collector


__all__ = [
    "X402MetricsCollector",
    "MetricPoint",
    "get_x402_metrics",
]
