# Public Testing Policy

Sardis uses package-owned test suites as the public contributor path.

## Maintained Test Suites

Run the narrowest suite that covers your change:

```bash
pnpm run check:contributor
uv run pytest packages/reference-api/tests/ -q
uv run pytest packages/sardis-core/tests/ -q
uv run pytest packages/sardis-ledger/tests/ -q
uv run pytest packages/sardis-chain/tests/ -q
pnpm --filter @sardis/sdk test
pnpm --filter @sardis/mcp-server test
```

The root `package.json` `test` script runs the maintained package-owned suites.
Root `pyproject.toml` also points pytest at `packages/reference-api/tests` by
default.

Some protocol packages are intentionally validated with package-local source
paths instead of relying on a published install. Use these commands when
changing paid HTTP protocol behavior:

```bash
PYTHONPATH=packages/sardis-protocol/src uv run pytest packages/sardis-protocol/tests -q
PYTHONPATH=packages/sardis-mpp/src uv run --with pympp pytest packages/sardis-mpp/tests -q
PYTHONPATH=packages/reference-api uv run pytest tests/test_x402_middleware.py tests/test_mpp_router.py -q
```

Run those protocol targets separately. The package-local protocol tests and
legacy root protocol tests load different pytest `tests.conftest` modules, so
combining them into one pytest invocation can produce plugin-registration
collisions unrelated to the code under test.

`pnpm run check:contributor` is the recommended first check for public OSS
cleanup PRs. It verifies the public/private surface guard, stale API path guard,
source-layout guard, generated-artifact guard, public docs local-link guard, CI
map drift guard, workflow secret-scope guard, GitHub template guard, community
health guard, package maturity matrix, contribution map coverage, root-test
migration inventory, and a small mixed root/package pytest smoke suite.

The public docs local-link guard covers the README, contribution/security/support
files, package matrix, development guide, docs index, quickstart, OSS docs, and
architecture docs.

## Legacy Root Tests

The repository-root `tests/` directory is a migration backlog from earlier
architecture phases. It contains cross-package, audit, integration, and
historical migration tests. It is intentionally not the default contributor or
CI path while the repository is being modernized.

Do not add new tests there unless the test genuinely spans multiple packages
and has no clearer package owner. When a root test becomes relevant again, move
it into the owning package first:

| Test kind | Target |
| --- | --- |
| API route and middleware tests | `packages/reference-api/tests/` |
| Policy, mandate, orchestration, and authority tests | `packages/sardis-core/tests/` |
| Ledger, receipt, and reconciliation tests | `packages/sardis-ledger/tests/` |
| Chain, token, Tempo, and Solana tests | `packages/sardis-chain/tests/` |
| SDK examples and contract tests | owning SDK package or docs test suite |

## Migration Inventory

The root-test backlog is tracked in `docs/oss/root-test-migration.md`.
Regenerate it after moving or deleting root tests:

```bash
python3 scripts/root_test_inventory.py --write
```

The inventory includes:

- total root Python tests
- stale API import/path reference count
- suggested package owner buckets
- files that still mention removed API package names or router paths

## Stale API Paths

Active public surfaces must use the current API import package and path layout:

```text
server
packages/reference-api/server
```

Run this guard before opening PRs that touch docs, examples, or test routing:

```bash
python3 scripts/stale_api_path_check.py
```

For cleanup work, also run the stricter local audit:

```bash
pnpm repo:stale-paths:local
```

The local audit includes ignored and untracked text files, so it can surface old
planning docs, generated canvases, or archived notes that still mention removed
repeated API package paths. Do not wire that stricter mode into contributor CI
until those local-only surfaces have been archived or regenerated.

## Source Layout

The source-layout guard keeps the reference API contributor path readable and
prevents older package names from coming back:

```bash
python3 scripts/source_layout_check.py
```

It requires the active API tree to stay at `packages/reference-api/server` with
domain route modules under `routes/` and FastAPI registration under `route_registry/`.
Published Python libraries may still use `src/<import_package>` when that is
the package-correct layout for a library.
