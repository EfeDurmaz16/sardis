# Package Layout

Sardis uses a monorepo package name and a language import package name for each maintained package. These names do not always match one-to-one because they serve different jobs.

## Canonical API Package

The reference API implementation lives at:

```text
packages/reference-api/
```

Its Python import package lives at:

```text
packages/reference-api/server/
```

This is intentional:

- `packages/reference-api` is the monorepo package boundary contributors navigate to.
- `server` is the short Python import namespace for the FastAPI server.
- The API package intentionally omits an extra `src/` layer because `packages/reference-api` already provides the local package boundary in this monorepo.
- `sardis-api` remains the Python distribution name for packaging compatibility.

The API package should not be reintroduced under longer names that repeat
`sardis`, `api`, or `server`; those names make path roaming harder without
improving the import model.

For day-to-day server-source navigation, do not use raw `find` from the
repository root. It will include ignored local artifacts such as `.venv`,
`node_modules`, `dist`, and `__pycache__`, and it will also bury the API source
under migration files. Use the contributor tree helper instead:

```bash
pnpm repo:api-tree
```

The API source tree should stay at this depth:

```text
packages/reference-api/server/routes/<domain>/<module>.py
```

Do not add route implementation folders below the domain layer unless a
separate architecture decision explains why the extra depth is worth it.

## Root Python Client

The root public Python client facade lives at:

```text
src/sardis/
```

This package owns the public SDK-style import:

```python
from sardis import SardisClient
```

Keep `src/sardis` separate from `packages/reference-api/server`. The former is
the public client facade; the latter is the server implementation.

## Protocol Packages

Protocol and integration packages keep their own package boundaries:

- `packages/sardis-protocol/` for protocol primitives.
- `packages/sardis-mpp/` for MPP client/payment-method primitives.
- `packages/sardis-mcp-server/` for the MCP tool surface.
- `packages/sardis-sdk-js/` and `packages/sardis-sdk-python/` for public SDKs.

When adding a new package, prefer:

```text
packages/<clear-package-name>/src/<python_import_name>/
```

for Python library packages, or:

```text
packages/<clear-package-name>/src/
```

for TypeScript packages.

Avoid adding another nested project folder under a package unless the package genuinely contains multiple independently built artifacts.
