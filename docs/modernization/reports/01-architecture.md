# 01 Architecture Audit

## Findings

### High: FastAPI app factory is an oversized composition root

- Evidence: `packages/server-api/src/sardis/main.py` contains middleware setup, provider construction, dependency overrides, router registration, feature flags, checkout setup, billing, facility-gate wiring, and health registration in one `create_app` path. Router registration spans hundreds of lines around `packages/server-api/src/sardis/main.py:781`, `packages/server-api/src/sardis/main.py:1891`, and `packages/server-api/src/sardis/main.py:2244`.
- Impact: Changes to one domain can regress unrelated startup behavior. Tests need to import a very large app to validate narrow routes.
- Recommended action: Refactor into domain registration modules such as `bootstrap/middleware.py`, `bootstrap/core_services.py`, `bootstrap/router_registry.py`, and per-domain registrars.
- Action type: Refactor.
- Estimated risk: Medium, because startup order and dependency overrides are behavior-sensitive.
- Validation method: `uv run pytest packages/server-api/tests/ -q` plus app startup smoke importing `sardis.main:create_app`.

### Medium: Backend still mixes v1, v2, and prototype naming

- Evidence: `packages/server-api/src/sardis/main.py` registers both `/api/v1/auth` and `/api/v2/auth`; it also imports `sardis_v2_core` throughout. The public Python client facade now lives at `src/sardis/`.
- Impact: Contributors cannot quickly infer which domain package is canonical.
- Recommended action: Document canonical surfaces and create a deprecation map before renaming packages.
- Action type: Migration.
- Estimated risk: Medium.
- Validation method: OpenAPI diff and SDK contract tests.

### Medium: Frontend/backend/API boundaries are not consistently centralized

- Evidence: `apps/dashboard/lib/sardis-api.ts` uses a same-origin `/api/sardis` proxy, while `apps/landing/lib/sardis-api.ts` reads browser-visible tokens and calls `NEXT_PUBLIC_API_URL`.
- Impact: Auth/session behavior can drift across public surfaces.
- Recommended action: Move browser API access to a shared package or generated client with explicit auth strategy wrappers.
- Action type: Refactor.
- Estimated risk: Medium.
- Validation method: dashboard auth smoke, landing no-token behavior test, TypeScript typecheck.

### Low: Full rewrite is not justified

- Evidence: Python/FastAPI, Next.js, pnpm, uv, and Foundry remain current enough; CI and tests already exist.
- Impact: A rewrite would increase risk without clear product upside.
- Recommended action: Incremental modularization and cleanup.
- Action type: No action for full rewrite; refactor for selected modules.
- Estimated risk: Low.
- Validation method: Keep package/API contracts stable while reducing local complexity.
