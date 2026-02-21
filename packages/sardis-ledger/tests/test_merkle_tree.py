"""Unit tests for Merkle tree implementation."""

import pytest
from sardis_ledger.merkle_tree import MerkleTree, MerkleNode, compute_entry_hash


class TestMerkleTree:
    """Test Merkle tree construction and verification."""

    def test_build_tree_single_entry(self):
        """Test building tree with single entry."""
        tree = MerkleTree()
        entries = [b"single_entry"]

        root = tree.build(entries)

        assert root is not None
        assert root.is_leaf()
        assert tree.get_leaf_count() == 1

    def test_build_tree_multiple_entries(self):
        """Test building tree with multiple entries."""
        tree = MerkleTree()
        entries = [
            b"entry_1",
            b"entry_2",
            b"entry_3",
            b"entry_4",
        ]

        root = tree.build(entries)

        assert root is not None
        assert not root.is_leaf()
        assert tree.get_leaf_count() == 4

    def test_build_tree_odd_count(self):
        """Test building tree with odd number of entries."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c"]

        root = tree.build(entries)

        assert root is not None
        assert tree.get_leaf_count() == 3

    def test_build_tree_power_of_two(self):
        """Test building tree with power-of-two entries."""
        tree = MerkleTree()
        entries = [f"entry_{i}".encode() for i in range(8)]

        root = tree.build(entries)

        assert root is not None
        assert tree.get_leaf_count() == 8

    def test_build_empty_raises_error(self):
        """Test building tree with empty entries raises ValueError."""
        tree = MerkleTree()

        with pytest.raises(ValueError) as exc_info:
            tree.build([])

        assert "empty entries" in str(exc_info.value).lower()

    def test_get_root_hash(self):
        """Test getting root hash."""
        tree = MerkleTree()
        entries = [b"entry_1", b"entry_2"]

        tree.build(entries)
        root_hash = tree.get_root()

        assert isinstance(root_hash, str)
        assert len(root_hash) == 64  # SHA-256 hex string

    def test_get_root_before_build_raises_error(self):
        """Test getting root before building raises ValueError."""
        tree = MerkleTree()

        with pytest.raises(ValueError) as exc_info:
            tree.get_root()

        assert "not built" in str(exc_info.value).lower()

    def test_deterministic_root_hash(self):
        """Test root hash is deterministic for same entries."""
        entries = [b"a", b"b", b"c", b"d"]

        tree1 = MerkleTree()
        tree1.build(entries)
        root1 = tree1.get_root()

        tree2 = MerkleTree()
        tree2.build(entries)
        root2 = tree2.get_root()

        assert root1 == root2

    def test_different_entries_different_root(self):
        """Test different entries produce different root hashes."""
        tree1 = MerkleTree()
        tree1.build([b"a", b"b"])
        root1 = tree1.get_root()

        tree2 = MerkleTree()
        tree2.build([b"c", b"d"])
        root2 = tree2.get_root()

        assert root1 != root2

    def test_get_proof_first_entry(self):
        """Test generating proof for first entry."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c", b"d"]

        tree.build(entries)
        proof = tree.get_proof(0)

        assert isinstance(proof, list)
        assert len(proof) > 0
        # For 4 entries, should have 2 proof elements (sibling at each level)
        assert len(proof) == 2

    def test_get_proof_last_entry(self):
        """Test generating proof for last entry."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c", b"d"]

        tree.build(entries)
        proof = tree.get_proof(3)

        assert isinstance(proof, list)
        assert len(proof) > 0

    def test_get_proof_middle_entry(self):
        """Test generating proof for middle entry."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c", b"d", b"e", b"f", b"g", b"h"]

        tree.build(entries)
        proof = tree.get_proof(3)

        assert isinstance(proof, list)
        assert len(proof) == 3  # 8 entries = 3 levels

    def test_get_proof_invalid_index_raises_error(self):
        """Test getting proof for invalid index raises ValueError."""
        tree = MerkleTree()
        entries = [b"a", b"b"]

        tree.build(entries)

        with pytest.raises(ValueError) as exc_info:
            tree.get_proof(5)

        assert "out of range" in str(exc_info.value).lower()

    def test_get_proof_negative_index_raises_error(self):
        """Test getting proof for negative index raises ValueError."""
        tree = MerkleTree()
        entries = [b"a", b"b"]

        tree.build(entries)

        with pytest.raises(ValueError):
            tree.get_proof(-1)

    def test_get_proof_before_build_raises_error(self):
        """Test getting proof before building raises ValueError."""
        tree = MerkleTree()

        with pytest.raises(ValueError) as exc_info:
            tree.get_proof(0)

        assert "not built" in str(exc_info.value).lower()

    def test_verify_proof_valid(self):
        """Test verifying valid proof."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c", b"d"]

        tree.build(entries)
        root = tree.get_root()

        # Get proof for entry 1
        proof = tree.get_proof(1)
        leaf_hash = tree._hash(entries[1])

        # Verify
        is_valid = tree.verify_proof(leaf_hash, proof, root)
        assert is_valid is True

    def test_verify_proof_all_entries(self):
        """Test verifying proofs for all entries."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c", b"d", b"e"]

        tree.build(entries)
        root = tree.get_root()

        # Verify each entry
        for i, entry in enumerate(entries):
            proof = tree.get_proof(i)
            leaf_hash = tree._hash(entry)
            is_valid = tree.verify_proof(leaf_hash, proof, root)
            assert is_valid is True, f"Proof for entry {i} failed"

    def test_verify_proof_invalid_leaf(self):
        """Test verifying proof with wrong leaf fails."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c", b"d"]

        tree.build(entries)
        root = tree.get_root()

        proof = tree.get_proof(1)
        wrong_leaf_hash = tree._hash(b"wrong")

        is_valid = tree.verify_proof(wrong_leaf_hash, proof, root)
        assert is_valid is False

    def test_verify_proof_invalid_root(self):
        """Test verifying proof with wrong root fails."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c", b"d"]

        tree.build(entries)

        proof = tree.get_proof(1)
        leaf_hash = tree._hash(entries[1])
        wrong_root = "0" * 64

        is_valid = tree.verify_proof(leaf_hash, proof, wrong_root)
        assert is_valid is False

    def test_verify_proof_tampered(self):
        """Test verifying proof with tampered proof data fails."""
        tree = MerkleTree()
        entries = [b"a", b"b", b"c", b"d"]

        tree.build(entries)
        root = tree.get_root()

        proof = tree.get_proof(1)
        leaf_hash = tree._hash(entries[1])

        # Tamper with proof
        if proof:
            proof[0] = ("0" * 64, proof[0][1])

        is_valid = tree.verify_proof(leaf_hash, proof, root)
        assert is_valid is False

    def test_different_hash_functions(self):
        """Test tree with different hash functions."""
        entries = [b"a", b"b", b"c", b"d"]

        # SHA-256
        tree_sha256 = MerkleTree(hash_function="sha256")
        tree_sha256.build(entries)
        root_sha256 = tree_sha256.get_root()

        # SHA3-256
        tree_sha3 = MerkleTree(hash_function="sha3_256")
        tree_sha3.build(entries)
        root_sha3 = tree_sha3.get_root()

        # BLAKE2b
        tree_blake2 = MerkleTree(hash_function="blake2b")
        tree_blake2.build(entries)
        root_blake2 = tree_blake2.get_root()

        # All should produce different roots
        assert root_sha256 != root_sha3
        assert root_sha256 != root_blake2
        assert root_sha3 != root_blake2

    def test_unsupported_hash_function_raises_error(self):
        """Test unsupported hash function raises ValueError."""
        tree = MerkleTree(hash_function="md5")
        entries = [b"a", b"b"]

        with pytest.raises(ValueError) as exc_info:
            tree.build(entries)

        assert "Unsupported hash function" in str(exc_info.value)

    def test_large_tree(self):
        """Test building and verifying large tree."""
        tree = MerkleTree()
        entries = [f"entry_{i}".encode() for i in range(1000)]

        tree.build(entries)
        root = tree.get_root()

        # Verify a few random entries
        for index in [0, 100, 500, 999]:
            proof = tree.get_proof(index)
            leaf_hash = tree._hash(entries[index])
            is_valid = tree.verify_proof(leaf_hash, proof, root)
            assert is_valid is True

    def test_single_entry_proof(self):
        """Test proof for single-entry tree."""
        tree = MerkleTree()
        entries = [b"only_one"]

        tree.build(entries)
        root = tree.get_root()

        proof = tree.get_proof(0)
        leaf_hash = tree._hash(entries[0])

        # Single entry should have empty proof
        assert len(proof) == 0

        # Verification should still work
        is_valid = tree.verify_proof(leaf_hash, proof, root)
        assert is_valid is True


class TestComputeEntryHash:
    """Test ledger entry hashing function."""

    def test_compute_entry_hash(self):
        """Test computing hash of dictionary entry."""
        entry = {
            "transaction_id": "tx_123",
            "amount": "100.00",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        hash_bytes = compute_entry_hash(entry)

        assert isinstance(hash_bytes, bytes)
        assert len(hash_bytes) == 32  # SHA-256 = 32 bytes

    def test_compute_entry_hash_deterministic(self):
        """Test hash is deterministic for same entry."""
        entry = {"key": "value", "number": 42}

        hash1 = compute_entry_hash(entry)
        hash2 = compute_entry_hash(entry)

        assert hash1 == hash2

    def test_compute_entry_hash_key_order_independent(self):
        """Test hash is same regardless of key order."""
        entry1 = {"a": 1, "b": 2, "c": 3}
        entry2 = {"c": 3, "a": 1, "b": 2}

        hash1 = compute_entry_hash(entry1)
        hash2 = compute_entry_hash(entry2)

        assert hash1 == hash2

    def test_compute_entry_hash_different_values(self):
        """Test different entries produce different hashes."""
        entry1 = {"key": "value1"}
        entry2 = {"key": "value2"}

        hash1 = compute_entry_hash(entry1)
        hash2 = compute_entry_hash(entry2)

        assert hash1 != hash2
