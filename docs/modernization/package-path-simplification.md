# Package Path Simplification Decision

## Problem

The current API implementation path is technically valid but hard to navigate:

```text
packages/sardis-api/src/sardis_api/...
```

The repetition comes from two different naming layers:

- `packages/sardis-api/` is the monorepo package directory and PyPI
  distribution boundary.
- `src/sardis_api/` is the Python import package, required because Python
  imports use underscores rather than hyphens.
- `src/` is the standard Python source layout used to avoid accidental imports
  from the repository root.

The Python package name `sardis_api` should stay stable. The directory
`packages/sardis-api` is the part that can be simplified.

## Decision

Do not collapse or remove `src/sardis_api`.

Instead, plan a separate package-directory migration from:

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
Python import path and the `src` layout.

This should be treated as an actual migration, not merely a documentation note.
The current path is technically defensible but ergonomically bad for an OSS
repo. The next safe package-layout milestone is:

```text
packages/api/src/sardis_api/...
```

That is still a normal Python package layout, but it removes the most confusing
double Sardis API wording from day-to-day navigation.

## Why Not Rename Immediately

The package directory is referenced by build, validation, Docker, OpenAPI, and
workspace configuration. A casual rename would touch many unrelated surfaces:

- root `pyproject.toml` editable workspace mapping
- root `package.json` OpenAPI scripts
- API Dockerfile and local compose paths
- CI workflows and deployment jobs
- package docs and README examples
- tests that add `packages/sardis-api/src` to `PYTHONPATH`
- generated OpenAPI commands and package-local scripts

This is a high-blast-radius change and should not be mixed into an unrelated
route move commit. It should be executed as its own atomic package-layout
commit with a broad reference update and validation pass.

## Migration Shape

When this migration is executed, it should be one dedicated branch/commit
sequence:

1. Add a temporary compatibility note in docs that `packages/sardis-api` is
   being renamed to `packages/api`.
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

## Current Priority

Continue the lower-risk route-domain migration first:

- move active implementation files out of `sardis_api.routers`
- keep temporary compatibility wrappers
- keep OpenAPI paths stable
- shrink `main.py` route registration into domain registrars

After the current route-domain commit, perform the package-directory rename as a
focused migration if the worktree is clean and the reference scan is tractable.
