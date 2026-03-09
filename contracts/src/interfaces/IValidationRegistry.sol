// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IValidationRegistry
 * @notice ERC-8004 compliant Validation Registry interface
 * @dev Manages validation requests and responses for agents.
 *      Validators assess agent capabilities, outputs, or trustworthiness.
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8004
 */
interface IValidationRegistry {
    // ============ Events ============

    event ValidationRequest(
        address indexed validatorAddress,
        uint256 indexed agentId,
        string requestURI,
        bytes32 indexed requestHash
    );

    event ValidationResponse(
        address indexed validatorAddress,
        uint256 indexed agentId,
        bytes32 indexed requestHash,
        uint8 response,
        string responseURI,
        bytes32 responseHash,
        string tag
    );

    // ============ Initialization ============

    /**
     * @notice Get the linked Identity Registry
     * @return identityRegistry Address of the Identity Registry contract
     */
    function getIdentityRegistry() external view returns (address identityRegistry);

    // ============ Validation Request ============

    /**
     * @notice Submit a validation request
     * @dev MUST be called by agent owner or approved operator
     * @param validatorAddress Address of the validator to assess the agent
     * @param agentId The agent token ID in the Identity Registry
     * @param requestURI URI pointing to off-chain request data (inputs/outputs)
     * @param requestHash KECCAK-256 commitment to the request payload
     */
    function validationRequest(
        address validatorAddress,
        uint256 agentId,
        string calldata requestURI,
        bytes32 requestHash
    ) external;

    // ============ Validation Response ============

    /**
     * @notice Submit a validation response
     * @dev MUST be called by the validatorAddress from the original request.
     *      Can be called multiple times for the same requestHash.
     * @param requestHash The hash from the original validation request
     * @param response Score 0-100 (0 = failed, 100 = passed)
     * @param responseURI Optional URI to off-chain response details
     * @param responseHash Optional KECCAK-256 hash of responseURI content
     * @param tag Optional categorization tag
     */
    function validationResponse(
        bytes32 requestHash,
        uint8 response,
        string calldata responseURI,
        bytes32 responseHash,
        string calldata tag
    ) external;

    // ============ Read Functions ============

    /**
     * @notice Get the status of a validation request
     * @param requestHash The request hash
     * @return validatorAddress The validator address
     * @return agentId The agent token ID
     * @return response Latest response score (0-100)
     * @return responseHash Hash of latest response
     * @return tag Tag from latest response
     * @return lastUpdate Timestamp of last update
     */
    function getValidationStatus(bytes32 requestHash) external view returns (
        address validatorAddress,
        uint256 agentId,
        uint8 response,
        bytes32 responseHash,
        string memory tag,
        uint256 lastUpdate
    );

    /**
     * @notice Get aggregated validation summary for an agent
     * @dev agentId is mandatory; validatorAddresses and tag are optional
     * @param agentId The agent token ID
     * @param validatorAddresses Optional filter by validators
     * @param tag Optional tag filter
     * @return count Number of matching validations
     * @return averageResponse Average response score
     */
    function getSummary(
        uint256 agentId,
        address[] calldata validatorAddresses,
        string calldata tag
    ) external view returns (uint64 count, uint8 averageResponse);

    /**
     * @notice Get all validation request hashes for an agent
     * @param agentId The agent token ID
     * @return requestHashes Array of request hashes
     */
    function getAgentValidations(uint256 agentId) external view returns (bytes32[] memory requestHashes);

    /**
     * @notice Get all validation request hashes for a validator
     * @param validatorAddress The validator address
     * @return requestHashes Array of request hashes
     */
    function getValidatorRequests(address validatorAddress) external view returns (bytes32[] memory requestHashes);
}
