// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title MandateComplianceVerifier
/// @notice Verifies zero-knowledge proofs that a payment satisfies spending
///         mandate bounds without revealing the mandate limits or payment amount.
/// @dev Generated from Noir circuit `mandate_compliance.nr`.
///      In production, replace verify() body with the Noir-generated verifier.
contract MandateComplianceVerifier {
    /// @notice Emitted when a proof is verified
    event ProofVerified(
        bytes32 indexed mandateCommitment,
        bytes32 indexed paymentCommitment,
        address verifier,
        uint256 timestamp
    );

    /// @notice Emitted when a proof verification fails
    event ProofRejected(
        bytes32 indexed mandateCommitment,
        bytes32 indexed paymentCommitment,
        address verifier,
        string reason
    );

    /// @notice Verification record for audit trail
    struct VerificationRecord {
        bytes32 mandateCommitment;
        bytes32 paymentCommitment;
        bool valid;
        uint256 timestamp;
        address verifier;
    }

    /// @notice All verification records
    VerificationRecord[] public records;

    /// @notice Number of verifications performed
    uint256 public verificationCount;

    /// @notice Verify a mandate compliance proof
    /// @param mandateCommitment Poseidon hash of the mandate rules (public input)
    /// @param paymentCommitment Poseidon hash of the payment details (public input)
    /// @param proof The zero-knowledge proof bytes
    /// @return valid Whether the proof is valid
    function verify(
        bytes32 mandateCommitment,
        bytes32 paymentCommitment,
        bytes calldata proof
    ) external returns (bool valid) {
        // TODO: Replace with Noir-generated verification logic
        // For now, validate proof structure
        require(proof.length >= 32, "Proof too short");
        require(mandateCommitment != bytes32(0), "Empty mandate commitment");
        require(paymentCommitment != bytes32(0), "Empty payment commitment");

        // Placeholder verification (always true for valid-length proofs)
        // In production: UltraPlonk verification from Noir output
        valid = true;

        records.push(VerificationRecord({
            mandateCommitment: mandateCommitment,
            paymentCommitment: paymentCommitment,
            valid: valid,
            timestamp: block.timestamp,
            verifier: msg.sender
        }));

        verificationCount++;

        if (valid) {
            emit ProofVerified(mandateCommitment, paymentCommitment, msg.sender, block.timestamp);
        } else {
            emit ProofRejected(mandateCommitment, paymentCommitment, msg.sender, "Invalid proof");
        }

        return valid;
    }

    /// @notice Get a verification record by index
    function getRecord(uint256 index) external view returns (VerificationRecord memory) {
        require(index < records.length, "Index out of bounds");
        return records[index];
    }
}
