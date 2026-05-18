# Final Modernization Report

## What Changed

- Added the modernization goal, twelve focused audit reports, a master report, and an ordered migration plan.
- Added `scripts/repo_inventory.py`, a Git-tracked-file inventory tool that prunes generated/build/cache surfaces.
- Added `check:modernization` to root `package.json`.
- Allowed `docs/modernization/**` through the existing docs ignore policy.
- Fixed TypeScript SDK CI/publish filters from the non-existent `@sardis/sdk-js` package name to the actual `@sardis/sdk` package.
- Aligned the legacy publish workflow's npm lanes with Node 22 and pnpm 9.15.4.
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
- No generated `canvases/`, `api` monitoring JSON, or `contracts/broadcast` cleanup yet.
- Dashboard and hosted-product code are still present as `private-candidate` until the private repo extraction is executed.
- Empty package shell directories remain ignored by Git tracking unless they gain a clear package goal.

## Before/After Architecture Summary

Before: Sardis had a viable monorepo stack, but modernization work lacked a committed coordination source of truth. Some public/docs/CI surfaces drifted from actual package names and auth architecture, and one checkout payment path could continue after mandate validation infrastructure failure.

After: The repo has a committed modernization map and a first set of safe implementation commits. CI filters point at the actual TypeScript SDK package, public quickstarts use exported clients, the landing app no longer carries an unused unsafe Sardis API browser client, checkout mandate validation fails closed, the public/private boundary is documented, public contribution paths exist, tracked private/company material has been removed, and the highest-risk idempotency/KYC/JWT issues from the audit have focused regression coverage.

Additional contributor-readiness pass: package docs now cover the tracked experimental/private-candidate packages that lacked README entrypoints, JS install paths are frozen by default across contributor scripts, release dry-run, Vercel config, and deploy workflow app jobs, uv resolves repo-local Sardis Python packages from editable checkout paths, and the first Pydantic/FastAPI upgrade blockers have been removed from core/API config surfaces.

## Test, Build, And Lint Results

- `python3 scripts/repo_inventory.py` passed.
- `python3 scripts/oss_surface_check.py` passed.
- `pnpm --filter @sardis/sdk typecheck` passed.
- `pnpm --filter @sardis/mcp-server build` passed.
- `pnpm --filter @sardis/app-landing typecheck` passed.
- `python3 - <<'PY' ... from sardis import SardisClient ...` passed in simulation mode.
- `uv run pytest packages/sardis-api/tests/test_merchant_checkout.py -q` passed: 44 tests.
- `uv run pytest packages/sardis-api/tests/test_idempotency_db_fallback.py packages/sardis-api/tests/test_didit_webhook.py packages/sardis-api/tests/test_auth_jwt_issuer.py -q` passed: 18 tests.
- Public example drift scan passed for stale `Sardis` constructor/import snippets except the intentional React hook name `useSardis`.
- `pnpm --filter @sardis/connect build` passed.
- `pnpm --filter @sardis/checkout-ui build` passed.
- `uv run pytest packages/sardis-zk-policy/tests -q` passed: 31 tests.
- JSON parse check passed for `package.json`, `apps/landing/vercel.json`, and `apps/dashboard/vercel.json`.
- `uv lock --check` passed after adding the complete local editable Python source map.
- `uv run --extra api python - <<'PY' ... direct_url.json ...` verified `sardis-api`, `sardis-chain`, `sardis-compliance`, `sardis-ledger`, and `sardis-sdk` install from local editable `file://` sources.
- `uv run pytest packages/sardis-api/tests/test_idempotency_db_fallback.py packages/sardis-api/tests/test_auth_jwt_issuer.py -q` passed: 5 tests.
- `python3 -m compileall -q packages/sardis-core/src packages/sardis-api/src packages/sardis-striga/src` passed after Pydantic config cleanup.
- `uv run --extra api python - <<'PY' ... SardisSettings/Agent/AgentGroup/Wallet ...` verified settings prefixes and JSON-mode model serialization.
- `uv run --with-editable ./packages/sardis-striga python - <<'PY' ... StrigaConfig ...` verified the standalone Striga config prefix.
- `uv run pytest packages/sardis-api/tests/test_merchant_checkout.py packages/sardis-api/tests/test_idempotency_db_fallback.py packages/sardis-api/tests/test_auth_jwt_issuer.py -q` passed: 49 tests.
- `rg -n "class Config:|regex=|Field\\([^\\n]*example=" packages/sardis-core/src packages/sardis-api/src packages/sardis-striga/src` returned no matches.
- `python3 -m compileall -q packages/sardis-api/src/sardis_api/routers/pay.py packages/sardis-api/tests/test_pay_phase3_fx.py` passed after `/api/v2/pay` idempotency changes.
- `uv run pytest packages/sardis-api/tests/test_pay_phase3_fx.py -q` passed: 16 tests.
- `uv run pytest packages/sardis-api/tests/test_pay_phase3_fx.py packages/sardis-api/tests/test_merchant_checkout.py packages/sardis-api/tests/test_idempotency_db_fallback.py packages/sardis-api/tests/test_auth_jwt_issuer.py -q` passed: 65 tests.
- `python3 -m compileall -q packages/sardis-api/src/sardis_api/routers/batch_payments.py packages/sardis-api/tests/test_batch_payments_idempotency.py` passed after batch payment idempotency changes.
- `uv run pytest packages/sardis-api/tests/test_batch_payments_idempotency.py -q` passed: 2 tests.
- `uv run pytest packages/sardis-api/tests/test_batch_payments_idempotency.py packages/sardis-api/tests/test_pay_phase3_fx.py packages/sardis-api/tests/test_merchant_checkout.py packages/sardis-api/tests/test_idempotency_db_fallback.py packages/sardis-api/tests/test_auth_jwt_issuer.py -q` passed: 67 tests.
- `python3 -m compileall -q packages/sardis-api/src/sardis_api/routers/transactions.py packages/sardis-api/tests/test_transactions_batch_idempotency.py` passed after transactions batch idempotency changes.
- `uv run pytest packages/sardis-api/tests/test_transactions_batch_idempotency.py -q` passed: 2 tests.
- `uv run pytest packages/sardis-api/tests/test_transactions_batch_idempotency.py packages/sardis-api/tests/test_batch_payments_idempotency.py packages/sardis-api/tests/test_pay_phase3_fx.py packages/sardis-api/tests/test_merchant_checkout.py packages/sardis-api/tests/test_idempotency_db_fallback.py packages/sardis-api/tests/test_auth_jwt_issuer.py -q` passed: 69 tests.
- `pnpm check:openapi` passed and generated the OpenAPI schema in memory: 540 paths and 594 schemas.
- `uv lock --check` passed after adding `sardis-guardrails` to the API package dependency metadata.
- `python3 -m compileall -q packages/sardis-api/scripts/generate_openapi.py packages/sardis-api/src/sardis_api/main.py` passed.

Notes:

- pnpm commands warned that the local Node runtime is `v24.10.0` while the repo declares Node `22.x`.
- pytest emitted existing deprecation warnings from Pydantic/FastAPI/websockets code.

## Remaining Risks

- Some money-moving routes still need replay tests and a unified execution service; `/api/v2/pay`, `/api/v2/payments/batch`, and `/api/v2/transactions/batch` now have client-idempotency replay coverage.
- Database migration history remains split between Alembic and raw SQL.
- `packages/sardis-api/src/sardis_api/main.py` remains an oversized composition root, but OpenAPI generation now has a check command before router extraction work.
- Public/private repo hygiene still needs actual private-repo extraction for dashboard/product surfaces.
- Canvas and LLM exports still need registry-driven regeneration.
- Webhook replay protection remains uneven across provider routers.
- Checkout nonce/replay hardening remains to be completed.
- `actionlint` and `gitleaks` are not installed locally, so workflow linting and local secret scanning still need to run in an environment with those tools.

## Next 7 Days

- Add replay tests for remaining money-moving mutation routes.
- Standardize provider webhook replay protection.
- Harden checkout nonce/replay binding.
- Replace remaining `json_encoders` model config with Pydantic v2 field serializers and remove websocket/datetime deprecation warnings.
- Fix duplicate OpenAPI operation IDs before making `check:openapi` fail on warnings or adding a checked-in API snapshot.
- Create the private `sardis-product` or `sardis-cloud` repo and move dashboard/product surfaces out of the OSS contribution path.

## Next 30 Days

- Split `sardis_api.main` into bootstrap registrars without changing route contracts.
- Reconcile raw SQL and Alembic migration policy with a Postgres apply test.
- Consolidate dashboard request layers into one client plus hook wrapper.
- Generate canvas sitemap and `llms-full.txt` from one registry.
- Classify each integration package as core, supported, experimental, or demo.
- Raise critical-domain test coverage and add mypy as a staged CI gate.

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
