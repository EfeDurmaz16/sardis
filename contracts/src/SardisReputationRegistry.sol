// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";

import "./interfaces/IReputationRegistry.sol";

/**
 * @title SardisReputationRegistry
 * @notice ERC-8004 compliant Reputation Registry — on-chain feedback for agents
 * @dev Linked to an Identity Registry (ERC-721). Clients submit feedback (value + tags),
 *      agents or owners can respond, and aggregated summaries are queryable on-chain.
 *
 *      Rules:
 *        - Submitter MUST NOT be agent owner or approved operator
 *        - valueDecimals MUST be 0-18
 *        - Only original submitter can revoke
 *        - Feedback is never deleted, only marked revoked
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8004
 */
contract SardisReputationRegistry is IReputationRegistry {
    // ============ Structs (Internal) ============

    struct Feedback {
        int128 value;
        uint8 valueDecimals;
        string tag1;
        string tag2;
        string endpoint;
        string feedbackURI;
        bytes32 feedbackHash;
        bool isRevoked;
    }

    struct ResponseRecord {
        address responder;
        string responseURI;
        bytes32 responseHash;
    }

    // ============ State Variables ============

    /// @notice Linked Identity Registry
    address public immutable identityRegistry;

    /// @notice Feedback storage: agentId => clientAddress => feedbackIndex => Feedback
    mapping(uint256 => mapping(address => mapping(uint64 => Feedback))) private _feedback;

    /// @notice Next feedback index per agent-client pair
    mapping(uint256 => mapping(address => uint64)) private _nextIndex;

    /// @notice Responses: agentId => clientAddress => feedbackIndex => ResponseRecord[]
    mapping(uint256 => mapping(address => mapping(uint64 => ResponseRecord[]))) private _responses;

    /// @notice All client addresses that have submitted feedback for an agent
    mapping(uint256 => address[]) private _clients;

    /// @notice Track whether a client has submitted feedback (to avoid duplicates in _clients array)
    mapping(uint256 => mapping(address => bool)) private _isClient;

    // ============ Errors ============

    error InvalidDecimals();
    error SelfFeedback();
    error AgentDoesNotExist();
    error FeedbackDoesNotExist();
    error NotFeedbackSubmitter();
    error AlreadyRevoked();
    error ZeroAddress();

    // ============ Constructor ============

    constructor(address _identityRegistry) {
        if (_identityRegistry == address(0)) revert ZeroAddress();
        identityRegistry = _identityRegistry;
    }

    // ============ Initialization ============

    /// @inheritdoc IReputationRegistry
    function getIdentityRegistry() external view override returns (address) {
        return identityRegistry;
    }

    // ============ Feedback Submission ============

    /// @inheritdoc IReputationRegistry
    function giveFeedback(
        uint256 agentId,
        int128 value,
        uint8 valueDecimals,
        string calldata tag1,
        string calldata tag2,
        string calldata endpoint,
        string calldata feedbackURI,
        bytes32 feedbackHash
    ) external override {
        if (valueDecimals > 18) revert InvalidDecimals();
        _requireAgentExists(agentId);

        // Submitter MUST NOT be agent owner or approved operator
        address agentOwner = IERC721(identityRegistry).ownerOf(agentId);
        if (msg.sender == agentOwner) revert SelfFeedback();
        // Also check approval
        if (IERC721(identityRegistry).isApprovedForAll(agentOwner, msg.sender)) revert SelfFeedback();
        if (IERC721(identityRegistry).getApproved(agentId) == msg.sender) revert SelfFeedback();

        uint64 idx = _nextIndex[agentId][msg.sender];
        _feedback[agentId][msg.sender][idx] = Feedback({
            value: value,
            valueDecimals: valueDecimals,
            tag1: tag1,
            tag2: tag2,
            endpoint: endpoint,
            feedbackURI: feedbackURI,
            feedbackHash: feedbackHash,
            isRevoked: false
        });

        unchecked { _nextIndex[agentId][msg.sender] = idx + 1; }

        // Track client list
        if (!_isClient[agentId][msg.sender]) {
            _isClient[agentId][msg.sender] = true;
            _clients[agentId].push(msg.sender);
        }

        emit NewFeedback(
            agentId, msg.sender, idx, value, valueDecimals,
            tag1, tag1, tag2, endpoint, feedbackURI, feedbackHash
        );
    }

    /// @inheritdoc IReputationRegistry
    function revokeFeedback(uint256 agentId, uint64 feedbackIndex) external override {
        if (feedbackIndex >= _nextIndex[agentId][msg.sender]) revert FeedbackDoesNotExist();

        Feedback storage fb = _feedback[agentId][msg.sender][feedbackIndex];
        if (fb.isRevoked) revert AlreadyRevoked();

        fb.isRevoked = true;

        emit FeedbackRevoked(agentId, msg.sender, feedbackIndex);
    }

    // ============ Response ============

    /// @inheritdoc IReputationRegistry
    function appendResponse(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex,
        string calldata responseURI,
        bytes32 responseHash
    ) external override {
        if (feedbackIndex >= _nextIndex[agentId][clientAddress]) revert FeedbackDoesNotExist();

        _responses[agentId][clientAddress][feedbackIndex].push(ResponseRecord({
            responder: msg.sender,
            responseURI: responseURI,
            responseHash: responseHash
        }));

        emit ResponseAppended(agentId, clientAddress, feedbackIndex, msg.sender, responseURI, responseHash);
    }

    // ============ Read Functions ============

    /// @inheritdoc IReputationRegistry
    function getSummary(
        uint256 agentId,
        address[] calldata clientAddresses,
        string calldata tag1,
        string calldata tag2
    ) external view override returns (uint64 count, int128 summaryValue, uint8 summaryValueDecimals) {
        // Default to 0 decimals; will use max decimals found
        uint8 maxDecimals = 0;
        int256 scaledSum = 0;
        bytes32 tag1Hash = bytes(tag1).length > 0 ? keccak256(bytes(tag1)) : bytes32(0);
        bytes32 tag2Hash = bytes(tag2).length > 0 ? keccak256(bytes(tag2)) : bytes32(0);

        for (uint256 c = 0; c < clientAddresses.length; ++c) {
            uint64 lastIdx = _nextIndex[agentId][clientAddresses[c]];
            for (uint64 i = 0; i < lastIdx; ++i) {
                Feedback storage fb = _feedback[agentId][clientAddresses[c]][i];
                if (fb.isRevoked) continue;

                // Tag filtering
                if (tag1Hash != bytes32(0) && keccak256(bytes(fb.tag1)) != tag1Hash) continue;
                if (tag2Hash != bytes32(0) && keccak256(bytes(fb.tag2)) != tag2Hash) continue;

                // Track max decimals for normalization
                if (fb.valueDecimals > maxDecimals) {
                    // Scale existing sum to new decimals
                    scaledSum *= int256(10 ** (fb.valueDecimals - maxDecimals));
                    maxDecimals = fb.valueDecimals;
                }

                // Scale this value to maxDecimals
                int256 scaled = int256(fb.value) * int256(10 ** (maxDecimals - fb.valueDecimals));
                scaledSum += scaled;
                ++count;
            }
        }

        if (count > 0) {
            summaryValue = int128(scaledSum / int256(uint256(count)));
        }
        summaryValueDecimals = maxDecimals;
    }

    /// @inheritdoc IReputationRegistry
    function readFeedback(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex
    ) external view override returns (
        int128 value,
        uint8 valueDecimals,
        string memory tag1,
        string memory tag2,
        bool isRevoked
    ) {
        if (feedbackIndex >= _nextIndex[agentId][clientAddress]) revert FeedbackDoesNotExist();

        Feedback storage fb = _feedback[agentId][clientAddress][feedbackIndex];
        return (fb.value, fb.valueDecimals, fb.tag1, fb.tag2, fb.isRevoked);
    }

    /// @inheritdoc IReputationRegistry
    function readAllFeedback(
        uint256 agentId,
        address[] calldata clientAddresses,
        string calldata tag1,
        string calldata tag2,
        bool includeRevoked
    ) external view override returns (
        address[] memory clients,
        uint64[] memory feedbackIndexes,
        int128[] memory values,
        uint8[] memory valueDecimals,
        string[] memory tag1s,
        string[] memory tag2s,
        bool[] memory revokedStatuses
    ) {
        bytes32 tag1Hash = bytes(tag1).length > 0 ? keccak256(bytes(tag1)) : bytes32(0);
        bytes32 tag2Hash = bytes(tag2).length > 0 ? keccak256(bytes(tag2)) : bytes32(0);

        // First pass: count matching entries
        uint256 total = 0;
        for (uint256 c = 0; c < clientAddresses.length; ++c) {
            uint64 lastIdx = _nextIndex[agentId][clientAddresses[c]];
            for (uint64 i = 0; i < lastIdx; ++i) {
                Feedback storage fb = _feedback[agentId][clientAddresses[c]][i];
                if (!includeRevoked && fb.isRevoked) continue;
                if (tag1Hash != bytes32(0) && keccak256(bytes(fb.tag1)) != tag1Hash) continue;
                if (tag2Hash != bytes32(0) && keccak256(bytes(fb.tag2)) != tag2Hash) continue;
                ++total;
            }
        }

        // Allocate arrays
        clients = new address[](total);
        feedbackIndexes = new uint64[](total);
        values = new int128[](total);
        valueDecimals = new uint8[](total);
        tag1s = new string[](total);
        tag2s = new string[](total);
        revokedStatuses = new bool[](total);

        // Second pass: populate
        uint256 pos = 0;
        for (uint256 c = 0; c < clientAddresses.length; ++c) {
            uint64 lastIdx = _nextIndex[agentId][clientAddresses[c]];
            for (uint64 i = 0; i < lastIdx; ++i) {
                Feedback storage fb = _feedback[agentId][clientAddresses[c]][i];
                if (!includeRevoked && fb.isRevoked) continue;
                if (tag1Hash != bytes32(0) && keccak256(bytes(fb.tag1)) != tag1Hash) continue;
                if (tag2Hash != bytes32(0) && keccak256(bytes(fb.tag2)) != tag2Hash) continue;

                clients[pos] = clientAddresses[c];
                feedbackIndexes[pos] = i;
                values[pos] = fb.value;
                valueDecimals[pos] = fb.valueDecimals;
                tag1s[pos] = fb.tag1;
                tag2s[pos] = fb.tag2;
                revokedStatuses[pos] = fb.isRevoked;
                ++pos;
            }
        }
    }

    /// @inheritdoc IReputationRegistry
    function getResponseCount(
        uint256 agentId,
        address clientAddress,
        uint64 feedbackIndex,
        address[] calldata responders
    ) external view override returns (uint64 count) {
        ResponseRecord[] storage responses = _responses[agentId][clientAddress][feedbackIndex];
        for (uint256 r = 0; r < responses.length; ++r) {
            for (uint256 a = 0; a < responders.length; ++a) {
                if (responses[r].responder == responders[a]) {
                    ++count;
                    break;
                }
            }
        }
    }

    /// @inheritdoc IReputationRegistry
    function getClients(uint256 agentId) external view override returns (address[] memory) {
        return _clients[agentId];
    }

    /// @inheritdoc IReputationRegistry
    function getLastIndex(
        uint256 agentId,
        address clientAddress
    ) external view override returns (uint64) {
        return _nextIndex[agentId][clientAddress];
    }

    // ============ Internal Functions ============

    function _requireAgentExists(uint256 agentId) internal view {
        // Check the identity registry owns this token
        try IERC721(identityRegistry).ownerOf(agentId) returns (address) {
            // exists
        } catch {
            revert AgentDoesNotExist();
        }
    }
}
