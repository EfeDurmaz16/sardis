# Package Path Simplification Decision

## Problem

The API implementation path went through two readability cleanups. The first
removed the old monorepo package-directory repetition. The remaining problem
was the import package itself:

```text
packages/api/src/sardis_api/...
```

That path was technically valid Python packaging, but it forced contributors to
read "API" twice:

- `packages/api/` is already the monorepo API package boundary.
- `src/sardis_api/` repeated that boundary in the import package name.
- `src/` is still the standard Python source layout used to avoid accidental
  imports from the repository root.

For a contributor, the important name is Sardis. The package boundary already
says API, so the Python import package should not repeat it.

## Decision

Do not collapse or remove `src`; keep the standard Python source layout.

Rename the API import package from:

```text
packages/api/src/sardis_api/
```

to:

```text
packages/api/src/sardis/
```

This removes the repeated API naming while keeping a short, natural import path:

```python
from sardis.main import create_app
```

The earlier monorepo directory rename from `packages/sardis-api/` to
`packages/api/` remains in place.

## Execution Notes

The import package is referenced by build, validation, Docker, OpenAPI, and
tests. The rename therefore updated:

- `packages/api/pyproject.toml` wheel and coverage source settings
- API Dockerfiles and local server commands
- CI workflows and deployment jobs
- package docs and README examples
- tests and scripts that import the API package
- generated OpenAPI commands and package-local scripts

This was intentionally executed as its own atomic package-root commit with a
broad reference update and validation pass. The HTTP API path contract is not
part of this rename and must stay stable.

## Migration Shape

The migration sequence was:

1. Confirm the old `sardis_api` import package is internal to this repo surface.
2. Rename the package root with `git mv packages/api/src/sardis_api packages/api/src/sardis`.
3. Update imports, startup commands, packaging config, docs, and tests from
   `sardis_api` to `sardis`.
4. Remove the unused `sardis_v2_api` prototype package.
5. Run compile, focused tests, OpenAPI, package maturity, and whitespace checks.

## Validation

Minimum validation for the import-package rename:

```bash
python3 -m compileall -q packages/api/src/sardis packages/api/scripts/generate_openapi.py api/index.py
PYTHONPATH="$(find packages -maxdepth 2 -type d -name src | tr '\n' ':')" uv run pytest packages/api/tests/test_funding_bootstrap.py packages/api/tests/test_sandbox_isolation.py packages/api/tests/test_facility_requests_router.py -q
pnpm check:openapi
python3 scripts/package_maturity_check.py
git diff --check
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
packages/api/src/sardis/...
```

Remaining path cleanup should focus below `src/sardis`: continue moving route
registration and bootstrap concerns out of the oversized `main.py` into domain
registrars and bootstrap modules. The legacy `routers/` bucket and the unused
`sardis_v2_api` package have been removed.
