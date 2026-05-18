# @sardis/ui-web

Status: private-candidate

Shared React UI components used by Sardis web applications.

## Why This Exists

This package reduces duplicated app-shell and component code across hosted Sardis web surfaces. It is currently product infrastructure, not a stable public design system.

## Local Development

There is no standalone build script yet. Validate through the consuming app:

```bash
pnpm --filter @sardis/app-dashboard typecheck
pnpm --filter @sardis/app-landing typecheck
```

## Public / Private Boundary

This package should move with the hosted product repo unless Sardis intentionally publishes a public design system. Public OSS contributions should focus on protocol docs, SDKs, MCP tooling, examples, tests, and API contracts.

## Contribution Notes

Do not add protocol or payment logic here. UI components should stay presentation-only and consume typed APIs from the supported SDK/API layers.
