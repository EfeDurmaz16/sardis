# Public Testing Policy

Sardis uses package-owned test suites as the public contributor path.

## Maintained Test Suites

Run the narrowest suite that covers your change:

```bash
pnpm run check:contributor
uv run pytest packages/server-api/tests/ -q
uv run pytest packages/sardis-core/tests/ -q
uv run pytest packages/sardis-ledger/tests/ -q
uv run pytest packages/sardis-chain/tests/ -q
pnpm --filter @sardis/sdk test
pnpm --filter @sardis/mcp-server test
```

The root `package.json` `test` script runs the maintained package-owned suites.
Root `pyproject.toml` also points pytest at `packages/server-api/tests` by
default.

`pnpm run check:contributor` is the recommended first check for public OSS
cleanup PRs. It verifies the public/private surface guard, stale API path guard,
package maturity matrix, root-test migration inventory, and a small mixed
root/package pytest smoke suite.

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
| API route and middleware tests | `packages/server-api/tests/` |
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
sardis_server
packages/server-api/src/sardis_server
```

Run this guard before opening PRs that touch docs, examples, or test routing:

```bash
python3 scripts/stale_api_path_check.py
```
