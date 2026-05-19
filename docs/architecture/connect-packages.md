# Sardis Connect Package Boundary

Sardis currently keeps two Connect packages because they integrate with
different runtime surfaces. They share protocol concepts, but they are not
interchangeable packages.

## Package Roles

| Package | Runtime surface | Primary user | Owns | Does not own |
| --- | --- | --- | --- | --- |
| `packages/sardis-connect/` | Python FastAPI and Starlette-style server apps | Python merchants exposing paid HTTP APIs | FastAPI router mounting, service manifest generation, `/sardis/pay`, `/sardis/verify`, `/sardis/usage`, webhook signature verification, Python pricing models | Browser widgets, TypeScript SDK behavior, canonical protocol validation |
| `packages/sardis-connect-js/` | TypeScript Node, Express, and Connect-style middleware | TypeScript merchants exposing paid HTTP APIs | Express/Connect middleware, TypeScript manifest types, Node payment and verification route helpers | Python middleware, browser checkout UI, canonical TypeScript SDK behavior |

## Naming Decision

Keep both package directories for now:

- `sardis-connect` remains the Python distribution and import package boundary.
- `@sardis/connect` remains the TypeScript package name.
- `packages/sardis-connect-js/` is the monorepo directory name that prevents
  path collision with the Python package.

Do not rename either package until the migration can preserve:

1. published package names
2. local editable installs or package manager filters
3. README installation commands
4. package-owned validation commands
5. downstream import paths

## Contribution Rules

- Put FastAPI or Starlette behavior in `packages/sardis-connect/`.
- Put Node, Express, or Connect middleware behavior in
  `packages/sardis-connect-js/`.
- Put reusable payment protocol primitives in `packages/sardis-protocol/` or
  `packages/sardis-mpp/`, not in either Connect package.
- Put public TypeScript SDK behavior in `packages/sardis-sdk-js/`, not in
  `packages/sardis-connect-js/`.
- Keep hosted dashboard, checkout UI, approval inbox, and managed merchant ops
  outside these packages unless the OSS/private boundary explicitly changes.

## Validation

Run the owning package command before changing either package:

```bash
PYTHONPATH=packages/sardis-connect/src uv run pytest packages/sardis-connect/tests -q
pnpm --filter @sardis/connect build
```

Run the contributor gate before landing cross-package changes:

```bash
pnpm run check:contributor
```
