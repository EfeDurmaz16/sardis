# Package Path Simplification Decision

## Problem

The API implementation path went through three readability cleanups. The first
removed the old `packages/sardis-api` monorepo directory repetition. The second
renamed the import package from `sardis_api` to `sardis`. The remaining problem
was that `packages/api` was too generic for a package that is the deployable
FastAPI server/reference implementation:

```text
packages/api/src/sardis/...
```

That path was technically valid, but it made the package boundary too vague:

- `api` did not say whether this was a schema package, generated client, or deployable server.
- `src/sardis/` is the import package and should remain short.
- `src/` is still the standard Python source layout used to avoid accidental
  imports from the repository root.

For a contributor, the package directory should say what is inside before they
open it. The package is the server/reference API, so `server-api` is clearer
than a bare `api`.

## Decision

Do not collapse or remove `src`; keep the standard Python source layout.

Keep the API import package as:

```text
packages/server-api/src/sardis/
```

Rename the monorepo package directory from:

```text
packages/api/
```

to:

```text
packages/server-api/
```

This keeps a short, natural import path:

```python
from sardis.main import create_app
```

The Python distribution name remains `sardis-api`. That is a package/release
identity and should not be bundled with a repository path cleanup.

## Execution Notes

The server package path is referenced by build, validation, Docker, OpenAPI,
deploy, docs, and tests. The rename therefore updated:

- root and package-local Python package source mappings
- API Dockerfiles and local server commands
- CI workflows and deployment jobs
- package docs and README examples
- tests and scripts that import the API package
- generated OpenAPI commands and package-local scripts

This was intentionally executed as its own atomic path-layout commit with a
broad reference update and validation pass. The HTTP API path contract and
Python import path are not part of this rename and must stay stable.

## Migration Shape

The current migration sequence is:

1. Confirm the deployable FastAPI package is still the OSS reference server, not only a protocol schema package.
2. Rename the package directory with `git mv packages/api packages/server-api`.
3. Update path references in packaging config, scripts, CI, Docker, OpenAPI, docs, and tests.
4. Keep `src/sardis` and the `sardis-api` distribution name stable.
5. Run compile, focused tests, OpenAPI, package maturity, and whitespace checks.

## Validation

Minimum validation for the server package-directory rename:

```bash
python3 -m compileall -q packages/server-api/src/sardis packages/server-api/scripts/generate_openapi.py api/index.py
PYTHONPATH="$(find packages -maxdepth 2 -type d -name src | tr '\n' ':')" uv run pytest packages/server-api/tests/test_funding_bootstrap.py packages/server-api/tests/test_sandbox_isolation.py packages/server-api/tests/test_facility_requests_router.py -q
pnpm check:openapi
python3 scripts/package_maturity_check.py
git diff --check
```

Recommended broader validation:

```bash
python3 scripts/repo_inventory.py
pnpm check
uv run pytest packages/server-api/tests -q
```

## Current State

The contributor-facing API path is now:

```text
packages/server-api/src/sardis/...
```

Remaining path cleanup should focus below `src/sardis`: continue moving route
registration and bootstrap concerns out of the oversized `main.py` into domain
registrars and bootstrap modules. The legacy `routers/` bucket and the unused
`sardis_v2_api` package have been removed.
