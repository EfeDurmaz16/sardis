# Legacy Root Test Suite

The maintained public API test suite lives in:

```text
packages/server-api/tests/
```

Run it with:

```bash
uv run pytest packages/server-api/tests/
```

This root `tests/` directory contains older cross-package, audit, integration,
and historical migration tests. It is intentionally not the default contributor
or CI test path while the public repository is being modernized. Many files in
this directory still refer to legacy API module paths that were removed during
the `sardis_api` to `sardis` import-package migration.

Before re-enabling any root test in CI, move it to the owning package's
`tests/` directory or update it to the current package layout:

- API route tests: `packages/server-api/tests/`
- Core policy/orchestration tests: `packages/sardis-core/tests/`
- Ledger tests: `packages/sardis-ledger/tests/`
- Chain execution tests: `packages/sardis-chain/tests/`

Do not add new tests to this root directory unless the test genuinely spans
multiple packages and has no clearer package owner.
