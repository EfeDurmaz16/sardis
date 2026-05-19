# sardis-striga

Experimental Striga adapter package for Sardis EEA banking and card integration
work.

This package contains Python helpers for Striga cards, vIBANs, SEPA transfers,
KYC flows, standing orders, swaps, and signed webhooks. It is a provider adapter,
not the canonical Sardis protocol layer. Keep shared payment authority and
policy semantics in the protocol/core packages and use this package only for
Striga-specific transport and model mapping.

## Status

Experimental. The local tests are credential-free and exercise adapter behavior,
request construction, webhook parsing, and provider-not-configured paths. Before
using this package in production, refresh it against current Striga API docs,
program eligibility, sandbox behavior, and regional compliance constraints.

## Local Development

```bash
PYTHONPATH=packages/sardis-striga/src:packages/sardis-cards/src:packages/sardis-ramp/src uv run pytest packages/sardis-striga/tests -q
```

Do not add live API credentials to tests or examples. Provider credentials must
stay in local environment variables or deployment secret stores.
