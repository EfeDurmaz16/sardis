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
| `routers/ledger.py`, `routers/holds.py`, `routers/transactions.py`, `routers/payments_refund.py`, `routers/payment_objects.py`, `routers/batch_payments.py`, `routers/streaming_payments.py`, `routers/fx.py`, `routers/swap.py`, `routers/settlements.py`, `routers/receipts.py` implementations | `routes/money_movement/*` with compatibility wrappers in `routers/` | Groups core payment, ledger, transaction, FX, settlement, receipt, and refund surfaces under the money movement domain. |
| `routers/cards.py`, `routers/virtual_cards.py`, `routers/stablecoin_cards.py`, `routers/treasury.py`, `routers/treasury_ops.py`, `routers/cpn.py`, `routers/funding_capabilities.py` implementations | `routes/wallets/*` with compatibility wrappers in `routers/` | Starts the wallet/card/funding domain move with the lower-coupling card, treasury, CPN, and capability surfaces. |
| `routers/funding.py`, `routers/ramp.py`, `routers/offramp.py` implementations | `routes/wallets/*` with compatibility wrappers in `routers/` | Moves the lower-coupling funding/ramp surfaces before the high-coupling wallet/onchain/onramp routes. |
| `routers/onchain_payments.py` implementation | `routes/wallets/onchain_payments.py` with a compatibility wrapper in `routers/` | Moves the on-chain wallet payment route into the wallet domain and aligns tests with the current PaymentOrchestrator execution boundary. |
| `routers/onramp.py` implementation | `routes/wallets/onramp.py` with a compatibility wrapper in `routers/` | Moves fiat onramp and onramp webhook handling into the wallet domain while preserving old public and monkeypatch import targets during migration. |
| `routers/wallets.py` implementation | `routes/wallets/wallets.py` with a compatibility wrapper in `routers/` | Completes the first wallet-domain placement pass by moving core wallet lifecycle, balance, transfer, and x402 wallet routes into the same domain. |
| `routers/stripe_webhooks.py`, `routers/stripe_spt_webhooks.py`, `routers/mastercard_webhooks.py`, `routers/visa_tap_webhooks.py`, `routers/partner_card_webhooks.py`, `routers/cpn_webhooks.py`, `routers/polar_webhook.py` implementations | `routes/providers/*` with compatibility wrappers in `routers/` | Separates inbound provider callback handling from outbound customer webhook subscription APIs. |
| `routers/policies.py`, `routers/policy_simulation.py`, `routers/policy_analytics.py`, `routers/fallback_policies.py` implementations | `routes/policy/*` with compatibility module aliases in `routers/` | Moves policy definition, simulation, analytics, and fallback policy APIs into a control-plane policy domain while preserving stateful legacy import targets. |
| `routers/evidence.py`, `routers/evidence_export.py`, `routers/audit_anchors.py`, `routers/attestation.py` implementations | `routes/evidence/*` with compatibility module aliases in `routers/` | Groups evidence capture, export, audit anchors, and attestation proof APIs under one evidence domain while preserving stateful legacy import targets. |
| `routers/compliance.py`, `routers/compliance_export.py`, `routers/kyc_onboarding.py` implementations | `routes/compliance/*` with compatibility module aliases in `routers/` | Moves regulatory controls, compliance exports, and Didit KYC onboarding into one compliance domain while preserving stateful legacy import targets. |
| `routers/x402.py`, `routers/mpp.py`, `routers/mpp_demo.py` implementations | `routes/protocol/*` with compatibility module aliases in `routers/` | Groups payment protocol adapters together while keeping x402 and MPP as separate packages and request flows. |
| `routers/a2a.py`, `routers/a2a_payments.py`, `routers/acp.py`, `routers/erc8183.py`, `routers/spt.py` implementations | `routes/protocol/*` with compatibility module aliases in `routers/` | Moves the remaining protocol-adapter routes out of the flat router bucket while preserving old import paths for tests and downstream users. |
| `routers/fides_identity.py`, `routers/agent_auth.py`, `routers/trust.py` implementations | `routes/identity/*` with compatibility module aliases in `routers/` | Separates identity, trust, and agent-authority routes from payment protocol adapters and the legacy flat router bucket. |

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
    identity/
      agent_auth.py
      fides_identity.py
      trust.py
    authority/
      mandates.py
      policies.py
      approvals.py
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

## Recommended Move Order

Proceed bucket-by-bucket. Each bucket should leave a temporary compatibility
wrapper in `sardis_api/routers/` until internal imports and downstream users have
moved to `sardis_api/routes/<domain>/...`.

1. Authority: completed for `mandates`, `ap2`, `mvp`, `approvals`, and
   `approval_config`.
2. Money movement and ledger: completed for `ledger`, `holds`, `transactions`,
   `payments_refund`, `payment_objects`, `batch_payments`, `streaming_payments`,
   `fx`, `swap`, `settlements`, and `receipts`.
3. Wallets, funding, and cards: completed for `cards`, `virtual_cards`,
   `stablecoin_cards`, `treasury`, `treasury_ops`, `cpn`, and
   `funding_capabilities`, `funding`, `ramp`, `offramp`, `onchain_payments`,
   `onramp`, and `wallets`.
4. Provider callbacks: completed for `stripe_webhooks`,
   `stripe_spt_webhooks`, `mastercard_webhooks`, `visa_tap_webhooks`,
   `partner_card_webhooks`, `cpn_webhooks`, and `polar_webhook`.
5. Policy, compliance, and evidence: completed for `policies`,
   `policy_simulation`, `policy_analytics`, `fallback_policies`, `evidence`,
   `evidence_export`, `audit_anchors`, `attestation`, `compliance`,
   `compliance_export`, and `kyc_onboarding`.
6. Protocol adapters: completed for `x402`, `mpp`, `mpp_demo`, `a2a`,
   `a2a_payments`, `acp`, `erc8183`, and `spt`.
7. Identity, trust, and agent authority: completed for `agent_auth`,
   `fides_identity`, and `trust`; remaining identity/account files include
   `agents`, `agent_registry`, `agent_activity`, `agent_events`,
   `agent_heartbeat`, `auth`, `email_verification`, `me`, `organizations`,
   `groups`, and `api_keys`.
8. Admin, operations, observability, and miscellaneous contributor tools:
   `admin`, `admin_reconciliation`, `analytics`, `metrics`,
   `dashboard_metrics`, `alerts`, `ws_alerts`, `event_stream`, `reports`,
   `data_export`, `usage`, `notifications`, `sandbox`, `dev`, `reliability`,
   `plugins`, `workflow_templates`, `environment_templates`, and
   `enterprise_support`.

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
