"""Tests for graph-based fraud detection.

Covers issue #143. Tests transaction graph construction, pattern
detection (circular, hub-spoke, rapid chains, peeling chains,
pass-through, clusters), and risk scoring.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from sardis_guardrails.graph_fraud import (
    CLUSTER_MIN_SIZE,
    HUB_DEGREE_THRESHOLD,
    MAX_CYCLE_LENGTH,
    PATTERN_RISK_WEIGHTS,
    RAPID_CHAIN_MIN_LENGTH,
    GraphAnalysisResult,
    GraphFraudAnalyzer,
    GraphPattern,
    GraphRiskLevel,
    PatternMatch,
    TransactionEdge,
    TransactionGraph,
    WalletNode,
    create_graph_analyzer,
    detect_clusters,
    detect_cycles,
    detect_hub_spoke,
    detect_pass_through,
    detect_peeling_chains,
    detect_rapid_chains,
)


def _edge(from_w: str, to_w: str, amount: float, minutes_offset: int = 0, tx_id: str = "") -> TransactionEdge:
    """Helper to create a transaction edge."""
    return TransactionEdge(
        tx_id=tx_id or f"tx_{from_w}_{to_w}_{minutes_offset}",
        from_wallet=from_w,
        to_wallet=to_w,
        amount=Decimal(str(amount)),
        timestamp=datetime(2026, 3, 1, tzinfo=UTC) + timedelta(minutes=minutes_offset),
    )


# ============ Transaction Graph Tests ============


class TestTransactionGraph:
    def test_add_transaction(self):
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100))
        assert graph.node_count == 2
        assert graph.edge_count == 1

    def test_node_totals(self):
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100))
        graph.add_transaction(_edge("A", "C", 50))
        node_a = graph.get_node("A")
        assert node_a.total_sent == Decimal("150")
        assert node_a.total_received == Decimal("0")

    def test_node_degree(self):
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100))
        graph.add_transaction(_edge("A", "C", 50))
        graph.add_transaction(_edge("D", "A", 200))
        node_a = graph.get_node("A")
        assert node_a.out_degree == 2
        assert node_a.in_degree == 1
        assert node_a.degree == 3

    def test_get_neighbors(self):
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100))
        graph.add_transaction(_edge("C", "A", 50))
        neighbors = graph.get_neighbors("A")
        assert neighbors == {"B", "C"}

    def test_get_edges_between(self):
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100, 0))
        graph.add_transaction(_edge("A", "B", 200, 5))
        graph.add_transaction(_edge("A", "C", 50, 10))
        edges = graph.get_edges_between("A", "B")
        assert len(edges) == 2

    def test_net_flow(self):
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100))
        graph.add_transaction(_edge("B", "A", 30))
        node_a = graph.get_node("A")
        assert node_a.net_flow == Decimal("-70")  # Sent 100, received 30

    def test_timestamps(self):
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100, 0))
        graph.add_transaction(_edge("A", "C", 50, 60))
        node_a = graph.get_node("A")
        assert node_a.first_seen is not None
        assert node_a.last_seen is not None
        assert node_a.last_seen > node_a.first_seen

    def test_add_transactions_bulk(self):
        graph = TransactionGraph()
        edges = [_edge("A", "B", 100, i) for i in range(10)]
        graph.add_transactions(edges)
        assert graph.edge_count == 10

    def test_get_node_not_found(self):
        graph = TransactionGraph()
        assert graph.get_node("nonexistent") is None


# ============ Wallet Node Tests ============


class TestWalletNode:
    def test_pass_through_detection(self):
        node = WalletNode(
            address="A",
            total_sent=Decimal("1000"),
            total_received=Decimal("1050"),
        )
        assert node.is_pass_through is True

    def test_not_pass_through(self):
        node = WalletNode(
            address="A",
            total_sent=Decimal("100"),
            total_received=Decimal("1000"),
        )
        assert node.is_pass_through is False

    def test_zero_received(self):
        node = WalletNode(address="A", total_sent=Decimal("100"))
        assert node.is_pass_through is False


# ============ Circular Pattern Tests ============


class TestCircularDetection:
    def test_simple_cycle(self):
        """A → B → C → A"""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100, 0))
        graph.add_transaction(_edge("B", "C", 100, 5))
        graph.add_transaction(_edge("C", "A", 100, 10))
        patterns = detect_cycles(graph, "A")
        assert len(patterns) >= 1
        assert patterns[0].pattern == GraphPattern.CIRCULAR
        assert set(patterns[0].wallets_involved) == {"A", "B", "C"}

    def test_no_cycle(self):
        """A → B → C (no return)"""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100))
        graph.add_transaction(_edge("B", "C", 100))
        patterns = detect_cycles(graph, "A")
        assert len(patterns) == 0

    def test_cycle_confidence(self):
        """Higher confidence when amounts are consistent."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100, 0))
        graph.add_transaction(_edge("B", "C", 100, 5))
        graph.add_transaction(_edge("C", "A", 100, 10))
        patterns = detect_cycles(graph, "A")
        assert patterns[0].confidence > 0.5

    def test_nonexistent_wallet(self):
        graph = TransactionGraph()
        patterns = detect_cycles(graph, "Z")
        assert patterns == []


# ============ Hub-Spoke Tests ============


class TestHubSpokeDetection:
    def test_fan_out(self):
        """One sender to many receivers."""
        graph = TransactionGraph()
        for i in range(HUB_DEGREE_THRESHOLD):
            graph.add_transaction(_edge("HUB", f"SPOKE_{i}", 100, i))
        patterns = detect_hub_spoke(graph, HUB_DEGREE_THRESHOLD)
        fan_outs = [p for p in patterns if p.pattern == GraphPattern.FAN_OUT]
        assert len(fan_outs) >= 1
        assert "HUB" in fan_outs[0].wallets_involved

    def test_fan_in(self):
        """Many senders to one receiver."""
        graph = TransactionGraph()
        for i in range(HUB_DEGREE_THRESHOLD):
            graph.add_transaction(_edge(f"SOURCE_{i}", "COLLECTOR", 100, i))
        patterns = detect_hub_spoke(graph, HUB_DEGREE_THRESHOLD)
        fan_ins = [p for p in patterns if p.pattern == GraphPattern.FAN_IN]
        assert len(fan_ins) >= 1

    def test_below_threshold(self):
        """Not enough connections for hub detection."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100))
        graph.add_transaction(_edge("A", "C", 100))
        patterns = detect_hub_spoke(graph, HUB_DEGREE_THRESHOLD)
        fan_outs = [p for p in patterns if p.pattern == GraphPattern.FAN_OUT]
        assert len(fan_outs) == 0


# ============ Rapid Chain Tests ============


class TestRapidChainDetection:
    def test_rapid_chain(self):
        """A → B → C → D within 30 min each."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 1000, 0))
        graph.add_transaction(_edge("B", "C", 900, 10))
        graph.add_transaction(_edge("C", "D", 800, 20))
        patterns = detect_rapid_chains(graph, max_delay_minutes=30, min_length=3)
        assert len(patterns) >= 1
        assert patterns[0].pattern == GraphPattern.RAPID_CHAIN
        assert len(patterns[0].wallets_involved) >= 4

    def test_slow_chain_no_match(self):
        """Transfers too far apart."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 1000, 0))
        graph.add_transaction(_edge("B", "C", 900, 120))  # 2 hours later
        graph.add_transaction(_edge("C", "D", 800, 240))
        patterns = detect_rapid_chains(graph, max_delay_minutes=30, min_length=3)
        assert len(patterns) == 0

    def test_short_chain_no_match(self):
        """Chain too short."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 1000, 0))
        graph.add_transaction(_edge("B", "C", 900, 5))
        patterns = detect_rapid_chains(graph, max_delay_minutes=30, min_length=3)
        assert len(patterns) == 0


# ============ Peeling Chain Tests ============


class TestPeelingChainDetection:
    def test_peeling_chain(self):
        """Decreasing amounts: 1000 → 800 → 640 → 512."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 1000, 0))
        graph.add_transaction(_edge("B", "C", 800, 5))
        graph.add_transaction(_edge("C", "D", 640, 10))
        graph.add_transaction(_edge("D", "E", 512, 15))
        patterns = detect_peeling_chains(graph, min_length=3)
        assert len(patterns) >= 1
        assert patterns[0].pattern == GraphPattern.PEELING_CHAIN

    def test_constant_amounts_no_peeling(self):
        """Same amounts don't trigger peeling (too close to 1.0 ratio)."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 1000, 0))
        graph.add_transaction(_edge("B", "C", 1000, 5))
        graph.add_transaction(_edge("C", "D", 1000, 10))
        patterns = detect_peeling_chains(graph, min_length=3)
        assert len(patterns) == 0

    def test_increasing_amounts_no_peeling(self):
        """Increasing amounts don't match peeling pattern."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100, 0))
        graph.add_transaction(_edge("B", "C", 200, 5))
        graph.add_transaction(_edge("C", "D", 400, 10))
        patterns = detect_peeling_chains(graph, min_length=3)
        assert len(patterns) == 0


# ============ Pass-Through Tests ============


class TestPassThroughDetection:
    def test_pass_through_wallet(self):
        """Wallet receives and sends roughly equal amounts."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("X", "TRANSIT", 1000, 0))
        graph.add_transaction(_edge("Y", "TRANSIT", 500, 5))
        graph.add_transaction(_edge("TRANSIT", "Z", 1400, 10))
        patterns = detect_pass_through(graph)
        transit_matches = [
            p for p in patterns
            if "TRANSIT" in p.wallets_involved and p.pattern == GraphPattern.PASS_THROUGH
        ]
        assert len(transit_matches) >= 1

    def test_no_pass_through(self):
        """Wallet only sends, doesn't receive."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 1000))
        patterns = detect_pass_through(graph)
        assert len(patterns) == 0


# ============ Cluster Detection Tests ============


class TestClusterDetection:
    def test_connected_cluster(self):
        """3+ wallets forming a cluster."""
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100, 0))
        graph.add_transaction(_edge("B", "C", 100, 5))
        graph.add_transaction(_edge("C", "A", 100, 10))
        graph.add_transaction(_edge("A", "C", 50, 15))
        patterns = detect_clusters(graph, min_cluster_size=3)
        assert len(patterns) >= 1
        assert patterns[0].pattern == GraphPattern.CLUSTER

    def test_too_small_cluster(self):
        graph = TransactionGraph()
        graph.add_transaction(_edge("A", "B", 100))
        patterns = detect_clusters(graph, min_cluster_size=3)
        assert len(patterns) == 0

    def test_isolated_clusters(self):
        """Two separate clusters."""
        graph = TransactionGraph()
        # Cluster 1
        graph.add_transaction(_edge("A1", "A2", 100))
        graph.add_transaction(_edge("A2", "A3", 100))
        graph.add_transaction(_edge("A3", "A1", 100))
        # Cluster 2 (separate)
        graph.add_transaction(_edge("B1", "B2", 200))
        graph.add_transaction(_edge("B2", "B3", 200))
        graph.add_transaction(_edge("B3", "B1", 200))
        patterns = detect_clusters(graph, min_cluster_size=3)
        assert len(patterns) >= 2


# ============ Pattern Match Properties ============


class TestPatternMatch:
    def test_risk_weight(self):
        match = PatternMatch(pattern=GraphPattern.CIRCULAR, confidence=1.0)
        assert match.risk_weight == PATTERN_RISK_WEIGHTS[GraphPattern.CIRCULAR]

    def test_risk_score(self):
        match = PatternMatch(pattern=GraphPattern.CIRCULAR, confidence=0.8)
        expected = PATTERN_RISK_WEIGHTS[GraphPattern.CIRCULAR] * 0.8
        assert abs(match.risk_score - expected) < 0.01

    def test_risk_score_low_confidence(self):
        match = PatternMatch(pattern=GraphPattern.CLUSTER, confidence=0.3)
        assert match.risk_score < 0.25


# ============ Full Analysis Tests ============


class TestGraphFraudAnalyzer:
    def test_clean_transactions(self):
        """Simple A→B, C→D should be clean."""
        analyzer = GraphFraudAnalyzer()
        edges = [
            _edge("A", "B", 100, 0),
            _edge("C", "D", 200, 60),
        ]
        result = analyzer.analyze(edges, focus_wallet="A")
        assert isinstance(result, GraphAnalysisResult)
        assert result.risk_level == GraphRiskLevel.CLEAN
        assert result.risk_score == 0.0

    def test_circular_analysis(self):
        """Full analysis detecting a circular pattern."""
        analyzer = GraphFraudAnalyzer()
        edges = [
            _edge("A", "B", 1000, 0),
            _edge("B", "C", 1000, 5),
            _edge("C", "A", 1000, 10),
        ]
        result = analyzer.analyze(edges, focus_wallet="A")
        assert result.has_suspicious_patterns is True
        assert GraphPattern.CIRCULAR in result.pattern_types

    def test_analysis_metadata(self):
        analyzer = GraphFraudAnalyzer()
        edges = [_edge("A", "B", 100)]
        result = analyzer.analyze(edges, focus_wallet="A")
        assert result.node_count == 2
        assert result.edge_count == 1
        assert result.analyzed_at is not None

    def test_highest_risk_pattern(self):
        analyzer = GraphFraudAnalyzer()
        edges = [
            _edge("A", "B", 1000, 0),
            _edge("B", "C", 1000, 5),
            _edge("C", "A", 1000, 10),
        ]
        result = analyzer.analyze(edges, focus_wallet="A")
        if result.has_suspicious_patterns:
            highest = result.highest_risk_pattern
            assert highest is not None
            assert highest.risk_score > 0

    def test_no_focus_wallet(self):
        """Analysis without focus_wallet runs cycles on all nodes."""
        analyzer = GraphFraudAnalyzer()
        edges = [
            _edge("A", "B", 1000, 0),
            _edge("B", "C", 1000, 5),
            _edge("C", "A", 1000, 10),
        ]
        result = analyzer.analyze(edges)
        assert result.subject_wallet == ""
        # Should still detect circular
        assert result.has_suspicious_patterns is True

    def test_complex_network(self):
        """Network with multiple pattern types."""
        analyzer = GraphFraudAnalyzer(hub_threshold=3, min_cluster_size=3)
        edges = [
            # Circular: A → B → C → A
            _edge("A", "B", 1000, 0),
            _edge("B", "C", 1000, 5),
            _edge("C", "A", 1000, 10),
            # Fan-out from HUB
            _edge("HUB", "D1", 500, 20),
            _edge("HUB", "D2", 500, 21),
            _edge("HUB", "D3", 500, 22),
        ]
        result = analyzer.analyze(edges, focus_wallet="A")
        assert result.risk_score > 0


# ============ Risk Level Tests ============


class TestRiskLevels:
    def test_clean(self):
        analyzer = GraphFraudAnalyzer()
        assert analyzer._score_to_level(0.0) == GraphRiskLevel.CLEAN

    def test_low(self):
        analyzer = GraphFraudAnalyzer()
        assert analyzer._score_to_level(0.20) == GraphRiskLevel.LOW

    def test_medium(self):
        analyzer = GraphFraudAnalyzer()
        assert analyzer._score_to_level(0.40) == GraphRiskLevel.MEDIUM

    def test_high(self):
        analyzer = GraphFraudAnalyzer()
        assert analyzer._score_to_level(0.60) == GraphRiskLevel.HIGH

    def test_critical(self):
        analyzer = GraphFraudAnalyzer()
        assert analyzer._score_to_level(0.90) == GraphRiskLevel.CRITICAL


# ============ Analysis Result Properties ============


class TestAnalysisResultProperties:
    def test_has_no_patterns(self):
        result = GraphAnalysisResult(subject_wallet="A")
        assert result.has_suspicious_patterns is False
        assert result.highest_risk_pattern is None
        assert result.pattern_types == []

    def test_has_patterns(self):
        result = GraphAnalysisResult(
            subject_wallet="A",
            patterns=[
                PatternMatch(pattern=GraphPattern.CIRCULAR, confidence=0.8),
            ],
        )
        assert result.has_suspicious_patterns is True
        assert result.pattern_types == [GraphPattern.CIRCULAR]


# ============ Enum Tests ============


class TestEnums:
    def test_graph_patterns(self):
        assert len(GraphPattern) == 8

    def test_risk_levels(self):
        assert len(GraphRiskLevel) == 5

    def test_pattern_values(self):
        assert GraphPattern.CIRCULAR.value == "circular"
        assert GraphPattern.PEELING_CHAIN.value == "peeling_chain"


# ============ Constants Tests ============


class TestConstants:
    def test_risk_weights_all_present(self):
        for pattern in GraphPattern:
            assert pattern in PATTERN_RISK_WEIGHTS

    def test_risk_weights_range(self):
        for weight in PATTERN_RISK_WEIGHTS.values():
            assert 0.0 < weight <= 1.0

    def test_default_thresholds(self):
        assert MAX_CYCLE_LENGTH == 6
        assert HUB_DEGREE_THRESHOLD == 5
        assert RAPID_CHAIN_MIN_LENGTH == 3
        assert CLUSTER_MIN_SIZE == 3


# ============ Factory Tests ============


class TestFactory:
    def test_create_analyzer(self):
        analyzer = create_graph_analyzer()
        assert isinstance(analyzer, GraphFraudAnalyzer)

    def test_create_custom(self):
        analyzer = create_graph_analyzer(
            hub_threshold=10,
            rapid_chain_delay_minutes=60,
        )
        assert analyzer._hub_threshold == 10
        assert analyzer._rapid_delay == 60


# ============ Module Export Tests ============


class TestModuleExports:
    def test_imports_from_guardrails(self):
        from sardis_guardrails import (
            GraphAnalysisResult,
            GraphFraudAnalyzer,
            GraphPattern,
            GraphRiskLevel,
            PatternMatch,
            TransactionEdge,
            TransactionGraph,
            WalletNode,
            create_graph_analyzer,
        )
        assert all([
            GraphAnalysisResult, GraphFraudAnalyzer, GraphPattern,
            GraphRiskLevel, PatternMatch, TransactionEdge,
            TransactionGraph, WalletNode, create_graph_analyzer,
        ])
