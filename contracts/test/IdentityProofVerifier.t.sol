// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/verifiers/IdentityProofVerifier.sol";

contract IdentityProofVerifierTest is Test {
    IdentityProofVerifier internal verifier;

    function setUp() public {
        verifier = new IdentityProofVerifier();
    }

    // ============ Placeholder Revert Behavior ============
    // ZK placeholder: all verify() calls revert (fail-closed until real Noir circuits).

    function test_verify_revertsForValidIdentityProof() public {
        bytes32 identityCommitment = keccak256(abi.encodePacked(address(0xBEEF), uint256(1)));
        uint8 requiredKyaLevel = 1;
        bytes memory proof = hex"aabbccdd";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }

    function test_verify_revertsForInvalidProof() public {
        bytes32 identityCommitment = keccak256(abi.encodePacked(address(0xBEEF), uint256(1)));
        uint8 requiredKyaLevel = 1;
        bytes memory proof = hex"00000000"; // garbage proof

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }

    function test_verify_revertsForExpiredProof() public {
        // Warp to a realistic timestamp so subtraction doesn't underflow
        vm.warp(1_700_000_000);
        // Simulate an expired proof by embedding a past timestamp in the commitment
        bytes32 identityCommitment =
            keccak256(abi.encodePacked(address(0xBEEF), uint256(1), uint256(block.timestamp - 365 days)));
        uint8 requiredKyaLevel = 2;
        bytes memory proof = hex"00112233";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }

    function test_verify_revertsForWrongIdentity() public {
        // Commitment for address(0xCAFE) but proof would be for address(0xBEEF) - mismatch
        bytes32 identityCommitment = keccak256(abi.encodePacked(address(0xCAFE), uint256(1)));
        uint8 requiredKyaLevel = 1;
        bytes memory proof = hex"44556677";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }

    function test_verify_revertsForZeroKyaLevel() public {
        bytes32 identityCommitment = keccak256(abi.encodePacked(address(0xBEEF)));
        uint8 requiredKyaLevel = 0;
        bytes memory proof = hex"1234";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }

    function test_verify_revertsForMaxKyaLevel() public {
        bytes32 identityCommitment = keccak256(abi.encodePacked(address(0xBEEF)));
        uint8 requiredKyaLevel = type(uint8).max; // 255
        bytes memory proof = hex"5678";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }

    function test_verify_revertsForEmptyCommitment() public {
        bytes32 identityCommitment = bytes32(0);
        uint8 requiredKyaLevel = 1;
        bytes memory proof = hex"9abc";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }

    function test_verify_revertsForEmptyProof() public {
        bytes32 identityCommitment = keccak256(abi.encodePacked(address(0xBEEF)));
        uint8 requiredKyaLevel = 1;
        bytes memory proof = "";

        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }

    // ============ Fuzz Tests ============

    function testFuzz_verify_alwaysReverts(bytes32 identityCommitment, uint8 requiredKyaLevel, bytes calldata proof)
        public
    {
        vm.expectRevert("ZK verification not implemented - deploy with real Noir circuits");
        verifier.verify(identityCommitment, requiredKyaLevel, proof);
    }
}
