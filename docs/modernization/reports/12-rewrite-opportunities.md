# 12 Rewrite Opportunities

## Decision

A full language/framework/runtime rewrite is not justified now.

## Why Refactor Instead

- Python/FastAPI is suitable for the API, background jobs, policy evaluation, and provider integrations.
- TypeScript/Next.js is suitable for the dashboard and landing surfaces.
- Existing CI, tests, migrations, SDKs, and production guards provide useful safety rails.
- The main pain is organization, duplicated artifacts, and canonical-source drift, not a fundamentally wrong runtime.

## Rewrite Candidates

### Targeted rewrite: API bootstrap structure

- Evidence: `packages/api/src/sardis_api/main.py`.
- Proposal: Extract registrars and service factories while preserving routes.
- Risk: Medium.
- Validation: app startup and route tests.

### Targeted rewrite: frontend API client layer

- Evidence: `apps/dashboard/lib/sardis-api.ts` and `apps/landing/lib/sardis-api.ts`.
- Proposal: Rebuild as shared typed transport plus per-app auth adapter.
- Risk: Medium.
- Validation: typecheck and auth smoke.

### Targeted rewrite: migration management

- Evidence: Alembic through 030 and raw SQL through 106.
- Proposal: Reconcile and declare canonical migration runner.
- Risk: High.
- Validation: empty Postgres apply and repository tests.

## What To Discard

- Undocumented generated build output.
- Redundant package-local lockfiles for workspace-managed JS packages after verification.
- Stale demos/examples that do not run and are not part of public docs.

## What To Preserve

- Public package names.
- `/api/v2` contracts.
- Production auth and safety guards.
- Existing migration history until a verified replacement path exists.
