# sardis-coinbase

Coinbase CDP and x402 integration utilities for Sardis.

## Validation

Run the package-owned smoke suite before changing x402 payment retry behavior,
policy checks, or the optional CDP dependency boundary:

```bash
PYTHONPATH=packages/sardis-coinbase/src uv run pytest packages/sardis-coinbase/tests -q
```
