// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title SardisLedgerAnchor
 * @notice Stores Merkle roots of audit log batches for tamper evidence
 * @dev Minimal contract for anchoring ledger state to the blockchain.
 *      Each anchor records a Merkle root with a timestamp, providing
 *      immutable proof that a set of audit entries existed at a specific time.
 */
contract SardisLedgerAnchor is Ownable {
    /// @notice Mapping from Merkle root to the timestamp it was anchored
    mapping(bytes32 => uint256) public anchors;

    /// @notice Emitted when a new Merkle root is anchored
    event Anchored(bytes32 indexed root, string anchorId, uint256 timestamp);

    constructor() Ownable(msg.sender) { }

    /**
     * @notice Anchor a Merkle root on-chain
     * @param root The Merkle root hash of the audit log batch
     * @param anchorId Human-readable anchor identifier
     */
    function anchor(bytes32 root, string calldata anchorId) external onlyOwner {
        require(anchors[root] == 0, "SardisLedgerAnchor: root already anchored");
        anchors[root] = block.timestamp;
        emit Anchored(root, anchorId, block.timestamp);
    }

    /**
     * @notice Verify whether a Merkle root has been anchored
     * @param root The Merkle root to verify
     * @return timestamp The timestamp when it was anchored (0 if not anchored)
     */
    function verify(bytes32 root) external view returns (uint256 timestamp) {
        return anchors[root];
    }

    /**
     * @notice Verify a Merkle inclusion proof against an anchored root
     * @param root The anchored Merkle root
     * @param leaf The leaf hash to verify inclusion of
     * @param proof Array of sibling hashes along the path
     * @param isLeft Array indicating whether each sibling is on the left (true) or right (false)
     * @return valid True if the proof is valid and the root is anchored
     */
    function verifyProof(bytes32 root, bytes32 leaf, bytes32[] calldata proof, bool[] calldata isLeft)
        external
        view
        returns (bool valid)
    {
        // Root must be anchored
        if (anchors[root] == 0) {
            return false;
        }
        require(proof.length == isLeft.length, "SardisLedgerAnchor: proof/isLeft length mismatch");

        bytes32 current = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            if (isLeft[i]) {
                // Sibling is on the left: hash(sibling, current)
                current = _hashPair(proof[i], current);
            } else {
                // Sibling is on the right: hash(current, sibling)
                current = _hashPair(current, proof[i]);
            }
        }
        return current == root;
    }

    /**
     * @dev Hash a pair of nodes in sorted order for deterministic results
     */
    function _hashPair(bytes32 a, bytes32 b) internal pure returns (bytes32) {
        if (a <= b) {
            return keccak256(abi.encodePacked(a, b));
        }
        return keccak256(abi.encodePacked(b, a));
    }
}
