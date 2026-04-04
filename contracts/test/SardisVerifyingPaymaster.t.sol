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

    // ============ Fuzz: Gas Calculation ============

    function testFuzz_gasCalculation(uint256 maxCost) public {
        // Bound maxCost to reasonable range
        maxCost = bound(maxCost, 0, 100 ether);

        paymaster.setWalletAllowed(wallet, true);

        PackedUserOperation memory op = _buildUserOp(wallet);

        if (maxCost > 1 ether) {
            // Exceeds maxSponsoredCostPerOp (set to 1 ether in setUp)
            vm.expectRevert();
            paymaster.validatePaymasterUserOp(op, bytes32("op"), maxCost);
        } else {
            // Should succeed; cap check passes
            (bytes memory context, uint256 validationData) =
                paymaster.validatePaymasterUserOp(op, bytes32("op"), maxCost);
            assertGt(context.length, 0);
            assertEq(validationData, 0);
        }
    }

    function testFuzz_postOpAccumulatesSpend(uint256 gasCost1, uint256 gasCost2) public {
        gasCost1 = bound(gasCost1, 0, 5 ether);
        gasCost2 = bound(gasCost2, 0, 5 ether);

        paymaster.setWalletAllowed(wallet, true);

        bytes memory context = abi.encode(wallet, 1 ether);

        paymaster.postOp(IPaymaster.PostOpMode.opSucceeded, context, gasCost1, 0);
        paymaster.postOp(IPaymaster.PostOpMode.opSucceeded, context, gasCost2, 0);

        assertEq(paymaster.spentToday(), gasCost1 + gasCost2);
    }

    function testFuzz_dailyCapExhaustion(uint256 maxCost) public {
        // Exhaust most of the daily cap, then try one more
        maxCost = bound(maxCost, 0.01 ether, 1 ether);

        paymaster.setWalletAllowed(wallet, true);

        // Spend up to the cap via postOp
        bytes memory context = abi.encode(wallet, 1 ether);
        paymaster.postOp(IPaymaster.PostOpMode.opSucceeded, context, 9.5 ether, 0);

        PackedUserOperation memory op = _buildUserOp(wallet);

        uint256 remaining = 10 ether - 9.5 ether; // 0.5 ether
        if (maxCost > remaining) {
            vm.expectRevert();
            paymaster.validatePaymasterUserOp(op, bytes32("op"), maxCost);
        } else {
            (bytes memory ctx,) = paymaster.validatePaymasterUserOp(op, bytes32("op"), maxCost);
            assertGt(ctx.length, 0);
        }
    }

    // ============ Reentrancy: postOp ============

    function test_reentrancy_postOpDoubleCall() public {
        // The paymaster's postOp only tracks spend, no external calls.
        // Verify that calling postOp twice doesn't create inconsistency.
        paymaster.setWalletAllowed(wallet, true);

        bytes memory context = abi.encode(wallet, 0.5 ether);

        // First call
        paymaster.postOp(IPaymaster.PostOpMode.opSucceeded, context, 0.3 ether, 0);
        assertEq(paymaster.spentToday(), 0.3 ether);

        // Second call (simulates what would happen in reentrancy)
        paymaster.postOp(IPaymaster.PostOpMode.opSucceeded, context, 0.2 ether, 0);
        assertEq(paymaster.spentToday(), 0.5 ether);
    }

    function test_reentrancy_validateAndPostOpSequence() public {
        // Ensure validate followed by postOp correctly tracks state
        paymaster.setWalletAllowed(wallet, true);

        PackedUserOperation memory op = _buildUserOp(wallet);
        (bytes memory context,) = paymaster.validatePaymasterUserOp(op, bytes32("op"), 0.5 ether);

        // postOp with actual cost less than maxCost
        paymaster.postOp(IPaymaster.PostOpMode.opSucceeded, context, 0.3 ether, 0);
        assertEq(paymaster.spentToday(), 0.3 ether);

        // Another validate should still have remaining cap
        (bytes memory context2,) = paymaster.validatePaymasterUserOp(op, bytes32("op2"), 0.5 ether);
        assertGt(context2.length, 0);
    }

    // ============ Daily Reset ============

    function testDailyCapResets() public {
        paymaster.setWalletAllowed(wallet, true);

        bytes memory context = abi.encode(wallet, 1 ether);
        paymaster.postOp(IPaymaster.PostOpMode.opSucceeded, context, 9 ether, 0);
        assertEq(paymaster.spentToday(), 9 ether);

        // Warp to next day
        vm.warp(block.timestamp + 1 days);

        // spentToday should reset on next interaction
        PackedUserOperation memory op = _buildUserOp(wallet);
        (bytes memory ctx,) = paymaster.validatePaymasterUserOp(op, bytes32("op"), 0.5 ether);
        assertGt(ctx.length, 0);
    }
}
