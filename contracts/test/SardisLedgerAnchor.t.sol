// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisLedgerAnchor.sol";

contract SardisLedgerAnchorTest is Test {
    SardisLedgerAnchor public anchor;
    address public owner;
    address public nonOwner;

    event Anchored(bytes32 indexed root, string anchorId, uint256 timestamp);

    function setUp() public {
        owner = address(this);
        nonOwner = address(0xBEEF);
        anchor = new SardisLedgerAnchor();
    }

    // ── Anchor submission ───────────────────────────────────────────

    function testAnchor_success() public {
        bytes32 root = keccak256("audit_batch_001");

        vm.expectEmit(true, false, false, true);
        emit Anchored(root, "batch_001", block.timestamp);

        anchor.anchor(root, "batch_001");

        uint256 ts = anchor.verify(root);
        assertGt(ts, 0, "Anchor timestamp should be non-zero");
        assertEq(ts, block.timestamp, "Timestamp should match block.timestamp");
    }

    function testAnchor_duplicateReverts() public {
        bytes32 root = keccak256("duplicate_batch");
        anchor.anchor(root, "batch_dup");

        vm.expectRevert("SardisLedgerAnchor: root already anchored");
        anchor.anchor(root, "batch_dup_2");
    }

    function testAnchor_differentRoots() public {
        bytes32 root1 = keccak256("batch_1");
        bytes32 root2 = keccak256("batch_2");

        anchor.anchor(root1, "id_1");
        anchor.anchor(root2, "id_2");

        assertGt(anchor.verify(root1), 0);
        assertGt(anchor.verify(root2), 0);
    }

    // ── Batch anchoring ─────────────────────────────────────────────

    function testBatchAnchoring() public {
        for (uint256 i = 0; i < 5; i++) {
            bytes32 root = keccak256(abi.encodePacked("batch_", i));
            anchor.anchor(root, string(abi.encodePacked("batch_", vm.toString(i))));
        }

        for (uint256 i = 0; i < 5; i++) {
            bytes32 root = keccak256(abi.encodePacked("batch_", i));
            assertGt(anchor.verify(root), 0);
        }
    }

    // ── Verify ──────────────────────────────────────────────────────

    function testVerify_unanchoredReturnsZero() public view {
        bytes32 unknown = keccak256("never_anchored");
        uint256 ts = anchor.verify(unknown);
        assertEq(ts, 0, "Unanchored root should return 0");
    }

    // ── Access control ──────────────────────────────────────────────

    function testAnchor_onlyOwner() public {
        bytes32 root = keccak256("unauthorized_batch");

        vm.prank(nonOwner);
        vm.expectRevert();
        anchor.anchor(root, "unauth");
    }

    function testOwner_isDeployer() public view {
        assertEq(anchor.owner(), owner);
    }

    // ── Merkle proof verification ───────────────────────────────────

    function testVerifyProof_validProof() public {
        // Build a simple 2-leaf Merkle tree
        bytes32 leaf1 = keccak256("tx_001");
        bytes32 leaf2 = keccak256("tx_002");

        // Sorted hash: smaller value first
        bytes32 root;
        if (leaf1 <= leaf2) {
            root = keccak256(abi.encodePacked(leaf1, leaf2));
        } else {
            root = keccak256(abi.encodePacked(leaf2, leaf1));
        }

        // Anchor the root
        anchor.anchor(root, "merkle_test");

        // Verify leaf1 with proof = [leaf2]
        bytes32[] memory proof = new bytes32[](1);
        proof[0] = leaf2;
        bool[] memory isLeft = new bool[](1);
        isLeft[0] = false;

        bool valid = anchor.verifyProof(root, leaf1, proof, isLeft);
        assertTrue(valid, "Valid Merkle proof should verify");
    }

    function testVerifyProof_unanchoredRoot() public view {
        bytes32 fakeRoot = keccak256("not_anchored");
        bytes32 leaf = keccak256("leaf");
        bytes32[] memory proof = new bytes32[](0);
        bool[] memory isLeft = new bool[](0);

        bool valid = anchor.verifyProof(fakeRoot, leaf, proof, isLeft);
        assertFalse(valid, "Proof against unanchored root should fail");
    }

    function testVerifyProof_invalidProof() public {
        bytes32 leaf1 = keccak256("tx_001");
        bytes32 leaf2 = keccak256("tx_002");
        bytes32 wrongLeaf = keccak256("tx_wrong");

        bytes32 root;
        if (leaf1 <= leaf2) {
            root = keccak256(abi.encodePacked(leaf1, leaf2));
        } else {
            root = keccak256(abi.encodePacked(leaf2, leaf1));
        }

        anchor.anchor(root, "proof_test");

        // Try to prove wrongLeaf is in the tree
        bytes32[] memory proof = new bytes32[](1);
        proof[0] = leaf2;
        bool[] memory isLeft = new bool[](1);
        isLeft[0] = false;

        bool valid = anchor.verifyProof(root, wrongLeaf, proof, isLeft);
        assertFalse(valid, "Invalid proof should not verify");
    }

    function testVerifyProof_lengthMismatchReverts() public {
        bytes32 root = keccak256("mismatch_test");
        anchor.anchor(root, "mismatch");

        bytes32[] memory proof = new bytes32[](2);
        proof[0] = bytes32(0);
        proof[1] = bytes32(0);
        bool[] memory isLeft = new bool[](1);
        isLeft[0] = false;

        vm.expectRevert("SardisLedgerAnchor: proof/isLeft length mismatch");
        anchor.verifyProof(root, bytes32(0), proof, isLeft);
    }
}
