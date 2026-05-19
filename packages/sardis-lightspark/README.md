# sardis-lightspark

Experimental Lightspark Grid adapter package for Sardis provider integration work.

This package contains Python helpers for UMA addresses, FX quotes, payouts,
transfers, Plaid-linked funding, and signed Grid webhooks. It is a provider
adapter, not the canonical Sardis protocol layer. Keep protocol semantics in
the protocol/core packages and use this package only for Lightspark-specific
transport and model mapping.

## Status

Experimental. The local tests are credential-free and exercise client behavior,
UMA helpers, payout request construction, and provider-not-configured paths.
Before using this package in production, refresh it against current Lightspark
Grid documentation and sandbox behavior.

## Local Development

```bash
PYTHONPATH=packages/sardis-lightspark/src:packages/sardis-ramp/src uv run pytest packages/sardis-lightspark/tests -q
```

Do not add live API credentials to tests or examples. Provider credentials must
stay in local environment variables or deployment secret stores.
