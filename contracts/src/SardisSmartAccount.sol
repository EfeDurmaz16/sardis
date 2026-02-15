// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/account/Account.sol";
import "@openzeppelin/contracts/utils/cryptography/signers/SignerECDSA.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/interfaces/draft-IERC4337.sol";
import "@openzeppelin/contracts/account/utils/draft-ERC4337Utils.sol";
import "@openzeppelin/contracts/utils/Address.sol";

/**
 * @title SardisSmartAccount
 * @notice ERC-4337 compatible smart account (v2) for Sardis wallets
 * @dev Supports UserOperation validation, owner controls, and policy signer rotation.
 */
contract SardisSmartAccount is Account, SignerECDSA, Ownable, Pausable, ReentrancyGuard {
    using Address for address;

    /// @notice Current policy signer used to validate UserOperation signatures.
    address public policySigner;

    /// @notice Fixed EntryPoint contract used for ERC-4337 execution.
    IEntryPoint public immutable sardisEntryPoint;

    event PolicySignerUpdated(address indexed oldSigner, address indexed newSigner);
    event Executed(address indexed target, uint256 value, bytes data);

    error ZeroAddress();

    /**
     * @param owner_ Owner/admin of the account
     * @param policySigner_ ECDSA signer for UserOperation authorization
     * @param entryPoint_ ERC-4337 entry point v0.7
     */
    constructor(address owner_, address policySigner_, address entryPoint_)
        SignerECDSA(policySigner_)
        Ownable(owner_)
    {
        if (owner_ == address(0) || policySigner_ == address(0) || entryPoint_ == address(0)) {
            revert ZeroAddress();
        }
        policySigner = policySigner_;
        sardisEntryPoint = IEntryPoint(entryPoint_);
    }

    /**
     * @inheritdoc Account
     */
    function entryPoint() public view override returns (IEntryPoint) {
        return sardisEntryPoint;
    }

    /**
     * @notice Execute a call from EntryPoint or self.
     */
    function execute(address target, uint256 value, bytes calldata data)
        external
        onlyEntryPointOrSelf
        whenNotPaused
        nonReentrant
    {
        target.functionCallWithValue(data, value);
        emit Executed(target, value, data);
    }

    /**
     * @notice Execute multiple calls in sequence from EntryPoint or self.
     */
    function executeBatch(address[] calldata targets, uint256[] calldata values, bytes[] calldata data)
        external
        onlyEntryPointOrSelf
        whenNotPaused
        nonReentrant
    {
        require(targets.length == values.length && values.length == data.length, "Length mismatch");
        for (uint256 i = 0; i < targets.length; i++) {
            targets[i].functionCallWithValue(data[i], values[i]);
            emit Executed(targets[i], values[i], data[i]);
        }
    }

    /**
     * @notice Rotate policy signer.
     */
    function setPolicySigner(address newSigner) external onlyOwner {
        if (newSigner == address(0)) revert ZeroAddress();
        address oldSigner = policySigner;
        policySigner = newSigner;
        _setSigner(newSigner);
        emit PolicySignerUpdated(oldSigner, newSigner);
    }

    /**
     * @notice Pause account execution.
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause account execution.
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @inheritdoc Account
     * @dev Uses personal_sign style hash for compatibility with common MPC signers.
     */
    function _signableUserOpHash(PackedUserOperation calldata, bytes32 userOpHash)
        internal
        pure
        override
        returns (bytes32)
    {
        return keccak256(abi.encodePacked("\\x19Ethereum Signed Message:\\n32", userOpHash));
    }
}
