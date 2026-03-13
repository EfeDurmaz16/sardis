// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/interfaces/IERC1271.sol";

import "./interfaces/IIdentityRegistry.sol";

/**
 * @title SardisIdentityRegistry
 * @notice ERC-8004 compliant Identity Registry — ERC-721 based on-chain agent identity
 * @dev Each minted token represents an agent. Agents are identified globally as:
 *      eip155:{chainId}:{registryAddress}#{agentId}
 *
 *      Features:
 *        - Three register() overloads (URI+metadata, URI only, bare)
 *        - Agent wallet linking via EIP-712 signature (EOA) or ERC-1271 (smart contract)
 *        - Arbitrary metadata storage (except reserved "agentWallet" key)
 *        - Wallet cleared on token transfer; new owner must re-verify
 *
 *      Spec: https://eips.ethereum.org/EIPS/eip-8004
 */
contract SardisIdentityRegistry is IIdentityRegistry, ERC721URIStorage, EIP712 {
    using ECDSA for bytes32;

    // ============ Constants ============

    bytes32 private constant SET_AGENT_WALLET_TYPEHASH =
        keccak256("SetAgentWallet(uint256 agentId,address newWallet,uint256 deadline)");

    bytes32 private constant RESERVED_WALLET_KEY_HASH = keccak256("agentWallet");

    // ============ State Variables ============

    /// @notice Monotonically increasing agent ID counter
    uint256 public nextAgentId;

    /// @notice Linked wallet for each agent (verified via signature)
    mapping(uint256 => address) private _agentWallets;

    /// @notice Arbitrary metadata storage: agentId => keccak256(key) => value
    mapping(uint256 => mapping(bytes32 => bytes)) private _metadata;

    // ============ Errors ============

    event AgentWalletSet(uint256 indexed agentId, address indexed wallet);
    event AgentWalletUnset(uint256 indexed agentId);

    error NotAgentOwnerOrApproved();
    error ReservedMetadataKey();
    error InvalidSignature();
    error ExpiredDeadline();
    error ZeroAddress();
    error AgentDoesNotExist();

    // ============ Constructor ============

    constructor() ERC721("Sardis Agent Identity", "SAGENT") EIP712("SardisIdentityRegistry", "1") { }

    // ============ Registration ============

    /// @inheritdoc IIdentityRegistry
    function register(string calldata agentURI, MetadataEntry[] calldata metadata)
        external
        override
        returns (uint256 agentId)
    {
        agentId = _registerAgent(agentURI);

        for (uint256 i = 0; i < metadata.length; ++i) {
            bytes32 keyHash = keccak256(bytes(metadata[i].metadataKey));
            if (keyHash == RESERVED_WALLET_KEY_HASH) revert ReservedMetadataKey();
            _metadata[agentId][keyHash] = metadata[i].metadataValue;
            emit MetadataSet(agentId, metadata[i].metadataKey, metadata[i].metadataKey, metadata[i].metadataValue);
        }
    }

    /// @inheritdoc IIdentityRegistry
    function register(string calldata agentURI) external override returns (uint256 agentId) {
        agentId = _registerAgent(agentURI);
    }

    /// @inheritdoc IIdentityRegistry
    function register() external override returns (uint256 agentId) {
        agentId = _registerAgent("");
    }

    // ============ Agent URI ============

    /// @inheritdoc IIdentityRegistry
    function setAgentURI(uint256 agentId, string calldata newURI) external override {
        _requireOwnerOrApproved(agentId);
        _setTokenURI(agentId, newURI);
        emit URIUpdated(agentId, newURI, msg.sender);
    }

    // ============ Agent Wallet ============

    /// @inheritdoc IIdentityRegistry
    function setAgentWallet(uint256 agentId, address newWallet, uint256 deadline, bytes calldata signature)
        external
        override
    {
        _requireOwnerOrApproved(agentId);
        if (newWallet == address(0)) revert ZeroAddress();
        if (block.timestamp > deadline) revert ExpiredDeadline();

        // Verify signature from newWallet
        bytes32 structHash = keccak256(abi.encode(SET_AGENT_WALLET_TYPEHASH, agentId, newWallet, deadline));
        bytes32 digest = _hashTypedDataV4(structHash);

        // Try EIP-712 ECDSA first
        address recovered = digest.recover(signature);
        if (recovered == newWallet) {
            _agentWallets[agentId] = newWallet;
            emit AgentWalletSet(agentId, newWallet);
            return;
        }

        // Try ERC-1271 for smart contract wallets
        if (newWallet.code.length > 0) {
            try IERC1271(newWallet).isValidSignature(digest, signature) returns (bytes4 magicValue) {
                if (magicValue == IERC1271.isValidSignature.selector) {
                    _agentWallets[agentId] = newWallet;
                    emit AgentWalletSet(agentId, newWallet);
                    return;
                }
            } catch { }
        }

        revert InvalidSignature();
    }

    /// @inheritdoc IIdentityRegistry
    function getAgentWallet(uint256 agentId) external view override returns (address) {
        _requireExists(agentId);
        return _agentWallets[agentId];
    }

    /// @inheritdoc IIdentityRegistry
    function unsetAgentWallet(uint256 agentId) external override {
        _requireOwnerOrApproved(agentId);
        delete _agentWallets[agentId];
        emit AgentWalletUnset(agentId);
    }

    // ============ Metadata ============

    /// @inheritdoc IIdentityRegistry
    function getMetadata(uint256 agentId, string calldata metadataKey) external view override returns (bytes memory) {
        _requireExists(agentId);
        return _metadata[agentId][keccak256(bytes(metadataKey))];
    }

    /// @inheritdoc IIdentityRegistry
    function setMetadata(uint256 agentId, string calldata metadataKey, bytes calldata metadataValue) external override {
        _requireOwnerOrApproved(agentId);
        bytes32 keyHash = keccak256(bytes(metadataKey));
        if (keyHash == RESERVED_WALLET_KEY_HASH) revert ReservedMetadataKey();

        _metadata[agentId][keyHash] = metadataValue;
        emit MetadataSet(agentId, metadataKey, metadataKey, metadataValue);
    }

    // ============ EIP-712 Domain ============

    /**
     * @notice Returns the EIP-712 domain separator for wallet verification
     */
    function DOMAIN_SEPARATOR() external view returns (bytes32) {
        return _domainSeparatorV4();
    }

    // ============ Internal Functions ============

    function _registerAgent(string memory agentURI) internal returns (uint256 agentId) {
        agentId = nextAgentId;
        unchecked {
            ++nextAgentId;
        }

        _safeMint(msg.sender, agentId);

        if (bytes(agentURI).length > 0) {
            _setTokenURI(agentId, agentURI);
        }

        // Default wallet is owner address per spec
        _agentWallets[agentId] = msg.sender;

        emit Registered(agentId, agentURI, msg.sender);
    }

    function _requireOwnerOrApproved(uint256 agentId) internal view {
        _requireExists(agentId);
        if (!_isAuthorized(ownerOf(agentId), msg.sender, agentId)) {
            revert NotAgentOwnerOrApproved();
        }
    }

    function _requireExists(uint256 agentId) internal view {
        if (agentId >= nextAgentId) revert AgentDoesNotExist();
        // Also detect burned tokens — _ownerOf returns address(0) for burned tokens
        if (_ownerOf(agentId) == address(0)) revert AgentDoesNotExist();
    }

    /**
     * @dev Clear wallet on transfer per ERC-8004 spec:
     *      "Cleared on token transfer; new owner must re-verify"
     */
    function _update(address to, uint256 tokenId, address auth) internal override returns (address) {
        address from = super._update(to, tokenId, auth);

        // Clear wallet on transfer (not on mint)
        if (from != address(0) && to != address(0)) {
            delete _agentWallets[tokenId];
        }

        return from;
    }
}
