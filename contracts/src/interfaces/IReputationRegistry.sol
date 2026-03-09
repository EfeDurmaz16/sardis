// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IReputationRegistry
 * @notice ERC-8004 compliant Reputation Registry interface
 * @dev Tracks on-chain feedback for agents registered in the Identity Registry.
 *      Feedback is submitted by clients (callers), can be revoked, and agents can respond.
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8004
 */
interface IReputationRegistry {
    // ============ Events ============

    event NewFeedback(
        uint256 indexed agentId,
        address indexed clientAddress,
        uint64 feedbackIndex,
        int128 value,
        uint8 valueDecimals,
        string indexed indexedTag1,
        string tag1,
        string tag2,
        string endpoint,
        string feedbackURI,
        bytes32 feedbackHash
    );

    event FeedbackRevoked(
        uint256 indexed agentId,
        address indexed clientAddress,
        uint64 indexed feedbackIndex
    );

    event ResponseAppended(
        uint256 indexed agentId,
        address indexed clientAddress,
        uint64 feedbackIndex,
        address indexed responder,
        string responseURI,
        bytes32 responseHash
    );

    // ============ Initialization ============

    /**
     * @notice Get the linked Identity Registry
     * @return identityRegistry Address of the Identity Registry contract
     */
    function getIdentityRegistry() external view returns (address identityRegistry);

    // ============ Feedback Submission ============

    /**
     * @notice Submit feedback for an agent
     * @dev Submitter MUST NOT be the agent owner or approved operator.
     *      valueDecimals MUST be 0-18.
     * @param agentId The agent token ID in the Identity Registry
     * @param value Feedback value (signed, allows negative feedback)
     * @param valueDecimals Decimal precision of the value (0-18)
     * @param tag1 Optional categorization tag
     * @param tag2 Optional categorization tag
     * @param endpoint Optional service endpoint this feedback relates to
     * @param feedbackURI Optional URI to off-chain feedback details
     * @param feedbackHash Optional KECCAK-256 hash of feedbackURI content
     */
    function giveFeedback(
        uint256 agentId,
        int128 value,
        uint8 valueDecimals,
        string calldata tag1,
        string calldata tag2,
        string calldata endpoint,
        string calldata feedbackURI,
        bytes32 feedbackHash
    ) external;

    /**
     * @notice Revoke previously submitted feedback
     * @dev Only the original submitter can revoke
     * @param agentId The agent token ID
     * @param feedbackIndex Index of the feedback to revoke
     */
    function revokeFeedback(uint256 agentId, uint64 feedbackIndex) external;

    // ============ Response ============

    /**
     * @notice Append a response to feedback
     * @param agentId The agent token ID
     * @param clientAddress The address that submitted the original feedback
     * @param feedbackIndex Index of the feedback being responded to
     * @param responseURI URI to off-chain response details
     * @param responseHash KECCAK-256 hash of responseURI content
     */
    function appendResponse(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex,
        string calldata responseURI,
        bytes32 responseHash
    ) external;

    // ============ Read Functions ============

    /**
     * @notice Get aggregated feedback summary
     * @dev clientAddresses MUST be non-empty. tag1/tag2 are optional filters.
     * @param agentId The agent token ID
     * @param clientAddresses Addresses to aggregate feedback from
     * @param tag1 Optional tag filter
     * @param tag2 Optional tag filter
     * @return count Number of matching feedback entries
     * @return summaryValue Aggregated value
     * @return summaryValueDecimals Decimal precision of summaryValue
     */
    function getSummary(
        uint256 agentId,
        address[] calldata clientAddresses,
        string calldata tag1,
        string calldata tag2
    ) external view returns (uint64 count, int128 summaryValue, uint8 summaryValueDecimals);

    /**
     * @notice Read a single feedback entry
     * @param agentId The agent token ID
     * @param clientAddress The feedback submitter
     * @param feedbackIndex Index of the feedback
     * @return value Feedback value
     * @return valueDecimals Decimal precision
     * @return tag1 Categorization tag
     * @return tag2 Categorization tag
     * @return isRevoked Whether the feedback has been revoked
     */
    function readFeedback(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex
    ) external view returns (
        int128 value,
        uint8 valueDecimals,
        string memory tag1,
        string memory tag2,
        bool isRevoked
    );

    /**
     * @notice Read all feedback matching filters
     * @param agentId The agent token ID
     * @param clientAddresses Addresses to read feedback from
     * @param tag1 Optional tag filter
     * @param tag2 Optional tag filter
     * @param includeRevoked Whether to include revoked feedback
     */
    function readAllFeedback(
        uint256 agentId,
        address[] calldata clientAddresses,
        string calldata tag1,
        string calldata tag2,
        bool includeRevoked
    ) external view returns (
        address[] memory clients,
        uint64[] memory feedbackIndexes,
        int128[] memory values,
        uint8[] memory valueDecimals,
        string[] memory tag1s,
        string[] memory tag2s,
        bool[] memory revokedStatuses
    );

    /**
     * @notice Get the number of responses for a feedback entry
     * @param agentId The agent token ID
     * @param clientAddress The feedback submitter
     * @param feedbackIndex Index of the feedback
     * @param responders Addresses to count responses from
     * @return count Number of responses
     */
    function getResponseCount(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex,
        address[] calldata responders
    ) external view returns (uint64 count);

    /**
     * @notice Get all client addresses that have submitted feedback for an agent
     * @param agentId The agent token ID
     * @return clients Array of client addresses
     */
    function getClients(uint256 agentId) external view returns (address[] memory clients);

    /**
     * @notice Get the last feedback index for a client-agent pair
     * @param agentId The agent token ID
     * @param clientAddress The client address
     * @return lastIndex The last feedback index (0 if no feedback)
     */
    function getLastIndex(
        uint256 agentId,
        address clientAddress
    ) external view returns (uint64 lastIndex);
}
