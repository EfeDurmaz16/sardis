# Source Layout Policy

Sardis optimizes the public tree for contributor navigation first. Package and
module names should make it clear whether a contributor is editing the
reference API, a public SDK, a protocol primitive, or a provider integration.
Use this file for API source-tree rules and `docs/oss/package-layout.md` for
repo-wide package naming and nesting policy.

## Reference API

The reference API uses this active source layout:

```text
packages/reference-api/server/
```

Do not reintroduce the old repeated API shapes. They may appear in migration
notes or validation scripts only as forbidden examples:

```text
packages/sardis-api/src/sardis_api/
packages/reference-api/src/sardis_api/
packages/reference-api/src/sardis/
packages/reference-api/server/routers/
```

The package has two explicit boundaries:

- `packages/reference-api/` is the monorepo package boundary for the deployable
  reference API service.
- `server/` is the Python import boundary for the FastAPI application.

This is not meant to say "Sardis API" twice. The first layer is the repository
package for the deployable reference API. The second layer is the Python import
package for the FastAPI application. We keep that import package named `server`
instead of `sardis_api` so contributors do not have to read the same API concept
three times in one path.

The short version: `packages/reference-api/server` is the maximum acceptable API
nesting. `packages/sardis-api/src/sardis_api` is not acceptable because it says
the same thing three times.

There should not be a third generic `src/` layer inside the API package. The API
is an application package, not a small import-only library, so the monorepo
package boundary already provides the isolation that `src/` would otherwise add.

Route implementation files should live under domain folders:

```text
packages/reference-api/server/routes/protocol/x402.py
packages/reference-api/server/routes/protocol/mpp.py
packages/reference-api/server/routes/providers/stripe_webhooks.py
packages/reference-api/server/routes/wallets/wallets.py
```

FastAPI registration and dependency wiring should live under:

```text
packages/reference-api/server/route_registry/
```

Use one registrar module per domain when route mounting needs dependencies or
runtime state. Use `route_registry/static_routes.py` only for dependency-light
public/protocol routes that are mounted together near the end of app startup.
Do not put endpoint implementations, request models, provider clients, or
business logic in `route_registry/`.

Do not add more route nesting below the domain layer. This is acceptable:

```text
routes/protocol/x402.py
```

This is not:

```text
routes/protocol/payments/x402/handlers.py
```

`packages/reference-api/server/main.py` should remain a composition root, not a
catch-all file for every route, provider, and bootstrap concern. New runtime
construction should go into focused helpers such as `card_runtime.py`,
`checkout_runtime.py`, or `funding_runtime.py` when it can be tested without
booting the full FastAPI app.

The source-layout guard enforces a 1,000-line ceiling for
`packages/reference-api/server/main.py`. If a change would exceed that limit,
move route registration into `route_registry/` or runtime construction into a
focused `*_runtime.py` helper first.

The same guard rejects direct `app.include_router(...)`, `APIRouter`, and
`server.routes` imports in `main.py`. New endpoint mounting belongs in
`route_registry/<domain>.py` or `route_registry/static_routes.py`; `main.py`
should call registrars, not know individual route modules.

## Python Libraries

Published Python libraries may keep the standard `src/<import_package>` layout
when it protects packaging correctness. For example:

```text
packages/sardis-core/src/sardis_v2_core/
packages/sardis-sdk-python/src/sardis_sdk/
packages/sardis-chain/src/sardis_chain/
```

That layout is acceptable for libraries because it prevents accidental imports
from the repository root and mirrors common Python packaging practice. Do not
flatten a published library solely to shorten the path. Flatten only when a
package-specific migration proves that the shorter layout preserves packaging,
editable installs, tests, and downstream imports.

Application packages are different. A deployable app should not use a repeated
shape such as `packages/sardis-api/src/sardis_api/`; the package name already
tells contributors they are inside the API, so the import package must be short
and role-based.

## Naming Rules

- Directory names should describe the package role, not repeat `sardis` at
  every level.
- Import package names should avoid collisions with the public SDK facade
  package, `sardis`.
- Generic buckets such as `routers/`, `utils/`, and `misc/` should be replaced
  with domain names when files already have clear ownership.
- Public HTTP paths should stay stable unless a migration plan explicitly
  changes the API contract.

## Validation

Run this before opening layout, routing, or contribution-path PRs:

```bash
pnpm repo:api-tree
python3 scripts/source_layout_check.py
python3 scripts/stale_api_path_check.py
pnpm run check:contributor
```
