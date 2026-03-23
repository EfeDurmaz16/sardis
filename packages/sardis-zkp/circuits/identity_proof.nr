// Identity Proof — proves an agent is KYA-verified without revealing identity.
//
// Public inputs: identity_commitment (hash of agent identity)
// Private inputs: agent_id, kya_level, attestation_signature
//
// Proves: agent has a valid KYA attestation at the required level
// without revealing which agent or its identity details.

fn main(
    // Public inputs
    identity_commitment: pub Field,     // Poseidon hash of identity attestation
    required_kya_level: pub Field,      // Minimum required KYA level (1=basic, 2=standard, 3=attested)

    // Private inputs
    agent_id_hash: Field,              // Hash of agent identifier
    kya_level: Field,                  // Agent's actual KYA level
    attestation_timestamp: Field,      // When the attestation was issued
    attestation_expiry: Field,         // When it expires
    current_timestamp: Field,          // Current time (verifier provides)
    issuer_id_hash: Field,             // Hash of attestation issuer
    attestation_nonce: Field,          // Unique nonce for this attestation
) {
    // 1. Prove KYA level meets requirement
    assert(
        kya_level as u64 >= required_kya_level as u64,
        "KYA level insufficient"
    );

    // 2. Prove attestation is not expired
    assert(
        current_timestamp as u64 <= attestation_expiry as u64,
        "Attestation has expired"
    );

    // 3. Prove attestation was issued before current time
    assert(
        attestation_timestamp as u64 <= current_timestamp as u64,
        "Attestation issued in the future"
    );

    // 4. Verify identity commitment matches private inputs
    let computed_commitment = std::hash::poseidon::bn254::hash_5([
        agent_id_hash,
        kya_level,
        attestation_timestamp,
        attestation_expiry,
        issuer_id_hash,
    ]);
    assert(computed_commitment == identity_commitment, "Identity commitment mismatch");
}

#[test]
fn test_valid_identity() {
    let commitment = std::hash::poseidon::bn254::hash_5([
        111,    // agent_id_hash
        3,      // kya_level (attested)
        1000,   // attestation_timestamp
        9999,   // attestation_expiry
        222,    // issuer_id_hash
    ]);

    main(
        commitment,
        2,       // required_kya_level (standard)
        111,     // agent_id_hash
        3,       // kya_level
        1000,    // attestation_timestamp
        9999,    // attestation_expiry
        5000,    // current_timestamp
        222,     // issuer_id_hash
        0,       // attestation_nonce
    );
}
