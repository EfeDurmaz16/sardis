// Mandate Compliance Proof — proves a payment satisfies mandate bounds
// without revealing the mandate limits or the payment amount.
//
// Public inputs: commitment (hash of mandate rules)
// Private inputs: amount, limit, mandate_hash
//
// Proves: amount <= limit AND hash(mandate_rules) == commitment

// Prove that a payment amount is within the mandate's per-transaction limit
fn main(
    // Public inputs (known to verifier)
    mandate_commitment: pub Field,      // Poseidon hash of mandate rules
    payment_commitment: pub Field,      // Poseidon hash of payment details

    // Private inputs (known only to prover)
    amount: Field,                      // Actual payment amount (scaled to integer)
    per_tx_limit: Field,               // Mandate per-transaction limit
    daily_limit: Field,                // Mandate daily limit
    daily_spent: Field,                // Amount already spent today
    merchant_id_hash: Field,           // Hash of merchant identifier
    allowed_merchant_root: Field,      // Merkle root of allowed merchants
    merchant_proof: [Field; 8],        // Merkle proof for merchant inclusion
    mandate_nonce: Field,              // Replay protection nonce
) {
    // 1. Prove amount <= per_tx_limit
    assert(amount as u64 <= per_tx_limit as u64, "Amount exceeds per-transaction limit");

    // 2. Prove daily_spent + amount <= daily_limit
    let new_daily = (daily_spent as u64) + (amount as u64);
    assert(new_daily <= daily_limit as u64, "Amount exceeds daily limit");

    // 3. Verify mandate commitment matches private inputs
    let computed_commitment = std::hash::poseidon::bn254::hash_4([
        per_tx_limit,
        daily_limit,
        allowed_merchant_root,
        mandate_nonce,
    ]);
    assert(computed_commitment == mandate_commitment, "Mandate commitment mismatch");

    // 4. Verify payment commitment matches
    let computed_payment = std::hash::poseidon::bn254::hash_4([
        amount,
        merchant_id_hash,
        daily_spent,
        mandate_nonce,
    ]);
    assert(computed_payment == payment_commitment, "Payment commitment mismatch");
}

// Test cases
#[test]
fn test_valid_payment() {
    let mandate_commitment = std::hash::poseidon::bn254::hash_4([
        100,   // per_tx_limit
        1000,  // daily_limit
        0,     // allowed_merchant_root (placeholder)
        42,    // nonce
    ]);

    let payment_commitment = std::hash::poseidon::bn254::hash_4([
        50,    // amount
        123,   // merchant_id_hash
        200,   // daily_spent
        42,    // nonce
    ]);

    main(
        mandate_commitment,
        payment_commitment,
        50,          // amount
        100,         // per_tx_limit
        1000,        // daily_limit
        200,         // daily_spent
        123,         // merchant_id_hash
        0,           // allowed_merchant_root
        [0; 8],      // merchant_proof (placeholder)
        42,          // mandate_nonce
    );
}
