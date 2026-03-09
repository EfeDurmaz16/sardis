// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IJobRegistry
 * @notice On-chain reputation registry for ERC-8183 agents
 * @dev Tracks completion rates, volume, and computes trust scores in basis points.
 *      Trust scores are used by hooks to gate job participation.
 */
interface IJobRegistry {
    // ============ Structs ============

    struct AgentReputation {
        uint256 completedJobs;
        uint256 rejectedJobs;
        uint256 totalEarned;
        uint256 totalSpent;
        uint256 lastActiveAt;
    }

    // ============ Functions ============

    /**
     * @notice Get the full reputation record for an agent
     * @param agent The agent address
     * @return reputation The agent's reputation struct
     */
    function getReputation(address agent) external view returns (AgentReputation memory reputation);

    /**
     * @notice Get the trust score for an agent in basis points (max 10000)
     * @param agent The agent address
     * @return score Trust score, 0-10000
     */
    function getTrustScore(address agent) external view returns (uint256 score);
}
