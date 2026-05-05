// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title FundingSufficiencyVerifier
/// @notice PLACEHOLDER: ZK verification NOT implemented. All calls revert.
/// @dev This contract is a placeholder awaiting real Noir circuit integration.
///      The verify() function intentionally reverts to prevent false validation.
///      To deploy with real ZK verification:
///        1. Compile the Noir circuit `funding_sufficiency.nr`
///        2. Generate the Solidity verifier using `nargo codegen-verifier`
///        3. Replace this file with the generated UltraPlonk verifier
contract FundingSufficiencyVerifier {
    /// @notice Verify a funding sufficiency proof
    /// @dev ALWAYS REVERTS. ZK verification is not yet implemented.
    /// @param paymentAmount The required payment amount (public input)
    /// @param cellsCommitment Poseidon hash of the funding cells (public input)
    /// @param proof The zero-knowledge proof bytes
    function verify(uint256 paymentAmount, bytes32 cellsCommitment, bytes calldata proof) external pure returns (bool) {
        // Suppress unused variable warnings
        paymentAmount;
        cellsCommitment;
        proof;

        revert("ZK verification not implemented - deploy with real Noir circuits");
    }
}
