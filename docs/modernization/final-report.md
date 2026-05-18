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

## What Was Deleted

- Deleted `apps/landing/lib/sardis-api.ts`.

## What Was Rewritten

- No broad rewrite was performed.
- The only behavioral rewrite was localized: mandate validation infrastructure errors now return `503 mandate_validation_unavailable` instead of falling through to payment execution.

## Intentionally Left Unchanged

- No package/runtime/framework migration.
- No database migration consolidation yet.
- No large FastAPI bootstrap extraction yet.
- No generated `canvases/`, `api` monitoring JSON, or `contracts/broadcast` cleanup yet.
- No private-facing docs deletion yet.
- No KYC payload retention change yet.
- No idempotency DB fallback migration yet.

## Before/After Architecture Summary

Before: Sardis had a viable monorepo stack, but modernization work lacked a committed coordination source of truth. Some public/docs/CI surfaces drifted from actual package names and auth architecture, and one checkout payment path could continue after mandate validation infrastructure failure.

After: The repo has a committed modernization map and a first set of safe implementation commits. CI filters point at the actual TypeScript SDK package, public quickstarts use exported clients, the landing app no longer carries an unused unsafe Sardis API browser client, and checkout mandate validation fails closed.

## Test, Build, And Lint Results

- `python3 scripts/repo_inventory.py` passed.
- `pnpm --filter @sardis/sdk typecheck` passed.
- `pnpm --filter @sardis/app-landing typecheck` passed.
- `python3 - <<'PY' ... from sardis import SardisClient ...` passed in simulation mode.
- `uv run pytest packages/sardis-api/tests/test_merchant_checkout.py -q` passed: 44 tests.

Notes:

- pnpm commands warned that the local Node runtime is `v24.10.0` while the repo declares Node `22.x`.
- pytest emitted existing deprecation warnings from Pydantic/FastAPI/websockets code.

## Remaining Risks

- DB idempotency fallback still needs a schema/code/test fix for request-hash binding.
- Money-moving routes still need replay tests and a unified execution service.
- KYC webhook logging/storage still needs PII minimization.
- Python local-source resolution can still drift to published PyPI packages.
- Database migration history remains split between Alembic and raw SQL.
- `packages/sardis-api/src/sardis_api/main.py` remains an oversized composition root.
- Public/private repo hygiene still needs archive/sanitize work for partnerships, sales, YC, and related docs.
- Canvas and LLM exports still need registry-driven regeneration.

## Next 7 Days

- Fix durable idempotency fallback: add request hash persistence and mismatch rejection.
- Add replay tests for `/api/v2/pay` and batch payments.
- Harden KYC webhook logging and metadata retention.
- Patch Python local package source resolution or introduce a uv workspace policy.
- Add an OpenAPI snapshot/diff command before router refactors.
- Archive or sanitize tracked private-facing GTM/fundraising docs.

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
