// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title SardisAgentRegistry
 * @notice ERC-8004 Trustless Agents on-chain identity registry
 * @dev ERC-721 based registry where each agent is an NFT with metadata URI
 *
 * Features:
 * - Register agents as NFTs with metadata URI (IPFS/HTTP)
 * - Update agent metadata (owner only)
 * - On-chain reputation system between agents
 * - Validation attestations from trusted validators
 * - ENS name binding support
 *
 * ERC-8004 Standard Compliance:
 * - Identity Registry: ERC-721 tokens with agentURI
 * - Reputation Registry: On-chain scores and categories
 * - Validation Registry: Attestations from validators
 */
contract SardisAgentRegistry is ERC721, Ownable, Pausable {
    // ============ State Variables ============

    /// @notice Next agent ID (token ID counter)
    uint256 private _nextAgentId = 1;

    /// @notice Agent metadata URI (IPFS/HTTP) per agent ID
    mapping(uint256 => string) private _agentURIs;

    /// @notice ENS name binding per agent ID
    mapping(uint256 => string) private _ensNames;

    /// @notice Reputation entries: agentId => ReputationEntry[]
    mapping(uint256 => ReputationEntry[]) private _reputations;

    /// @notice Validation results: agentId => ValidationResult[]
    mapping(uint256 => ValidationResult[]) private _validations;

    /// @notice Trusted validators who can submit attestations
    mapping(address => bool) public trustedValidators;

    // ============ Structs ============

    struct ReputationEntry {
        uint256 fromAgent;     // Agent giving reputation
        uint256 toAgent;       // Agent receiving reputation
        uint16 score;          // 0-1000 reputation score
        string category;       // e.g. "reliability", "speed", "quality"
        uint256 timestamp;
    }

    struct ValidationResult {
        address validator;
        uint256 agentId;
        bool isValid;
        string validationType;  // e.g. "kyc", "certification", "audit"
        string evidenceURI;     // IPFS/HTTP URI to evidence
        uint256 timestamp;
    }

    // ============ Events ============

    event AgentRegistered(
        uint256 indexed agentId,
        address indexed owner,
        string agentURI
    );

    event AgentUpdated(
        uint256 indexed agentId,
        string newAgentURI
    );

    event ReputationSubmitted(
        uint256 indexed fromAgent,
        uint256 indexed toAgent,
        uint16 score,
        string category
    );

    event ValidationSubmitted(
        uint256 indexed agentId,
        address indexed validator,
        bool isValid,
        string validationType
    );

    event ENSNameBound(
        uint256 indexed agentId,
        string ensName
    );

    event ValidatorAdded(address indexed validator);
    event ValidatorRemoved(address indexed validator);

    // ============ Constructor ============

    constructor() ERC721("Sardis Agent Identity", "SARDIS-AGENT") Ownable(msg.sender) {
        // Platform owner is trusted validator by default
        trustedValidators[msg.sender] = true;
    }

    // ============ Agent Registration ============

    /**
     * @notice Register a new agent identity
     * @param agentURI IPFS/HTTP URI pointing to agent metadata JSON
     * @return agentId The assigned agent token ID
     */
    function registerAgent(string memory agentURI) external whenNotPaused returns (uint256) {
        require(bytes(agentURI).length > 0, "Agent URI cannot be empty");

        uint256 agentId = _nextAgentId++;
        _safeMint(msg.sender, agentId);
        _agentURIs[agentId] = agentURI;

        emit AgentRegistered(agentId, msg.sender, agentURI);
        return agentId;
    }

    /**
     * @notice Update agent metadata URI (owner only)
     * @param agentId Agent token ID
     * @param newURI New metadata URI
     */
    function updateAgentURI(uint256 agentId, string memory newURI) external {
        require(ownerOf(agentId) == msg.sender, "Not agent owner");
        require(bytes(newURI).length > 0, "URI cannot be empty");

        _agentURIs[agentId] = newURI;
        emit AgentUpdated(agentId, newURI);
    }

    /**
     * @notice Get agent metadata URI
     * @param agentId Agent token ID
     * @return Agent metadata URI
     */
    function getAgentURI(uint256 agentId) external view returns (string memory) {
        require(_ownerOf(agentId) != address(0), "Agent does not exist");
        return _agentURIs[agentId];
    }

    /**
     * @notice Override tokenURI to return agentURI
     */
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_ownerOf(tokenId) != address(0), "Agent does not exist");
        return _agentURIs[tokenId];
    }

    // ============ ENS Binding ============

    /**
     * @notice Bind ENS name to agent (owner only)
     * @param agentId Agent token ID
     * @param ensName ENS name (e.g., "myagent.eth")
     */
    function bindENSName(uint256 agentId, string memory ensName) external {
        require(ownerOf(agentId) == msg.sender, "Not agent owner");
        _ensNames[agentId] = ensName;
        emit ENSNameBound(agentId, ensName);
    }

    /**
     * @notice Get ENS name for agent
     */
    function getENSName(uint256 agentId) external view returns (string memory) {
        return _ensNames[agentId];
    }

    // ============ Reputation System ============

    /**
     * @notice Submit reputation for an agent
     * @param fromAgent Agent giving reputation (must be owned by caller)
     * @param toAgent Agent receiving reputation
     * @param score Reputation score (0-1000)
     * @param category Reputation category
     */
    function submitReputation(
        uint256 fromAgent,
        uint256 toAgent,
        uint16 score,
        string memory category
    ) external {
        require(ownerOf(fromAgent) == msg.sender, "Not owner of fromAgent");
        require(_ownerOf(toAgent) != address(0), "toAgent does not exist");
        require(score <= 1000, "Score must be 0-1000");
        require(fromAgent != toAgent, "Cannot rate self");

        ReputationEntry memory entry = ReputationEntry({
            fromAgent: fromAgent,
            toAgent: toAgent,
            score: score,
            category: category,
            timestamp: block.timestamp
        });

        _reputations[toAgent].push(entry);
        emit ReputationSubmitted(fromAgent, toAgent, score, category);
    }

    /**
     * @notice Get reputation count for an agent
     */
    function getReputationCount(uint256 agentId) external view returns (uint256) {
        return _reputations[agentId].length;
    }

    /**
     * @notice Get reputation entries for an agent
     * @param agentId Agent token ID
     * @param offset Pagination offset
     * @param limit Pagination limit
     */
    function getReputations(
        uint256 agentId,
        uint256 offset,
        uint256 limit
    ) external view returns (ReputationEntry[] memory) {
        ReputationEntry[] storage allReputations = _reputations[agentId];
        uint256 total = allReputations.length;

        if (offset >= total) {
            return new ReputationEntry[](0);
        }

        uint256 end = offset + limit;
        if (end > total) {
            end = total;
        }

        ReputationEntry[] memory result = new ReputationEntry[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            result[i - offset] = allReputations[i];
        }

        return result;
    }

    /**
     * @notice Calculate average reputation score
     */
    function getAverageReputation(uint256 agentId) external view returns (uint256) {
        ReputationEntry[] storage reputations = _reputations[agentId];
        if (reputations.length == 0) {
            return 0;
        }

        uint256 sum = 0;
        for (uint256 i = 0; i < reputations.length; i++) {
            sum += reputations[i].score;
        }

        return sum / reputations.length;
    }

    // ============ Validation System ============

    /**
     * @notice Submit validation attestation (trusted validators only)
     * @param agentId Agent being validated
     * @param isValid Validation result
     * @param validationType Type of validation
     * @param evidenceURI URI to validation evidence
     */
    function submitValidation(
        uint256 agentId,
        bool isValid,
        string memory validationType,
        string memory evidenceURI
    ) external {
        require(trustedValidators[msg.sender], "Not a trusted validator");
        require(_ownerOf(agentId) != address(0), "Agent does not exist");

        ValidationResult memory result = ValidationResult({
            validator: msg.sender,
            agentId: agentId,
            isValid: isValid,
            validationType: validationType,
            evidenceURI: evidenceURI,
            timestamp: block.timestamp
        });

        _validations[agentId].push(result);
        emit ValidationSubmitted(agentId, msg.sender, isValid, validationType);
    }

    /**
     * @notice Get validation count for an agent
     */
    function getValidationCount(uint256 agentId) external view returns (uint256) {
        return _validations[agentId].length;
    }

    /**
     * @notice Get validations for an agent
     */
    function getValidations(
        uint256 agentId,
        uint256 offset,
        uint256 limit
    ) external view returns (ValidationResult[] memory) {
        ValidationResult[] storage allValidations = _validations[agentId];
        uint256 total = allValidations.length;

        if (offset >= total) {
            return new ValidationResult[](0);
        }

        uint256 end = offset + limit;
        if (end > total) {
            end = total;
        }

        ValidationResult[] memory result = new ValidationResult[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            result[i - offset] = allValidations[i];
        }

        return result;
    }

    // ============ Validator Management ============

    /**
     * @notice Add trusted validator (owner only)
     */
    function addValidator(address validator) external onlyOwner {
        trustedValidators[validator] = true;
        emit ValidatorAdded(validator);
    }

    /**
     * @notice Remove trusted validator (owner only)
     */
    function removeValidator(address validator) external onlyOwner {
        trustedValidators[validator] = false;
        emit ValidatorRemoved(validator);
    }

    // ============ Emergency Controls ============

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
