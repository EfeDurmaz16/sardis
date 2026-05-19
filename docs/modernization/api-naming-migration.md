# API Naming and Layout Migration

## Problem

The API package previously used deeper and less contributor-readable source
paths. During the migration, the routing layer had grown into a flat directory:

```text
packages/reference-api/server/routers/*.py
```

That path was not contributor-friendly. It contained protocol endpoints,
payments, wallets, hosted-product remnants, provider callbacks, admin surfaces,
metrics, and old prototypes in one flat list.

The result is that a new contributor has to know too much before finding the
right file. Names like `webhooks.py` are also ambiguous because Sardis has both:

- outbound webhook subscriptions managed by Sardis users
- inbound provider webhook callbacks from Stripe, card issuers, CPN, TAP, and
  other payment networks

The repeated-looking path prefix is tracked separately in
`docs/modernization/package-path-simplification.md`. The current contributor
path is `packages/reference-api/server/...`; the old `packages/sardis-api`
package directory, the extra API `src/` layer, the legacy `routers/` bucket,
and the old `sardis_api` import package name have been removed.

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

## Completed Migration

Completed so far:

| Old file | New state | Reason |
| --- | --- | --- |
| `routers/webhooks.py` | `routers/webhook_subscriptions.py` | The module manages outbound webhook subscriptions and delivery logs, not all webhook handling. |
| `routers/agent_identity.py` | deleted | The router was not imported or registered in the app and overlapped with the newer FIDES identity surface. |
| `routers/anomaly.py` | deleted | The router was not imported, registered, or covered by tests; anomaly scoring remains internal to control-plane and protocol flows until a properly wired operations API is added. |
| `routers/plugins.py` | deleted | The plugin API router was not imported, mounted, or covered by tests; keeping an unreachable plugin-management API in the public surface made the repo look broader than the runnable reference API. |
| `main.py` inline webhook subscription registration | `route_registry/developer.py::register_webhook_subscriptions` | Starts separating route registration by API audience/domain before moving 120+ router files. |
| `main.py` inline `/api/v2/pay` registration | `route_registry/money_movement.py::register_pay_endpoint` | Moves a small, high-traffic payment surface behind a money-movement registrar without changing the public path. |
| `main.py` inline mandates/AP2/MVP/approvals registration | `route_registry/authority.py::register_authority_routes` | Groups authority and mandate route wiring while returning the approval service needed by later payment/provider routers. |
| `main.py` inline auth/account registration | `route_registry/accounts.py::{register_auth_routes, register_account_group_routes, register_account_self_service_routes}` | Moves auth, email verification, account groups, API keys, current-user state, and data export wiring behind account-domain registrars without changing public paths or route ordering. |
| `main.py` inline admin registration | `route_registry/admin.py::register_admin_routes` | Groups admin control, admin reconciliation, and emergency freeze wiring behind one privileged-route registrar without changing public paths. |
| `main.py` inline agent lifecycle/registry registration | `route_registry/agents.py::{register_agent_lifecycle_routes, register_agent_registry_routes}` | Moves agent lifecycle, telemetry, heartbeat, events, FIDES identity, and registry wiring behind agent-domain registrars without changing public paths or route ordering. |
| `main.py` inline audit/evidence registration | `route_registry/evidence.py::{register_audit_anchor_routes, register_evidence_routes}` | Moves audit anchoring, evidence capture/export, and attestation wiring behind evidence-domain registrars without changing public paths or route ordering. |
| `routers/webhook_subscriptions.py` implementation | `routes/developer/webhook_subscriptions.py` after a temporary compatibility-wrapper phase | Starts the physical path simplification from flat routers to domain-grouped routes. |
| `routers/pay.py` implementation | `routes/money_movement/pay.py` after a temporary compatibility-wrapper phase | Moves the primary money-movement execution route to the domain where contributors expect to find payment logic. |
| `routers/mandates.py`, `routers/ap2.py`, `routers/mvp.py`, `routers/approvals.py`, `routers/approval_config.py` implementations | `routes/authority/*` after a temporary compatibility-wrapper phase | Groups authority, mandate, AP2, MVP, and approval surfaces under one contributor-readable domain. |
| `routers/spending_mandates.py`, `routers/mandate_delegation.py`, `routers/mandate_subscriptions.py` implementations | `routes/authority/*` after a temporary compatibility-alias phase | Moves the remaining mandate lifecycle, delegation, and recurring mandate billing APIs into the same authority domain as the core mandate and approval routes. |
| `routers/credentials.py` implementation | `routes/authority/credentials.py` after a temporary compatibility-alias phase | Moves delegated credential provisioning, consent validation, scope tightening, and revocation into the authority domain instead of leaving scoped authority credentials in the flat router bucket. |
| `routers/facility_requests.py` implementation | `routes/authority/facility_requests.py` after a temporary compatibility-alias phase | Moves partner-backed facility request, mandate authority, approval, revocation, and provider webhook handling into the authority domain instead of leaving a large facility gate API in the legacy flat router bucket. |
| `routers/ledger.py`, `routers/holds.py`, `routers/transactions.py`, `routers/payments_refund.py`, `routers/payment_objects.py`, `routers/batch_payments.py`, `routers/streaming_payments.py`, `routers/fx.py`, `routers/swap.py`, `routers/settlements.py`, `routers/receipts.py`, `routers/bridge.py` implementations | `routes/money_movement/*` after a temporary compatibility-wrapper phase | Groups core payment, ledger, transaction, FX, bridge, settlement, receipt, and refund surfaces under the money movement domain. |
| `routers/cards.py`, `routers/virtual_cards.py`, `routers/stablecoin_cards.py`, `routers/treasury.py`, `routers/treasury_ops.py`, `routers/cpn.py`, `routers/funding_capabilities.py` implementations | `routes/wallets/*` after a temporary compatibility-wrapper phase | Starts the wallet/card/funding domain move with the lower-coupling card, treasury, CPN, and capability surfaces. |
| `routers/funding.py`, `routers/ramp.py`, `routers/offramp.py` implementations | `routes/wallets/*` after a temporary compatibility-wrapper phase | Moves the lower-coupling funding/ramp surfaces before the high-coupling wallet/onchain/onramp routes. |
| `routers/onchain_payments.py` implementation | `routes/wallets/onchain_payments.py` after a temporary compatibility-wrapper phase | Moves the on-chain wallet payment route into the wallet domain and aligns tests with the current PaymentOrchestrator execution boundary. |
| `routers/onramp.py` implementation | `routes/wallets/onramp.py` after a temporary compatibility-wrapper phase | Moves fiat onramp and onramp webhook handling into the wallet domain while preserving old public and monkeypatch import targets during migration. |
| `routers/wallets.py` implementation | `routes/wallets/lifecycle.py` after a temporary compatibility-wrapper phase | Completes the first wallet-domain placement pass by moving core wallet lifecycle, balance, transfer, and x402 wallet routes into the same domain. |
| `routers/stripe_webhooks.py`, `routers/stripe_spt_webhooks.py`, `routers/mastercard_webhooks.py`, `routers/visa_tap_webhooks.py`, `routers/partner_card_webhooks.py`, `routers/cpn_webhooks.py`, `routers/polar_webhook.py` implementations | `routes/providers/*` after a temporary compatibility-wrapper phase | Separates inbound provider callback handling from outbound customer webhook subscription APIs. |
| `routers/stripe_connect.py`, `routers/stripe_funding.py` implementations | `routes/providers/*` after a temporary compatibility-alias phase | Moves Stripe Connect onboarding/webhooks and Stripe Issuing funding into the provider integration domain instead of keeping Stripe provider logic in the flat router bucket. |
| `routers/policies.py`, `routers/policy_simulation.py`, `routers/policy_analytics.py`, `routers/fallback_policies.py` implementations | `routes/policy/*` after a temporary compatibility-alias phase | Moves policy definition, simulation, analytics, and fallback policy APIs into a control-plane policy domain while preserving stateful legacy import targets. |
| `routers/evidence.py`, `routers/evidence_export.py`, `routers/audit_anchors.py`, `routers/attestation.py` implementations | `routes/evidence/*` after a temporary compatibility-alias phase | Groups evidence capture, export, audit anchors, and attestation proof APIs under one evidence domain while preserving stateful legacy import targets. |
| `routers/compliance.py`, `routers/compliance_export.py`, `routers/kyc_onboarding.py` implementations | `routes/compliance/*` after a temporary compatibility-alias phase | Moves regulatory controls, compliance exports, and Didit KYC onboarding into one compliance domain while preserving stateful legacy import targets. |
| `routers/x402.py`, `routers/mpp.py`, `routers/mpp_demo.py` implementations | `routes/protocol/*` after a temporary compatibility-alias phase | Groups payment protocol adapters together while keeping x402 and MPP as separate packages and request flows. |
| `routers/a2a.py`, `routers/a2a_payments.py`, `routers/acp.py`, `routers/erc8183.py`, `routers/spt.py` implementations | `routes/protocol/*` after a temporary compatibility-alias phase | Moves the remaining protocol-adapter routes out of the flat router bucket while preserving old import paths for tests and downstream users. |
| `routers/fides_identity.py`, `routers/agent_auth.py`, `routers/trust.py` implementations | `routes/identity/*` after a temporary compatibility-alias phase | Separates identity, trust, and agent-authority routes from payment protocol adapters and the legacy flat router bucket. |
| `routers/agent_activity.py`, `routers/agent_events.py`, `routers/agent_heartbeat.py` implementations | `routes/agents/*` after a temporary compatibility-alias phase | Groups agent lifecycle telemetry and heartbeat routes before moving the larger agent registry/lifecycle files. |
| `routers/agents.py`, `routers/agent_registry.py` implementations | `routes/agents/*` after a temporary compatibility-alias phase | Moves core agent lifecycle, payment identity, and registry routes into the agent domain so contributors do not have to hunt through the flat router bucket. |
| `routers/auth.py`, `routers/email_verification.py`, `routers/me.py`, `routers/groups.py`, `routers/api_keys.py`, `routers/organizations.py`, `routers/data_export.py` implementations | `routes/accounts/*` after a temporary compatibility-alias phase | Groups user auth, email verification, current-account state, account groups, organizations, API keys, and GDPR account export away from the flat router bucket and away from protocol identity/trust routes. |
| `routers/checkout.py`, `routers/checkout_controls.py`, `routers/merchant_checkout.py`, `routers/merchants.py`, `routers/invoices.py`, `routers/service_directory.py` implementations | `routes/commerce/*` after a temporary compatibility-alias phase | Groups merchant, checkout, checkout control, invoice, and agent service discovery APIs as the commerce-facing part of the reference API rather than leaving them scattered in the flat router bucket. |
| `routers/counterparties.py`, `routers/marketplace.py`, `routers/escrow_disputes.py` implementations | `routes/commerce/*` after a temporary compatibility-alias phase | Moves counterparty trust records, service marketplace, and escrow/dispute APIs into the commerce domain where contributors expect merchant/vendor interaction surfaces. |
| `routers/analytics.py`, `routers/alerts.py`, `routers/ws_alerts.py`, `routers/event_stream.py`, `routers/reports.py`, `routers/reliability.py`, `routers/dashboard_metrics.py`, `routers/metrics.py`, `routers/outcomes.py`, `routers/execution_modes.py`, `routers/exceptions.py`, `routers/emergency.py` implementations | `routes/operations/*` after a temporary compatibility-alias phase | Moves operational reporting, alerting, SSE, reliability, outcome/risk profiles, execution-mode discovery, exception workflow/retry policies, emergency incident response, dashboard metrics, and Prometheus collectors together under one operations domain. |
| `routers/striga.py`, `routers/lightspark.py`, `routers/currency.py`, `routers/fiat_rails.py` implementations | `routes/providers/*` after a temporary compatibility-alias phase | Keeps feature-flagged provider and fiat rail adapter surfaces with other provider callback/integration routes. |
| `routers/enterprise_support.py`, `routers/sdk_metrics.py`, `routers/notifications.py`, `routers/environment_templates.py`, `routers/workflow_templates.py`, `routers/simulation.py`, `routers/faucet.py`, `routers/dev.py`, `routers/sandbox.py` implementations | `routes/developer/*` after a temporary compatibility-alias phase | Moves contributor/developer support ticketing, public SDK install metrics, notification webhook configuration, environment templates, workflow templates, dry-run simulation, dev faucet utilities, no-signup sandbox playground, and testnet faucet routes out of the flat router bucket while preserving existing HTTP paths. |
| `routers/billing.py`, `routers/usage.py`, `routers/subscriptions.py` implementations | `routes/billing/*` after a temporary compatibility-alias phase | Groups subscription, checkout, billing provider, webhook, recurring subscription, and metered usage reporting APIs under a billing domain instead of leaving them in the flat router bucket. |
| `routers/admin.py`, `routers/admin_reconciliation.py` implementations | `routes/admin/control.py` and `routes/admin/reconciliation.py` after a temporary compatibility-alias phase | Makes privileged operations easier to find without repeating `admin/admin.py`, and keeps admin rate-limit helpers close to admin-only reconciliation surfaces. |
| `routers/secure_checkout.py` implementation | `routes/commerce/secure_checkout.py` after a temporary compatibility-alias phase | Moves PAN-safe checkout orchestration next to merchant checkout and checkout controls. |

Final cleanup: after internal imports and tests were migrated to
`server.routes.<domain>`, the temporary compatibility package was removed. The
HTTP API paths remain unchanged.

The external API remains unchanged:

```text
/api/v2/webhooks
```

## Path Simplification

The concrete contributor pain is path roaming. A file like:

```text
packages/reference-api/server/routers/webhook_subscriptions.py
```

is long, repeats API/package concepts, and hides the business domain in a flat
`routers` bucket. The migration target is therefore not only better names, but
shorter mental paths:

```text
packages/reference-api/server/routes/developer/webhook_subscriptions.py
```

The top-level Python package now uses `server` because that is the
standard packaging boundary and avoids colliding with the public Python SDK
package named `sardis`. The part we should actively simplify is everything
below it:

- `routes/<domain>/...` for HTTP route modules
- `route_registry/<domain>.py` for FastAPI registration/wiring
- no legacy `routers/` bucket in the active source tree

The package directory itself has already been simplified to
`packages/reference-api`. Further path cleanup should happen by shrinking
composition code and improving domain boundaries, not by reintroducing flat
router buckets.

## Current Layout

The flat router directory has been replaced with grouped route domains:

```text
server/
  routes/
    admin/
      control.py
      reconciliation.py
    protocol/
      ap2.py
      a2a.py
      a2a_payments.py
      x402.py
      acp.py
      erc8183.py
      mpp.py
      mpp_demo.py
      spt.py
    identity/
      agent_auth.py
      fides_identity.py
      trust.py
    accounts/
      auth.py
      email_verification.py
      me.py
      groups.py
      api_keys.py
      organizations.py
      data_export.py
    agents/
      agents.py
      agent_registry.py
      agent_activity.py
      agent_events.py
      agent_heartbeat.py
    authority/
      ap2.py
      approval_config.py
      approvals.py
      credentials.py
      facility_requests.py
      mandate_delegation.py
      mandate_subscriptions.py
      mandates.py
      mvp.py
      spending_mandates.py
    money_movement/
      batch_payments.py
      bridge.py
      fx.py
      holds.py
      ledger.py
      pay.py
      payment_objects.py
      payments_refund.py
      receipts.py
      settlements.py
      streaming_payments.py
      swap.py
      transactions.py
    commerce/
      checkout.py
      checkout_controls.py
      secure_checkout.py
      merchant_checkout.py
      merchants.py
      invoices.py
      service_directory.py
    billing/
      billing.py
      subscriptions.py
      usage.py
    policy/
      fallback_policies.py
      policies.py
      policy_analytics.py
      policy_simulation.py
    evidence/
      attestation.py
      audit_anchors.py
      evidence.py
      evidence_export.py
    compliance/
      compliance.py
      compliance_export.py
      kyc_onboarding.py
    wallets/
      wallets.py
      cards.py
      cpn.py
      funding.py
      funding_capabilities.py
      offramp.py
      onchain_payments.py
      onramp.py
      ramp.py
      stablecoin_cards.py
      treasury.py
      treasury_ops.py
      virtual_cards.py
    providers/
      cpn_webhooks.py
      currency.py
      fiat_rails.py
      lightspark.py
      striga.py
      mastercard_webhooks.py
      partner_card_webhooks.py
      polar_webhook.py
      stripe_connect.py
      stripe_funding.py
      stripe_spt_webhooks.py
      stripe_webhooks.py
      visa_tap_webhooks.py
    developer/
      dev.py
      enterprise_support.py
      environment_templates.py
      faucet.py
      notifications.py
      sandbox.py
      simulation.py
      webhook_subscriptions.py
      workflow_templates.py
      sdk_metrics.py
    operations/
      alerts.py
      analytics.py
      dashboard_metrics.py
      emergency.py
      event_stream.py
      exceptions.py
      execution_modes.py
      metrics.py
      outcomes.py
      reliability.py
      reports.py
      ws_alerts.py
```

Route registration now lives in `server.route_registry.<domain>` modules, keeping
`server.main` closer to a composition root instead of a file-by-file router
mount list.

## Recommended Move Order

The migration proceeded bucket-by-bucket. Temporary compatibility wrappers were
used during the migration and then removed after internal imports moved to
`server.routes.<domain>`.

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
   `fides_identity`, and `trust`.
8. Agent lifecycle and account routes: completed for `agents`,
   `agent_registry`, `agent_activity`, `agent_events`, `agent_heartbeat`,
   `auth`, `email_verification`, `me`, `groups`, `api_keys`, and
   `organizations`, and `data_export`.
9. Commerce and checkout: completed for `checkout`, `checkout_controls`,
   `merchant_checkout`, `merchants`, `invoices`, and `service_directory`.
10. Operations and observability: completed for `analytics`, `alerts`,
   `ws_alerts`, `event_stream`, `reports`, `reliability`,
   `dashboard_metrics`, `metrics`, `outcomes`, and `execution_modes`.
11. Developer and contributor-facing tools: completed for
   `webhook_subscriptions`, `enterprise_support`, `sdk_metrics`, and
   `notifications`, `environment_templates`, `workflow_templates`,
   `simulation`, `faucet`, `dev`, and `sandbox`.
12. Billing and usage: completed for `billing` and `usage`.
13. Provider and fiat rail adapters: completed for `striga`, `lightspark`,
   `currency`, and `fiat_rails`.
14. Admin and high-coupling checkout surfaces: completed for `admin`,
   `admin_reconciliation`, and `secure_checkout`.

## Validation Required For Each Move

Run these commands after each route move:

```bash
python3 -m compileall -q packages/reference-api/server
pnpm check:openapi
uv run pytest packages/reference-api/tests -q
```

For small route-only moves, the minimum acceptable validation is:

```bash
python3 -m compileall -q packages/reference-api/server
pnpm check:openapi
```

The OpenAPI route snapshot is the main guardrail: if a file move changes public
paths or operation IDs, the diff must be intentional and reviewed.
