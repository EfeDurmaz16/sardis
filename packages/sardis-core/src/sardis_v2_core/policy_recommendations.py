"""Policy recommendations engine for Sardis agents.

Analyses an agent's historical transaction data and produces concrete,
actionable policy suggestions with natural-language strings that can be
fed directly into the /policies/apply endpoint.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .database import Database


@dataclass
class PolicyRecommendation:
    """A suggested policy change for an agent."""

    agent_id: str
    recommendation_type: str   # "spending_limit" | "merchant_restriction" | "time_window" | "approval_threshold"
    description: str
    natural_language: str      # NL policy string that can be fed to /policies/apply
    confidence: float          # 0.0-1.0
    rationale: str
    data: dict                 # supporting data (averages, patterns, etc.)


class PolicyRecommendationEngine:
    """Analyses agent transaction history and suggests policies.

    Uses percentile-based heuristics over recent transaction history to
    recommend spending limits, merchant allowlists, time windows, and
    approval thresholds.

    Example::

        engine = PolicyRecommendationEngine(db=db)
        recs = await engine.get_recommendations("agent-123")
        for rec in recs:
            print(rec.natural_language)
    """

    # Minimum transaction count required before emitting recommendations.
    _MIN_TX_COUNT = 10

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_recommendations(self, agent_id: str) -> list[PolicyRecommendation]:
        """Generate policy recommendations based on transaction history.

        Args:
            agent_id: Unique identifier of the agent to analyse.

        Returns:
            List of :class:`PolicyRecommendation` objects, possibly empty if
            there is insufficient history.
        """
        stats = await self._get_agent_stats(agent_id)

        if stats["tx_count"] < self._MIN_TX_COUNT:
            return []

        recommendations: list[PolicyRecommendation] = []

        limits = await self._suggest_spending_limits(agent_id, stats)
        recommendations.extend(limits)

        merchant_recs = await self._suggest_merchant_restrictions(agent_id, stats)
        recommendations.extend(merchant_recs)

        time_recs = await self._suggest_time_windows(agent_id, stats)
        recommendations.extend(time_recs)

        approval_recs = await self._suggest_approval_threshold(agent_id, stats)
        recommendations.extend(approval_recs)

        return recommendations

    # ------------------------------------------------------------------
    # Private recommendation methods
    # ------------------------------------------------------------------

    async def _suggest_spending_limits(
        self, agent_id: str, stats: dict
    ) -> list[PolicyRecommendation]:
        """Suggest per-tx and daily limits based on historical patterns.

        Per-tx limit  = p90 of transaction amounts.
        Daily limit   = avg_daily_spend * 1.5.
        """
        recommendations: list[PolicyRecommendation] = []
        amounts: list[float] = stats.get("amounts", [])

        if not amounts:
            return recommendations

        sorted_amounts = sorted(amounts)
        p90_index = max(0, int(len(sorted_amounts) * 0.90) - 1)
        per_tx_limit = round(sorted_amounts[p90_index], 2)

        avg_daily = stats.get("avg_daily_spend", 0.0)
        daily_limit = round(avg_daily * 1.5, 2)

        # Per-transaction limit
        if per_tx_limit > 0:
            tx_count = stats["tx_count"]
            confidence = min(1.0, tx_count / 100)  # grows with more data, caps at 1.0
            recommendations.append(
                PolicyRecommendation(
                    agent_id=agent_id,
                    recommendation_type="spending_limit",
                    description=f"Limit individual transactions to ${per_tx_limit} (p90 of history).",
                    natural_language=(
                        f"Maximum transaction amount is ${per_tx_limit} USDC"
                    ),
                    confidence=round(confidence, 3),
                    rationale=(
                        f"The 90th percentile of {tx_count} transactions is ${per_tx_limit}. "
                        "Capping at this level allows normal operations while blocking outliers."
                    ),
                    data={
                        "per_tx_limit": per_tx_limit,
                        "p90_index": p90_index,
                        "sample_size": tx_count,
                        "amounts_min": min(amounts),
                        "amounts_max": max(amounts),
                        "amounts_mean": round(statistics.mean(amounts), 2),
                    },
                )
            )

        # Daily spending limit
        if daily_limit > 0:
            confidence = min(1.0, stats.get("active_days", 1) / 30)
            recommendations.append(
                PolicyRecommendation(
                    agent_id=agent_id,
                    recommendation_type="spending_limit",
                    description=f"Limit daily spending to ${daily_limit} (1.5× average daily spend).",
                    natural_language=(
                        f"Daily spending limit is ${daily_limit} USDC"
                    ),
                    confidence=round(confidence, 3),
                    rationale=(
                        f"Average daily spend is ${avg_daily:.2f}. "
                        "A 1.5× buffer accommodates legitimate spikes without unlimited exposure."
                    ),
                    data={
                        "daily_limit": daily_limit,
                        "avg_daily_spend": round(avg_daily, 2),
                        "active_days": stats.get("active_days", 0),
                    },
                )
            )

        return recommendations

    async def _suggest_merchant_restrictions(
        self, agent_id: str, stats: dict
    ) -> list[PolicyRecommendation]:
        """Suggest allowed merchant list based on frequent merchants.

        Recommends an allowlist when 80%+ of transactions go to fewer than
        5 distinct merchants.
        """
        merchant_counts: dict[str, int] = stats.get("merchant_counts", {})
        tx_count: int = stats.get("tx_count", 0)

        if not merchant_counts or tx_count == 0:
            return []

        # Sort merchants by frequency descending
        sorted_merchants = sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)

        # Find the top merchants that collectively cover ≥80% of transactions
        cumulative = 0
        top_merchants: list[str] = []
        for merchant_id, count in sorted_merchants:
            cumulative += count
            top_merchants.append(merchant_id)
            if cumulative / tx_count >= 0.80:
                break

        if len(top_merchants) >= 5:
            # Too many merchants — allowlist would be too broad to be useful
            return []

        coverage = round(cumulative / tx_count, 3)
        confidence = round(coverage * min(1.0, tx_count / 50), 3)
        merchant_list_str = ", ".join(top_merchants)

        return [
            PolicyRecommendation(
                agent_id=agent_id,
                recommendation_type="merchant_restriction",
                description=(
                    f"Restrict to {len(top_merchants)} merchants that account for "
                    f"{coverage * 100:.0f}% of transactions."
                ),
                natural_language=(
                    f"Only allow transactions to merchants: {merchant_list_str}"
                ),
                confidence=confidence,
                rationale=(
                    f"{len(top_merchants)} merchant(s) cover {coverage * 100:.0f}% of "
                    f"{tx_count} historical transactions. Allowlisting them blocks unexpected spend."
                ),
                data={
                    "allowed_merchants": top_merchants,
                    "coverage": coverage,
                    "tx_count": tx_count,
                    "merchant_counts": dict(sorted_merchants[:10]),
                },
            )
        ]

    async def _suggest_time_windows(
        self, agent_id: str, stats: dict
    ) -> list[PolicyRecommendation]:
        """Suggest time restrictions based on typical usage hours.

        Recommends an 8-hour window restriction when 90%+ of transactions
        occur within a contiguous 8-hour window.
        """
        hourly: dict[int, int] = stats.get("hourly_distribution", {})
        tx_count: int = stats.get("tx_count", 0)

        if not hourly or tx_count == 0:
            return []

        threshold = 0.90 * tx_count

        # Slide an 8-hour window across all 24 hours (wrap-around via modulo)
        best_window_start: int | None = None
        best_coverage = 0
        best_count = 0

        for start in range(24):
            window_hours = {(start + i) % 24 for i in range(8)}
            count = sum(hourly.get(h, 0) for h in window_hours)
            if count > best_count:
                best_count = count
                best_coverage = count / tx_count
                best_window_start = start

        if best_window_start is None or best_coverage < 0.90:
            return []

        window_end = (best_window_start + 8) % 24
        confidence = round(best_coverage * min(1.0, tx_count / 50), 3)

        # Format hours for readability
        start_str = f"{best_window_start:02d}:00 UTC"
        end_str = f"{window_end:02d}:00 UTC"

        return [
            PolicyRecommendation(
                agent_id=agent_id,
                recommendation_type="time_window",
                description=(
                    f"Restrict transactions to {start_str}–{end_str} "
                    f"(covers {best_coverage * 100:.0f}% of historical activity)."
                ),
                natural_language=(
                    f"Transactions are only allowed between {start_str} and {end_str}"
                ),
                confidence=confidence,
                rationale=(
                    f"{best_coverage * 100:.0f}% of {tx_count} transactions occurred in the "
                    f"8-hour window starting at {start_str}. "
                    "Restricting to this window prevents off-hours abuse."
                ),
                data={
                    "window_start_hour": best_window_start,
                    "window_end_hour": window_end,
                    "coverage": round(best_coverage, 3),
                    "tx_in_window": best_count,
                    "tx_count": tx_count,
                    "hourly_distribution": hourly,
                },
            )
        ]

    async def _suggest_approval_threshold(
        self, agent_id: str, stats: dict
    ) -> list[PolicyRecommendation]:
        """Suggest an approval threshold based on transaction distribution.

        Recommends requiring human approval for amounts above the p75.
        """
        amounts: list[float] = stats.get("amounts", [])
        tx_count: int = stats.get("tx_count", 0)

        if not amounts:
            return []

        sorted_amounts = sorted(amounts)
        p75_index = max(0, int(len(sorted_amounts) * 0.75) - 1)
        threshold = round(sorted_amounts[p75_index], 2)

        if threshold <= 0:
            return []

        confidence = round(min(1.0, tx_count / 100), 3)

        return [
            PolicyRecommendation(
                agent_id=agent_id,
                recommendation_type="approval_threshold",
                description=(
                    f"Require human approval for transactions above ${threshold} (p75)."
                ),
                natural_language=(
                    f"Transactions above ${threshold} USDC require human approval"
                ),
                confidence=confidence,
                rationale=(
                    f"The 75th percentile of {tx_count} transactions is ${threshold}. "
                    "Transactions above this amount are materially larger than typical "
                    "and warrant an approval gate."
                ),
                data={
                    "approval_threshold": threshold,
                    "p75_index": p75_index,
                    "sample_size": tx_count,
                    "amounts_mean": round(statistics.mean(amounts), 2),
                    "amounts_median": round(statistics.median(amounts), 2),
                },
            )
        ]

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    async def _get_agent_stats(self, agent_id: str) -> dict[str, Any]:
        """Query the transactions table and compute summary statistics.

        Expected columns on the ``transactions`` table:
        - ``agent_id``   TEXT
        - ``amount``     NUMERIC
        - ``merchant_id`` TEXT (nullable)
        - ``created_at`` TIMESTAMPTZ
        - ``status``     TEXT

        Returns a dict with keys:
        - tx_count (int)
        - amounts (list[float])
        - merchant_counts (dict[str, int])
        - hourly_distribution (dict[int, int])
        - avg_daily_spend (float)
        - active_days (int)
        """
        # Fetch all successful transactions for this agent
        rows = await self._db.fetch_all(
            """
            SELECT
                amount,
                merchant_id,
                EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')::int AS hour_of_day,
                created_at::date AS tx_date
            FROM transactions
            WHERE agent_id = $1
              AND status = 'completed'
            ORDER BY created_at DESC
            """,
            agent_id,
        )

        if not rows:
            return {
                "tx_count": 0,
                "amounts": [],
                "merchant_counts": {},
                "hourly_distribution": {},
                "avg_daily_spend": 0.0,
                "active_days": 0,
            }

        amounts: list[float] = []
        merchant_counts: dict[str, int] = {}
        hourly_distribution: dict[int, int] = {}
        daily_spend: dict[str, float] = {}

        for row in rows:
            amt = float(row["amount"])
            amounts.append(amt)

            merchant = row.get("merchant_id")
            if merchant:
                merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1

            hour = int(row["hour_of_day"])
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1

            tx_date = str(row["tx_date"])
            daily_spend[tx_date] = daily_spend.get(tx_date, 0.0) + amt

        active_days = len(daily_spend)
        avg_daily_spend = sum(daily_spend.values()) / active_days if active_days else 0.0

        return {
            "tx_count": len(amounts),
            "amounts": amounts,
            "merchant_counts": merchant_counts,
            "hourly_distribution": hourly_distribution,
            "avg_daily_spend": avg_daily_spend,
            "active_days": active_days,
        }
