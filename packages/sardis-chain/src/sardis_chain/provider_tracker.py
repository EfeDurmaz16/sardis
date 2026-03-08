"""Provider health tracking and reliability scorecards.

Records RPC provider events (calls, latency, errors) and computes
rolling availability/performance metrics for provider selection.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderEvent:
    """Single provider health event."""
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    provider: str = ""
    chain: str = ""
    event_type: str = ""    # 'rpc_call', 'tx_submission', 'tx_confirmation'
    success: bool = True
    latency_ms: int = 0
    error_type: str = ""    # 'timeout', 'rate_limit', '5xx', 'revert'
    gas_used: int = 0
    gas_price_gwei: float = 0.0
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ProviderScorecard:
    """Aggregated provider reliability metrics."""
    provider: str = ""
    chain: str = ""
    period: str = "24h"
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_rate: float = 0.0
    availability: float = 1.0
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "chain": self.chain,
            "period": self.period,
            "total_calls": self.total_calls,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "p95_latency_ms": round(self.p95_latency_ms, 1),
            "error_rate": round(self.error_rate, 4),
            "availability": round(self.availability, 4),
            "computed_at": self.computed_at.isoformat(),
        }


class ProviderTracker:
    """Tracks provider health events and computes reliability scorecards.

    In-memory implementation for dev/test. Production would be backed
    by the provider_health_events and provider_scorecards tables.
    """

    # Period durations in seconds
    _PERIOD_SECONDS = {
        "1h": 3600,
        "24h": 86400,
        "7d": 604800,
    }

    def __init__(self) -> None:
        # provider:chain -> list of events
        self._events: list[ProviderEvent] = []
        self._scorecards: dict[tuple[str, str, str], ProviderScorecard] = {}

    async def record_event(
        self,
        provider: str,
        chain: str,
        event_type: str,
        success: bool,
        latency_ms: int,
        error_type: str = "",
        gas_used: int = 0,
        gas_price_gwei: float = 0.0,
    ) -> str:
        """Record a provider health event."""
        event = ProviderEvent(
            provider=provider,
            chain=chain,
            event_type=event_type,
            success=success,
            latency_ms=latency_ms,
            error_type=error_type,
            gas_used=gas_used,
            gas_price_gwei=gas_price_gwei,
        )
        self._events.append(event)
        logger.debug(
            "Provider event: %s/%s %s success=%s latency=%dms",
            provider, chain, event_type, success, latency_ms,
        )
        return event.event_id

    async def get_scorecard(
        self,
        provider: str,
        chain: str,
        period: str = "24h",
    ) -> ProviderScorecard:
        """Get or compute a provider scorecard."""
        key = (provider, chain, period)
        if key in self._scorecards:
            return self._scorecards[key]
        # Compute on demand
        await self.compute_scorecards()
        return self._scorecards.get(key, ProviderScorecard(
            provider=provider, chain=chain, period=period,
        ))

    async def get_best_provider(self, chain: str) -> str:
        """Select best provider for a chain based on recent performance."""
        await self.compute_scorecards()
        candidates: list[tuple[str, float]] = []
        for (provider, ch, period), card in self._scorecards.items():
            if ch != chain or period != "24h":
                continue
            # Score = availability * (1 - error_rate) * latency_penalty
            latency_penalty = max(0.1, 1.0 - (card.avg_latency_ms / 5000.0))
            score = card.availability * (1.0 - card.error_rate) * latency_penalty
            candidates.append((provider, score))

        if not candidates:
            return "alchemy"  # Default fallback

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    async def compute_scorecards(self) -> None:
        """Recompute all scorecards from recent events."""
        now = time.time()
        # Group events by (provider, chain)
        grouped: dict[tuple[str, str], list[ProviderEvent]] = defaultdict(list)
        for event in self._events:
            grouped[(event.provider, event.chain)].append(event)

        for period, duration_s in self._PERIOD_SECONDS.items():
            cutoff = now - duration_s
            for (provider, chain), events in grouped.items():
                recent = [e for e in events if e.recorded_at.timestamp() >= cutoff]
                if not recent:
                    continue

                total = len(recent)
                successes = sum(1 for e in recent if e.success)
                failures = total - successes
                latencies = sorted(e.latency_ms for e in recent)
                avg_lat = sum(latencies) / total if total else 0
                p95_idx = int(total * 0.95) if total > 0 else 0
                p95_lat = latencies[min(p95_idx, total - 1)] if latencies else 0

                card = ProviderScorecard(
                    provider=provider,
                    chain=chain,
                    period=period,
                    total_calls=total,
                    success_count=successes,
                    failure_count=failures,
                    avg_latency_ms=avg_lat,
                    p95_latency_ms=p95_lat,
                    error_rate=failures / total if total else 0,
                    availability=successes / total if total else 1.0,
                )
                self._scorecards[(provider, chain, period)] = card

    async def get_all_scorecards(self) -> list[ProviderScorecard]:
        """Get all computed scorecards."""
        await self.compute_scorecards()
        return list(self._scorecards.values())
