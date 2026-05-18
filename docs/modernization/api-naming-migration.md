# API Naming and Layout Migration

## Problem

The API package uses a standard Python `src` layout, but the routing layer has
grown into a flat directory:

```text
packages/sardis-api/src/sardis_api/routers/*.py
```

That path is technically normal for Python packaging, but the last segment is
not contributor-friendly anymore. It contains protocol endpoints, payments,
wallets, hosted-product remnants, provider callbacks, admin surfaces, metrics,
and old prototypes in one flat list.

The result is that a new contributor has to know too much before finding the
right file. Names like `webhooks.py` are also ambiguous because Sardis has both:

- outbound webhook subscriptions managed by Sardis users
- inbound provider webhook callbacks from Stripe, card issuers, CPN, TAP, and
  other payment networks

## Naming Principles

1. Public HTTP paths stay stable unless a migration plan explicitly changes
   them.
2. Python module paths may change when they are internal implementation details.
3. File names should describe the business capability, not the implementation
   framework.
4. Inbound provider callbacks and outbound customer subscriptions must not share
   generic names.
5. Old prototype routers should be deleted when they are not registered or
   imported.
6. Moves should be mechanical and validated by OpenAPI route snapshot checks.

## First Migration Step

Completed so far:

| Old file | New state | Reason |
| --- | --- | --- |
| `routers/webhooks.py` | `routers/webhook_subscriptions.py` | The module manages outbound webhook subscriptions and delivery logs, not all webhook handling. |
| `routers/agent_identity.py` | deleted | The router was not imported or registered in the app and overlapped with the newer FIDES identity surface. |
| `main.py` inline webhook subscription registration | `routing/developer.py::register_webhook_subscriptions` | Starts separating route registration by API audience/domain before moving 120+ router files. |
| `main.py` inline `/api/v2/pay` registration | `routing/money_movement.py::register_pay_endpoint` | Moves a small, high-traffic payment surface behind a money-movement registrar without changing the public path. |
| `main.py` inline mandates/AP2/MVP/approvals registration | `routing/authority.py::register_authority_routes` | Groups authority and mandate route wiring while returning the approval service needed by later payment/provider routers. |
| `routers/webhook_subscriptions.py` implementation | `routes/developer/webhook_subscriptions.py` with a compatibility wrapper in `routers/` | Starts the physical path simplification from flat routers to domain-grouped routes. |
| `routers/pay.py` implementation | `routes/money_movement/pay.py` with a compatibility wrapper in `routers/` | Moves the primary money-movement execution route to the domain where contributors expect to find payment logic. |
| `routers/mandates.py`, `routers/ap2.py`, `routers/mvp.py`, `routers/approvals.py`, `routers/approval_config.py` implementations | `routes/authority/*` with compatibility wrappers in `routers/` | Groups authority, mandate, AP2, MVP, and approval surfaces under one contributor-readable domain. |

The external API remains unchanged:

```text
/api/v2/webhooks
```

## Path Simplification

The concrete contributor pain is path roaming. A file like:

```text
packages/sardis-api/src/sardis_api/routers/webhook_subscriptions.py
```

is long, repeats API/package concepts, and hides the business domain in a flat
`routers` bucket. The migration target is therefore not only better names, but
shorter mental paths:

```text
packages/sardis-api/src/sardis_api/routes/developer/webhook_subscriptions.py
```

The top-level Python package still uses `src/sardis_api` because that is the
standard packaging boundary. The part we should actively simplify is everything
below it:

- `routes/<domain>/...` for HTTP route modules
- `routing/<domain>.py` for FastAPI registration/wiring
- old `routers/` files only as temporary compatibility wrappers while imports
  migrate

## Target Layout

The long-term target is to replace the flat router directory with grouped route
domains:

```text
sardis_api/
  routes/
    protocol/
      ap2.py
      a2a.py
      x402.py
      tap.py
      acp.py
      mpp.py
    authority/
      mandates.py
      policies.py
      approvals.py
      trust.py
      fides_identity.py
    money_movement/
      pay.py
      onchain_payments.py
      batch_payments.py
      transactions.py
      settlements.py
      treasury.py
    wallets/
      wallets.py
      funding.py
      holds.py
    providers/
      stripe_callbacks.py
      card_callbacks.py
      cpn_callbacks.py
      visa_tap_callbacks.py
      mastercard_callbacks.py
    developer/
      api_keys.py
      webhook_subscriptions.py
      usage.py
      sdk_metrics.py
    operations/
      admin.py
      metrics.py
      health.py
      reliability.py
```

This should continue after `sardis_api.main` is split into router registration
functions. Moving 120+ files before extracting registration would create a large
rename diff without enough architectural payoff. The first extracted registrars
are `sardis_api.routing.developer.register_webhook_subscriptions`,
`sardis_api.routing.money_movement.register_pay_endpoint`, and
`sardis_api.routing.authority.register_authority_routes`.

## Validation Required For Each Move

Run these commands after each route move:

```bash
python3 -m compileall -q packages/sardis-api/src/sardis_api
pnpm check:openapi
uv run pytest packages/sardis-api/tests -q
```

For small route-only moves, the minimum acceptable validation is:

```bash
python3 -m compileall -q packages/sardis-api/src/sardis_api
pnpm check:openapi
```

The OpenAPI route snapshot is the main guardrail: if a file move changes public
paths or operation IDs, the diff must be intentional and reviewed.
