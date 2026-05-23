"""Graph-based fraud detection for transaction networks.

Analyzes transaction graph topology to detect fraud patterns that
are invisible to single-transaction analysis:
- Circular transactions (layering / round-tripping)
- Hub-and-spoke patterns (mule networks)
- Rapid fund movement chains (smurfing)
- Wallet cluster detection (related entities)
- Topology-based risk scoring

Uses pure Python graph algorithms (no external graph library required).
Designed to feed risk signals into AnomalyEngine.

Reference patterns:
- FATF Red Flag Indicators for ML/TF
- Chainalysis Typology Reports
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============ Enums ============


class GraphPattern(str, Enum):
    """Detected graph fraud patterns."""
    CIRCULAR = "circular"              # A → B → C → A (layering)
    HUB_SPOKE = "hub_spoke"            # Central node fans out/in (mule)
    RAPID_CHAIN = "rapid_chain"        # Fast sequential transfers
    CLUSTER = "cluster"                # Tightly connected wallet group
    FAN_OUT = "fan_out"                # One source, many destinations
    FAN_IN = "fan_in"                  # Many sources, one destination
    PEELING_CHAIN = "peeling_chain"    # Decreasing-amount chain
    PASS_THROUGH = "pass_through"      # Funds in = funds out (transit)


class GraphRiskLevel(str, Enum):
    """Risk level from graph analysis."""
    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============ Constants ============

# Circular detection
MAX_CYCLE_LENGTH = 6
MIN_CYCLE_AMOUNT_RATIO = 0.5  # Min ratio of amounts to count as circular

# Hub-spoke detection
HUB_DEGREE_THRESHOLD = 5      # Min connections to be a hub
HUB_TIME_WINDOW_HOURS = 24    # Window for hub activity

# Rapid chain detection
RAPID_CHAIN_MAX_DELAY_MINUTES = 30  # Max time between hops
RAPID_CHAIN_MIN_LENGTH = 3          # Min hops in a chain

# Cluster detection
CLUSTER_MIN_SIZE = 3          # Min wallets in a cluster
CLUSTER_MAX_DISTANCE = 2      # Max hops for clustering

# Peeling chain detection
PEELING_AMOUNT_DECAY_MIN = 0.6   # Min ratio of next/prev amount
PEELING_AMOUNT_DECAY_MAX = 0.99  # Max ratio (nearly same = pass-through)
PEELING_MIN_LENGTH = 3

# Risk weights per pattern
PATTERN_RISK_WEIGHTS: dict[GraphPattern, float] = {
    GraphPattern.CIRCULAR: 0.90,
    GraphPattern.HUB_SPOKE: 0.75,
    GraphPattern.RAPID_CHAIN: 0.70,
    GraphPattern.CLUSTER: 0.50,
    GraphPattern.FAN_OUT: 0.60,
    GraphPattern.FAN_IN: 0.65,
    GraphPattern.PEELING_CHAIN: 0.80,
    GraphPattern.PASS_THROUGH: 0.55,
}


# ============ Data Classes ============


@dataclass
class TransactionEdge:
    """An edge in the transaction graph."""
    tx_id: str
    from_wallet: str
    to_wallet: str
    amount: Decimal
    timestamp: datetime
    token: str = "USDC"
    chain: str = "base"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WalletNode:
    """A node (wallet) in the transaction graph."""
    address: str
    total_sent: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    tx_count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    outgoing: list[str] = field(default_factory=list)  # wallet addresses
    incoming: list[str] = field(default_factory=list)  # wallet addresses

    @property
    def net_flow(self) -> Decimal:
        """Net flow: positive = net receiver, negative = net sender."""
        return self.total_received - self.total_sent

    @property
    def degree(self) -> int:
        """Total unique connections (in + out)."""
        return len(set(self.outgoing) | set(self.incoming))

    @property
    def out_degree(self) -> int:
        return len(set(self.outgoing))

    @property
    def in_degree(self) -> int:
        return len(set(self.incoming))

    @property
    def is_pass_through(self) -> bool:
        """Wallet receives and sends roughly equal amounts."""
        if self.total_received == 0:
            return False
        ratio = float(self.total_sent / self.total_received)
        return 0.8 <= ratio <= 1.2


@dataclass
class PatternMatch:
    """A detected graph fraud pattern."""
    pattern: GraphPattern
    confidence: float  # 0.0–1.0
    wallets_involved: list[str] = field(default_factory=list)
    transactions_involved: list[str] = field(default_factory=list)
    amount: Decimal = Decimal("0")
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def risk_weight(self) -> float:
        return PATTERN_RISK_WEIGHTS.get(self.pattern, 0.5)

    @property
    def risk_score(self) -> float:
        """Combined risk: pattern weight * confidence."""
        return self.risk_weight * self.confidence


@dataclass
class GraphAnalysisResult:
    """Complete graph analysis result for a wallet or network."""
    subject_wallet: str
    patterns: list[PatternMatch] = field(default_factory=list)
    risk_level: GraphRiskLevel = GraphRiskLevel.CLEAN
    risk_score: float = 0.0
    node_count: int = 0
    edge_count: int = 0
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_suspicious_patterns(self) -> bool:
        return len(self.patterns) > 0

    @property
    def highest_risk_pattern(self) -> PatternMatch | None:
        if not self.patterns:
            return None
        return max(self.patterns, key=lambda p: p.risk_score)

    @property
    def pattern_types(self) -> list[GraphPattern]:
        return [p.pattern for p in self.patterns]


# ============ Transaction Graph ============


class TransactionGraph:
    """In-memory transaction graph for analysis.

    Builds a directed multigraph from transaction edges and provides
    methods for pattern detection. Designed for per-analysis construction
    rather than long-lived state.
    """

    def __init__(self):
        self._nodes: dict[str, WalletNode] = {}
        self._edges: list[TransactionEdge] = []
        # Adjacency: from_wallet -> [(to_wallet, edge_index)]
        self._adj: dict[str, list[tuple[str, int]]] = defaultdict(list)
        # Reverse adjacency: to_wallet -> [(from_wallet, edge_index)]
        self._rev_adj: dict[str, list[tuple[str, int]]] = defaultdict(list)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def add_transaction(self, edge: TransactionEdge) -> None:
        """Add a transaction edge to the graph."""
        idx = len(self._edges)
        self._edges.append(edge)
        self._adj[edge.from_wallet].append((edge.to_wallet, idx))
        self._rev_adj[edge.to_wallet].append((edge.from_wallet, idx))

        # Update/create nodes
        for addr in (edge.from_wallet, edge.to_wallet):
            if addr not in self._nodes:
                self._nodes[addr] = WalletNode(address=addr)

        sender = self._nodes[edge.from_wallet]
        sender.total_sent += edge.amount
        sender.tx_count += 1
        sender.outgoing.append(edge.to_wallet)
        if sender.first_seen is None or edge.timestamp < sender.first_seen:
            sender.first_seen = edge.timestamp
        if sender.last_seen is None or edge.timestamp > sender.last_seen:
            sender.last_seen = edge.timestamp

        receiver = self._nodes[edge.to_wallet]
        receiver.total_received += edge.amount
        receiver.tx_count += 1
        receiver.incoming.append(edge.from_wallet)
        if receiver.first_seen is None or edge.timestamp < receiver.first_seen:
            receiver.first_seen = edge.timestamp
        if receiver.last_seen is None or edge.timestamp > receiver.last_seen:
            receiver.last_seen = edge.timestamp

    def add_transactions(self, edges: list[TransactionEdge]) -> None:
        """Add multiple transactions."""
        for edge in edges:
            self.add_transaction(edge)

    def get_node(self, address: str) -> WalletNode | None:
        return self._nodes.get(address)

    def get_neighbors(self, address: str) -> set[str]:
        """Get all neighbors (in + out)."""
        out = {to for to, _ in self._adj.get(address, [])}
        inc = {fr for fr, _ in self._rev_adj.get(address, [])}
        return out | inc

    def get_edges_between(self, from_addr: str, to_addr: str) -> list[TransactionEdge]:
        """Get all edges from one wallet to another."""
        return [
            self._edges[idx]
            for to, idx in self._adj.get(from_addr, [])
            if to == to_addr
        ]


# ============ Pattern Detectors ============


def detect_cycles(
    graph: TransactionGraph,
    start_wallet: str,
    max_length: int = MAX_CYCLE_LENGTH,
) -> list[PatternMatch]:
    """Detect circular transaction patterns (layering).

    Uses DFS to find cycles starting and ending at the given wallet.
    """
    results: list[PatternMatch] = []
    if start_wallet not in graph._nodes:
        return results

    # DFS with path tracking
    stack: list[tuple[str, list[str], list[int]]] = [
        (start_wallet, [start_wallet], [])
    ]
    visited_cycles: set[tuple[str, ...]] = set()

    while stack:
        current, path, edge_indices = stack.pop()

        if len(path) > max_length + 1:
            continue

        for neighbor, edge_idx in graph._adj.get(current, []):
            if neighbor == start_wallet and len(path) >= 3:
                # Found a cycle
                cycle_key = tuple(sorted(path))
                if cycle_key not in visited_cycles:
                    visited_cycles.add(cycle_key)
                    tx_ids = [graph._edges[i].tx_id for i in edge_indices + [edge_idx]]
                    amounts = [graph._edges[i].amount for i in edge_indices + [edge_idx]]
                    total = sum(amounts, Decimal("0"))

                    # Confidence based on amount consistency
                    if amounts:
                        avg = total / len(amounts)
                        variance = sum(
                            float((a - avg) ** 2) for a in amounts
                        ) / len(amounts)
                        consistency = 1.0 / (1.0 + math.sqrt(variance) / float(avg)) if avg else 0
                    else:
                        consistency = 0

                    confidence = min(1.0, consistency * (1 + 0.1 * len(path)))

                    results.append(PatternMatch(
                        pattern=GraphPattern.CIRCULAR,
                        confidence=confidence,
                        wallets_involved=list(path),
                        transactions_involved=tx_ids,
                        amount=total,
                        description=(
                            f"Circular transaction: {' → '.join(path)} → {start_wallet} "
                            f"({len(path)} hops, ${total:.2f})"
                        ),
                        metadata={"cycle_length": len(path)},
                    ))

            elif neighbor not in path and len(path) <= max_length:
                stack.append((
                    neighbor,
                    path + [neighbor],
                    edge_indices + [edge_idx],
                ))

    return results


def detect_hub_spoke(
    graph: TransactionGraph,
    min_degree: int = HUB_DEGREE_THRESHOLD,
) -> list[PatternMatch]:
    """Detect hub-and-spoke patterns (mule networks).

    A hub is a wallet with high out-degree (fan-out) or high
    in-degree (fan-in) beyond the threshold.
    """
    results: list[PatternMatch] = []

    for addr, node in graph._nodes.items():
        # Fan-out pattern (one source, many destinations)
        unique_out = set(node.outgoing)
        if len(unique_out) >= min_degree:
            results.append(PatternMatch(
                pattern=GraphPattern.FAN_OUT,
                confidence=min(1.0, len(unique_out) / (min_degree * 2)),
                wallets_involved=[addr] + list(unique_out),
                amount=node.total_sent,
                description=(
                    f"Fan-out hub: {addr} sent to {len(unique_out)} unique wallets "
                    f"(${node.total_sent:.2f} total)"
                ),
                metadata={"out_degree": len(unique_out)},
            ))

        # Fan-in pattern (many sources, one destination)
        unique_in = set(node.incoming)
        if len(unique_in) >= min_degree:
            results.append(PatternMatch(
                pattern=GraphPattern.FAN_IN,
                confidence=min(1.0, len(unique_in) / (min_degree * 2)),
                wallets_involved=list(unique_in) + [addr],
                amount=node.total_received,
                description=(
                    f"Fan-in hub: {addr} received from {len(unique_in)} unique wallets "
                    f"(${node.total_received:.2f} total)"
                ),
                metadata={"in_degree": len(unique_in)},
            ))

        # Combined hub-spoke (high total degree)
        if node.degree >= min_degree * 2:
            results.append(PatternMatch(
                pattern=GraphPattern.HUB_SPOKE,
                confidence=min(1.0, node.degree / (min_degree * 4)),
                wallets_involved=[addr] + list(set(node.outgoing) | set(node.incoming)),
                amount=node.total_sent + node.total_received,
                description=(
                    f"Hub-spoke pattern: {addr} has {node.degree} connections "
                    f"(in:{node.in_degree}, out:{node.out_degree})"
                ),
                metadata={"degree": node.degree},
            ))

    return results


def detect_rapid_chains(
    graph: TransactionGraph,
    max_delay_minutes: int = RAPID_CHAIN_MAX_DELAY_MINUTES,
    min_length: int = RAPID_CHAIN_MIN_LENGTH,
) -> list[PatternMatch]:
    """Detect rapid fund movement chains.

    Finds sequences of transactions where funds move through
    multiple wallets in quick succession (smurfing indicator).
    """
    results: list[PatternMatch] = []
    visited_chains: set[tuple[str, ...]] = set()

    # Sort edges by timestamp
    sorted_edges = sorted(graph._edges, key=lambda e: e.timestamp)
    delay = timedelta(minutes=max_delay_minutes)

    # For each edge, try to extend a chain forward
    for start_edge in sorted_edges:
        chain = [start_edge]
        chain_wallets = [start_edge.from_wallet, start_edge.to_wallet]
        current = start_edge.to_wallet
        current_time = start_edge.timestamp

        while True:
            # Find outgoing edges from current wallet within time window
            next_edges = [
                (to, idx)
                for to, idx in graph._adj.get(current, [])
                if (
                    graph._edges[idx].timestamp >= current_time
                    and graph._edges[idx].timestamp <= current_time + delay
                    and to not in chain_wallets
                )
            ]
            if not next_edges:
                break

            # Pick earliest next hop
            best = min(next_edges, key=lambda x: graph._edges[x[1]].timestamp)
            next_edge = graph._edges[best[1]]
            chain.append(next_edge)
            chain_wallets.append(best[0])
            current = best[0]
            current_time = next_edge.timestamp

        if len(chain) >= min_length:
            chain_key = tuple(chain_wallets)
            if chain_key not in visited_chains:
                visited_chains.add(chain_key)
                total_time = (chain[-1].timestamp - chain[0].timestamp).total_seconds()
                total_amount = sum((e.amount for e in chain), Decimal("0"))

                results.append(PatternMatch(
                    pattern=GraphPattern.RAPID_CHAIN,
                    confidence=min(1.0, len(chain) / (min_length * 2)),
                    wallets_involved=chain_wallets,
                    transactions_involved=[e.tx_id for e in chain],
                    amount=total_amount,
                    description=(
                        f"Rapid chain: {len(chain)} hops in {total_time:.0f}s "
                        f"through {len(chain_wallets)} wallets (${total_amount:.2f})"
                    ),
                    metadata={
                        "chain_length": len(chain),
                        "total_seconds": total_time,
                    },
                ))

    return results


def detect_peeling_chains(
    graph: TransactionGraph,
    min_length: int = PEELING_MIN_LENGTH,
    decay_min: float = PEELING_AMOUNT_DECAY_MIN,
    decay_max: float = PEELING_AMOUNT_DECAY_MAX,
) -> list[PatternMatch]:
    """Detect peeling chain patterns.

    A peeling chain is a sequence where each hop "peels off" a portion,
    sending a decreasing amount to the next wallet.
    """
    results: list[PatternMatch] = []
    sorted_edges = sorted(graph._edges, key=lambda e: e.timestamp)

    for start_edge in sorted_edges:
        chain = [start_edge]
        current = start_edge.to_wallet
        current_amount = start_edge.amount
        chain_wallets = [start_edge.from_wallet, start_edge.to_wallet]

        while True:
            next_edges = [
                (to, idx)
                for to, idx in graph._adj.get(current, [])
                if to not in chain_wallets
            ]
            if not next_edges:
                break

            # Find edge with decayed amount
            found = False
            for to, idx in next_edges:
                edge = graph._edges[idx]
                if current_amount > 0:
                    ratio = float(edge.amount / current_amount)
                    if decay_min <= ratio <= decay_max:
                        chain.append(edge)
                        chain_wallets.append(to)
                        current = to
                        current_amount = edge.amount
                        found = True
                        break
            if not found:
                break

        if len(chain) >= min_length:
            total = sum((e.amount for e in chain), Decimal("0"))
            results.append(PatternMatch(
                pattern=GraphPattern.PEELING_CHAIN,
                confidence=min(1.0, len(chain) / (min_length * 2)),
                wallets_involved=chain_wallets,
                transactions_involved=[e.tx_id for e in chain],
                amount=total,
                description=(
                    f"Peeling chain: {len(chain)} hops with decreasing amounts "
                    f"({chain[0].amount:.2f} → {chain[-1].amount:.2f})"
                ),
                metadata={
                    "chain_length": len(chain),
                    "start_amount": str(chain[0].amount),
                    "end_amount": str(chain[-1].amount),
                },
            ))

    return results


def detect_pass_through(
    graph: TransactionGraph,
    ratio_min: float = 0.8,
    ratio_max: float = 1.2,
) -> list[PatternMatch]:
    """Detect pass-through wallets (transit nodes).

    Wallets where total_sent ≈ total_received, acting as
    intermediaries with no economic purpose.
    """
    results: list[PatternMatch] = []

    for addr, node in graph._nodes.items():
        if node.total_received == 0 or node.total_sent == 0:
            continue
        if node.tx_count < 2:
            continue

        ratio = float(node.total_sent / node.total_received)
        if ratio_min <= ratio <= ratio_max:
            tightness = 1.0 - abs(ratio - 1.0)  # Closer to 1.0 = higher confidence
            confidence = min(1.0, tightness * (node.tx_count / 10))

            results.append(PatternMatch(
                pattern=GraphPattern.PASS_THROUGH,
                confidence=confidence,
                wallets_involved=[addr] + list(set(node.incoming)) + list(set(node.outgoing)),
                amount=node.total_received,
                description=(
                    f"Pass-through: {addr} received ${node.total_received:.2f}, "
                    f"sent ${node.total_sent:.2f} (ratio: {ratio:.2f})"
                ),
                metadata={
                    "sent_received_ratio": ratio,
                    "tx_count": node.tx_count,
                },
            ))

    return results


def detect_clusters(
    graph: TransactionGraph,
    min_cluster_size: int = CLUSTER_MIN_SIZE,
    max_distance: int = CLUSTER_MAX_DISTANCE,
) -> list[PatternMatch]:
    """Detect tightly connected wallet clusters.

    Uses BFS-based connected component detection to find groups
    of wallets that frequently transact with each other.
    """
    results: list[PatternMatch] = []
    visited: set[str] = set()

    for start_addr in graph._nodes:
        if start_addr in visited:
            continue

        # BFS to find connected component within max_distance
        cluster: list[str] = []
        queue: deque[tuple[str, int]] = deque([(start_addr, 0)])
        local_visited: set[str] = {start_addr}

        while queue:
            addr, dist = queue.popleft()
            cluster.append(addr)

            if dist < max_distance:
                for neighbor in graph.get_neighbors(addr):
                    if neighbor not in local_visited:
                        local_visited.add(neighbor)
                        queue.append((neighbor, dist + 1))

        visited.update(local_visited)

        if len(cluster) >= min_cluster_size:
            # Calculate cluster density
            internal_edges = 0
            total_amount = Decimal("0")
            for w in cluster:
                for to, idx in graph._adj.get(w, []):
                    if to in local_visited:
                        internal_edges += 1
                        total_amount += graph._edges[idx].amount

            max_edges = len(cluster) * (len(cluster) - 1)
            density = internal_edges / max_edges if max_edges > 0 else 0

            results.append(PatternMatch(
                pattern=GraphPattern.CLUSTER,
                confidence=min(1.0, density * (len(cluster) / min_cluster_size)),
                wallets_involved=cluster,
                amount=total_amount,
                description=(
                    f"Wallet cluster: {len(cluster)} wallets, "
                    f"{internal_edges} internal edges, "
                    f"density={density:.2f}"
                ),
                metadata={
                    "cluster_size": len(cluster),
                    "internal_edges": internal_edges,
                    "density": density,
                },
            ))

    return results


# ============ Analyzer ============


class GraphFraudAnalyzer:
    """Main graph-based fraud analyzer.

    Builds a transaction graph and runs all pattern detectors
    to produce a comprehensive risk assessment.
    """

    def __init__(
        self,
        hub_threshold: int = HUB_DEGREE_THRESHOLD,
        rapid_chain_delay_minutes: int = RAPID_CHAIN_MAX_DELAY_MINUTES,
        rapid_chain_min_length: int = RAPID_CHAIN_MIN_LENGTH,
        min_cluster_size: int = CLUSTER_MIN_SIZE,
    ):
        self._hub_threshold = hub_threshold
        self._rapid_delay = rapid_chain_delay_minutes
        self._rapid_min_len = rapid_chain_min_length
        self._min_cluster = min_cluster_size

    def analyze(
        self,
        transactions: list[TransactionEdge],
        focus_wallet: str | None = None,
    ) -> GraphAnalysisResult:
        """Analyze a set of transactions for graph-based fraud patterns.

        Args:
            transactions: Transaction edges to analyze
            focus_wallet: Optional wallet to focus analysis on

        Returns:
            GraphAnalysisResult with detected patterns and risk score
        """
        graph = TransactionGraph()
        graph.add_transactions(transactions)

        patterns: list[PatternMatch] = []

        # Run detectors
        if focus_wallet:
            patterns.extend(detect_cycles(graph, focus_wallet))
        else:
            # Run cycles for each node
            for addr in list(graph._nodes.keys()):
                patterns.extend(detect_cycles(graph, addr))

        patterns.extend(detect_hub_spoke(graph, self._hub_threshold))
        patterns.extend(detect_rapid_chains(graph, self._rapid_delay, self._rapid_min_len))
        patterns.extend(detect_peeling_chains(graph))
        patterns.extend(detect_pass_through(graph))
        patterns.extend(detect_clusters(graph, self._min_cluster))

        # Deduplicate by pattern + wallet set
        seen: set[tuple[str, tuple[str, ...]]] = set()
        unique_patterns: list[PatternMatch] = []
        for p in patterns:
            key = (p.pattern.value, tuple(sorted(p.wallets_involved)))
            if key not in seen:
                seen.add(key)
                unique_patterns.append(p)

        # Calculate overall risk score
        risk_score = self._calculate_risk_score(unique_patterns)
        risk_level = self._score_to_level(risk_score)

        return GraphAnalysisResult(
            subject_wallet=focus_wallet or "",
            patterns=unique_patterns,
            risk_level=risk_level,
            risk_score=risk_score,
            node_count=graph.node_count,
            edge_count=graph.edge_count,
            metadata={
                "pattern_count": len(unique_patterns),
                "pattern_types": list({p.pattern.value for p in unique_patterns}),
            },
        )

    def _calculate_risk_score(self, patterns: list[PatternMatch]) -> float:
        """Calculate overall risk score from detected patterns."""
        if not patterns:
            return 0.0
        # Use max pattern score with additive boost for multiple patterns
        scores = [p.risk_score for p in patterns]
        max_score = max(scores)
        # Each additional pattern adds 5% (diminishing)
        additional = sum(
            s * 0.05 for s in sorted(scores, reverse=True)[1:]
        )
        return min(1.0, max_score + additional)

    def _score_to_level(self, score: float) -> GraphRiskLevel:
        if score <= 0.0:
            return GraphRiskLevel.CLEAN
        elif score <= 0.25:
            return GraphRiskLevel.LOW
        elif score <= 0.50:
            return GraphRiskLevel.MEDIUM
        elif score <= 0.75:
            return GraphRiskLevel.HIGH
        else:
            return GraphRiskLevel.CRITICAL


def create_graph_analyzer(
    hub_threshold: int = HUB_DEGREE_THRESHOLD,
    rapid_chain_delay_minutes: int = RAPID_CHAIN_MAX_DELAY_MINUTES,
) -> GraphFraudAnalyzer:
    """Factory function to create a GraphFraudAnalyzer."""
    return GraphFraudAnalyzer(
        hub_threshold=hub_threshold,
        rapid_chain_delay_minutes=rapid_chain_delay_minutes,
    )
