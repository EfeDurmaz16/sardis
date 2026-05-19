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
pnpm run doctor
uv sync
pnpm install --frozen-lockfile
```

`pnpm run doctor` checks the local Python, Node.js, pnpm, and uv versions before
running heavier setup commands. Run it first when onboarding or debugging local
CI parity.

Use local package sources where available. Do not rely on published Sardis packages while developing repo-local changes.

The root `pyproject.toml` maps every tracked Python `sardis-*` package under `[tool.uv.sources]` as an editable local path. This is intentional: contributor checks must exercise the checkout being edited, not a previously published PyPI package with the same name.

## Fast Checks

```bash
python3 scripts/repo_inventory.py
pnpm repo:ignored-artifacts
pnpm repo:package-validation
pnpm repo:stale-paths:local
pnpm check:openapi
pnpm --filter @sardis/sdk typecheck
pnpm --filter @sardis/mcp-server build
uv run pytest packages/reference-api/tests/test_merchant_checkout.py -q
```

`pnpm repo:ignored-artifacts` reports ignored generated folders such as
`node_modules`, `dist`, `.venv`, `.pytest_cache`, `.ruff_cache`, `.next`, and
`__pycache__` without reporting private ignored docs or local secret files. It
is a dry run by default; use `python3 scripts/ignored_artifact_inventory.py
--delete` only when you intentionally want to prune those generated artifacts
from your local checkout.

`pnpm repo:package-validation` prints every tracked public package, its maturity
status from `docs/packages.md`, its manifest type, and the most specific
credential-free validation command that can be inferred from the package
manifest.

Packages that still fall back to the repo-wide contributor gate, or that need a
non-default external tool, are tracked in
`docs/oss/package-validation-backlog.md`.

`pnpm repo:stale-paths:local` scans the full local working tree, including
ignored docs and generated canvases, for obsolete repeated API package paths.
The default contributor guard only scans tracked public surfaces; use this
local audit before declaring the checkout clean from a navigation standpoint.

The default maintained Python API suite is:

```bash
uv run pytest packages/reference-api/tests/
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
