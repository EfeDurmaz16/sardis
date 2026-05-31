"""RiskEngine — the agent-fraud Guard decision layer (Sardis-owned moat).

The in-house :class:`~sardis.guardrails.anomaly_engine.AnomalyEngine` already
turns agent-behavior features (amount-vs-baseline, velocity, new-counterparty,
off-pattern time, merchant category, behavioral alerts) into a 0-1 risk score
and a control-plane action.  ``RiskEngine`` *wraps and extends* it — it does not
re-implement it:

1. it calls ``AnomalyEngine.assess_risk`` for the internal behavioral score
   (reuse, not duplication), and normalizes that 0-1 score to 0-100;
2. it asks any configured external :class:`FraudSignalPort` feeds (Stripe Radar,
   SEON) to ``score(context)`` — cross-customer signals Sardis cannot
   self-generate — and folds them in by taking the max external score
   (a single highly-confident external decline must not be diluted by an
   abstaining feed);
3. it combines internal + external into one 0-100 ``combined_score`` and maps
   it to a binding :class:`GuardAction`: ALLOW / FLAG / REQUIRE_APPROVAL / BLOCK.

Hard rules:

* **Sardis owns the decision.**  External feeds only contribute a score +
  advisory recommendation; the engine maps the combined score to the action.
* **Fail-closed on a money path.**  If an external feed *raises* while scoring a
  high-value transaction, the engine does not silently allow — it escalates to
  REQUIRE_APPROVAL (or BLOCK at/above the block threshold).  A low-value feed
  error degrades to internal-only scoring.
* **Decimal money.**  Amounts are :class:`~decimal.Decimal`; ``float`` is never
  used for money.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .anomaly_engine import AnomalyEngine, RiskAction, get_anomaly_engine

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .behavioral_monitor import BehavioralAlert

logger = logging.getLogger("sardis.risk_engine")


class GuardAction(str, Enum):
    """The binding Guard decision for a transaction.

    Deliberately the four-rung ladder the task + ApprovalGate speak:

    * ``ALLOW`` — proceed.
    * ``FLAG`` — allow, but record the signal for monitoring / later review.
    * ``REQUIRE_APPROVAL`` — pause and route to the ApprovalGate (human step-up).
    * ``BLOCK`` — deny, fail-closed.  No money moves.
    """

    ALLOW = "allow"
    FLAG = "flag"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


@runtime_checkable
class _FraudSignalFeed(Protocol):
    """Structural type for the provider-layer ``FraudSignalPort``.

    Typed here so this core package never imports the apps/api provider modules
    (same boundary discipline the ApprovalGate uses for its notifier).
    """

    @property
    def provider(self) -> str: ...

    async def score(self, context: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class FeedSignal:
    """A normalized external feed read, captured as evidence."""

    provider: str
    score: float                    # 0-100
    reasons: tuple[str, ...]
    recommended_action: str
    sandbox: bool
    ok: bool                        # False when the feed raised (fail-closed)
    error: str | None = None


@dataclass
class RiskDecision:
    """The combined Guard assessment + the binding action.

    Carries the full breakdown so a BLOCK / REQUIRE_APPROVAL can be audited with
    evidence (which score, which feed, why).
    """

    agent_id: str
    action: GuardAction
    combined_score: float           # 0-100
    internal_score: float           # 0-100 (from the AnomalyEngine)
    external_score: float           # 0-100 (max across feeds; 0 if none)
    internal_action: RiskAction
    reasons: list[str]
    feeds: list[FeedSignal]
    timestamp: datetime
    amount: Decimal | None = None
    counterparty: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_blocking(self) -> bool:
        return self.action == GuardAction.BLOCK

    @property
    def requires_approval(self) -> bool:
        return self.action == GuardAction.REQUIRE_APPROVAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "action": self.action.value,
            "combined_score": round(self.combined_score, 2),
            "internal_score": round(self.internal_score, 2),
            "external_score": round(self.external_score, 2),
            "internal_action": self.internal_action.value,
            "reasons": list(self.reasons),
            "feeds": [
                {
                    "provider": f.provider,
                    "score": round(f.score, 2),
                    "recommended_action": f.recommended_action,
                    "sandbox": f.sandbox,
                    "ok": f.ok,
                    "error": f.error,
                }
                for f in self.feeds
            ],
            "amount": str(self.amount) if self.amount is not None else None,
            "counterparty": self.counterparty,
            "timestamp": self.timestamp.isoformat(),
        }


class RiskEngine:
    """Agent-fraud risk scoring + the binding ALLOW/FLAG/APPROVAL/BLOCK decision.

    Wraps the in-house :class:`AnomalyEngine` (reused for the behavioral score)
    and combines it with external :class:`FraudSignalPort` feeds.
    """

    # ── score → action thresholds (0-100) ──────────────────────────────
    #: ``< FLAG``            → ALLOW
    #: ``[FLAG, APPROVAL)``  → FLAG (allow + record)
    #: ``[APPROVAL, BLOCK)`` → REQUIRE_APPROVAL (route to ApprovalGate)
    #: ``>= BLOCK``          → BLOCK (deny, fail-closed)
    FLAG_THRESHOLD = 30.0
    APPROVAL_THRESHOLD = 60.0
    BLOCK_THRESHOLD = 85.0

    #: Combine weights for internal-behavioral vs external-feed scores.  The
    #: internal behavioral model is the moat and leads; external feeds add
    #: cross-customer lift.  (Used for the *blended* score; a high-confidence
    #: external decline can still floor the action — see ``_combine``.)
    INTERNAL_WEIGHT = 0.6
    EXTERNAL_WEIGHT = 0.4

    #: At/above this token amount a transaction is "high value": an external
    #: feed error must fail closed (escalate), never silently allow.
    HIGH_VALUE_THRESHOLD = Decimal("1000")

    def __init__(
        self,
        *,
        anomaly_engine: AnomalyEngine | None = None,
        fraud_feeds: list[_FraudSignalFeed] | None = None,
        high_value_threshold: Decimal | None = None,
    ) -> None:
        # Reuse the existing singleton engine by default — do NOT duplicate it.
        self._anomaly = anomaly_engine or get_anomaly_engine()
        self._feeds: list[_FraudSignalFeed] = list(fraud_feeds or [])
        self._high_value = (
            high_value_threshold
            if high_value_threshold is not None
            else self.HIGH_VALUE_THRESHOLD
        )

    async def assess(
        self,
        *,
        agent_id: str,
        amount: Decimal,
        counterparty: str | None = None,
        merchant_category: str | None = None,
        behavioral_alerts: "list[BehavioralAlert] | None" = None,
        baseline_mean: float | None = None,
        baseline_std: float | None = None,
        recent_tx_count_1h: int = 0,
        is_new_merchant: bool = False,
        hour_of_day: int | None = None,
        typical_hours: set[int] | None = None,
        signal_context: dict[str, Any] | None = None,
    ) -> RiskDecision:
        """Compute the combined risk decision for an agent transaction.

        The behavioral features map 1:1 onto :meth:`AnomalyEngine.assess_risk`;
        ``signal_context`` is the opaque dict passed to external feeds (it should
        carry the agent id, amount, counterparty, and any ip/email/device hints).
        """
        amount = Decimal(str(amount))

        # ── 1. Internal behavioral score (reuse the AnomalyEngine) ──────
        internal = self._anomaly.assess_risk(
            agent_id=agent_id,
            amount=amount,
            merchant_id=counterparty,
            merchant_category=merchant_category,
            behavioral_alerts=behavioral_alerts,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            recent_tx_count_1h=recent_tx_count_1h,
            is_new_merchant=is_new_merchant,
            hour_of_day=hour_of_day,
            typical_hours=typical_hours,
        )
        internal_score = internal.overall_score * 100.0  # 0-1 → 0-100
        reasons: list[str] = [
            f"internal behavioral score {internal_score:.1f}/100 "
            f"({internal.action.value})"
        ]

        # ── 2. External feeds (signal-only) ─────────────────────────────
        ctx = dict(signal_context or {})
        ctx.setdefault("agent_id", agent_id)
        ctx.setdefault("amount", str(amount))
        if counterparty:
            ctx.setdefault("counterparty", counterparty)

        is_high_value = amount >= self._high_value
        feeds: list[FeedSignal] = []
        external_score = 0.0
        feed_error_high_value = False

        for feed in self._feeds:
            provider = getattr(feed, "provider", "external")
            try:
                result = await feed.score(ctx)
            except Exception as exc:  # noqa: BLE001 - fail-closed handling below
                # A feed that raises on a HIGH-VALUE path cannot be allowed to
                # pass silently — record the failure and force an escalation.
                feeds.append(
                    FeedSignal(
                        provider=provider,
                        score=0.0,
                        reasons=("feed error",),
                        recommended_action="not_assessed",
                        sandbox=getattr(feed, "sandbox", True),
                        ok=False,
                        error=str(exc),
                    )
                )
                logger.warning(
                    "risk_engine: feed %s errored (high_value=%s): %s",
                    provider, is_high_value, exc,
                )
                if is_high_value:
                    feed_error_high_value = True
                    reasons.append(
                        f"feed {provider} unavailable on high-value tx → fail-closed"
                    )
                else:
                    reasons.append(f"feed {provider} unavailable (low value, degraded)")
                continue

            fscore = float(getattr(result, "score", 0.0) or 0.0)
            fscore = max(0.0, min(100.0, fscore))
            rec = getattr(getattr(result, "recommended_action", None), "value", None) or str(
                getattr(result, "recommended_action", "not_assessed")
            )
            freasons = tuple(getattr(result, "reasons", ()) or ())
            feeds.append(
                FeedSignal(
                    provider=provider,
                    score=fscore,
                    reasons=freasons,
                    recommended_action=rec,
                    sandbox=bool(getattr(result, "sandbox", True)),
                    ok=True,
                )
            )
            # Take the max external score: a single confident decline must not
            # be diluted by an abstaining feed.
            external_score = max(external_score, fscore)
            if freasons:
                reasons.append(f"feed {provider} ({rec}): {freasons[0]}")

        # ── 3. Combine + map to the binding action ──────────────────────
        combined_score = self._combine(internal_score, external_score, has_feeds=bool(self._feeds))
        action = self._action_for_score(combined_score)

        # Fail-closed: a high-value transaction whose external feed could not be
        # reached is never auto-ALLOWed.  Escalate to at least REQUIRE_APPROVAL
        # (or honor a BLOCK the internal score already demanded).
        if feed_error_high_value and action in (GuardAction.ALLOW, GuardAction.FLAG):
            action = GuardAction.REQUIRE_APPROVAL
            reasons.append("escalated to REQUIRE_APPROVAL: high-value feed error (fail-closed)")

        decision = RiskDecision(
            agent_id=agent_id,
            action=action,
            combined_score=combined_score,
            internal_score=internal_score,
            external_score=external_score,
            internal_action=internal.action,
            reasons=reasons,
            feeds=feeds,
            timestamp=datetime.now(UTC),
            amount=amount,
            counterparty=counterparty,
        )
        logger.info(
            "risk_engine: agent=%s combined=%.1f internal=%.1f external=%.1f action=%s",
            agent_id, combined_score, internal_score, external_score, action.value,
        )
        return decision

    # ── helpers ─────────────────────────────────────────────────────────

    def _combine(self, internal: float, external: float, *, has_feeds: bool) -> float:
        """Blend internal + external 0-100 scores.

        With no feeds configured the internal score stands alone.  With feeds,
        a weighted blend gives the moat (internal behavioral model) the lead
        while letting cross-customer signals lift the score — and a very
        high-confidence external decline floors the blend so it cannot be washed
        out (the blend never reads *lower* than a near-certain external decline).
        """
        if not has_feeds:
            return max(0.0, min(100.0, internal))
        blended = self.INTERNAL_WEIGHT * internal + self.EXTERNAL_WEIGHT * external
        # An external feed can only ever *lift* risk — it must never let a calm
        # (or abstaining / errored, score=0) feed dilute a hot internal model
        # below what the internal behavioral score alone already demands.  The
        # combined score is therefore floored at the internal score.
        blended = max(blended, internal)
        # Symmetrically, a near-certain external decline (>= block threshold)
        # cannot be washed out by a calm internal model.
        if external >= self.BLOCK_THRESHOLD:
            blended = max(blended, self.BLOCK_THRESHOLD)
        return max(0.0, min(100.0, blended))

    def _action_for_score(self, score: float) -> GuardAction:
        if score >= self.BLOCK_THRESHOLD:
            return GuardAction.BLOCK
        if score >= self.APPROVAL_THRESHOLD:
            return GuardAction.REQUIRE_APPROVAL
        if score >= self.FLAG_THRESHOLD:
            return GuardAction.FLAG
        return GuardAction.ALLOW


# Singleton (mirrors get_anomaly_engine / get_kill_switch).
_global_risk_engine: RiskEngine | None = None


def get_risk_engine() -> RiskEngine:
    """Get the global :class:`RiskEngine` singleton (internal-only by default).

    External feeds are wired by the app layer (it constructs an engine with
    ``fraud_feeds=[...]`` from the provider registry).  The default singleton
    runs internal-only so dev + tests work with no providers configured.
    """
    global _global_risk_engine
    if _global_risk_engine is None:
        _global_risk_engine = RiskEngine()
    return _global_risk_engine


def set_risk_engine(engine: RiskEngine | None) -> None:
    """Override the global RiskEngine (app wiring / tests)."""
    global _global_risk_engine
    _global_risk_engine = engine
