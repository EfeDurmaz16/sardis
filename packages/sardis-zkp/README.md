# sardis-zkp

Status: experimental

Experimental zero-knowledge proof circuits for Sardis concepts such as identity proof, mandate compliance, and funding sufficiency.

## Why This Exists

Sardis may eventually need proofs that preserve privacy while keeping financial authority enforceable. This package holds exploratory circuits separate from supported runtime code.

## Local Development

```bash
PYTHONPATH=packages/sardis-zkp/src uv run pytest packages/sardis-zkp/tests -q
```

That credential-free smoke test checks the Python wrapper, circuit manifest,
public/private input documentation, and the safety invariant that mock proofs
are not treated as verified cryptographic proofs.

When working on the Noir circuits directly, also run:

```bash
cd packages/sardis-zkp
nargo check
```

## Security Notes

Do not treat these circuits as audited or production-ready. They need reproducible proving/verifying commands, stable fixtures, and independent review before they can affect real payment decisions.

## Contribution Notes

Keep each circuit small, documented, and paired with public/private input explanations. Prefer adding test vectors over adding new circuit concepts.
