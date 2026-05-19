# Package Path Simplification Decision

## Problem

The API implementation path went through several readability cleanups. The
early tree repeated `sardis-api` at both package and import-package levels.
The monorepo package directory was then renamed to `packages/api`. The
remaining problem was that the server import package still used `sardis`, which
collided conceptually and technically with the public Python SDK:

```text
packages/api/sardis/...
```

That path was technically valid, but it made the package boundary too vague:

- `api` did not say whether this was a schema package, generated client, or deployable server.
- `src/sardis/` collided with the root public SDK package name.
- `src/` is still the standard Python source layout used to avoid accidental
  imports from the repository root.

For a contributor, the package directory should be short enough to scan quickly
from the repository root. The package is the deployable/reference API, and it
already sits under `packages/`, so `packages/api` is clearer than repeating the
same concept in `packages/server-api`.

## Decision

The API package now intentionally omits the extra `src/` layer because
`packages/api` is already an explicit monorepo package boundary.

Keep the API import package as:

```text
packages/api/sardis_server/
```

Rename the monorepo package directory from:

```text
packages/server-api/
```

to:

```text
packages/api/
```

This keeps a clear server-only import path:

```python
from sardis_server.main import create_app
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
public SDK import path are not part of this rename and must stay stable.

## Migration Shape

The current migration sequence is:

1. Confirm the deployable FastAPI package is still the OSS reference server, not only a protocol schema package.
2. Rename the package directory with `git mv packages/server-api packages/api`.
3. Update path references in packaging config, scripts, CI, Docker, OpenAPI, docs, and tests.
4. Rename the server import package from `sardis` to `sardis_server`.
5. Keep the root public SDK import package as `src/sardis`.
6. Run compile, focused tests, OpenAPI, package maturity, and whitespace checks.

## Validation

Minimum validation for the server package-directory rename:

```bash
python3 -m compileall -q packages/api/sardis_server packages/api/scripts/generate_openapi.py api/index.py
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
packages/api/sardis_server/...
```

This still contains two naming layers:

- `packages/api` is the monorepo package boundary: the deployable
  reference API service.
- `sardis_server` is the Python import boundary: the package imported by
  tests, ASGI servers, and internal modules.

That duplication is intentional only at the Python import boundary. The old
`src/` layer was removed from the API package because `packages/api` is already
the package boundary in this monorepo. It should not leak into public docs as
`sardis-api/src/sardis_api` or `packages/api/sardis_server`, and the active
source tree must not keep an extra `routers/` bucket below it. A contributor
should land in a domain path such as:

```text
packages/api/sardis_server/routes/protocol/x402.py
packages/api/sardis_server/routes/protocol/mpp.py
packages/api/sardis_server/routes/commerce/merchant_checkout.py
```

The clean migration target is therefore domain placement below
`sardis_server`, plus accurate public docs and generated artifacts.

Remaining path cleanup should focus below `sardis_server`: continue moving
route registration concerns out of the oversized `main.py` into domain
registrars. Local monorepo import bootstrapping now lives in
`sardis_server.bootstrap`, so `main.py` is closer to a composition root instead
of a mixed bootstrap plus app-factory module. Developer utility routes
(`sdk_metrics`, simulation, non-production dev routes, and sandbox onboarding)
now register through `sardis_server.routing.developer` instead of being wired
inline in `main.py`. The legacy `routers/` bucket and the unused
`sardis_v2_api` package have been removed.
