# Migration Plan

## 1. Safety And Tests

- Goal: Add cheap validation and inventory tooling before risky changes.
- Files likely affected: `scripts/repo_inventory.py`, `package.json`, `README.md`, `packages/api/tests`, `docs/modernization/*`.
- Implementation notes: Prune generated folders and report canonical stack/scripts. Add a credential-free validation command.
- Risk: Low.
- Rollback plan: Revert script and package script commit.
- Validation command: `python3 scripts/repo_inventory.py`.

### 1a. Payment safety test expansion

- Goal: Cover idempotency fallback, checkout mandate fail-closed behavior, and KYC redaction before deep refactors.
- Exact files likely affected: `packages/api/src/sardis_server/idempotency.py`, `packages/api/src/sardis_server/routes/commerce/merchant_checkout.py`, `packages/api/src/sardis_server/routes/compliance/kyc_onboarding.py`, related tests.
- Implementation notes: Start with narrow tests and bug fixes; defer schema migration until DB fallback contract is fully mapped.
- Risk: Medium-high.
- Rollback plan: Revert individual safety fix commit.
- Validation command: targeted pytest for changed router/service.

## 2. Dependency Cleanup

- Goal: Make package-manager ownership explicit.
- Files likely affected: `package.json`, `.gitignore`, `.github/workflows/*`, package-local lockfiles, `pyproject.toml`.
- Implementation notes: Prefer root `pnpm-lock.yaml` and root `uv.lock` for monorepo checks. Only remove package-local lockfiles after confirming package is in workspace and CI uses pnpm/uv.
- Risk: Medium.
- Rollback plan: Restore deleted lockfiles from git.
- Validation command: `pnpm install --frozen-lockfile` and targeted package builds.

## 3. Dead Code Removal

- Goal: Remove generated/local artifacts and stale prototypes after proof.
- Files likely affected: generated folders, `canvases`, old demos, archived internal docs.
- Implementation notes: Archive before deleting anything with business value. Do not remove ignored private guards.
- Risk: Medium.
- Rollback plan: Restore from git or archive.
- Validation command: inventory script plus affected tests.

## 4. Duplication Removal

- Goal: Replace obvious duplicate API client and constants across public SDKs and private product clients.
- Files likely affected: `packages/sardis-sdk-js`, OpenAPI snapshots, and private product repo clients after split.
- Implementation notes: Extract shared public types first, then point private product clients at generated SDK/OpenAPI contracts.
- Risk: Medium.
- Rollback plan: Revert per-client extraction commit.
- Validation command: `pnpm --filter @sardis/sdk-js typecheck` plus private product repo typecheck after migration.

## 5. Architecture Restructuring

- Goal: Shrink `create_app` into maintainable registrars.
- Files likely affected: `packages/api/src/sardis_server/main.py`, new `packages/api/src/sardis_server/bootstrap/*`, route-domain modules under `packages/api/src/sardis_server/routes/*`.
- Implementation notes: Start with pure middleware registration, then router groups. Keep route prefixes unchanged. Continue route-domain migration before any package-directory rename.
- Risk: Medium-high.
- Rollback plan: Revert each extraction commit independently.
- Validation command: `uv run pytest packages/api/tests/ -q`.

### 5a. Server API Package Path Simplification

- Goal: Reduce contributor-visible ambiguity by renaming the monorepo API package directory from `packages/api` to `packages/api` and the server import package from `sardis` to `sardis_server`.
- Exact files likely affected: root `pyproject.toml`, root `package.json`, CI workflows, Docker files, OpenAPI scripts, docs, API test commands, and any path references to `packages/api`.
- Implementation notes: Do not remove `src/sardis_server`; it is the stable Python import package and the standard `src` layout. Keep the Python distribution name `sardis-api`; this is a repository path cleanup, not a breaking package rename.
- Risk: High.
- Rollback plan: Revert the directory rename commit and path-reference updates together.
- Validation command: `python3 scripts/package_maturity_check.py && pnpm check:openapi && PYTHONPATH="$(find packages -maxdepth 2 -type d -name src | tr '\n' ':')" uv run pytest packages/api/tests/test_agent_auth.py packages/api/tests/test_agent_events_and_holds_wiring.py -q`.

### 5b. Root Python Client Src Layout

- Goal: Remove repo-root import shadowing by moving the public Python client facade from `sardis/` to `src/sardis/` while preserving `from sardis import SardisClient`.
- Exact files likely affected: root `pyproject.toml`, root `Dockerfile`, `scripts/release/version_consistency_check.sh`, README, package docs, security docs, and root SDK tests.
- Implementation notes: Keep the package name `sardis`; only move the source directory into the standard Python `src` layout.
- Risk: Medium.
- Rollback plan: Revert the directory move and package metadata update together.
- Validation command: `uv run python -c 'from sardis import SardisClient; print(SardisClient)' && PYTHONPATH=packages/api/src uv run python -c 'from sardis_server.main import create_app; print(create_app)'`.

## 6. Language/Framework/Runtime Migrations

- Goal: Avoid full rewrite unless future evidence changes.
- Files likely affected: none now.
- Implementation notes: Current stack is suitable. Use targeted rewrites only.
- Risk: Low.
- Rollback plan: Not applicable.
- Validation command: not applicable.

## 7. Database/Schema Migrations

- Goal: Declare canonical migration path and test it.
- Files likely affected: `packages/api/migrations`, `packages/api/alembic`, docs, CI scripts.
- Implementation notes: Do not delete historical migrations until a Postgres reconciliation test passes.
- Risk: High.
- Rollback plan: Keep old migration paths available until cutover.
- Validation command: empty Postgres migration apply plus repository smoke tests.

## 8. API Contract Stabilization

- Goal: Protect `/api/v2` route behavior.
- Files likely affected: OpenAPI generation scripts, `packages/api/openapi`, SDK tests.
- Implementation notes: Add OpenAPI snapshot diff before router refactors.
- Risk: Medium.
- Rollback plan: Revert snapshot gate.
- Validation command: OpenAPI generation/diff command.

## 9. Performance Improvements

- Goal: Reduce app startup and frontend bundle drift.
- Files likely affected: bootstrap modules, frontend imports, package deps.
- Implementation notes: Lazy-load optional integrations and keep heavy frontend libs out of initial routes.
- Risk: Medium.
- Rollback plan: Revert specific lazy-load commit.
- Validation command: app startup timing and Next build output.

## 10. Final Cleanup And Documentation

- Goal: Update public repo docs and contributor workflow.
- Files likely affected: `README.md`, `CONTRIBUTING.md`, `docs/architecture.md`.
- Implementation notes: Document canonical stack, validation, public/private surfaces, and migration policy.
- Risk: Low.
- Rollback plan: Revert docs commit.
- Validation command: markdown/link checks where available.
