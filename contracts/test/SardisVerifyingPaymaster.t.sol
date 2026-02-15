// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SardisVerifyingPaymaster.sol";
import "@openzeppelin/contracts/interfaces/draft-IERC4337.sol";

contract SardisVerifyingPaymasterTest is Test {
    SardisVerifyingPaymaster internal paymaster;

    address internal wallet = address(0xAAA1);

    function setUp() public {
        // this test contract acts as mock EntryPoint.
        paymaster = new SardisVerifyingPaymaster(address(this), address(this), 1 ether, 10 ether);
    }

    function _buildUserOp(address sender) internal pure returns (PackedUserOperation memory op) {
        op.sender = sender;
        op.nonce = 0;
        op.initCode = "";
        op.callData = "";
        op.accountGasLimits = bytes32(0);
        op.preVerificationGas = 0;
        op.gasFees = bytes32(0);
        op.paymasterAndData = "";
        op.signature = "";
    }

    function testValidatePaymasterUserOpSuccess() public {
        paymaster.setWalletAllowed(wallet, true);

        PackedUserOperation memory op = _buildUserOp(wallet);
        (bytes memory context, uint256 validationData) = paymaster.validatePaymasterUserOp(op, bytes32("op"), 0.1 ether);

        assertGt(context.length, 0);
        assertEq(validationData, 0);
    }

    function testValidatePaymasterUserOpRevertsWhenWalletNotAllowed() public {
        PackedUserOperation memory op = _buildUserOp(wallet);
        vm.expectRevert();
        paymaster.validatePaymasterUserOp(op, bytes32("op"), 0.1 ether);
    }

    function testValidatePaymasterUserOpRevertsOnCapExceeded() public {
        paymaster.setWalletAllowed(wallet, true);

        PackedUserOperation memory op = _buildUserOp(wallet);
        vm.expectRevert();
        paymaster.validatePaymasterUserOp(op, bytes32("op"), 2 ether);
    }

    function testPostOpTracksSpend() public {
        paymaster.setWalletAllowed(wallet, true);
        bytes memory context = abi.encode(wallet, 0.1 ether);

        paymaster.postOp(IPaymaster.PostOpMode.opSucceeded, context, 0.05 ether, 0);

        assertEq(paymaster.spentToday(), 0.05 ether);
    }
}
