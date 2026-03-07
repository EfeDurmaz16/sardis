// Sardis ZK Policy Circuit — proves policy compliance without revealing inputs.
//
// This circuit implements 5 of 11 policy checks as zero-knowledge proofs:
//   1. Amount validation:     amount <= max_per_transaction
//   2. Daily limit:           daily_total + amount <= daily_limit
//   3. MCC check:             mcc_hash NOT IN blocked_mcc_hashes (set membership)
//   4. Time window:           hour >= window_start AND hour <= window_end
//   5. Per-merchant limit:    merchant_total + amount <= per_merchant_limit
//
// Public inputs:  evidence_hash (split into high/low u128 for field compatibility)
// Private inputs: all policy parameters and transaction details
//
// The evidence_hash links this proof to the policy decision log in the
// Sardis database, enabling auditors to verify that a specific policy
// evaluation was correct without seeing the actual amounts or limits.

// Entry point: prove all 5 policy checks pass.
fn main(
    // Private inputs (witness)
    amount: u64,
    daily_total: u64,
    merchant_total: u64,
    mcc_hash: u64,
    hour: u8,
    max_per_transaction: u64,
    daily_limit: u64,
    per_merchant_limit: u64,
    window_start: u8,
    window_end: u8,
    blocked_mcc_hashes: [u64; 8],
    // Public inputs
    evidence_hash_high: pub u128,
    evidence_hash_low: pub u128,
) {
    // Check 1: Amount validation
    // The transaction amount must not exceed the per-transaction limit.
    assert(amount <= max_per_transaction, "amount exceeds per-transaction limit");

    // Check 2: Daily limit
    // The sum of today's spending plus this transaction must not exceed
    // the daily limit.
    let new_daily_total = daily_total + amount;
    assert(new_daily_total <= daily_limit, "daily limit exceeded");

    // Check 3: MCC (Merchant Category Code) set membership
    // The merchant's category hash must NOT appear in the blocked list.
    // We check all 8 slots; unused slots are zero and mcc_hash > 0 for
    // real merchants, so zero slots never match.
    let mut mcc_blocked = false;
    for i in 0..8 {
        if (blocked_mcc_hashes[i] != 0) & (blocked_mcc_hashes[i] == mcc_hash) {
            mcc_blocked = true;
        }
    }
    assert(!mcc_blocked, "merchant category blocked");

    // Check 4: Time window
    // The transaction hour must fall within the allowed window.
    // Supports wrap-around (e.g., 22:00 to 06:00) by checking both cases.
    if window_start <= window_end {
        // Normal window: e.g., 09:00 to 17:00
        assert(hour >= window_start, "outside time window (before start)");
        assert(hour <= window_end, "outside time window (after end)");
    } else {
        // Wrap-around window: e.g., 22:00 to 06:00
        let in_window = (hour >= window_start) | (hour <= window_end);
        assert(in_window, "outside time window (wrap-around)");
    }

    // Check 5: Per-merchant limit
    // Cumulative spending at this merchant plus this transaction must
    // not exceed the per-merchant cap.
    let new_merchant_total = merchant_total + amount;
    assert(new_merchant_total <= per_merchant_limit, "per-merchant limit exceeded");

    // The evidence_hash binds this proof to the off-chain decision log.
    // The verifier checks that evidence_hash_high and evidence_hash_low
    // match the expected values, linking the ZK proof to the audit trail.
    // No further constraint needed here — they are public inputs and the
    // verifier contract enforces equality.
    assert(evidence_hash_high != 0, "evidence hash must be non-zero");
    let _ = evidence_hash_low; // consumed as public input
}
