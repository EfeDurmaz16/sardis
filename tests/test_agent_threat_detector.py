"""Tests for AI agent-specific threat detection.

Covers issue #135.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from sardis_guardrails.agent_threat_detector import (
    AgentThreatDetector,
    AgentThreatSignals,
    ThreatCategory,
    get_agent_threat_detector,
)
from sardis_guardrails.anomaly_engine import RiskAction


class TestPromptInjectionDetection:
    """Detect prompt injection → payment attacks."""

    def test_merchant_mismatch_high_score(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            declared_merchant_id="api-credits-provider",
            actual_merchant_id="offshore-gaming-site",
        )
        result = detector.assess("agent-1", signals)
        # Intent mismatch should have high score
        intent_sig = next(s for s in result.signals if s.signal_type == "intent_mismatch")
        assert intent_sig.score >= 0.8

    def test_merchant_match_zero_score(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            declared_merchant_id="api-credits",
            actual_merchant_id="api-credits",
        )
        result = detector.assess("agent-1", signals)
        intent_sig = next(s for s in result.signals if s.signal_type == "intent_mismatch")
        assert intent_sig.score == 0.0

    def test_amount_mismatch_100x(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            declared_amount=Decimal("50"),
            actual_amount=Decimal("5000"),
        )
        result = detector.assess("agent-1", signals)
        amount_sig = next(s for s in result.signals if s.signal_type == "amount_mismatch")
        assert amount_sig.score >= 0.5
        assert ThreatCategory.PROMPT_INJECTION in result.threat_categories

    def test_amount_match_within_10pct(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            declared_amount=Decimal("100"),
            actual_amount=Decimal("105"),
        )
        result = detector.assess("agent-1", signals)
        amount_sig = next(s for s in result.signals if s.signal_type == "amount_mismatch")
        assert amount_sig.score == 0.0


class TestMCPToolPoisoning:
    """Detect MCP tool poisoning via velocity, latency, and chain depth."""

    def test_high_velocity_flagged(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            mcp_tool_calls=15,
            mcp_baseline_calls=3.0,
        )
        result = detector.assess("agent-2", signals)
        vel_sig = next(s for s in result.signals if s.signal_type == "mcp_velocity")
        assert vel_sig.score > 0.3
        assert ThreatCategory.MCP_TOOL_POISONING in result.threat_categories

    def test_normal_velocity_allowed(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            mcp_tool_calls=3,
            mcp_baseline_calls=3.0,
        )
        result = detector.assess("agent-2", signals)
        vel_sig = next(s for s in result.signals if s.signal_type == "mcp_velocity")
        assert vel_sig.score == 0.0

    def test_high_latency_flagged(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            mcp_response_latency_ms=800.0,
            mcp_baseline_latency_ms=100.0,
        )
        result = detector.assess("agent-2", signals)
        lat_sig = next(s for s in result.signals if s.signal_type == "mcp_latency")
        assert lat_sig.score > 0.3

    def test_deep_chain_blocked(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(mcp_chain_depth=20)
        result = detector.assess("agent-2", signals)
        depth_sig = next(s for s in result.signals if s.signal_type == "mcp_chain_depth")
        assert depth_sig.score >= 0.8

    def test_normal_chain_depth_allowed(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(mcp_chain_depth=3)
        result = detector.assess("agent-2", signals)
        depth_sig = next(s for s in result.signals if s.signal_type == "mcp_chain_depth")
        assert depth_sig.score == 0.0


class TestBehavioralDrift:
    """Detect agent behavioral fingerprint changes."""

    def test_execution_time_drift(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            execution_time_ms=2000.0,  # Way above baseline
            baseline_execution_time_ms=200.0,
            baseline_execution_std_ms=50.0,
        )
        result = detector.assess("agent-3", signals)
        exec_sig = next(s for s in result.signals if s.signal_type == "execution_drift")
        assert exec_sig.score > 0.3
        assert ThreatCategory.BEHAVIORAL_DRIFT in result.threat_categories

    def test_normal_execution_time(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            execution_time_ms=210.0,
            baseline_execution_time_ms=200.0,
            baseline_execution_std_ms=50.0,
        )
        result = detector.assess("agent-3", signals)
        exec_sig = next(s for s in result.signals if s.signal_type == "execution_drift")
        assert exec_sig.score == 0.0

    def test_never_used_token_flagged(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            token_used="USDT",
            token_distribution={"USDC": 0.95, "EURC": 0.05},
        )
        result = detector.assess("agent-3", signals)
        token_sig = next(s for s in result.signals if s.signal_type == "token_drift")
        assert token_sig.score >= 0.5

    def test_common_token_allowed(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            token_used="USDC",
            token_distribution={"USDC": 0.90, "EURC": 0.10},
        )
        result = detector.assess("agent-3", signals)
        token_sig = next(s for s in result.signals if s.signal_type == "token_drift")
        assert token_sig.score == 0.0

    def test_never_used_chain_flagged(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            chain_used="bsc",
            chain_distribution={"base": 0.80, "ethereum": 0.20},
        )
        result = detector.assess("agent-3", signals)
        chain_sig = next(s for s in result.signals if s.signal_type == "chain_drift")
        assert chain_sig.score >= 0.5


class TestCrossAgentCoordination:
    """Detect coordinated multi-agent fraud."""

    def test_many_agents_same_merchant(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            org_agents_same_merchant_5min=5,
            org_agents_total_active_5min=6,
        )
        result = detector.assess("agent-4", signals)
        coord_sig = next(s for s in result.signals if s.signal_type == "coordination")
        assert coord_sig.score >= 0.7
        assert ThreatCategory.COORDINATION in result.threat_categories

    def test_single_agent_no_coordination(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            org_agents_same_merchant_5min=0,
            org_agents_total_active_5min=1,
        )
        result = detector.assess("agent-4", signals)
        coord_sig = next(s for s in result.signals if s.signal_type == "coordination")
        assert coord_sig.score == 0.0

    def test_round_number_suspicious(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            org_agents_same_merchant_5min=3,
            org_agents_total_active_5min=10,
            amounts_sum_round_number=True,
        )
        result = detector.assess("agent-4", signals)
        coord_sig = next(s for s in result.signals if s.signal_type == "coordination")
        assert coord_sig.score >= 0.5


class TestThresholdEvasion:
    """Detect structuring / threshold evasion patterns."""

    def test_near_per_tx_limit(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            amount=Decimal("980"),
            policy_max_per_tx=Decimal("1000"),
        )
        result = detector.assess("agent-5", signals)
        evasion_sig = next(s for s in result.signals if s.signal_type == "threshold_evasion")
        assert evasion_sig.score >= 0.5
        assert ThreatCategory.THRESHOLD_EVASION in result.threat_categories

    def test_normal_amount_no_evasion(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            amount=Decimal("50"),
            policy_max_per_tx=Decimal("1000"),
        )
        result = detector.assess("agent-5", signals)
        evasion_sig = next(s for s in result.signals if s.signal_type == "threshold_evasion")
        assert evasion_sig.score == 0.0

    def test_rapid_small_txns(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            amount=Decimal("100"),
            policy_max_per_tx=Decimal("1000"),
            recent_tx_count_30min=8,
        )
        result = detector.assess("agent-5", signals)
        evasion_sig = next(s for s in result.signals if s.signal_type == "threshold_evasion")
        assert evasion_sig.score >= 0.4


class TestReplayAttacks:
    """Detect mandate replay and staleness."""

    def test_duplicate_mandate_blocked(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(is_duplicate_mandate=True)
        result = detector.assess("agent-6", signals)
        replay_sig = next(s for s in result.signals if s.signal_type == "replay")
        assert replay_sig.score == 1.0
        assert ThreatCategory.REPLAY_ATTACK in result.threat_categories

    def test_stale_mandate_flagged(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(mandate_age_seconds=600.0)  # 10 minutes
        result = detector.assess("agent-6", signals)
        replay_sig = next(s for s in result.signals if s.signal_type == "replay")
        assert replay_sig.score > 0.3

    def test_fresh_mandate_allowed(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(mandate_age_seconds=30.0)
        result = detector.assess("agent-6", signals)
        replay_sig = next(s for s in result.signals if s.signal_type == "replay")
        assert replay_sig.score == 0.0


class TestOverallAssessment:
    """Test combined scoring and action determination."""

    def test_clean_transaction_allowed(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals()  # All defaults = safe
        result = detector.assess("agent-clean", signals)
        assert result.action == RiskAction.ALLOW
        assert result.overall_score < 0.3
        assert not result.should_block
        assert not result.requires_review

    def test_multi_threat_escalates(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            # Prompt injection
            declared_merchant_id="legit-api",
            actual_merchant_id="scam-merchant",
            declared_amount=Decimal("100"),
            actual_amount=Decimal("10000"),
            # MCP poisoning
            mcp_tool_calls=30,
            mcp_baseline_calls=3.0,
            # Behavioral drift
            execution_time_ms=5000.0,
            baseline_execution_time_ms=200.0,
            baseline_execution_std_ms=50.0,
        )
        result = detector.assess("agent-multi-threat", signals)
        assert result.overall_score > 0.5
        assert len(result.threat_categories) >= 2

    def test_should_block_property(self):
        detector = AgentThreatDetector()
        signals = AgentThreatSignals(
            declared_merchant_id="legit",
            actual_merchant_id="scam",
            declared_amount=Decimal("10"),
            actual_amount=Decimal("100000"),
            is_duplicate_mandate=True,
            mcp_tool_calls=50,
            mcp_baseline_calls=3.0,
            mcp_chain_depth=20,
        )
        result = detector.assess("agent-extreme", signals)
        # Multiple extreme signals should push score very high
        assert result.overall_score > 0.5

    def test_singleton(self):
        d1 = get_agent_threat_detector()
        d2 = get_agent_threat_detector()
        assert d1 is d2


class TestModuleExports:
    """Verify exports from sardis_guardrails."""

    def test_detector_exported(self):
        from sardis_guardrails import AgentThreatDetector
        assert AgentThreatDetector is not None

    def test_signals_exported(self):
        from sardis_guardrails import AgentThreatSignals
        assert AgentThreatSignals is not None

    def test_assessment_exported(self):
        from sardis_guardrails import AgentThreatAssessment
        assert AgentThreatAssessment is not None

    def test_threat_category_exported(self):
        from sardis_guardrails import ThreatCategory
        assert ThreatCategory is not None
