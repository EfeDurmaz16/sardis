# Package Layout

Sardis uses a monorepo package name and a language import package name for each maintained package. These names do not always match one-to-one because they serve different jobs.

## Canonical API Package

The reference API implementation lives at:

```text
packages/api/
```

Its Python import package lives at:

```text
packages/api/src/sardis_server/
```

This is intentional:

- `packages/api` is the monorepo package boundary contributors navigate to.
- `sardis_server` is the Python import namespace for the FastAPI server.
- `src/` is the standard Python package layout and prevents accidental imports from the repository root during tests.
- `sardis-api` remains the Python distribution name for packaging compatibility.

The API package should not be reintroduced under longer names that repeat `api` or `server`; those names make path roaming harder without improving the import model.

## Root Python Client

The root public Python client facade lives at:

```text
src/sardis/
```

This package owns the public SDK-style import:

```python
from sardis import SardisClient
```

Keep `src/sardis` separate from `packages/api/src/sardis_server`. The former is the public client facade; the latter is the server implementation.

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

for Python packages, or:

```text
packages/<clear-package-name>/src/
```

for TypeScript packages.

Avoid adding another nested project folder under a package unless the package genuinely contains multiple independently built artifacts.
