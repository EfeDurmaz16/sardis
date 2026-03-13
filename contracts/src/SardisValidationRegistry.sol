// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";

import "./interfaces/IValidationRegistry.sol";

/**
 * @title SardisValidationRegistry
 * @notice ERC-8004 compliant Validation Registry — on-chain validation for agents
 * @dev Linked to an Identity Registry (ERC-721). Agent owners request validation
 *      from validators, who respond with scores (0-100). Validators can update scores.
 *
 *      Rules:
 *        - Only agent owner/operator can create validation requests
 *        - Only the designated validator can respond to a request
 *        - Validators can respond multiple times (updates score)
 *        - On-chain: requestHash, validatorAddress, agentId, response, responseHash, lastUpdate, tag
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8004
 */
contract SardisValidationRegistry is IValidationRegistry {
    // ============ Structs (Internal) ============

    struct ValidationRecord {
        address validatorAddress;
        uint256 agentId;
        uint8 response;
        bytes32 responseHash;
        string tag;
        uint256 lastUpdate;
        bool exists;
    }

    // ============ State Variables ============

    /// @notice Linked Identity Registry
    address public immutable identityRegistry;

    /// @notice Validation records by requestHash
    mapping(bytes32 => ValidationRecord) private _validations;

    /// @notice All request hashes per agent
    mapping(uint256 => bytes32[]) private _agentValidations;

    /// @notice All request hashes per validator
    mapping(address => bytes32[]) private _validatorRequests;

    // ============ Errors ============

    error NotAgentOwnerOrApproved();
    error NotDesignatedValidator();
    error InvalidResponse();
    error RequestAlreadyExists();
    error RequestDoesNotExist();
    error ZeroAddress();
    error AgentDoesNotExist();

    // ============ Constructor ============

    constructor(address _identityRegistry) {
        if (_identityRegistry == address(0)) revert ZeroAddress();
        identityRegistry = _identityRegistry;
    }

    // ============ Initialization ============

    /// @inheritdoc IValidationRegistry
    function getIdentityRegistry() external view override returns (address) {
        return identityRegistry;
    }

    // ============ Validation Request ============

    /// @inheritdoc IValidationRegistry
    function validationRequest(
        address validatorAddress,
        uint256 agentId,
        string calldata requestURI,
        bytes32 requestHash
    ) external override {
        if (validatorAddress == address(0)) revert ZeroAddress();
        _requireAgentOwnerOrApproved(agentId);
        if (_validations[requestHash].exists) revert RequestAlreadyExists();

        _validations[requestHash] = ValidationRecord({
            validatorAddress: validatorAddress,
            agentId: agentId,
            response: 0,
            responseHash: bytes32(0),
            tag: "",
            lastUpdate: 0, // Only set when validator responds
            exists: true
        });

        _agentValidations[agentId].push(requestHash);
        _validatorRequests[validatorAddress].push(requestHash);

        emit ValidationRequest(validatorAddress, agentId, requestURI, requestHash);
    }

    // ============ Validation Response ============

    /// @inheritdoc IValidationRegistry
    function validationResponse(
        bytes32 requestHash,
        uint8 response,
        string calldata responseURI,
        bytes32 responseHash,
        string calldata tag
    ) external override {
        ValidationRecord storage record = _validations[requestHash];
        if (!record.exists) revert RequestDoesNotExist();
        if (msg.sender != record.validatorAddress) revert NotDesignatedValidator();
        if (response > 100) revert InvalidResponse();

        record.response = response;
        record.responseHash = responseHash;
        record.tag = tag;
        record.lastUpdate = block.timestamp;

        emit ValidationResponse(msg.sender, record.agentId, requestHash, response, responseURI, responseHash, tag);
    }

    // ============ Read Functions ============

    /// @inheritdoc IValidationRegistry
    function getValidationStatus(bytes32 requestHash)
        external
        view
        override
        returns (
            address validatorAddress,
            uint256 agentId,
            uint8 response,
            bytes32 responseHash,
            string memory tag,
            uint256 lastUpdate
        )
    {
        ValidationRecord storage record = _validations[requestHash];
        return (
            record.validatorAddress, record.agentId, record.response, record.responseHash, record.tag, record.lastUpdate
        );
    }

    /// @inheritdoc IValidationRegistry
    function getSummary(uint256 agentId, address[] calldata validatorAddresses, string calldata tag)
        external
        view
        override
        returns (uint64 count, uint8 averageResponse)
    {
        bytes32[] storage hashes = _agentValidations[agentId];
        bytes32 tagHash = bytes(tag).length > 0 ? keccak256(bytes(tag)) : bytes32(0);
        uint256 totalScore = 0;

        for (uint256 i = 0; i < hashes.length; ++i) {
            ValidationRecord storage record = _validations[hashes[i]];

            // Skip records with no response (lastUpdate == 0 means no response yet)
            if (record.lastUpdate == 0) continue;

            // Filter by validator addresses if provided
            if (validatorAddresses.length > 0) {
                bool matchesValidator = false;
                for (uint256 v = 0; v < validatorAddresses.length; ++v) {
                    if (record.validatorAddress == validatorAddresses[v]) {
                        matchesValidator = true;
                        break;
                    }
                }
                if (!matchesValidator) continue;
            }

            // Filter by tag if provided
            if (tagHash != bytes32(0) && keccak256(bytes(record.tag)) != tagHash) continue;

            // Only count if validator has responded (response > 0 or explicitly set)
            totalScore += record.response;
            ++count;
        }

        if (count > 0) {
            averageResponse = uint8(totalScore / count);
        }
    }

    /// @inheritdoc IValidationRegistry
    function getAgentValidations(uint256 agentId) external view override returns (bytes32[] memory) {
        return _agentValidations[agentId];
    }

    /// @inheritdoc IValidationRegistry
    function getValidatorRequests(address validatorAddress) external view override returns (bytes32[] memory) {
        return _validatorRequests[validatorAddress];
    }

    // ============ Internal Functions ============

    function _requireAgentOwnerOrApproved(uint256 agentId) internal view {
        address agentOwner;
        try IERC721(identityRegistry).ownerOf(agentId) returns (address owner) {
            agentOwner = owner;
        } catch {
            revert AgentDoesNotExist();
        }

        if (msg.sender != agentOwner) {
            if (!IERC721(identityRegistry).isApprovedForAll(agentOwner, msg.sender)) {
                if (IERC721(identityRegistry).getApproved(agentId) != msg.sender) {
                    revert NotAgentOwnerOrApproved();
                }
            }
        }
    }
}
