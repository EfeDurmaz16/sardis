// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./SardisSmartAccount.sol";

/**
 * @title SardisSmartAccountFactory
 * @notice Factory for deterministic SardisSmartAccount deployments.
 */
contract SardisSmartAccountFactory is Ownable {
    /// @notice Default ERC-4337 entry point for created accounts.
    address public immutable entryPoint;

    event SmartAccountCreated(
        address indexed owner,
        address indexed policySigner,
        bytes32 indexed salt,
        address smartAccount
    );

    constructor(address entryPoint_, address owner_) Ownable(owner_) {
        require(entryPoint_ != address(0), "entrypoint=0");
        entryPoint = entryPoint_;
    }

    /**
     * @notice Create a SardisSmartAccount using CREATE2.
     */
    function createAccount(address owner_, address policySigner, bytes32 salt) external returns (address smartAccount) {
        smartAccount = getAddress(owner_, policySigner, salt);
        if (smartAccount.code.length > 0) {
            return smartAccount;
        }

        SardisSmartAccount account = new SardisSmartAccount{salt: _salt(owner_, policySigner, salt)}(
            owner_,
            policySigner,
            entryPoint
        );
        smartAccount = address(account);

        emit SmartAccountCreated(owner_, policySigner, salt, smartAccount);
    }

    /**
     * @notice Predict deterministic smart account address.
     */
    function getAddress(address owner_, address policySigner, bytes32 salt) public view returns (address) {
        bytes memory bytecode = abi.encodePacked(
            type(SardisSmartAccount).creationCode,
            abi.encode(owner_, policySigner, entryPoint)
        );

        bytes32 hash = keccak256(
            abi.encodePacked(
                bytes1(0xff),
                address(this),
                _salt(owner_, policySigner, salt),
                keccak256(bytecode)
            )
        );

        return address(uint160(uint256(hash)));
    }

    function _salt(address owner_, address policySigner, bytes32 salt) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(owner_, policySigner, salt));
    }
}
