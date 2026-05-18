# 04 Dependencies Audit

## Findings

### High: JavaScript package manager state is fragmented

- Evidence: root `package.json` declares `packageManager: pnpm@9.15.4`, but `package-lock.json` files exist at root, `apps/canvas-site`, `apps/dashboard`, `packages/n8n-nodes-sardis`, `packages/sardis-activepieces`, `packages/sardis-checkout-ui`, `packages/sardis-cli-js`, `packages/sardis-mpp-proxy`, `packages/sardis-solana-program`, and `packages/sardis-stagehand`.
- Impact: Developers and CI can install different dependency graphs.
- Recommended action: Use root `pnpm-lock.yaml` for workspace packages. Keep package-local lockfiles only for intentionally standalone packages and document them.
- Action type: Migration/deletion.
- Estimated risk: Medium.
- Validation method: `pnpm install --frozen-lockfile`, targeted package builds.

### High: TypeScript SDK CI filters use the wrong package name

- Evidence: `packages/sardis-sdk-js/package.json` is named `@sardis/sdk`, while CI/publish workflows reference `@sardis/sdk-js`.
- Impact: SDK build/test/publish jobs can miss or fail against the intended workspace.
- Recommended action: Replace stale `@sardis/sdk-js` filters with `@sardis/sdk`.
- Action type: CI fix.
- Estimated risk: Low.
- Validation method: `pnpm --filter @sardis/sdk build && pnpm --filter @sardis/sdk test`.

### High: Python local package resolution can drift to PyPI

- Evidence: root `pyproject.toml` maps only a subset of local packages in `[tool.uv.sources]`; `uv.lock` contains published `sardis-api` and related packages.
- Impact: local tests and release gates can import stale published packages instead of checkout source.
- Recommended action: complete local path sources or define a real uv workspace for all monorepo Python packages used by root extras.
- Action type: Dependency graph migration.
- Estimated risk: Medium.
- Validation method: fresh `uv sync --all-extras` and import path assertions.

### Medium: Python lockfile state is also mixed

- Evidence: root `uv.lock` plus package-local `uv.lock` in `packages/server-api`, `sardis-chain`, `sardis-cli`, `sardis-connect`, `sardis-core`, `sardis-guardrails`, `sardis-ledger`, `sardis-sdk-python`, and `sardis-striga`.
- Impact: It is unclear whether package tests use root or package-local resolution.
- Recommended action: Document canonical lock behavior. Prefer root for monorepo validation and package-local only for published standalone packages that require it.
- Action type: Migration.
- Estimated risk: Medium.
- Validation method: root `uv sync` and selected package `uv sync --project`.

### Medium: Security overrides are doing heavy lifting

- Evidence: root `package.json` pins many transitive security overrides for `next`, `vite`, `rollup`, `axios`, `@modelcontextprotocol/sdk`, and others.
- Impact: Overrides can mask stale direct dependencies and create surprise incompatibility.
- Recommended action: Convert repeated override needs into direct package upgrades where possible.
- Action type: Dependency cleanup.
- Estimated risk: Medium.
- Validation method: `pnpm why`, `pnpm audit`, package builds.

### Low: Dependency research is required before any new payment/auth/db SDK

- Evidence: payment/auth packages include Better Auth, Polar, Stripe, asyncpg, SQLAlchemy, and several provider adapters.
- Impact: Adding packages without current docs can introduce security drift.
- Recommended action: Keep the minimal-dependency policy; research official docs before any integration change.
- Action type: No action now.
- Estimated risk: Low.
- Validation method: dependency review checklist.
