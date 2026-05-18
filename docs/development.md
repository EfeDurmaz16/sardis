# Development Guide

This guide describes the public OSS development loop for Sardis.

## Requirements

- Python 3.12
- Node.js 22
- pnpm 9.15.4 or newer
- uv
- Foundry, only when working on `contracts/`

## Setup

```bash
uv sync
pnpm install --frozen-lockfile
```

Use local package sources where available. Do not rely on published Sardis packages while developing repo-local changes.

The root `pyproject.toml` maps every tracked Python `sardis-*` package under `[tool.uv.sources]` as an editable local path. This is intentional: contributor checks must exercise the checkout being edited, not a previously published PyPI package with the same name.

## Fast Checks

```bash
python3 scripts/repo_inventory.py
pnpm check:openapi
pnpm --filter @sardis/sdk typecheck
pnpm --filter @sardis/mcp-server build
uv run pytest packages/api/tests/test_merchant_checkout.py -q
```

The default maintained Python API suite is:

```bash
uv run pytest packages/api/tests/
```

The root `tests/` directory is a legacy migration backlog and is not part of
the default public CI path until individual tests are moved to their owning
package or updated to the current package layout.

When an intentional API contract change updates the generated OpenAPI schema, review the diff and then run:

```bash
pnpm openapi:update
```

## Public CI Scope

Required public checks should cover:

- Python lint and tests for core API packages.
- TypeScript SDK and MCP build/typecheck/tests.
- Contract formatting/build/tests.
- OSS surface inventory.
- Secret scanning and dependency review.

Hosted dashboard, managed deployment, customer operations, and private provider workflows should not be required for normal external contributions.

## Updating JavaScript Dependencies

The default contributor install is frozen. If you intentionally need to update `pnpm-lock.yaml`, use:

```bash
pnpm run bootstrap:mutable
```

Commit lockfile changes separately from implementation changes when possible.

## Adding Dependencies

Before adding a dependency:

1. Check whether the repository already has an equivalent.
2. Prefer standard library or small local code for simple HTTP calls.
3. Verify license, maintenance, current docs, changelog, and security issues.
4. Commit dependency changes separately.
5. Document why the dependency is worth the extra surface.

## Working on Security-Sensitive Code

Payment, wallet, signing, policy, auth, compliance, webhook, and evidence code must be treated as security-sensitive.

Default expectations:

- fail closed
- verify signatures
- bind idempotency keys to request fingerprints
- avoid logging raw KYC, payment, token, or credential payloads
- enforce policy before execution or signing
- preserve append-only evidence
- add regression tests for bypasses

## Package Stability

Use `docs/packages.md` before changing a package. Do not promote a package from experimental to supported without tests, docs, and a stable API explanation.

## Verifying Python Local Sources

When changing Python package metadata or root extras, run:

```bash
uv lock --check
uv run --extra api python - <<'PY'
from importlib import metadata
for name in ["sardis-api", "sardis-chain", "sardis-compliance", "sardis-ledger", "sardis-sdk"]:
    direct_url = metadata.distribution(name).read_text("direct_url.json")
    assert direct_url and "file://" in direct_url and '"editable":true' in direct_url
print("local editable sources verified")
PY
```
