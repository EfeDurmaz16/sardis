# 03 Duplication Audit

## Findings

### High: Database migration history exists in two systems

- Evidence: `packages/sardis-api/alembic/versions/001_initial_schema.py` through `030_facility_gate.py`; raw SQL migrations continue through `packages/sardis-api/migrations/106_agent_registry.sql`.
- Impact: It is unclear whether Alembic or raw SQL is canonical, and drift can create production migration gaps.
- Recommended action: Declare one canonical migration path. Keep historical files, but add drift checks and stop adding to both without an explicit policy.
- Action type: Migration.
- Estimated risk: High.
- Validation method: spin up Postgres, apply canonical migrations, compare expected tables/indexes.

### Medium: Frontend API clients duplicate types and error handling

- Evidence: `apps/dashboard/lib/sardis-api.ts` and `apps/landing/lib/sardis-api.ts` both define `ApiError`, `AuthRequiredError`, `AgentApiRecord`, `WalletApiRecord`, and request helpers.
- Impact: API behavior and shape handling can diverge, especially auth and collection responses.
- Recommended action: Extract shared public types to `packages/sardis-sdk-js` or a generated client, then use thin auth-specific adapters per app.
- Action type: Refactor.
- Estimated risk: Medium.
- Validation method: TypeScript typecheck for dashboard and landing.

### Medium: Spending policy constants are mirrored manually

- Evidence: `apps/dashboard/lib/sardis-api.ts` says `SPENDING_POLICY_TEMPLATES` mirrors `packages/sardis-core/src/sardis_v2_core/spending_policy.py`.
- Impact: Product defaults can silently diverge between frontend and backend.
- Recommended action: Add a backend endpoint or generated JSON artifact for policy templates.
- Action type: Migration.
- Estimated risk: Medium.
- Validation method: unit test comparing exported frontend constants with backend source of truth until generated source exists.

### Low: Static canvas exports duplicate landing/docs narratives

- Evidence: `canvases/*/index.html`, `apps/canvas-site`, `apps/landing`, and `docs-site` overlap as public documentation surfaces.
- Impact: Narrative and product claims drift.
- Recommended action: Pick canonical public surfaces and treat generated canvases as build output unless intentionally published.
- Action type: Deletion or documentation.
- Estimated risk: Low.
- Validation method: link map and sitemap checks.
