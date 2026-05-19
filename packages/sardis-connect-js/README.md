# @sardis/connect

Status: experimental

TypeScript helper package for adding Sardis-aware payment and mandate handling to merchant or agent-facing HTTP surfaces.

## Why This Exists

`@sardis/connect` is intended to be a small integration layer, not a second SDK. It should help applications accept Sardis payment authority metadata while delegating protocol correctness to the core SDK and API contracts.

## Install

```bash
pnpm add @sardis/connect
```

## Local Development

```bash
pnpm --filter @sardis/connect build
```

## Security Notes

This package should not verify payment authority with ad hoc string checks. Use signed mandates, API validation, and server-side verification from Sardis protocol surfaces.

## Contribution Notes

Keep this package minimal. If a feature belongs in the canonical TypeScript SDK, add it to `packages/sardis-sdk-js` instead.
