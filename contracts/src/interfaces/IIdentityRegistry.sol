// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IIdentityRegistry
 * @notice ERC-8004 compliant Identity Registry interface
 * @dev ERC-721 based on-chain agent identity. Each token represents one agent.
 *      Global agent identifier: eip155:{chainId}:{registryAddress}#{agentId}
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8004
 */
interface IIdentityRegistry {
    // ============ Structs ============

    struct MetadataEntry {
        string metadataKey;
        bytes metadataValue;
    }

    // ============ Events ============

    event Registered(
        uint256 indexed agentId,
        string agentURI,
        address indexed owner
    );

    event URIUpdated(
        uint256 indexed agentId,
        string newURI,
        address indexed updatedBy
    );

    event MetadataSet(
        uint256 indexed agentId,
        string indexed indexedMetadataKey,
        string metadataKey,
        bytes metadataValue
    );

    // ============ Registration Functions ============

    /**
     * @notice Register a new agent with URI and metadata
     * @param agentURI URI pointing to agent registration file
     * @param metadata Array of key-value metadata entries
     * @return agentId The unique token ID for the registered agent
     */
    function register(
        string calldata agentURI,
        MetadataEntry[] calldata metadata
    ) external returns (uint256 agentId);

    /**
     * @notice Register a new agent with URI only
     * @param agentURI URI pointing to agent registration file
     * @return agentId The unique token ID for the registered agent
     */
    function register(
        string calldata agentURI
    ) external returns (uint256 agentId);

    /**
     * @notice Register a new agent with no URI or metadata
     * @return agentId The unique token ID for the registered agent
     */
    function register() external returns (uint256 agentId);

    // ============ Agent URI ============

    /**
     * @notice Update the URI for an agent
     * @param agentId The agent token ID
     * @param newURI New URI for the agent
     */
    function setAgentURI(uint256 agentId, string calldata newURI) external;

    // ============ Agent Wallet ============

    /**
     * @notice Set or change the agent's linked wallet address
     * @dev Requires EIP-712 signature from the new wallet (EOA) or ERC-1271 (smart contract)
     * @param agentId The agent token ID
     * @param newWallet Address of the wallet to link
     * @param deadline Signature expiry timestamp
     * @param signature EIP-712 or ERC-1271 signature from newWallet
     */
    function setAgentWallet(
        uint256 agentId,
        address newWallet,
        uint256 deadline,
        bytes calldata signature
    ) external;

    /**
     * @notice Get the linked wallet for an agent
     * @param agentId The agent token ID
     * @return wallet The linked wallet address
     */
    function getAgentWallet(uint256 agentId) external view returns (address wallet);

    /**
     * @notice Remove the linked wallet for an agent
     * @param agentId The agent token ID
     */
    function unsetAgentWallet(uint256 agentId) external;

    // ============ Metadata ============

    /**
     * @notice Get metadata value for a key
     * @param agentId The agent token ID
     * @param metadataKey The metadata key
     * @return value The metadata value
     */
    function getMetadata(
        uint256 agentId,
        string calldata metadataKey
    ) external view returns (bytes memory value);

    /**
     * @notice Set metadata for an agent
     * @dev "agentWallet" key is reserved and cannot be set via this function
     * @param agentId The agent token ID
     * @param metadataKey The metadata key
     * @param metadataValue The metadata value
     */
    function setMetadata(
        uint256 agentId,
        string calldata metadataKey,
        bytes calldata metadataValue
    ) external;
}
