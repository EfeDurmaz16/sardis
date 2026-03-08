"""Smart provider router — selects providers based on reliability data.

Uses Phase 4 scorecard data to make informed routing decisions,
weighted by availability, latency, error rate trends, and cost.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .provider_tracker import ProviderTracker

logger = logging.getLogger(__name__)

# Default weights for provider selection scoring
_AVAILABILITY_WEIGHT = 0.40
_LATENCY_WEIGHT = 0.30
_ERROR_RATE_WEIGHT = 0.20
_COST_WEIGHT = 0.10

# Default providers per chain
_DEFAULT_PROVIDERS: dict[str, str] = {
    "base": "alchemy",
    "ethereum": "alchemy",
    "polygon": "alchemy",
    "arbitrum": "alchemy",
    "optimism": "alchemy",
}


class SmartRouter:
    """Provider routing that learns from reliability data.

    Selects the best RPC provider for a given chain based on
    recent availability, latency, error rate, and cost metrics.
    """

    def __init__(
        self,
        tracker: Optional["ProviderTracker"] = None,
        default_providers: Optional[dict[str, str]] = None,
    ) -> None:
        self._tracker = tracker
        self._defaults = default_providers or dict(_DEFAULT_PROVIDERS)

    async def select_provider(
        self,
        chain: str,
        urgency: str = "normal",
    ) -> str:
        """Select the best provider for a chain.

        Args:
            chain: Target blockchain
            urgency: 'low', 'normal', or 'high' — high urgency
                     weights latency more heavily

        Returns:
            Provider name (e.g., 'alchemy', 'infura')
        """
        if self._tracker is None:
            return self._defaults.get(chain, "alchemy")

        best = await self._tracker.get_best_provider(chain)
        if not best:
            return self._defaults.get(chain, "alchemy")

        logger.debug("SmartRouter: selected %s for %s (urgency=%s)", best, chain, urgency)
        return best

    async def get_routing_explanation(self, chain: str) -> dict[str, Any]:
        """Get detailed explanation of routing decision for a chain."""
        if self._tracker is None:
            return {
                "chain": chain,
                "selected": self._defaults.get(chain, "alchemy"),
                "reason": "No tracker configured — using default provider",
                "candidates": [],
            }

        scorecards = await self._tracker.get_all_scorecards()
        chain_cards = [c for c in scorecards if c.chain == chain and c.period == "24h"]

        if not chain_cards:
            return {
                "chain": chain,
                "selected": self._defaults.get(chain, "alchemy"),
                "reason": "No scorecard data — using default provider",
                "candidates": [],
            }

        best = await self._tracker.get_best_provider(chain)
        candidates = []
        for card in chain_cards:
            latency_penalty = max(0.1, 1.0 - (card.avg_latency_ms / 5000.0))
            score = card.availability * (1.0 - card.error_rate) * latency_penalty
            candidates.append({
                "provider": card.provider,
                "score": round(score, 4),
                "availability": round(card.availability, 4),
                "avg_latency_ms": round(card.avg_latency_ms, 1),
                "error_rate": round(card.error_rate, 4),
                "total_calls": card.total_calls,
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)

        return {
            "chain": chain,
            "selected": best,
            "reason": f"Selected based on 24h scorecard (top score: {candidates[0]['score']:.4f})" if candidates else "No data",
            "candidates": candidates,
        }
