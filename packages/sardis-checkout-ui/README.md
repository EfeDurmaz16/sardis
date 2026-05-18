# @sardis/checkout-ui

Status: private-candidate

React/Vite checkout UI for hosted Sardis checkout experiences.

## Why This Exists

This package provides the product-facing checkout experience around Sardis sessions, wallet payment, funding, processing, and success/error states. It is currently useful as an implementation reference, but it is not part of the stable OSS protocol surface.

## Local Development

```bash
pnpm --filter @sardis/checkout-ui build
pnpm --filter @sardis/checkout-ui test
```

## Public / Private Boundary

Keep public:

- embeddable interface contracts if they become stable
- sandbox examples that use placeholder sessions

Move private:

- hosted checkout product UX
- production provider wiring
- brand/commercial flows
- customer-specific checkout configuration

## Contribution Notes

External contributors should prefer protocol, SDK, API, and sandbox checkout work in `packages/sardis-checkout` unless this package is explicitly promoted to a supported public widget.
