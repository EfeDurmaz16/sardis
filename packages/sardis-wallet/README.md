# sardis-wallet

Deterministic wallet policy engine + MPC orchestration. Provides per-agent spending controls, key references, and policy evaluation for Payment mandates.

## Status

Beta library package. This is wallet orchestration and policy evaluation code,
not a custody service. Keep provider credentials, private keys, and live signing
material out of tests and examples.

## Local Development

```bash
PYTHONPATH=packages/sardis-wallet/src:packages/sardis-core/src uv run pytest packages/sardis-wallet/tests -q
```
