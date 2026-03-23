# Noir ZKP — Privacy Proofs for Sardis

> MIT license. Safe alternative to circom/snarkjs (GPL-3.0).

## When to Use

Noir becomes relevant when Sardis needs:
- Private compliance proofs (prove KYC without revealing identity)
- Hidden transaction amounts (prove amount < limit without revealing exact value)
- Anonymous spending mandates (prove agent has authority without revealing principal)

## Setup (Future)

```bash
# Install Noir
curl -L https://raw.githubusercontent.com/noir-lang/noirup/main/install | bash
noirup

# Create Sardis circuits
nargo new sardis_circuits
cd sardis_circuits

# Example: prove amount is within mandate limit
# src/main.nr:
# fn main(amount: u64, limit: u64) {
#     assert(amount <= limit);
# }
```

## Architecture

```
Agent → Intent → Noir Proof → Verifier Contract (Tempo) → Settlement
                     ↓
              ZK Proof: "amount ≤ mandate limit"
              Without revealing: actual amount
```

## Alternatives Evaluated

| Tool | License | Status |
|------|---------|--------|
| **Noir** (Aztec) | MIT | Recommended |
| Halo2 (Zcash/EFF) | MIT/Apache | Alternative |
| SP1 (Succinct) | Apache-2.0 | zkVM approach |
| Risc Zero | Apache-2.0 | General zkVM |
| circom/snarkjs | GPL-3.0 | **BLOCKED** — license incompatible |
