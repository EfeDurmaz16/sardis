// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/verifiers/FundingSufficiencyVerifier.sol";

contract FundingSufficiencyVerifierTest is Test {
    FundingSufficiencyVerifier internal verifier;

    function setUp() public {
        verifier = new FundingSufficiencyVerifier();
    }

    // ============ Placeholder Revert Behavior ============
    // All three verifier contracts are ZK placeholders that always revert.
    // These tests document and enforce the fail-closed behavior until
    // real Noir circuit integration replaces the placeholder.

    function test_verify_revertsForSufficientBalance() public {
        uint256 paymentAmount = 100e6; // $100 USDC
        bytes32 cellsCommitment = keccak256(abi.encodePacked(uint256(200e6))); // commitment covering balance > amount
        bytes memory proof = hex"deadbeef";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }

    function test_verify_revertsForInsufficientBalance() public {
        uint256 paymentAmount = 500e6; // $500 USDC
        bytes32 cellsCommitment = keccak256(abi.encodePacked(uint256(100e6))); // commitment covering balance < amount
        bytes memory proof = hex"aabbccdd";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }

    function test_verify_revertsForZeroBalance() public {
        uint256 paymentAmount = 1e6;
        bytes32 cellsCommitment = bytes32(0); // zero commitment
        bytes memory proof = "";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }

    function test_verify_revertsForExactBalance() public {
        uint256 paymentAmount = 100e6;
        bytes32 cellsCommitment = keccak256(abi.encodePacked(uint256(100e6))); // exact match
        bytes memory proof = hex"1234";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }

    function test_verify_revertsForDifferentDecimals() public {
        // Token with 18 decimals (e.g., DAI-like)
        uint256 paymentAmount = 100e18;
        bytes32 cellsCommitment = keccak256(abi.encodePacked(uint256(200e18)));
        bytes memory proof = hex"5678";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);

        // Token with 8 decimals (e.g., WBTC-like)
        paymentAmount = 1e8;
        cellsCommitment = keccak256(abi.encodePacked(uint256(2e8)));
        proof = hex"9abc";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }

    function test_verify_revertsForZeroPaymentAmount() public {
        uint256 paymentAmount = 0;
        bytes32 cellsCommitment = keccak256(abi.encodePacked(uint256(100e6)));
        bytes memory proof = hex"00";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }

    function test_verify_revertsForMaxValues() public {
        uint256 paymentAmount = type(uint256).max;
        bytes32 cellsCommitment = bytes32(type(uint256).max);
        bytes memory proof = new bytes(1024); // large proof

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }

    function test_verify_revertsForEmptyProof() public {
        uint256 paymentAmount = 50e6;
        bytes32 cellsCommitment = keccak256(abi.encodePacked(uint256(100e6)));
        bytes memory proof = "";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }

    // ============ Fuzz Tests ============

    function testFuzz_verify_alwaysReverts(uint256 paymentAmount, bytes32 cellsCommitment, bytes calldata proof)
        public
    {
        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(paymentAmount, cellsCommitment, proof);
    }
}
