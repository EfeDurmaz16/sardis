# Final Modernization Report

## What Changed

- Added the modernization goal, twelve focused audit reports, a master report, and an ordered migration plan.
- Added `scripts/repo_inventory.py`, a Git-tracked-file inventory tool that prunes generated/build/cache surfaces.
- Added `check:modernization` to root `package.json`.
- Allowed `docs/modernization/**` through the existing docs ignore policy.
- Fixed TypeScript SDK CI/publish filters from the non-existent `@sardis/sdk-js` package name to the actual `@sardis/sdk` package.
- Aligned the legacy publish workflow's npm lanes with Node 22 and pnpm 9.15.4.
- Added public CI/CD inventory, workflow secret-scope, and workflow toolchain guards to the default contributor gate.
- Broadened the public docs link guard to cover README, contribution/security/support docs, package docs, quickstart, OSS docs, and architecture docs.
- Reduced deploy, publish, operations, and public PR workflow permissions from broad `read-all` defaults to explicit least-privilege permissions where practical.
- Required PR-triggered workflows and private-secret workflows to avoid top-level `permissions: read-all`.
- Required public workflows that install JavaScript dependencies to use Node 22, pnpm 9.15.4 when explicitly pinned, and `pnpm install --frozen-lockfile`.
- Added a source-layout policy and contributor gate so the API cannot drift back
  to repeated API package names, an extra API `src` layer, or the legacy flat
  router bucket.
- Fixed public quickstarts to use the existing `SardisClient` export.
- Removed unused `apps/landing/lib/sardis-api.ts`, which contained stale browser-readable token and direct API auth assumptions.
- Changed merchant checkout mandate validation to fail closed when a required mandate cannot be validated.
- Added the OSS goal, public/private boundary, package maturity matrix, development guide, contribution guide, code of conduct, PR template, issue templates, open-core note, provider abstraction note, and legal disclaimer.
- Removed tracked private/company material from public source tracking: CDP drafts, hiring docs, partner LOIs, sales/YC docs, GTM scripts, staging deployment env YAMLs, monitoring dashboards, and generated Solana local-validator ledger/keypair artifacts.
- Added `scripts/oss_surface_check.py` and a required CI job to block private/company paths from re-entering the public OSS repo.
- Removed dashboard build from required public CI and updated required check metadata around the OSS contribution path.
- Bound durable idempotency fallback records to a request hash with migration `102_idempotency_request_hash.sql`.
- Sanitized Didit KYC webhook logging and metadata persistence so raw provider payloads are not logged or stored.
- Bound internal and Better Auth JWT validation to expected issuer/audience semantics and added regression tests.
- Aligned remaining public examples and landing/docs snippets from `Sardis` to `SardisClient`.
- Made contributor and release install paths deterministic by default with `pnpm install --frozen-lockfile`, leaving `bootstrap:mutable` only for intentional lockfile updates.
- Fixed stale deploy workflow app paths from `landing`/`dashboard` to `apps/landing`/`apps/dashboard` and added pnpm setup for those jobs.
- Replaced legacy Vercel `npm install --legacy-peer-deps` install commands with workspace-aligned pnpm frozen installs.
- Added package README entrypoints for experimental and private-candidate packages that previously had tracked source but no README.
- Mapped every tracked Python `sardis-*` package to a local editable `[tool.uv.sources]` entry so contributor checks exercise the checkout instead of published packages with matching names.
- Documented the Python local-source verification command in `docs/development.md`.
- Modernized low-risk Pydantic/FastAPI configuration usage by replacing class-based config, deprecated `regex=`, and deprecated `Field(example=...)` usage in the touched API/core/provider modules.
- Added client-supplied idempotency protection to `/api/v2/pay` so same-key/same-payload retries replay the first response and same-key/different-payload attempts are rejected before re-execution.
- Added client-supplied idempotency protection and first dedicated replay tests for `/api/v2/payments/batch`.
- Added client-supplied idempotency protection and dedicated replay tests for `/api/v2/transactions/batch`.
- Added `pnpm check:openapi`, fixed local OpenAPI generation imports/env setup, and documented the check in the public development loop.
- Removed duplicate OpenAPI/runtime routes by keeping the canonical MPP router mount and canonical bridge quote router.
- Made the OpenAPI check fail when FastAPI emits duplicate operation ID warnings.
- Added a checked-in OpenAPI route contract snapshot and `pnpm openapi:update` for reviewed API surface changes.
- Added the OpenAPI route snapshot check to the required `Python Lint & Test` CI path so public PRs cannot drift API route contracts accidentally.
- Removed public dashboard deployment workflows from OSS CI/CD while keeping API and landing deployment paths intact.
- Removed tracked company-specific SOC2/ops docs from the public source surface and expanded `scripts/oss_surface_check.py` to block investor, ops, and SOC2 private prefixes going forward.
- Made public quickstart entrypoints simulation-first by removing hosted dashboard signup as a prerequisite for contributor onboarding.
- Removed generated audit evidence/latest-run artifacts from public tracking and expanded the OSS surface check to block audit evidence, outbound, outreach, and GTM paths.
- Removed generated uptime/response-time JSON snapshots and Foundry broadcast artifacts from public source tracking, then ignored them going forward.
- Removed hosted production, compliance, runbook, design-partner, investor-demo, and private release-gate material from public tracking.
- Reworked release readiness into a public OSS gate covering SDKs, MCP, landing, Python protocol tests, OSS surface, and OpenAPI route snapshot validation.
- Removed hosted product UI source from the public repo: `apps/dashboard`, `packages/ui-web`, and `packages/sardis-checkout-ui`.
- Removed dashboard/product UI scripts, Dependabot entries, landing deploy path filters, stale canvas dashboard pages, and product UI references from public canvas docs.
- Regenerated tracked canvas HTML and LLM exports from the updated public canvas source.
- Made `apps/canvas-site/scripts/build-llms-full.mjs` deterministic by removing per-build timestamp churn from generated `llms-full.txt`.
- Fixed the docs-site chat route dependency declaration so `@sardis/docs` builds from a clean contributor install.
- Added `scripts/package_maturity_check.py` and wired it into `pnpm run verify` so every tracked public package must have both a README and an active `docs/packages.md` entry.
- Removed remaining private/live ops scripts from the public repo and blocked them from re-entering through `scripts/oss_surface_check.py`.
- Replaced private deployment runbook references with a public-safe self-hosting/deployment guide and added a tracked `cloudbuild.yaml` so the Cloud Run workflow is self-contained.
- Added `docs/modernization/api-naming-migration.md` to define the API route naming/layout cleanup policy.
- Renamed the generic outbound webhook router module from `routers/webhooks.py` to `routers/webhook_subscriptions.py` while preserving the public `/api/v2/webhooks` path.
- Removed the unregistered legacy `routers/agent_identity.py` prototype, which overlapped with the newer FIDES identity surface and was not imported by the app.
- Removed the unregistered `routers/anomaly.py` prototype; anomaly scoring still exists through control-plane/protocol internals, but the old standalone API router was not mounted or dependency-wired.
- Removed the unregistered `routers/plugins.py` plugin-management API prototype; plugin primitives remain in `sardis_v2_core.plugins`, but no public FastAPI plugin-management surface was mounted.
- Added the first domain-scoped route registrar at `server.route_registry.developer.register_webhook_subscriptions` and moved outbound webhook subscription wiring out of `server.main`.
- Added `server.route_registry.money_movement.register_pay_endpoint` and moved the unified `/api/v2/pay` route wiring out of `server.main`.
- Added `server.route_registry.authority.register_authority_routes` and moved mandates/AP2/MVP/approvals wiring out of `server.main` while preserving the approval service handoff needed by later payment/provider routes.
- Added `server.route_registry.accounts` account-domain registrars and moved auth, email verification, groups, API keys, current-user state, and data export wiring out of `server.main` without changing route order.
- Added `server.route_registry.admin.register_admin_routes` and moved admin control, reconciliation, and emergency-freeze wiring out of `server.main`.
- Added `server.route_registry.agents` agent-domain registrars and moved agent lifecycle, telemetry, heartbeat, events, FIDES identity, and registry wiring out of `server.main`.
- Added `server.route_registry.evidence` evidence-domain registrars and moved audit-anchor, evidence capture/export, and attestation wiring out of `server.main`.
- Added `server.route_registry.operations` operations-domain registrars and moved alert, realtime event, analytics, metrics, execution-mode, outcome, reliability, exception, and dashboard-metric route wiring out of `server.main` while preserving route order.
- Added `server.route_registry.commerce` commerce-domain registrars and moved marketplace, invoices, service directory, checkout controls, counterparties, and escrow/dispute route wiring out of `server.main` while preserving route order.
- Added `server.route_registry.policy` policy-domain registrars and moved policy CRUD, policy simulation, policy analytics, and fallback policy route wiring out of `server.main` while preserving route order.
- Added `server.route_registry.billing` billing-domain registrars and moved recurring subscription, billing account/webhook, and metered usage route wiring out of `server.main` while preserving the recurring billing service handoff used by later autofund wiring.
- Added `server.route_registry.protocol` protocol-domain registrars and moved x402, ERC-8183, A2A, A2A payments, MPP, MPP demo, SPT, and ACP route wiring out of `server.main` while preserving feature flags and route order.
- Expanded `server.route_registry.money_movement` and moved ledger, holds, transactions, bridge, refunds, settlements, receipts, payment objects, FX, batch payments, and streaming payment route wiring out of `server.main` while preserving route order and dependency handoffs.
- Repaired stale authority/payment policy tests by replacing brittle implementation-string assertions with current orchestrator/control-plane boundary checks and fixed FastAPI dependency overrides in the mandates router tests.
- Started the physical route placement migration by moving the outbound webhook subscription implementation to `server.routes.developer.webhook_subscriptions`.
- Used temporary compatibility imports during the route move, then removed the
  compatibility package after internal imports and tests moved to
  domain-grouped `server.routes.<domain>` modules.
- Moved the unified `/api/v2/pay` implementation to `server.routes.money_movement.pay`.
- Updated pay route tests to patch/import the real implementation module instead of the compatibility wrapper.
- Moved authority route implementations to `server.routes.authority`: mandates, AP2, MVP, approvals, and approval configuration now share one domain directory.
- Updated authority-focused tests to import and patch the real `routes.authority.*` implementation modules instead of the compatibility wrappers.
- Modernized stale spend-recording and compliance router tests so they assert the current PaymentOrchestrator/ControlPlane execution boundaries instead of counting old direct router-local calls.
- Moved the money movement and ledger route implementations to `server.routes.money_movement`: ledger, holds, transactions, refunds, payment objects, batch payments, streaming payments, FX, swaps, cross-chain bridge, settlements, and receipts now share the same domain directory.
- Updated `server.main` and the batch idempotency tests to import the money movement implementations from the new domain package.
- Moved the lower-coupling wallet/card/funding route implementations to `server.routes.wallets`: cards, virtual cards, stablecoin cards, treasury, treasury operations, CPN, and funding capabilities now share one domain directory.
- Updated `server.main`, provider docs, and focused card/CPN/treasury/funding tests to import the moved wallet routes from the new domain package.
- Moved the remaining lower-coupling funding/ramp route implementations to `server.routes.wallets`: funding commitments, fiat ramp, and fiat offramp now share the wallet domain while high-coupling `wallets`, `onchain_payments`, and `onramp` remain for separate migration.
- Moved the on-chain wallet payment route implementation to `server.routes.wallets.onchain_payments`.
- Updated on-chain payment tests from the stale `chain_executor.dispatch_payment` dependency shape to the current `payment_orchestrator.execute_chain` execution boundary.
- Moved fiat onramp route and webhook handling to `server.routes.wallets.onramp`.
- Updated Turnkey and Conduit onramp tests to import and patch the real wallet-domain route module instead of the compatibility wrapper.
- Moved core wallet lifecycle, balance, transfer, and x402 wallet routes to `server.routes.wallets.wallets`.
- Updated wallet x402 and remaining wallet source-inspection tests to use the real wallet-domain implementation module.
- Moved inbound provider callback routes to `server.routes.providers`: Stripe, Stripe SPT, Mastercard, Visa TAP, partner card, CPN, and Polar callbacks now sit apart from outbound customer webhook subscriptions.
- Moved feature-flagged provider and fiat rail adapter routes to `server.routes.providers`: Striga, Lightspark Grid, currency, and unified fiat rails now sit with provider integrations instead of the flat router bucket.
- Moved Stripe Connect and Stripe Issuing funding route implementations into `server.routes.providers`, keeping provider onboarding, callbacks, and funding rail surfaces together.
- Updated `server.main` and partner-card webhook tests to import provider callback implementations from the new provider-domain package.
- Moved policy route implementations to `server.routes.policy`: policy definitions, policy simulation, policy analytics, and fallback policy APIs now share one control-plane policy domain.
- Kept stateful policy compatibility modules as module aliases so legacy imports and monkeypatch targets resolve to the same implementation module object.
- Moved evidence route implementations to `server.routes.evidence`: evidence capture, evidence export, audit anchors, and attestation proof APIs now share one evidence domain.
- Kept stateful evidence compatibility modules as module aliases and hardened attestation approval timestamp serialization for string or datetime-backed rows.
- Moved compliance route implementations to `server.routes.compliance`: compliance APIs, compliance export, and Didit KYC onboarding now share one regulatory-control domain.
- Updated KYC onboarding tests from stale iDenfy assumptions to the current Didit provider contract and fake-provider boundary.
- Moved x402 and MPP API route implementations to `server.routes.protocol` while keeping `sardis-protocol` and `sardis-mpp` as separate packages.
- Moved A2A, A2A payments, ACP, ERC-8183, and SPT route implementations into `server.routes.protocol` so protocol adapter code is no longer buried in the legacy flat router bucket.
- Moved FIDES identity, agent-auth, and trust route implementations into `server.routes.identity` so identity and authority code is not mixed with payment protocol adapters.
- Added deterministic local Agent Auth behavior for dev/test/local environments so OSS contributors can run agent-auth tests without a dashboard Better Auth service.
- Moved agent activity, agent events, and agent heartbeat route implementations into `server.routes.agents` so agent lifecycle telemetry is no longer mixed into the flat router bucket.
- Moved account route implementations into `server.routes.accounts`: auth, email verification, current-account state, groups, organizations, API keys, and GDPR account export now sit in a contributor-readable account domain.
- Moved commerce route implementations into `server.routes.commerce`: checkout, checkout controls, merchant checkout, merchants, invoices, service directory, counterparties, marketplace, and escrow/dispute APIs now share one contributor-readable domain.
- Moved billing, recurring subscription, and metered usage route implementations into `server.routes.billing` so subscription, checkout, provider, webhook, and usage-reporting APIs share one billing domain.
- Moved operational route implementations into `server.routes.operations`: analytics, alerts, websocket alerts, event stream, reports, reliability, outcomes, execution modes, exception workflows/retry policies, emergency incident response, dashboard metrics, and Prometheus metrics now share one contributor-readable operations domain.
- Moved remaining mandate route implementations into `server.routes.authority`: spending mandate CRUD/lifecycle, mandate delegation, and mandate-based subscriptions now live with the core authority and approval APIs.
- Moved delegated credential route implementation into `server.routes.authority`, keeping credential provisioning, consent validation, scope tightening, and revocation with the rest of the scoped authority APIs.
- Expanded `server.route_registry.authority` so facility gate requests/webhooks, delegated credentials, mandate delegation, and mandate subscription registration no longer live inline in `main.py`.
- Moved enterprise support ticket/profile routes, public SDK install metrics, notification webhook configuration, environment templates, workflow templates, dry-run simulation, dev faucet utilities, and testnet faucet routes into `server.routes.developer` so contributor-facing support, transparency, webhook setup, testing, and onboarding APIs are no longer buried in the flat router bucket.
- Expanded `server.route_registry.developer` so enterprise support, testnet faucet, notification webhook configuration, and workflow/environment template registration no longer live inline in `main.py`.
- Added `server.route_registry.wallets` for simple wallet-edge route registration so offramp, onramp, Stripe onramp webhook, and virtual-card route mounting no longer lives inline in `main.py`.
- Expanded `server.route_registry.wallets` so core wallet and on-chain payment dependency wiring no longer lives inline in `main.py`.
- Expanded `server.route_registry.wallets` with fiat ramp registration and added a focused wiring test for dependency overrides plus public webhook route mounting.
- Expanded `server.route_registry.wallets` with treasury and treasury-ops registration, keeping repository/client construction in `main.py` while moving route dependency wiring and Lithic webhook mounting into the wallet registrar.
- Expanded `server.route_registry.wallets` with Circle CPN registration and extended the wallet routing test to cover CPN dependencies plus public webhook mounting.
- Removed the temporary compatibility package after migrating internal source and tests to the new domain route modules.
- Added and executed a package path simplification decision: keep the Python import package `server`, but consolidate the monorepo API package directory at `packages/reference-api`.
- Renamed the reference API import root from `sardis_server` to `server`, so the
  active source path is now `packages/reference-api/server/...` instead of a
  repeated product/API namespace.
- Updated repo imports/startup docs and removed the unused `sardis_v2_api` prototype package.
- Removed the extra API `src/` layer so the contributor-facing server path is now `packages/reference-api/server/...` instead of the old nested source layout.
- Updated API packaging, OpenAPI generation, Vercel/Docker startup paths, local run scripts, API test bootstrapping, architecture docs, canvas references, and stale-path guardrails for the flatter API layout.
- Added a contributor-facing clean tree helper, `pnpm repo:tree`, so maintainers can inspect source layout without local `node_modules`, `dist`, `.venv`, `.pytest_cache`, private ignored app folders, or generated build artifacts overwhelming the repository map.
- Added `docs/architecture/x402-and-mpp.md` to document the difference between x402 direct HTTP payments and MPP method-negotiated machine payments.
- Updated the API naming migration note to explicitly treat path roaming and overly nested/flat placement as a contributor-readability problem, not only a naming problem.
- Expanded `server.route_registry.money_movement` with swap, exchange, and verification route registration so those provider-backed money-movement helper routes no longer mount inline in `server.main`.
- Added `server.route_registry.compliance` for KYC onboarding and compliance evidence export registration so low-coupling regulatory routes no longer mount inline in `server.main`.
- Expanded `server.route_registry.compliance` so compliance screening, KYC/KYA, audit, and Persona webhook dependency wiring no longer lives inline in `server.main`.
- Expanded `server.route_registry.commerce` so agentic checkout route dependency wiring no longer lives inline in `server.main`.
- Expanded `server.route_registry.commerce` so secure checkout executor dependency wiring, executor flag handling, and production Postgres enforcement no longer live inline in `server.main`.
- Expanded `server.route_registry.commerce` so merchant management and checkout-link route dependency wiring no longer lives inline in `server.main`.
- Expanded `server.route_registry.commerce` so Pay with Sardis merchant checkout session route dependency wiring no longer lives inline in `server.main`.
- Expanded `server.route_registry.providers` so feature-flagged Striga, Lightspark Grid, fiat rails, and currency route registration no longer lives inline in `server.main`.
- Added `server.route_registry.identity` so Agent Auth discovery/management and enterprise SSO route registration no longer live inline in `server.main`.
- Expanded `server.route_registry.authority` so spending mandate CRUD and lifecycle route registration no longer lives inline in `server.main`.
- Expanded `server.route_registry.providers` so Polar billing-provider webhook registration no longer lives inline in `server.main`.
- Expanded `server.route_registry.protocol` so the A2A `.well-known/agent-card.json` discovery route no longer lives inline in `server.main`.
- Added `server.route_registry.health` so liveness, readiness, service discovery, and deep-health route registration no longer lives inline in `server.main`.
- Added a tested `resolve_storage_backend` helper so database URL selection and production PostgreSQL enforcement no longer live inline in `server.main`.
- Added a tested `resolve_cache_backend` helper so Redis URL selection and production Redis enforcement no longer live inline in `server.main`.
- Added a tested `validate_live_execution_config` helper so live-chain and MPC signer safety rules no longer live inline in `server.main`.
- Added a tested `initialize_turnkey_client` helper so Turnkey credential precedence and optional client creation no longer live inline in `server.main`.
- Added tested `expose_runtime_state` and `expose_support_services_state` helpers so route dependency state wiring no longer lives as scattered inline `app.state` assignments in `server.main`.
- Added a tested `configure_provider_runtime` helper so Coinbase CDP and Circle Gateway nanopayments bootstrap logic no longer lives inline in `server.main`.
- Added a tested `configure_inbound_payment_runtime` helper so event-bus webhook wiring and inbound payment service construction no longer live inline in `server.main`.
- Added a tested `configure_ramp_runtime` helper so Bridge off-ramp, mock off-ramp fallback, SardisFiatRamp setup, and ramp webhook credential collection no longer live inline in `server.main`.
- Redirected default pytest, root `pnpm test`, Python CI, and contributor docs from the stale root `tests/` backlog to maintained package-owned suites.
- Documented root `tests/` as a legacy migration backlog until individual tests are moved to their owning packages or updated to the current package layout.
- Fixed the API app's holds dependency wiring so the mounted holds router receives the repository through the request app state used by its live dependency.
- Added public Facility Gate alert/dashboard artifacts required by the pilot readiness gate.
- Updated JWT logout regression coverage to test the current internal-token revocation path instead of the removed shared admin password fallback.
- Consolidated the deployable FastAPI/reference API package directory at `packages/reference-api` so contributors can distinguish it from protocol schemas, generated clients, or generic API artifacts at a glance.
- Updated CI, Docker, Vercel/serverless entrypoints, package source mappings, OpenAPI scripts, migration scripts, tests, docs, and generated public canvas references to the new `packages/reference-api` path.
- Adjusted local/serverless startup paths so `server.main` resolves to the server package rather than the root simulation SDK package when launching the API.
- Moved the root public Python client facade from `sardis/` to `src/sardis/` so the repository root no longer shadows the server package's `server.main` import.
- Updated root package build metadata, Docker copy paths, version consistency checks, package docs, and security scope references for the new root `src` layout.

## What Was Deleted

- Deleted `apps/landing/lib/sardis-api.ts`.
- Deleted tracked private/company artifacts from public tracking:
  - `docs/cdp/`
  - `docs/hiring/`
  - `docs/partnerships/`
  - `docs/sales/`
  - `docs/yc/`
  - `scripts/gtm/`
  - `scripts/audit/investor_claims_evidence.md`
  - `deploy/gcp/staging/*.yaml`
  - `monitoring/`
  - `ops/grafana/`
- Deleted generated Solana local-validator ledger/keypair artifacts under `packages/sardis-solana-program/.anchor/test-ledger/`.
- Deleted `.github/workflows/deploy-dashboard.yml`; hosted dashboard deployment belongs in the future private product repo.
- Deleted tracked company-specific SOC2/ops docs from `docs/compliance/soc2/` and `docs/ops/`.
- Deleted generated/private operational evidence under `docs/audits/evidence/`.
- Deleted generated uptime/response-time snapshots under `api/*/*.json` and generated Foundry deployment artifacts under `contracts/broadcast/`.
- Deleted hosted production/compliance/runbook docs and private launch/remediation docs from public tracking.
- Deleted private release/design-partner scripts that depended on private evidence artifacts.
- Deleted hosted product source from public tracking:
  - `apps/dashboard/`
  - `packages/ui-web/`
  - `packages/sardis-checkout-ui/`
  - `apps/canvas-site/src/pages/dashboard.astro`
  - `canvases/dashboard/index.html`
- Deleted private/live ops scripts from public tracking:
  - `scripts/bootstrap_staging_api_key.sh`
  - `scripts/check_demo_deploy_readiness.sh`
  - `scripts/demo-mainnet-e2e.py`
  - `scripts/deploy-cloudrun.sh`
  - `scripts/deploy-demo-testnet.sh`
  - `scripts/deploy-mainnet-contracts.sh`
  - `scripts/deploy-mainnet.sh`
  - `scripts/deploy-sardis-connect.sh`
  - `scripts/deploy_gcp_cloudrun_staging.sh`
  - `scripts/generate_phase2_targets.mjs`
  - `scripts/generate_staging_secrets.sh`
  - `scripts/health_monitor.sh`
  - `scripts/monitor_contracts.sh`
  - `scripts/onboard_partner.sh`
  - `scripts/setup-monitoring.sh`
  - `scripts/setup-production.sh`
  - `scripts/submit_ecosystem_prs.sh`
  - `scripts/verify-mainnet.sh`
  - `scripts/yc_wow_demo.py`
- Deleted `agent_identity.py`, an unregistered legacy identity router from the old flat router bucket.
- Deleted `anomaly.py`, an unregistered anomaly API prototype from the old flat router bucket with no live app wiring.
- Deleted `plugins.py`, an unregistered plugin-management API prototype from the old flat router bucket with no live app wiring.
- Deleted `packages/reference-api/sardis_v2_api/routes/budgets.py`, an unused early budget-allocation prototype package that was not imported or mounted by the live API.

## What Was Rewritten

- No broad rewrite was performed.
- Behavioral rewrites were localized:
  - mandate validation infrastructure errors now return `503 mandate_validation_unavailable` instead of falling through to payment execution.
  - durable idempotency DB fallback rejects same-key/different-payload replay attempts.
  - KYC webhook persistence stores allowlisted metadata plus payload hash instead of raw provider payloads.
  - JWT validation checks expected issuer/audience boundaries for new internal tokens and Better Auth JWKS tokens.
  - `/api/v2/pay` now uses the shared idempotency helper when an idempotency header is supplied.
  - `/api/v2/payments/batch` now uses the shared idempotency helper when an idempotency header is supplied.
  - `/api/v2/transactions/batch` now uses the shared idempotency helper when an idempotency header is supplied.

## Intentionally Left Unchanged

- No package/runtime/framework migration.
- No database migration consolidation yet.
- No large FastAPI bootstrap extraction yet.
- Hosted dashboard, checkout UI, and hosted product design-system source were removed from the OSS repo but preserved in git history for private-repo recovery.
- Empty package shell directories remain ignored by Git tracking unless they gain a clear package goal.

## Before/After Architecture Summary

Before: Sardis had a viable monorepo stack, but modernization work lacked a committed coordination source of truth. Some public/docs/CI surfaces drifted from actual package names and auth architecture, and one checkout payment path could continue after mandate validation infrastructure failure.

After: The repo has a committed modernization map and a first set of safe implementation commits. CI filters point at the actual TypeScript SDK package, public quickstarts use exported clients, the landing app no longer carries an unused unsafe Sardis API browser client, checkout mandate validation fails closed, the public/private boundary is documented, public contribution paths exist, tracked private/company material has been removed, hosted product UI source has been removed from the public contribution path, and the highest-risk idempotency/KYC/JWT issues from the audit have focused regression coverage.

Additional contributor-readiness pass: package docs now cover the tracked experimental/private-candidate packages that lacked README entrypoints, JS install paths are frozen by default across contributor scripts, release dry-run, Vercel config, and deploy workflow app jobs, uv resolves repo-local Sardis Python packages from editable checkout paths, and the first Pydantic/FastAPI upgrade blockers have been removed from core/API config surfaces.

Latest public-surface pass: remaining private deployment, staging, mainnet, partner, monitoring, and demo scripts have been removed from the OSS repo. Public deployment docs now describe local/container/Cloud Run deployment without organization-specific bootstrap scripts, and package maturity is enforced by the default verification command.

Latest API layout pass: the first route naming cleanup removed one dead prototype router and renamed the generic outbound webhook module to make room for a clearer distinction between customer webhook subscriptions and inbound provider callbacks. Route registration now lives under `server.route_registry.<domain>` modules so `main.py` can shrink toward a composition root. The physical route placement pass is complete: outbound webhook subscription and dev utility route code lives under `server.routes.developer`, inbound provider callback and provider adapter code lives under `server.routes.providers`, pay/ledger/transaction/payment/bridge code lives under `server.routes.money_movement`, mandate/AP2/MVP/approval/delegation/subscription/credential/facility code lives under `server.routes.authority`, wallet/card/treasury/funding/ramp/on-chain/onramp code lives under `server.routes.wallets`, and the remaining account, commerce, billing, policy, evidence, compliance, protocol, identity, operations, and agent lifecycle surfaces live under their matching domain route packages. The old flat router compatibility package has been removed after internal imports and tests moved to the domain modules.

Latest contributor-test pass: the public default Python test path now exercises maintained package-owned suites instead of the stale root `tests/` backlog. The newly exposed API-suite failures were fixed in the holds router wiring, Facility Gate readiness artifacts, and JWT logout regression test.

Latest path-layout pass: the deployable API package now lives at `packages/reference-api`, while the API Python import package remains `server` and the distribution name remains `sardis-api`. The root public client facade remains `src/sardis`. This makes the monorepo package boundary more explicit without changing HTTP routes or published package identity.

Latest root package pass: the public simulation/client facade now uses the same standard `src` layout as the server package. This removes the repo-root `sardis/` directory that previously shadowed `packages/reference-api/server` during local import probes.

Latest CI/CD guardrail pass: the public CI map now inventories every workflow file, required check metadata is cross-checked against workflow job names, public docs links are checked across the main contributor docs and architecture docs, PR-triggered workflows cannot use private deploy/publish/provider secrets without a PR-excluding job condition, private-secret workflows cannot use top-level `permissions: read-all`, public PR workflows cannot use top-level `permissions: read-all`, and workflow Node/pnpm/install commands are checked against the repo's Node 22, pnpm 9.15.4, and frozen-lockfile policy.

Latest source-layout pass: the contributor gate now enforces the current API
source layout directly. The reference API must stay at
`packages/reference-api/server`, route implementations must stay under domain
`routes/` modules, registration must stay under `route_registry/`, and the old
repeated API package/source shape must not return. Published Python libraries
may still use `src/<import_package>` when that is the package-correct library
layout. The contributor tree helper now has an API-focused command,
`pnpm repo:api-tree`, and the source-layout gate rejects route implementation
files nested deeper than `routes/<domain>/<module>.py`.
Latest route registration naming pass: the former `server.routing` package was
renamed to `server.route_registry` so contributors can distinguish endpoint
implementations under `server.routes` from FastAPI registration helpers without
parsing two nearly identical directory names.

Latest API bootstrap pass: KYC provider/service construction moved out of
`server.main` into a tested dependency helper. The production
fail-closed requirement, Persona credential checks, mock fallback behavior, and
non-production factory fallback are now covered without booting the full app.
Sanctions provider/service construction now follows the same pattern, covering
Elliptic, Scorechain, mock fallback, duplicate fallback suppression, production
fail-closed behavior, and non-production factory fallback outside the full app.
KYA service, audit store, and ComplianceEngine wiring are now constructed by a
tested dependency helper, leaving `main.py` closer to a composition root instead
of a mixed provider-bootstrap module.
Core API service construction now also sits behind a tested helper covering the
Postgres versus in-memory policy store, wallet repository, agent repository,
wallet manager, chain executor, and ledger store selection.
Mandate archive, replay cache, verifier, and payment orchestrator construction
now sit behind a tested payment runtime helper, including Postgres, SQLite, and
in-memory replay-cache selection.
Cache service and API-key manager construction now sit behind a tested support
services helper, preserving production Redis requirements and Postgres versus
memory API-key manager storage selection.
Facility Gate repository and adapter construction now also sits behind a tested
helper, preserving the Postgres versus memory repository DSN selection used by
facility request routes.
Provider runtime, inbound payment runtime, fiat ramp runtime, and treasury
runtime construction now follow the same tested bootstrap-helper pattern. The
treasury pass removed Lithic client and treasury repository construction from
`server.main` while preserving the route dependency handoff and no-key warning
behavior.
Circle CPN route client construction now also lives behind a tested helper,
including settings/env precedence, default Circle paths, webhook secret
resolution, disabled-mode behavior, and client initialization failure recovery.
Virtual card repository/provider construction now lives behind the same
bootstrap-helper boundary in `server.card_runtime`, not the generic dependency
module. The extraction preserves feature-flag behavior, mock/Lithic/Stripe/Rain/
Bridge provider selection, primary/fallback routing, organization overrides,
partner webhook secrets, and Lithic ASA handler wiring while leaving
`server.main` responsible only for route registration.
Stripe treasury and funding route configuration parsing now has a dedicated
`server.funding_runtime` helper with focused tests for settings/env precedence,
connected-account map parsing, non-Stripe funding credentials, and live-mode
fail-closed bootstrap activation.
Funding adapter construction now also lives in `server.funding_runtime`, with
tests for Stripe treasury, Rain, Bridge, Coinbase CDP, Circle CPN, unknown
adapter names, missing credentials, and ordered primary/fallback adapter
selection.
Recurring billing auto-fund handler wiring now lives beside funding runtime
configuration, with tests for request shaping, fail-closed live mode behavior,
simulated no-op behavior, invalid token rejection, and non-positive amount
rejection.
Stripe Issuing webhook policy evaluation now also lives in
`server.funding_runtime`, with tests for fail-open behavior when policy context
is unavailable, missing wallet/policy handling, Decimal amount normalization,
and MCC-to-merchant-category policy evaluation.
Checkout and Pay with Sardis merchant runtime construction now lives in
`server.checkout_runtime`, with tests for Stripe PSP connector registration,
no-key behavior, merchant repository/webhook/settlement wiring, Sardis-native
connector dependencies, Stripe Connect settlement fallback, and checkout base
URL defaults.
Stripe Connect route registration now reuses the checkout runtime's resolved
Stripe Connect provider instead of constructing a second provider inline in
`server.main`.
Late-stage dependency-light route registration now lives in
`server.route_registry.static_routes`, reducing the app factory's route
registration tail while preserving coverage for service directory, compliance
export, agent registry, evidence, policy simulation, settlement, funding, FX,
batch payment, streaming payment, ACP, ramp, and A2A discovery paths.

## Test, Build, And Lint Results

Current validation after the latest API bootstrap cleanup:

- `python3 -m compileall -q packages/reference-api/server/main.py packages/reference-api/server/funding_runtime.py packages/reference-api/tests/test_funding_runtime.py` passed.
- `uv run ruff check packages/reference-api/server/main.py packages/reference-api/server/funding_runtime.py packages/reference-api/tests/test_funding_runtime.py` passed.
- `PYTHONPATH="$(find packages -maxdepth 2 -type d -name src | tr '\n' ':'):packages/reference-api" uv run pytest packages/reference-api/tests/test_funding_runtime.py packages/reference-api/tests/test_funding_bootstrap.py -q` passed: 18 passed.
- `PYTHONPATH="$(find packages -maxdepth 2 -type d -name src | tr '\n' ':'):packages/reference-api" uv run pytest packages/reference-api/tests/test_checkout_runtime.py packages/reference-api/tests/test_funding_runtime.py packages/reference-api/tests/test_funding_bootstrap.py -q` passed: 22 passed.
- `PYTHONPATH="$(find packages -maxdepth 2 -type d -name src | tr '\n' ':'):packages/reference-api" uv run pytest packages/reference-api/tests/test_static_routes.py packages/reference-api/tests/test_commerce_routing.py packages/reference-api/tests/test_money_movement_routing.py packages/reference-api/tests/test_protocol_routing.py -q` passed: 10 passed.
- `python3 scripts/source_layout_check.py && python3 scripts/stale_api_path_check.py && python3 scripts/package_maturity_check.py && python3 scripts/public_doc_link_check.py` passed.
- `pnpm check:openapi` passed: 540 paths, 592 schemas.
- `pnpm run check:contributor` passed, including OSS surface, stale path, source layout, generated artifact, public doc link, CI/CD, workflow, template, community health, package maturity, contribution map, root-test inventory, and focused smoke tests.

Representative earlier validation during the modernization run:

- Full maintained API package tests passed during the prior import-root cleanup: 972 passed, 5 skipped.
- `python3 scripts/source_layout_check.py && python3 scripts/stale_api_path_check.py && python3 scripts/package_maturity_check.py && python3 scripts/public_doc_link_check.py`, `pnpm check:openapi`, `pnpm run check:contributor`, and `git diff --check` passed during the prior docs/source-layout cleanup.
- Maintained API package tests passed repeatedly during route placement and runtime bootstrap extraction.
- `packages/sardis-core`, `packages/sardis-ledger`, `packages/sardis-chain`, and `packages/sardis-zk-policy` package-owned tests passed during earlier package validation passes.
- `pnpm --filter @sardis/sdk typecheck`, `pnpm --filter @sardis/mcp-server build`, `pnpm --filter @sardis/app-landing typecheck`, `pnpm --filter @sardis/app-landing build`, `pnpm --filter @sardis/docs build`, and `pnpm --filter canvas-site build` passed during earlier OSS surface and docs cleanup passes.
- `uv lock --check`, JSON/YAML parse smokes, package maturity checks, public-surface scans, and route snapshot checks passed during earlier dependency, CI, and public-boundary cleanup passes.

Notes:

- pnpm commands warn that the local Node runtime is `v24.10.0` while the repo declares Node `22.x`.
- pytest emits existing deprecation warnings from Pydantic, FastAPI, websockets, httpx, and JWT test fixtures.

## Remaining Risks

- Some money-moving routes still need replay tests and a unified execution service; `/api/v2/pay`, `/api/v2/payments/batch`, and `/api/v2/transactions/batch` now have client-idempotency replay coverage.
- Database migration history remains split between Alembic and raw SQL.
- `packages/reference-api/server/main.py` remains an oversized composition root, but OpenAPI generation now has a duplicate-clean check command before router extraction work.
- Public/private repo hygiene still needs actual private-repo creation and history-preserving recovery of dashboard/product surfaces from git history.
- Dashboard deployment automation and source are no longer in the public OSS repo; the private product repo must recreate its CI/CD from the moved history.
- Private staging/mainnet/demo/partner/monitoring automation is no longer in the public OSS repo; the private product/cloud repo needs a clean replacement from history or fresh infrastructure-as-code.
- Private production, compliance, and provider-certification gates now need to live in the future private product/compliance repository; the public gate intentionally does not prove hosted production readiness.
- Canvas and LLM exports are regenerated from source, but still need a single typed registry so route order, nav, sitemap, and LLM dumps cannot drift.
- Webhook replay protection remains uneven across provider routers.
- Checkout nonce/replay hardening remains to be completed.
- `actionlint` and `gitleaks` are not installed locally, so workflow linting and local secret scanning still need to run in an environment with those tools.

## Next 7 Days

- Add replay tests for remaining money-moving mutation routes.
- Standardize provider webhook replay protection.
- Harden checkout nonce/replay binding.
- Replace remaining `json_encoders` model config with Pydantic v2 field serializers and remove websocket/datetime deprecation warnings.
- Review duplicate Pydantic model class names before considering a full component-schema snapshot instead of the current stable route-level snapshot.
- Create the private `sardis-product` or `sardis-cloud` repo and recover dashboard/product surfaces from this repo's history.
- Recreate private staging/mainnet/demo/partner/monitoring automation in the private repo with explicit owner, secret, and environment boundaries.

## Next 30 Days

- Split `server.main` into bootstrap registrars without changing route contracts.
- Continue extracting `server.main` route registration into `route_registry/authority.py`, `route_registry/money_movement.py`, `route_registry/providers.py`, and `route_registry/operations.py`.
- Continue extracting `server.main` route registration into smaller domain registrars now that route implementation placement is domain-based.
- Continue replacing source-inspection tests with behavior-level tests where practical; the authority/payment policy tests now track current orchestrator/control-plane boundaries instead of stale route-local implementation strings.
- Reconcile raw SQL and Alembic migration policy with a Postgres apply test.
- Consolidate dashboard request layers into one client plus hook wrapper.
- Generate canvas sitemap, nav, route order, and `llms-full.txt` from one typed registry.
- Classify each integration package as core, supported, experimental, or demo.
- Raise critical-domain test coverage and add mypy as a staged CI gate.
- Add a CI job that runs `pnpm --filter @sardis/docs build` so docs dependency drift is caught before merge.

## Commits Created

- `18eef66f docs: add modernization audit and migration plan`
- `f749544b chore: add modernization inventory check`
- `1caceb95 ci: fix TypeScript SDK workspace filters`
- `beec970d docs: fix Sardis client quickstarts`
- `76a2d013 fix(landing): remove stale browser API client`
- `da0c3919 fix(checkout): fail closed on mandate validation errors`
- `edf8ad10 docs: add modernization final report`
- `56792266 chore: prepare public OSS contribution surface`
- `646eec77 fix(api): bind idempotency fallback and sanitize KYC webhooks`
- `81420c1d fix(auth): bind JWT validation to expected issuers`
- `efefabe1 docs: align public examples with SardisClient`
- `fcf01d86 docs: update modernization final report`
- `8c5be376 chore: make OSS tooling installs deterministic`
- `3f0716c1 docs: document experimental and private-candidate packages`
- `b3cee4d4 chore(python): map Sardis packages to local uv sources`
- `6cf2117f docs: record Python source mapping cleanup`
- `f7621c11 chore(python): modernize Pydantic config usage`
- `68943d32 docs: record Pydantic modernization pass`
- `fd7bb9cb fix(pay): add idempotent replay protection`
- `89e015e1 docs: record pay idempotency protection`
- `b14656b6 fix(batch-payments): add idempotent replay protection`
- `9ed83d20 docs: record batch payment idempotency protection`
- `d0b52966 fix(transactions): add batch idempotency protection`
- `e57ea626 docs: record transactions batch idempotency protection`
- `79bf97e5 chore(api): add OpenAPI contract check`
- `1a9fa253 docs: record OpenAPI contract check`
- `ee121646 fix(api): remove duplicate OpenAPI routes`
- `00835504 docs: record OpenAPI duplicate route cleanup`
- `0b970a44 chore(api): fail OpenAPI check on duplicate operations`
- `34ffe33d docs: record strict OpenAPI check`
- `02d9cccd chore(api): add OpenAPI route snapshot gate`
- `1c9d52f3 docs: record OpenAPI snapshot gate`
- `16cad813 ci: enforce OpenAPI route snapshot`
- `a34a3573 docs: record OpenAPI CI gate`
- `6acd44ec ci: remove dashboard deploy workflows`
- `ece27ef4 docs: record dashboard deploy cleanup`
- `5706d1c5 chore: remove private ops docs from public surface`
- `e753d904 fix(docs): declare docs chat schema dependency`
- `106f499c chore: enforce package maturity docs`
- `904bf3fa chore: remove private ops scripts from public surface`
- `6156c7c9 refactor(api): clarify webhook subscription routing`
- `7783e291 refactor(api): extract developer route registration`
- `1ae31368 refactor(api): extract pay route registration`
- `58e57232 refactor(api): extract authority route registration`
- `b6713ff0 test(api): align policy enforcement tests with orchestrator paths`
- `91493f65 refactor(api): move webhook route into developer routes`
- `0a491efc docs: record private ops docs cleanup`
- `45d67a52 docs: make quickstarts simulation first`
- `91bf799e docs: record simulation-first quickstarts`
- `5ded7702 chore: remove generated audit evidence from public surface`
- `85fb48af docs: record audit evidence cleanup`
- `0a1ed87d chore: remove generated deployment artifacts`
- `aff751a8 docs: record generated artifact cleanup`
- `7c560f5a chore: remove private production docs from public surface`
- `e6cc469f chore: make release readiness public-only`
- `218695ad chore: keep readiness wrapper executable`
- `d77ef988 docs: record public release gate cleanup`
- `b2dff4e3 chore: move product UI source out of public repo`
- `af1eba12 ci: check public doc links`
- `d597b842 docs: map public ci gates`
- `b6286241 chore: strengthen contributor templates`
- `1c2e9087 ci: align required check metadata`
- `a08ed4af docs: add community health guard`
- `1292fc12 docs: clarify package layout boundaries`
- `340a5a8b ci: broaden public doc link guard`
- `8d819468 ci: require workflow inventory coverage`
- `372fcb01 ci: guard workflow secret scope`
- `40e7a800 ci: reduce secret workflow permissions`
- `02205d84 ci: reduce public pr workflow permissions`
- `8f6bfc7c ci: guard workflow toolchain drift`
