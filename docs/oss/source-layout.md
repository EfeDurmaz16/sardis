# Source Layout Policy

Sardis optimizes the public tree for contributor navigation first. Package and
module names should make it clear whether a contributor is editing the
reference API, a public SDK, a protocol primitive, or a provider integration.

## Reference API

The reference API uses this active source layout:

```text
packages/api/sardis_server/
```

Do not reintroduce any of these old shapes:

```text
packages/sardis-api/src/sardis_api/
packages/api/src/sardis_api/
packages/api/src/sardis/
packages/api/sardis_server/routers/
```

The package has two explicit boundaries:

- `packages/api/` is the monorepo package boundary for the deployable
  reference API service.
- `sardis_server/` is the Python import boundary for the FastAPI application.

This is not meant to say "Sardis API" twice. The first layer is a repository
package, and the second layer is a Python import package. We keep
`sardis_server` instead of a generic `server` package because imports such as
`server.main` are collision-prone and unclear in test runners, ASGI loaders, and
editable installs.

There should not be a third generic `src/` layer inside the API package. The old
`packages/sardis-api/src/sardis_api/` shape made paths harder to scan and
repeated the same concept across the distribution directory, source root, and
import package.

Route implementation files should live under domain folders:

```text
packages/api/sardis_server/routes/protocol/x402.py
packages/api/sardis_server/routes/protocol/mpp.py
packages/api/sardis_server/routes/providers/stripe_webhooks.py
packages/api/sardis_server/routes/wallets/wallets.py
```

FastAPI registration and dependency wiring should live under:

```text
packages/api/sardis_server/routing/
```

`packages/api/sardis_server/main.py` should remain a composition root, not a
catch-all file for every route, provider, and bootstrap concern.

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
python3 scripts/source_layout_check.py
python3 scripts/stale_api_path_check.py
pnpm run check:contributor
```
