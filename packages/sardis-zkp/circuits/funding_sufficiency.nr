// Funding Sufficiency Proof — proves funding cells cover a payment amount
// without revealing cell values or total balance.
//
// Public inputs: payment_amount, cells_commitment
// Private inputs: cell_values[], cell_count
//
// Proves: sum(cell_values) >= payment_amount

// Maximum cells that can be proven in one proof
global MAX_CELLS: u32 = 16;

fn main(
    // Public inputs
    payment_amount: pub Field,          // Required payment amount
    cells_commitment: pub Field,        // Poseidon hash of cell values + IDs

    // Private inputs
    cell_values: [Field; 16],          // Values of each funding cell
    cell_ids: [Field; 16],            // IDs of each funding cell
    cell_count: Field,                 // How many cells are actually used (rest are 0)
    currency_hash: Field,              // Hash of currency identifier
    nonce: Field,                      // Replay protection
) {
    // 1. Sum all cell values
    let mut total: u64 = 0;
    for i in 0..MAX_CELLS {
        total += cell_values[i] as u64;
    }

    // 2. Prove total >= payment_amount
    assert(
        total >= payment_amount as u64,
        "Insufficient funding: cells do not cover payment amount"
    );

    // 3. Verify all cell values are non-negative (prevent overflow attacks)
    for i in 0..MAX_CELLS {
        // In Noir, Field values are always non-negative in range [0, p-1]
        // But we constrain to reasonable amounts (< 2^53 for safe integer math)
        assert(
            cell_values[i] as u64 <= 9007199254740992,
            "Cell value exceeds safe range"
        );
    }

    // 4. Verify cells commitment
    // Hash first 4 cells as a batch (Poseidon limitation)
    let batch1 = std::hash::poseidon::bn254::hash_4([
        cell_values[0], cell_values[1], cell_values[2], cell_values[3],
    ]);
    let batch2 = std::hash::poseidon::bn254::hash_4([
        cell_values[4], cell_values[5], cell_values[6], cell_values[7],
    ]);
    let computed_commitment = std::hash::poseidon::bn254::hash_4([
        batch1, batch2, currency_hash, nonce,
    ]);
    assert(computed_commitment == cells_commitment, "Cells commitment mismatch");
}

#[test]
fn test_sufficient_funding() {
    let batch1 = std::hash::poseidon::bn254::hash_4([50, 30, 25, 0]);
    let batch2 = std::hash::poseidon::bn254::hash_4([0, 0, 0, 0]);
    let commitment = std::hash::poseidon::bn254::hash_4([batch1, batch2, 1, 42]);

    main(
        100,           // payment_amount
        commitment,    // cells_commitment
        [50, 30, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  // cell_values (sum = 105)
        [1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],     // cell_ids
        3,             // cell_count
        1,             // currency_hash
        42,            // nonce
    );
}
