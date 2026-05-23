# sardis-zk-policy

Status: experimental

Noir and Python scaffold for experimenting with zero-knowledge proofs around Sardis policy constraints.

## Why This Exists

Some agent-payment policies may need privacy-preserving proofs: for example proving that a transaction fits a mandate or limit without exposing every underlying policy input. This package is the experimental workspace for that direction.

## Local Development

Python simulator tests:

```bash
uv run pytest packages/sardis-zk-policy/tests -q
```

Noir development requires a compatible Nargo/Noir toolchain:

```bash
cd packages/sardis-zk-policy
nargo check
```

## Security Notes

This package is not production cryptography. Treat the Python simulator and Noir circuits as research artifacts until they have conformance tests, reproducible proving setup, and external review.

## Contribution Notes

Useful contributions:

- test vectors shared between Python simulation and Noir circuits
- clearer public inputs/outputs
- documentation of what is proven and what is deliberately not proven
