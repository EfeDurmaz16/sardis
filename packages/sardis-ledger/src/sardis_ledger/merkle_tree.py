"""
Merkle tree implementation for audit log tamper evidence.

Provides cryptographic proof of entry inclusion in the ledger through
Merkle tree construction and verification.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MerkleNode:
    """Node in a Merkle tree."""
    hash: str
    left: Optional[MerkleNode] = None
    right: Optional[MerkleNode] = None
    data: Optional[bytes] = None  # Only leaf nodes have data

    def is_leaf(self) -> bool:
        """Check if this is a leaf node."""
        return self.left is None and self.right is None


class MerkleTree:
    """
    Merkle tree for cryptographic verification of audit log entries.

    Features:
    - Build tree from list of entries
    - Generate inclusion proofs
    - Verify inclusion proofs
    - Support for any hash function (default SHA-256)
    """

    def __init__(self, hash_function: str = "sha256"):
        """
        Initialize Merkle tree.

        Args:
            hash_function: Hash function name (sha256, sha3_256, blake2b)
        """
        self.hash_function = hash_function
        self._root: Optional[MerkleNode] = None
        self._leaves: list[MerkleNode] = []
        self._leaf_count = 0

    def _hash(self, data: bytes) -> str:
        """Compute hash of data using configured hash function."""
        if self.hash_function == "sha256":
            return hashlib.sha256(data).hexdigest()
        elif self.hash_function == "sha3_256":
            return hashlib.sha3_256(data).hexdigest()
        elif self.hash_function == "blake2b":
            return hashlib.blake2b(data).hexdigest()
        else:
            raise ValueError(f"Unsupported hash function: {self.hash_function}")

    def _hash_pair(self, left_hash: str, right_hash: str) -> str:
        """Hash a pair of node hashes together."""
        # Concatenate in sorted order for deterministic results
        combined = left_hash + right_hash if left_hash <= right_hash else right_hash + left_hash
        return self._hash(combined.encode('utf-8'))

    def build(self, entries: list[bytes]) -> MerkleNode:
        """
        Build Merkle tree from list of leaf data.

        Args:
            entries: List of byte data for leaf nodes

        Returns:
            Root node of the tree

        Raises:
            ValueError: If entries list is empty
        """
        if not entries:
            raise ValueError("Cannot build Merkle tree from empty entries list")

        # Create leaf nodes
        self._leaves = []
        for entry_data in entries:
            leaf_hash = self._hash(entry_data)
            node = MerkleNode(hash=leaf_hash, data=entry_data)
            self._leaves.append(node)

        self._leaf_count = len(self._leaves)

        # Build tree bottom-up
        current_level = self._leaves[:]

        # Handle single entry case
        if len(current_level) == 1:
            self._root = current_level[0]
            return self._root

        # Build tree level by level
        while len(current_level) > 1:
            next_level = []

            # Process pairs
            for i in range(0, len(current_level), 2):
                left = current_level[i]

                # If odd number of nodes, duplicate last node
                if i + 1 >= len(current_level):
                    right = left
                else:
                    right = current_level[i + 1]

                # Create parent node
                parent_hash = self._hash_pair(left.hash, right.hash)
                parent = MerkleNode(hash=parent_hash, left=left, right=right)
                next_level.append(parent)

            current_level = next_level

        self._root = current_level[0]
        return self._root

    def get_root(self) -> str:
        """
        Get root hash of the tree.

        Returns:
            Hex string of root hash

        Raises:
            ValueError: If tree hasn't been built yet
        """
        if self._root is None:
            raise ValueError("Tree not built yet - call build() first")
        return self._root.hash

    def get_proof(self, index: int) -> list[tuple[str, str]]:
        """
        Get Merkle proof for entry at given index.

        The proof is a list of (hash, direction) tuples that can be used
        to verify inclusion of the entry in the tree.

        Args:
            index: Index of the leaf node (0-based)

        Returns:
            List of (hash, direction) tuples where direction is 'L' or 'R'

        Raises:
            ValueError: If tree not built or index out of range
        """
        if self._root is None:
            raise ValueError("Tree not built yet - call build() first")
        if index < 0 or index >= self._leaf_count:
            raise ValueError(f"Index {index} out of range [0, {self._leaf_count})")

        proof: list[tuple[str, str]] = []

        # Build proof by walking up from leaf to root
        # We need to track which nodes to include at each level
        current_level = self._leaves[:]
        current_index = index

        while len(current_level) > 1:
            next_level = []
            next_index = current_index // 2

            for i in range(0, len(current_level), 2):
                left = current_level[i]

                if i + 1 >= len(current_level):
                    # Odd node, duplicated
                    right = left
                else:
                    right = current_level[i + 1]

                # If this is the pair containing our target node
                if i == current_index or i == current_index - 1:
                    if i == current_index:
                        # Our node is on the left, include right sibling
                        if i + 1 < len(current_level):
                            proof.append((right.hash, 'R'))
                        else:
                            # Odd-node duplication is part of the hash path.
                            # Include duplicated sibling so verification can
                            # reconstruct the same parent hash.
                            proof.append((right.hash, 'R'))
                    else:
                        # Our node is on the right, include left sibling
                        proof.append((left.hash, 'L'))

                # Create parent for next level
                parent_hash = self._hash_pair(left.hash, right.hash)
                parent = MerkleNode(hash=parent_hash, left=left, right=right)
                next_level.append(parent)

            current_level = next_level
            current_index = next_index

        return proof

    def verify_proof(self, leaf_hash: str, proof: list[tuple[str, str]], root: str) -> bool:
        """
        Verify a Merkle proof.

        Args:
            leaf_hash: Hash of the leaf node to verify
            proof: List of (hash, direction) tuples from get_proof()
            root: Expected root hash

        Returns:
            True if proof is valid, False otherwise
        """
        current_hash = leaf_hash

        # Walk up the tree following the proof
        for sibling_hash, direction in proof:
            if direction == 'L':
                # Sibling is on the left
                current_hash = self._hash_pair(sibling_hash, current_hash)
            elif direction == 'R':
                # Sibling is on the right
                current_hash = self._hash_pair(current_hash, sibling_hash)
            else:
                # Invalid direction
                return False

        # Check if we arrived at the expected root
        return current_hash == root

    def get_leaf_count(self) -> int:
        """
        Get number of leaf nodes in the tree.

        Returns:
            Number of leaves
        """
        return self._leaf_count


def compute_entry_hash(entry: dict[str, Any]) -> bytes:
    """
    Compute deterministic hash of a ledger entry.

    Args:
        entry: Dictionary representing a ledger entry

    Returns:
        SHA-256 hash of the entry as bytes
    """
    # Create canonical JSON representation
    # Sort keys for deterministic ordering
    canonical = json.dumps(entry, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).digest()


__all__ = [
    "MerkleNode",
    "MerkleTree",
    "compute_entry_hash",
]
