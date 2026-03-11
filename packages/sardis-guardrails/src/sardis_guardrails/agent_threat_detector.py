"""Agent-specific threat detection for AI payment agents.

Detects threats unique to AI agents that traditional fraud systems miss:
- Prompt injection → payment attacks
- MCP tool poisoning
- Agent behavioral drift (model manipulation)
- Cross-agent coordination / collusion
- Threshold evasion (structuring)
- Replay attack patterns

Designed to complement the existing AnomalyEngine with agent-only signals.
"""
from __future__ import annotations

import hashlib
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from .anomaly_engine import RiskAction, RiskSignal

logger = logging.getLogger(__name__)


class ThreatCategory(str, Enum):
    """Categories of agent-specific threats."""
    PROMPT_INJECTION = "prompt_injection"
    MCP_TOOL_POISONING = "mcp_tool_poisoning"
    BEHAVIORAL_DRIFT = "behavioral_drift"
    COORDINATION = "coordination"
    THRESHOLD_EVASION = "threshold_evasion"
    REPLAY_ATTACK = "replay_attack"


@dataclass
class AgentThreatSignals:
    """Input signals for agent-specific threat detection.

    Callers populate the fields they have data for; unpopulated fields
    default to safe values and produce a 0.0 score.
    """
    # --- Prompt injection signals ---
    declared_intent: str | None = None        # What the mandate says (AP2 intent)
    actual_merchant_id: str | None = None     # Where payment actually goes
    declared_merchant_id: str | None = None   # Merchant in mandate
    declared_amount: Decimal | None = None    # Amount in mandate
    actual_amount: Decimal | None = None      # Actual transaction amount

    # --- MCP tool signals ---
    mcp_tool_calls: int = 0                   # Number of MCP tool invocations
    mcp_baseline_calls: float = 3.0           # Historical average per tx
    mcp_response_latency_ms: float = 0.0      # Latest response latency
    mcp_baseline_latency_ms: float = 100.0    # Historical average latency
    mcp_chain_depth: int = 0                  # Depth of tool chaining

    # --- Behavioral fingerprint signals ---
    execution_time_ms: float = 0.0            # Agent's processing time for this tx
    baseline_execution_time_ms: float = 200.0 # Historical mean processing time
    baseline_execution_std_ms: float = 50.0   # Std dev of processing time
    token_used: str | None = None             # Token for this tx
    chain_used: str | None = None             # Chain for this tx
    token_distribution: dict[str, float] | None = None   # Historical {token: pct}
    chain_distribution: dict[str, float] | None = None   # Historical {chain: pct}

    # --- Cross-agent coordination signals ---
    org_agents_same_merchant_5min: int = 0    # Other agents in org → same merchant recently
    org_agents_total_active_5min: int = 1     # Total active agents in org window
    amounts_sum_round_number: bool = False    # If combined amounts are suspiciously round

    # --- Threshold evasion signals ---
    amount: Decimal = Decimal("0")
    policy_max_per_tx: Decimal | None = None  # Agent's per-tx limit
    policy_daily_cap: Decimal | None = None   # Agent's daily limit
    daily_spend_so_far: Decimal = Decimal("0")
    recent_tx_count_30min: int = 0            # Transactions in last 30 min

    # --- Replay signals ---
    mandate_age_seconds: float = 0.0          # Age of the mandate/request
    mandate_hash: str | None = None           # Hash of mandate content
    is_duplicate_mandate: bool = False         # Idempotency check result


@dataclass
class AgentThreatAssessment:
    """Result of agent-specific threat analysis."""
    agent_id: str
    overall_score: float              # 0.0-1.0
    action: RiskAction
    signals: list[RiskSignal]
    threat_categories: list[ThreatCategory]  # Which categories triggered
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def should_block(self) -> bool:
        return self.action in (RiskAction.FREEZE_AGENT, RiskAction.KILL_SWITCH)

    @property
    def requires_review(self) -> bool:
        return self.action in (RiskAction.FLAG, RiskAction.REQUIRE_APPROVAL)


class AgentThreatDetector:
    """Detects AI agent-specific fraud and threat patterns.

    Complements the existing AnomalyEngine with signals that only apply
    to AI agents, not human users.

    Example::

        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            declared_amount=Decimal("50"),
            actual_amount=Decimal("5000"),
            declared_merchant_id="api-credits",
            actual_merchant_id="unknown-offshore",
        )
        assessment = detector.assess(agent_id="agent-123", signals=signals)
        if assessment.should_block:
            raise ComplianceViolationError("Agent threat detected")
    """

    # Weights for agent-specific signal categories
    WEIGHTS: dict[str, float] = {
        "intent_mismatch": 0.20,
        "amount_mismatch": 0.15,
        "mcp_velocity": 0.12,
        "mcp_latency": 0.10,
        "mcp_chain_depth": 0.05,
        "execution_drift": 0.08,
        "token_drift": 0.05,
        "chain_drift": 0.05,
        "coordination": 0.08,
        "threshold_evasion": 0.07,
        "replay": 0.05,
    }

    # Thresholds
    _MCP_VELOCITY_MULTIPLIER = 3.0     # Flag at 3x baseline calls
    _MCP_LATENCY_MULTIPLIER = 5.0      # Flag at 5x baseline latency
    _MCP_CHAIN_DEPTH_WARN = 5          # Flag at depth > 5
    _MCP_CHAIN_DEPTH_BLOCK = 15        # Block at depth > 15
    _EXECUTION_DRIFT_SIGMA = 3.0       # Flag at 3 sigma drift
    _MANDATE_MAX_AGE_S = 300.0         # 5 minutes max mandate age
    _THRESHOLD_PROXIMITY_PCT = 0.95    # Flag at 95% of limit

    def assess(
        self,
        agent_id: str,
        signals: AgentThreatSignals,
    ) -> AgentThreatAssessment:
        """Run all agent-specific threat detection checks.

        Args:
            agent_id: Agent identifier.
            signals: Populated threat signal inputs.

        Returns:
            AgentThreatAssessment with scores and recommended action.
        """
        risk_signals: list[RiskSignal] = []
        triggered_categories: list[ThreatCategory] = []

        # 1. Prompt injection detection
        intent_sig = self._score_intent_mismatch(signals)
        amount_sig = self._score_amount_mismatch(signals)
        risk_signals.extend([intent_sig, amount_sig])
        if intent_sig.score > 0.3 or amount_sig.score > 0.3:
            triggered_categories.append(ThreatCategory.PROMPT_INJECTION)

        # 2. MCP tool poisoning detection
        mcp_vel = self._score_mcp_velocity(signals)
        mcp_lat = self._score_mcp_latency(signals)
        mcp_depth = self._score_mcp_chain_depth(signals)
        risk_signals.extend([mcp_vel, mcp_lat, mcp_depth])
        if any(s.score > 0.3 for s in [mcp_vel, mcp_lat, mcp_depth]):
            triggered_categories.append(ThreatCategory.MCP_TOOL_POISONING)

        # 3. Behavioral drift
        exec_sig = self._score_execution_drift(signals)
        token_sig = self._score_token_drift(signals)
        chain_sig = self._score_chain_drift(signals)
        risk_signals.extend([exec_sig, token_sig, chain_sig])
        if any(s.score > 0.3 for s in [exec_sig, token_sig, chain_sig]):
            triggered_categories.append(ThreatCategory.BEHAVIORAL_DRIFT)

        # 4. Cross-agent coordination
        coord_sig = self._score_coordination(signals)
        risk_signals.append(coord_sig)
        if coord_sig.score > 0.3:
            triggered_categories.append(ThreatCategory.COORDINATION)

        # 5. Threshold evasion
        evasion_sig = self._score_threshold_evasion(signals)
        risk_signals.append(evasion_sig)
        if evasion_sig.score > 0.3:
            triggered_categories.append(ThreatCategory.THRESHOLD_EVASION)

        # 6. Replay attacks
        replay_sig = self._score_replay(signals)
        risk_signals.append(replay_sig)
        if replay_sig.score > 0.3:
            triggered_categories.append(ThreatCategory.REPLAY_ATTACK)

        # Weighted average
        total_weight = sum(self.WEIGHTS.get(s.signal_type, 0.0) for s in risk_signals)
        if total_weight > 0:
            overall = sum(
                s.score * self.WEIGHTS.get(s.signal_type, 0.0) for s in risk_signals
            ) / total_weight
        else:
            overall = 0.0

        overall = max(0.0, min(1.0, overall))

        return AgentThreatAssessment(
            agent_id=agent_id,
            overall_score=overall,
            action=self._determine_action(overall),
            signals=risk_signals,
            threat_categories=list(set(triggered_categories)),
        )

    # ------------------------------------------------------------------
    # Prompt injection signals
    # ------------------------------------------------------------------

    def _score_intent_mismatch(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect merchant mismatch between declared intent and actual payment."""
        if not s.declared_merchant_id or not s.actual_merchant_id:
            return RiskSignal(
                signal_type="intent_mismatch",
                weight=self.WEIGHTS["intent_mismatch"],
                score=0.0,
                description="No intent data to compare.",
            )

        if s.declared_merchant_id.lower() == s.actual_merchant_id.lower():
            return RiskSignal(
                signal_type="intent_mismatch",
                weight=self.WEIGHTS["intent_mismatch"],
                score=0.0,
                description="Merchant matches declared intent.",
            )

        return RiskSignal(
            signal_type="intent_mismatch",
            weight=self.WEIGHTS["intent_mismatch"],
            score=0.9,
            description=(
                f"Merchant mismatch: declared '{s.declared_merchant_id}' "
                f"but paying '{s.actual_merchant_id}'"
            ),
            metadata={
                "declared": s.declared_merchant_id,
                "actual": s.actual_merchant_id,
            },
        )

    def _score_amount_mismatch(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect amount deviation between declared and actual."""
        if s.declared_amount is None or s.actual_amount is None:
            return RiskSignal(
                signal_type="amount_mismatch",
                weight=self.WEIGHTS["amount_mismatch"],
                score=0.0,
                description="No amount comparison data.",
            )

        if s.declared_amount == 0:
            return RiskSignal(
                signal_type="amount_mismatch",
                weight=self.WEIGHTS["amount_mismatch"],
                score=0.0,
                description="Declared amount is zero.",
            )

        ratio = float(s.actual_amount) / float(s.declared_amount)
        if 0.9 <= ratio <= 1.1:
            score = 0.0
        elif 0.5 <= ratio <= 2.0:
            score = 0.4
        else:
            score = min(1.0, abs(ratio - 1.0) / 10.0 + 0.5)

        return RiskSignal(
            signal_type="amount_mismatch",
            weight=self.WEIGHTS["amount_mismatch"],
            score=score,
            description=(
                f"Amount ratio: {ratio:.2f}x "
                f"(declared={s.declared_amount}, actual={s.actual_amount})"
            ),
            metadata={
                "declared": str(s.declared_amount),
                "actual": str(s.actual_amount),
                "ratio": ratio,
            },
        )

    # ------------------------------------------------------------------
    # MCP tool poisoning signals
    # ------------------------------------------------------------------

    def _score_mcp_velocity(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect abnormal MCP tool call frequency."""
        if s.mcp_tool_calls == 0 or s.mcp_baseline_calls <= 0:
            return RiskSignal(
                signal_type="mcp_velocity",
                weight=self.WEIGHTS["mcp_velocity"],
                score=0.0,
                description="No MCP tool call data.",
            )

        ratio = s.mcp_tool_calls / s.mcp_baseline_calls
        if ratio <= 1.5:
            score = 0.0
        elif ratio <= self._MCP_VELOCITY_MULTIPLIER:
            score = (ratio - 1.5) / (self._MCP_VELOCITY_MULTIPLIER - 1.5) * 0.5
        else:
            score = min(1.0, 0.5 + (ratio - self._MCP_VELOCITY_MULTIPLIER) / 10.0)

        return RiskSignal(
            signal_type="mcp_velocity",
            weight=self.WEIGHTS["mcp_velocity"],
            score=score,
            description=(
                f"MCP tool calls: {s.mcp_tool_calls} "
                f"(baseline: {s.mcp_baseline_calls:.1f}, ratio: {ratio:.1f}x)"
            ),
            metadata={"calls": s.mcp_tool_calls, "baseline": s.mcp_baseline_calls, "ratio": ratio},
        )

    def _score_mcp_latency(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect abnormal MCP response latency (compromised server)."""
        if s.mcp_response_latency_ms <= 0 or s.mcp_baseline_latency_ms <= 0:
            return RiskSignal(
                signal_type="mcp_latency",
                weight=self.WEIGHTS["mcp_latency"],
                score=0.0,
                description="No MCP latency data.",
            )

        ratio = s.mcp_response_latency_ms / s.mcp_baseline_latency_ms
        if ratio <= 2.0:
            score = 0.0
        elif ratio <= self._MCP_LATENCY_MULTIPLIER:
            score = (ratio - 2.0) / (self._MCP_LATENCY_MULTIPLIER - 2.0) * 0.6
        else:
            score = min(1.0, 0.6 + (ratio - self._MCP_LATENCY_MULTIPLIER) / 20.0)

        return RiskSignal(
            signal_type="mcp_latency",
            weight=self.WEIGHTS["mcp_latency"],
            score=score,
            description=(
                f"MCP latency: {s.mcp_response_latency_ms:.0f}ms "
                f"(baseline: {s.mcp_baseline_latency_ms:.0f}ms, ratio: {ratio:.1f}x)"
            ),
            metadata={"latency_ms": s.mcp_response_latency_ms, "baseline_ms": s.mcp_baseline_latency_ms},
        )

    def _score_mcp_chain_depth(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect deep MCP tool chaining (possible infinite loop or escape)."""
        if s.mcp_chain_depth <= 0:
            return RiskSignal(
                signal_type="mcp_chain_depth",
                weight=self.WEIGHTS["mcp_chain_depth"],
                score=0.0,
                description="No MCP chain depth data.",
            )

        if s.mcp_chain_depth <= self._MCP_CHAIN_DEPTH_WARN:
            score = 0.0
        elif s.mcp_chain_depth <= self._MCP_CHAIN_DEPTH_BLOCK:
            score = (s.mcp_chain_depth - self._MCP_CHAIN_DEPTH_WARN) / (
                self._MCP_CHAIN_DEPTH_BLOCK - self._MCP_CHAIN_DEPTH_WARN
            ) * 0.8
        else:
            score = 1.0

        return RiskSignal(
            signal_type="mcp_chain_depth",
            weight=self.WEIGHTS["mcp_chain_depth"],
            score=score,
            description=f"MCP tool chain depth: {s.mcp_chain_depth}",
            metadata={"depth": s.mcp_chain_depth},
        )

    # ------------------------------------------------------------------
    # Behavioral drift signals
    # ------------------------------------------------------------------

    def _score_execution_drift(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect deviation in agent processing time (model manipulation)."""
        if s.execution_time_ms <= 0 or s.baseline_execution_std_ms <= 0:
            return RiskSignal(
                signal_type="execution_drift",
                weight=self.WEIGHTS["execution_drift"],
                score=0.0,
                description="No execution timing data.",
            )

        z = abs(s.execution_time_ms - s.baseline_execution_time_ms) / s.baseline_execution_std_ms
        if z <= 1.5:
            score = 0.0
        elif z <= self._EXECUTION_DRIFT_SIGMA:
            score = (z - 1.5) / (self._EXECUTION_DRIFT_SIGMA - 1.5) * 0.5
        else:
            score = min(1.0, 0.5 + (z - self._EXECUTION_DRIFT_SIGMA) / 6.0)

        return RiskSignal(
            signal_type="execution_drift",
            weight=self.WEIGHTS["execution_drift"],
            score=score,
            description=(
                f"Execution time {s.execution_time_ms:.0f}ms is "
                f"{z:.1f} sigma from baseline ({s.baseline_execution_time_ms:.0f}ms)"
            ),
            metadata={"time_ms": s.execution_time_ms, "baseline_ms": s.baseline_execution_time_ms, "z_score": z},
        )

    def _score_token_drift(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect sudden change in token preference."""
        if not s.token_used or not s.token_distribution:
            return RiskSignal(
                signal_type="token_drift",
                weight=self.WEIGHTS["token_drift"],
                score=0.0,
                description="No token preference data.",
            )

        usage_pct = s.token_distribution.get(s.token_used, 0.0)
        if usage_pct >= 0.1:
            score = 0.0  # Token is in normal usage pattern
        elif usage_pct > 0:
            score = 0.4  # Rare but not unseen
        else:
            score = 0.7  # Never-before-used token

        return RiskSignal(
            signal_type="token_drift",
            weight=self.WEIGHTS["token_drift"],
            score=score,
            description=(
                f"Token '{s.token_used}' usage: {usage_pct:.0%} of historical"
            ),
            metadata={"token": s.token_used, "historical_pct": usage_pct},
        )

    def _score_chain_drift(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect sudden change in chain preference."""
        if not s.chain_used or not s.chain_distribution:
            return RiskSignal(
                signal_type="chain_drift",
                weight=self.WEIGHTS["chain_drift"],
                score=0.0,
                description="No chain preference data.",
            )

        usage_pct = s.chain_distribution.get(s.chain_used, 0.0)
        if usage_pct >= 0.1:
            score = 0.0
        elif usage_pct > 0:
            score = 0.4
        else:
            score = 0.7

        return RiskSignal(
            signal_type="chain_drift",
            weight=self.WEIGHTS["chain_drift"],
            score=score,
            description=(
                f"Chain '{s.chain_used}' usage: {usage_pct:.0%} of historical"
            ),
            metadata={"chain": s.chain_used, "historical_pct": usage_pct},
        )

    # ------------------------------------------------------------------
    # Cross-agent coordination
    # ------------------------------------------------------------------

    def _score_coordination(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect coordinated multi-agent activity."""
        if s.org_agents_total_active_5min <= 1:
            return RiskSignal(
                signal_type="coordination",
                weight=self.WEIGHTS["coordination"],
                score=0.0,
                description="Single agent active, no coordination risk.",
            )

        same_merchant_ratio = s.org_agents_same_merchant_5min / s.org_agents_total_active_5min
        score = 0.0

        if same_merchant_ratio >= 0.8 and s.org_agents_same_merchant_5min >= 3:
            score = 0.85
        elif same_merchant_ratio >= 0.5 and s.org_agents_same_merchant_5min >= 2:
            score = 0.5
        elif s.amounts_sum_round_number and s.org_agents_same_merchant_5min >= 2:
            score = 0.6

        return RiskSignal(
            signal_type="coordination",
            weight=self.WEIGHTS["coordination"],
            score=score,
            description=(
                f"{s.org_agents_same_merchant_5min}/{s.org_agents_total_active_5min} "
                f"agents targeting same merchant in 5min window"
            ),
            metadata={
                "same_merchant_count": s.org_agents_same_merchant_5min,
                "total_active": s.org_agents_total_active_5min,
                "round_number": s.amounts_sum_round_number,
            },
        )

    # ------------------------------------------------------------------
    # Threshold evasion (structuring)
    # ------------------------------------------------------------------

    def _score_threshold_evasion(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect transactions just below policy limits (structuring)."""
        score = 0.0
        reasons = []

        # Per-transaction limit proximity
        if s.policy_max_per_tx and s.amount > 0:
            proximity = float(s.amount) / float(s.policy_max_per_tx)
            if proximity >= self._THRESHOLD_PROXIMITY_PCT:
                score = max(score, 0.6)
                reasons.append(f"Amount is {proximity:.0%} of per-tx limit")

        # Daily cap proximity with high velocity
        if s.policy_daily_cap and s.daily_spend_so_far > 0:
            daily_proximity = float(s.daily_spend_so_far + s.amount) / float(s.policy_daily_cap)
            if daily_proximity >= self._THRESHOLD_PROXIMITY_PCT and s.recent_tx_count_30min >= 3:
                score = max(score, 0.7)
                reasons.append(
                    f"Daily spend at {daily_proximity:.0%} of cap "
                    f"with {s.recent_tx_count_30min} txns in 30min"
                )

        # Rapid small transactions (structuring pattern)
        if s.recent_tx_count_30min >= 5 and s.policy_max_per_tx:
            avg_amount = float(s.amount)
            if avg_amount < float(s.policy_max_per_tx) * 0.3:
                score = max(score, 0.55)
                reasons.append(
                    f"Many small txns ({s.recent_tx_count_30min} in 30min) "
                    f"below per-tx limit"
                )

        return RiskSignal(
            signal_type="threshold_evasion",
            weight=self.WEIGHTS["threshold_evasion"],
            score=score,
            description="; ".join(reasons) if reasons else "No structuring pattern detected.",
            metadata={
                "amount": str(s.amount),
                "recent_tx_30min": s.recent_tx_count_30min,
            },
        )

    # ------------------------------------------------------------------
    # Replay attack detection
    # ------------------------------------------------------------------

    def _score_replay(self, s: AgentThreatSignals) -> RiskSignal:
        """Detect mandate replay or staleness."""
        score = 0.0
        reasons = []

        if s.is_duplicate_mandate:
            score = 1.0
            reasons.append("Duplicate mandate detected (idempotency violation)")

        if s.mandate_age_seconds > self._MANDATE_MAX_AGE_S:
            age_score = min(1.0, s.mandate_age_seconds / (self._MANDATE_MAX_AGE_S * 3))
            score = max(score, age_score)
            reasons.append(f"Mandate age: {s.mandate_age_seconds:.0f}s (max: {self._MANDATE_MAX_AGE_S:.0f}s)")

        return RiskSignal(
            signal_type="replay",
            weight=self.WEIGHTS["replay"],
            score=score,
            description="; ".join(reasons) if reasons else "No replay indicators.",
            metadata={
                "is_duplicate": s.is_duplicate_mandate,
                "mandate_age_s": s.mandate_age_seconds,
            },
        )

    # ------------------------------------------------------------------
    # Action determination
    # ------------------------------------------------------------------

    def _determine_action(self, score: float) -> RiskAction:
        """Map overall score to action (same thresholds as AnomalyEngine)."""
        if score < 0.30:
            return RiskAction.ALLOW
        if score < 0.60:
            return RiskAction.FLAG
        if score < 0.80:
            return RiskAction.REQUIRE_APPROVAL
        if score < 0.95:
            return RiskAction.FREEZE_AGENT
        return RiskAction.KILL_SWITCH


# Singleton
_detector: AgentThreatDetector | None = None


def get_agent_threat_detector() -> AgentThreatDetector:
    """Get the global AgentThreatDetector singleton."""
    global _detector
    if _detector is None:
        _detector = AgentThreatDetector()
    return _detector
