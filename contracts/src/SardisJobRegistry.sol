// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

import "./interfaces/IJobRegistry.sol";

/**
 * @title SardisJobRegistry
 * @notice On-chain reputation store for ERC-8183 agents
 * @dev Tracks completed/rejected jobs, earnings, and spending per agent.
 *      Only authorized writers (e.g., SardisJobManager, hooks) can update records.
 *      Trust scores are computed on-chain in basis points (0-10000).
 *
 *      Trust score formula:
 *        baseScore = (completedJobs * 10000) / (completedJobs + rejectedJobs)
 *        volumeBonus = min(totalEarned / 1e18, 1000)  // up to 10% bonus for volume
 *        trustScore = min(baseScore + volumeBonus, 10000)
 */
contract SardisJobRegistry is IJobRegistry, Ownable {
    // ============ State Variables ============

    /// @notice Reputation data for each agent address
    mapping(address => AgentReputation) public reputations;

    /// @notice Addresses authorized to write reputation data
    mapping(address => bool) public authorizedWriters;

    // ============ Events ============

    event CompletionRecorded(address indexed provider, uint256 amount, uint256 completedJobs);
    event RejectionRecorded(address indexed provider, uint256 rejectedJobs);
    event SpendingRecorded(address indexed client, uint256 amount, uint256 totalSpent);
    event AuthorizedWriterSet(address indexed writer, bool authorized);

    // ============ Errors ============

    error NotAuthorizedWriter();
    error ZeroAddress();

    // ============ Modifiers ============

    modifier onlyAuthorizedWriter() {
        if (!authorizedWriters[msg.sender]) revert NotAuthorizedWriter();
        _;
    }

    // ============ Constructor ============

    /**
     * @param _owner Contract owner (can manage authorized writers)
     */
    constructor(address _owner) Ownable(_owner) { }

    // ============ Write Functions ============

    /**
     * @notice Record a completed job for a provider
     * @param provider Address of the provider who completed the job
     * @param amount Payment amount earned
     */
    function recordCompletion(address provider, uint256 amount) external onlyAuthorizedWriter {
        AgentReputation storage rep = reputations[provider];
        unchecked {
            ++rep.completedJobs;
        }
        rep.totalEarned += amount;
        rep.lastActiveAt = block.timestamp;

        emit CompletionRecorded(provider, amount, rep.completedJobs);
    }

    /**
     * @notice Record a rejected job for a provider
     * @param provider Address of the provider whose job was rejected
     */
    function recordRejection(address provider) external onlyAuthorizedWriter {
        AgentReputation storage rep = reputations[provider];
        unchecked {
            ++rep.rejectedJobs;
        }
        rep.lastActiveAt = block.timestamp;

        emit RejectionRecorded(provider, rep.rejectedJobs);
    }

    /**
     * @notice Record spending by a client
     * @param client Address of the client who spent funds
     * @param amount Amount spent
     */
    function recordSpending(address client, uint256 amount) external onlyAuthorizedWriter {
        AgentReputation storage rep = reputations[client];
        rep.totalSpent += amount;
        rep.lastActiveAt = block.timestamp;

        emit SpendingRecorded(client, amount, rep.totalSpent);
    }

    // ============ View Functions ============

    /// @inheritdoc IJobRegistry
    function getReputation(address agent) external view override returns (AgentReputation memory) {
        return reputations[agent];
    }

    /// @inheritdoc IJobRegistry
    function getTrustScore(address agent) external view override returns (uint256) {
        return _computeTrustScore(agent);
    }

    // ============ Admin Functions ============

    /**
     * @notice Authorize or revoke a writer address
     * @param writer Address to authorize/revoke
     * @param authorized Whether the address should be authorized
     */
    function setAuthorizedWriter(address writer, bool authorized) external onlyOwner {
        if (writer == address(0)) revert ZeroAddress();
        authorizedWriters[writer] = authorized;

        emit AuthorizedWriterSet(writer, authorized);
    }

    // ============ Internal Functions ============

    /**
     * @dev Compute trust score in basis points (0-10000)
     *      Formula:
     *        If no jobs: 0
     *        baseScore = (completed * 10000) / (completed + rejected)
     *        volumeBonus = min(totalEarned / 1e18, 1000)
     *        result = min(baseScore + volumeBonus, 10000)
     */
    function _computeTrustScore(address agent) internal view returns (uint256) {
        AgentReputation storage rep = reputations[agent];
        uint256 totalJobs = rep.completedJobs + rep.rejectedJobs;

        if (totalJobs == 0) return 0;

        uint256 baseScore = (rep.completedJobs * 10000) / totalJobs;

        // Volume bonus: 1 bp per 1e18 earned, capped at 1000 bp (10%)
        uint256 volumeBonus = rep.totalEarned / 1e18;
        if (volumeBonus > 1000) volumeBonus = 1000;

        uint256 score = baseScore + volumeBonus;
        if (score > 10000) score = 10000;

        return score;
    }
}
