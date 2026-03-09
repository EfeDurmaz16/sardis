"""Trust graph with BFS traversal and decay-based scoring.

Ported from fides/services/trust-graph/src/services/graph.ts.

Algorithm:
- BFS from source DID to target DID
- Trust decays by DEFAULT_TRUST_DECAY (0.85) per hop
- Cumulative trust = product of (edge_trust/100 * decay^depth) along path
- Max depth: 6 hops
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum

DEFAULT_TRUST_DECAY = 0.85
MAX_TRUST_DEPTH = 6


class TrustLevel(IntEnum):
    NONE = 0
    LOW = 25
    MEDIUM = 50
    HIGH = 75
    ABSOLUTE = 100


@dataclass(slots=True)
class TrustEdge:
    source_did: str
    target_did: str
    trust_level: int  # 0-100
    revoked_at: datetime | None = None
    expires_at: datetime | None = None


@dataclass(slots=True)
class TrustPathNode:
    did: str
    trust_level: int


@dataclass(slots=True)
class TrustPathResult:
    from_did: str
    to_did: str
    found: bool
    path: list[TrustPathNode] = field(default_factory=list)
    cumulative_trust: float = 0.0
    hops: int = 0
    reason: str | None = None


def _is_edge_valid(edge: TrustEdge) -> bool:
    """Check if an edge is active (not revoked, not expired)."""
    now = datetime.now(UTC)
    if edge.revoked_at is not None:
        return False
    if edge.expires_at is not None and edge.expires_at < now:
        return False
    return edge.trust_level > 0


def find_trust_path(
    edges: list[TrustEdge],
    from_did: str,
    to_did: str,
    max_depth: int = MAX_TRUST_DEPTH,
) -> TrustPathResult:
    """Find trust path between two DIDs using BFS traversal.

    Pure function — no database dependency, easy to test.

    Uses index-based dequeue (O(1) vs O(n) for list.pop(0)),
    parent pointer chain (no path cloning), and pre-computed decay powers.
    """
    # Filter valid edges and build forward adjacency list
    valid_edges = [e for e in edges if _is_edge_valid(e)]
    adjacency: dict[str, list[tuple[str, int]]] = {}
    for e in valid_edges:
        adjacency.setdefault(e.source_did, []).append((e.target_did, e.trust_level))

    # Pre-compute decay powers
    decay_powers = [1.0]
    for _i in range(1, max_depth + 1):
        decay_powers.append(decay_powers[-1] * DEFAULT_TRUST_DECAY)

    # BFS with parent pointers
    @dataclass
    class _QItem:
        did: str
        parent_index: int  # -1 for root
        trust_level: int
        cumulative_trust: float
        depth: int

    queue: list[_QItem] = [_QItem(
        did=from_did, parent_index=-1, trust_level=100,
        cumulative_trust=1.0, depth=0,
    )]
    visited: set[str] = {from_did}
    head = 0

    while head < len(queue):
        current = queue[head]
        head += 1

        if current.did == to_did:
            # Reconstruct path from parent pointers
            path: list[TrustPathNode] = []
            idx = head - 1
            while idx >= 0:
                item = queue[idx]
                path.append(TrustPathNode(did=item.did, trust_level=item.trust_level))
                idx = item.parent_index
            path.reverse()
            return TrustPathResult(
                from_did=from_did, to_did=to_did, found=True,
                path=path, cumulative_trust=current.cumulative_trust,
                hops=current.depth,
            )

        if current.depth >= max_depth:
            continue

        for target, trust in adjacency.get(current.did, []):
            if target not in visited:
                visited.add(target)
                trust_factor = (trust / 100) * decay_powers[current.depth]
                queue.append(_QItem(
                    did=target, parent_index=head - 1,
                    trust_level=trust,
                    cumulative_trust=current.cumulative_trust * trust_factor,
                    depth=current.depth + 1,
                ))

    return TrustPathResult(
        from_did=from_did, to_did=to_did, found=False,
        path=[], cumulative_trust=0.0, hops=0,
    )


class TrustGraphService:
    """In-memory trust graph for agent reputation.

    In production, edges would be loaded from PostgreSQL.
    """

    def __init__(self) -> None:
        self._edges: list[TrustEdge] = []

    def add_edge(self, edge: TrustEdge) -> None:
        self._edges.append(edge)

    def add_attestation(
        self,
        source_did: str,
        target_did: str,
        trust_level: int = TrustLevel.MEDIUM,
        expires_at: datetime | None = None,
    ) -> TrustEdge:
        """Record a trust attestation from source to target."""
        edge = TrustEdge(
            source_did=source_did,
            target_did=target_did,
            trust_level=trust_level,
            expires_at=expires_at,
        )
        self._edges.append(edge)
        return edge

    def revoke_attestation(self, source_did: str, target_did: str) -> bool:
        """Revoke trust from source to target."""
        for edge in self._edges:
            if edge.source_did == source_did and edge.target_did == target_did and edge.revoked_at is None:
                edge.revoked_at = datetime.now(UTC)
                return True
        return False

    def get_trust_score(self, from_did: str, to_did: str) -> float:
        """Get transitive trust score from source to target.

        Returns 0.0 if no path exists, otherwise the cumulative trust (0.0-1.0).
        """
        if from_did == to_did:
            return 1.0
        result = find_trust_path(self._edges, from_did, to_did)
        return result.cumulative_trust

    def find_path(self, from_did: str, to_did: str) -> TrustPathResult:
        """Find the trust path between two DIDs."""
        return find_trust_path(self._edges, from_did, to_did)

    def get_direct_trust(self, source_did: str, target_did: str) -> int:
        """Get direct (1-hop) trust level. Returns 0 if no direct edge."""
        for edge in self._edges:
            if (
                edge.source_did == source_did
                and edge.target_did == target_did
                and _is_edge_valid(edge)
            ):
                return edge.trust_level
        return 0
