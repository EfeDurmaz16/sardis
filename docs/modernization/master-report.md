# Master Modernization Report

## Executive Summary

Sardis is a substantial monorepo, not a thin prototype. The current stack remains viable: Python/FastAPI for the backend and domain packages, TypeScript/Next.js for product surfaces and SDKs, Foundry for contracts, and uv/pnpm for package management. The modernization priority is not a full rewrite. It is boundary cleanup, generated-artifact hygiene, canonical migration policy, API contract protection, auth consistency, and incremental extraction from oversized bootstrap files.

## Biggest Technical Risks

- `packages/sardis-api/src/sardis_api/main.py` is too large and centralizes too many unrelated concerns.
- Database migrations are split between Alembic and raw SQL.
- Frontend authenticated API behavior differs between dashboard and landing.
- Package manager state is fragmented across root and package-local lockfiles.
- Static/generated/public documentation surfaces can drift.
- DB idempotency fallback and money-moving route replay behavior need stronger tests.
- Merchant checkout mandate validation must fail closed on infrastructure errors.
- Root Python dependency resolution can import published packages instead of local monorepo packages.

## Biggest Product Risks

- Auth or billing changes can regress production login, checkout, or usage metering.
- Payment policy enforcement can behave differently in dev/test than production.
- Public docs can overstate unfinished or stale capabilities if multiple surfaces drift.
- SDK/API contract drift can break integrations.
- KYC and partnership/fundraising content can leak sensitive or strategically private information if public repo hygiene is not maintained.

## Duplicate Code Map

- Frontend API transport/types: `apps/dashboard/lib/sardis-api.ts`, `apps/landing/lib/sardis-api.ts`.
- Migration systems: `packages/sardis-api/alembic/versions`, `packages/sardis-api/migrations`.
- Public docs/canvas surfaces: `apps/landing`, `apps/canvas-site`, `docs-site`, `canvases`.
- Spending-policy defaults: frontend constants mirror backend values manually.

## Dead Code Map

Deletion requires proof. Current candidates:

- Generated/local folders: `.next`, `.venv`, `.pytest_cache`, `.ruff_cache`, `dist`, Foundry `contracts/out` and `contracts/cache`.
- Package-local `package-lock.json` files inside pnpm workspace packages.
- Old demo/prototype folders under `demos/`, `api/`, and `api-proxy` after smoke validation.
- Static `canvases` if confirmed generated from `apps/canvas-site`.

## Bad Abstraction Map

- App bootstrap acts as service container, router registry, middleware registry, feature-flag evaluator, and integration factory.
- Frontend clients combine transport, records, policy templates, onboarding constants, and response parsing.
- Migration abstractions are split between Python Alembic and hand-authored SQL.

## Dependency Risk Map

- JavaScript: root pnpm is canonical, but many npm lockfiles remain.
- Python: root uv lock exists, with several package-local uv locks.
- Security overrides in root `package.json` indicate direct dependencies should be kept current rather than relying only on transitive overrides.

## Test Coverage Gaps

- Production fail-closed startup behavior.
- Webhook signature/replay coverage by provider.
- OpenAPI contract snapshots.
- Frontend auth strategy parity.
- Database migration reconciliation against empty Postgres.
- Idempotency mismatch handling across Redis and DB fallback.
- Checkout mandate fail-closed behavior.
- KYC payload redaction and metadata minimization.

## Rewrite Candidates

- API bootstrap modules.
- Frontend API client/auth adapters.
- Migration runner policy and reconciliation harness.

## Migration Candidates

- Canonicalize package-manager lockfiles.
- Add repo inventory and modernization validation scripts.
- Add OpenAPI snapshot/diff gate.
- Split FastAPI registration by domain.
- Move frontend shared types to SDK/generated contract layer.

## Stable Modules

- `apps/dashboard/lib/auth.ts` multi-host Better Auth configuration.
- Existing `/api/v2` route behavior.
- Existing raw SQL migration history until reconciliation.
- Production guards in `packages/sardis-api/src/sardis_api/lifespan.py`.

## Delete Candidates

- Untracked local generated/cache folders.
- Redundant package-local JS lockfiles for workspace packages after package-owner review.
- Generated static exports that can be reproduced.
- Tracked private-facing docs under `docs/partnerships`, `docs/sales`, and `docs/yc` should be archived or sanitized before public-clean claims.

## Recommended Final Architecture

- `packages/sardis-api/src/sardis_api/bootstrap/` for middleware, services, routers, and production guards.
- `packages/sardis-api/src/sardis_api/domains/<domain>/` for cohesive payment, policy, wallet, billing, webhook, evidence, and facility modules over time.
- Root-managed `uv` and `pnpm` validation for monorepo development.
- SDK/generated-contract shared types used by apps.
- Canonical migration runner with drift tests.
- Clear docs map: landing for product/public writing, docs-site for developer docs, canvases only as generated/published artifacts if still needed.
