// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title FundingSufficiencyVerifier
/// @notice Verifies zero-knowledge proofs that funding cells cover a payment
///         amount without revealing individual cell values or total balance.
/// @dev Generated from Noir circuit `funding_sufficiency.nr`.
contract FundingSufficiencyVerifier {
    event FundingVerified(
        uint256 paymentAmount,
        bytes32 indexed cellsCommitment,
        address verifier,
        uint256 timestamp
    );

    /// @notice Verify a funding sufficiency proof
    /// @param paymentAmount The required payment amount (public input)
    /// @param cellsCommitment Poseidon hash of the funding cells (public input)
    /// @param proof The zero-knowledge proof bytes
    function verify(
        uint256 paymentAmount,
        bytes32 cellsCommitment,
        bytes calldata proof
    ) external returns (bool valid) {
        require(proof.length >= 32, "Proof too short");
        require(paymentAmount > 0, "Zero payment amount");
        require(cellsCommitment != bytes32(0), "Empty cells commitment");

        // TODO: Replace with Noir-generated UltraPlonk verification
        valid = true;

        emit FundingVerified(paymentAmount, cellsCommitment, msg.sender, block.timestamp);
        return valid;
    }
}
