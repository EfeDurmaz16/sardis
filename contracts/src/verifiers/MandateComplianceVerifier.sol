// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title MandateComplianceVerifier
/// @notice PLACEHOLDER: ZK verification NOT implemented. All calls revert.
/// @dev This contract is a placeholder awaiting real Noir circuit integration.
///      The verify() function intentionally reverts to prevent false validation.
///      To deploy with real ZK verification:
///        1. Compile the Noir circuit `mandate_compliance.nr`
///        2. Generate the Solidity verifier using `nargo codegen-verifier`
///        3. Replace this file with the generated UltraPlonk verifier
contract MandateComplianceVerifier {
    /// @notice Verify a mandate compliance proof
    /// @dev ALWAYS REVERTS. ZK verification is not yet implemented.
    /// @param mandateCommitment Poseidon hash of the mandate rules (public input)
    /// @param paymentCommitment Poseidon hash of the payment details (public input)
    /// @param proof The zero-knowledge proof bytes
    /// @return valid Whether the proof is valid (never returns, always reverts)
    function verify(bytes32 mandateCommitment, bytes32 paymentCommitment, bytes calldata proof)
        external
        pure
        returns (bool valid)
    {
        // Suppress unused variable warnings
        mandateCommitment;
        paymentCommitment;
        proof;

        revert("ZK verification not implemented - deploy with real Noir circuits");
    }
}
