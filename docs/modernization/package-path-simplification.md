# Package Path Simplification Decision

## Problem

The previous API implementation path was technically valid but hard to
navigate:

```text
packages/sardis-api/src/sardis_api/...
```

The repetition comes from two different naming layers:

- `packages/sardis-api/` was the monorepo package directory and PyPI
  distribution boundary.
- `src/sardis_api/` is the Python import package, required because Python
  imports use underscores rather than hyphens.
- `src/` is the standard Python source layout used to avoid accidental imports
  from the repository root.

The Python package name `sardis_api` should stay stable. The directory
`packages/sardis-api` was the part that could be simplified.

## Decision

Do not collapse or remove `src/sardis_api`.

Rename the monorepo package directory from:

```text
packages/sardis-api/
```

to:

```text
packages/api/
```

The resulting contributor path would be:

```text
packages/api/src/sardis_api/...
```

This removes one visible `sardis-api` repetition while preserving the stable
Python import path and the standard `src` layout.

## Execution Notes

The package directory is referenced by build, validation, Docker, OpenAPI, and
workspace configuration. The rename therefore must update:

- root `pyproject.toml` editable workspace mapping
- root `package.json` OpenAPI scripts
- API Dockerfile and local compose paths
- CI workflows and deployment jobs
- package docs and README examples
- tests that add `packages/api/src` to `PYTHONPATH`
- generated OpenAPI commands and package-local scripts

This was intentionally executed as its own atomic package-layout commit with a
broad reference update and validation pass.

## Migration Shape

The migration sequence is:

1. Add a compatibility note in docs that `packages/sardis-api` was renamed to
   `packages/api`.
2. Rename the directory with `git mv packages/sardis-api packages/api`.
3. Update root workspace mappings and scripts.
4. Update CI/workflows, Docker, OpenAPI, and docs references.
5. Run the full API validation suite and OpenAPI snapshot check.
6. Leave the Python import path as `sardis_api`.

## Validation

Minimum validation for the directory rename:

```bash
python3 scripts/package_maturity_check.py
pnpm check:openapi
PYTHONPATH="$(find packages -maxdepth 2 -type d -name src | tr '\n' ':')" uv run pytest packages/api/tests/test_agent_auth.py packages/api/tests/test_agent_events_and_holds_wiring.py -q
```

Recommended broader validation:

```bash
python3 scripts/repo_inventory.py
pnpm check
uv run pytest packages/api/tests -q
```

## Current State

The contributor-facing API path is now:

```text
packages/api/src/sardis_api/...
```

Remaining path cleanup should focus below `src/sardis_api`: continue moving
active route implementations out of the legacy flat `routers/` bucket into
domain-grouped `routes/<domain>/` modules, while keeping compatibility wrappers
until imports have migrated.
