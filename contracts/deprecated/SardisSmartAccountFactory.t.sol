// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "./SardisSmartAccountFactory.sol";

contract SardisSmartAccountFactoryTest is Test {
    SardisSmartAccountFactory internal factory;

    address internal owner = address(this);
    address internal entryPoint = address(0x4337);
    address internal walletOwner = address(0x1111);
    address internal policySigner = address(0x2222);

    function setUp() public {
        factory = new SardisSmartAccountFactory(entryPoint, owner);
    }

    function testCreateDeterministicAccount() public {
        bytes32 salt = keccak256("sardis");
        address predicted = factory.getAddress(walletOwner, policySigner, salt);
        address deployed = factory.createAccount(walletOwner, policySigner, salt);

        assertEq(predicted, deployed);
        assertGt(deployed.code.length, 0);
    }

    function testCreateIsIdempotentForSameSalt() public {
        bytes32 salt = keccak256("idempotent");
        address first = factory.createAccount(walletOwner, policySigner, salt);
        address second = factory.createAccount(walletOwner, policySigner, salt);

        assertEq(first, second);
    }
}
