# Contributing to Sardis

Sardis is an open-source financial authority layer for AI agents. The best contributions improve the shared protocol, SDKs, policy/evidence primitives, MCP tooling, examples, tests, and public documentation.

The hosted dashboard, managed provider operations, sales material, investor material, and customer-specific workflows are outside the public contribution path.

New here? Read [`ARCHITECTURE.md`](../ARCHITECTURE.md) first — it is the map of
the repository (the single authority path, the typed provider ports, the route
domains, and a "where to make your first change" table). The goal is that you can
understand the layout and open a useful PR in under an hour.

## What is contributable vs commercial

This repo is MIT open-core. **Contributable:** the authority core (mandates,
policy, approvals, revocation, signed audit), the typed provider-port contracts
and sandbox adapters, the three SDKs/MCP server, protocol adapters, examples,
tests, and public docs. **Not contributable here:** the hosted dashboard,
managed credential vault / provider operations, and any sales/investor/customer
material. The exact line is in
[`docs/oss/public-private-boundary.md`](../docs/oss/public-private-boundary.md);
per-package paths and validation commands are in
[`docs/oss/contribution-map.md`](../docs/oss/contribution-map.md).

## The experimental quarantine

`packages/sardis/src/sardis/protocol/experimental/` holds protocol code that is
**not production-ready** — in-memory simulations, draft-EIP sketches with
unverified crypto, or unwired schemes. Nothing in `core/`, `routes/`, or
`middleware/` may depend on it. If you finish hardening an adapter (real
verification + fail-closed + bad-case tests), it graduates out of
`experimental/`. Do not add new production wiring that imports from there.

## Good First Contribution Areas

- Fix SDK docs or quickstarts that drift from the actual API.
- Add tests for policy, mandate, idempotency, replay, and evidence behavior.
- Improve MCP tool schemas and examples.
- Add sandbox-only provider adapter examples.
- Improve package READMEs using the standard in `docs/packages.md`.
- Add conformance fixtures for AP2, TAP, x402, UCP, or A2A interoperability.

For package-specific contribution paths and validation commands, use
`docs/oss/contribution-map.md`.

## Before You Start

Read:

- [`README.md`](../README.md) — what Sardis is, install, the open-core boundary
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — the repo map: authority path, provider ports, where to make your first change
- [`docs/oss/public-private-boundary.md`](../docs/oss/public-private-boundary.md) — what is OSS-contributable vs commercial
- [`docs/oss/contribution-map.md`](../docs/oss/contribution-map.md) — per-package contribution paths and validation commands
- [`docs/oss/ci-cd.md`](../docs/oss/ci-cd.md)
- [`docs/packages.md`](../docs/packages.md) — package maturity matrix
- [`docs/development.md`](../docs/development.md)
- [`docs/oss/testing.md`](../docs/oss/testing.md)
- [`.github/SECURITY.md`](SECURITY.md)
- [`.github/CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- [`.github/SUPPORT.md`](SUPPORT.md)

## Setup

```bash
pnpm run doctor
uv sync
pnpm install --frozen-lockfile
```

`pnpm run doctor` checks Python, Node.js, pnpm, and uv before heavier
bootstrap or CI gates. Fix any failing toolchain item first; the repository
expects Node.js 22 LTS, pnpm 9.15.4 or newer, Python 3.12 or newer, and uv.

## Common Checks

Run the narrowest check that covers your change.

```bash
pnpm run check:contributor
python3 scripts/repo_inventory.py
python3 scripts/oss_surface_check.py
python3 scripts/stale_api_path_check.py
pnpm run check:generated
pnpm run check:docs-links
pnpm run check:ci-map
pnpm run check:github-templates
pnpm run check:community
pnpm run check:contribution-map
pnpm --filter sardis typecheck
pnpm --filter @sardis/mcp-server build
uv run pytest packages/sardis/tests -q
```

`pnpm run check:contributor` is the fast public-surface gate for most docs,
package metadata, contribution-map, generated-artifact, local-doc-link, CI-map,
GitHub-template, community-health, and API routing cleanup PRs. It
intentionally avoids private services and production provider credentials.

For contracts:

```bash
cd contracts
forge fmt --check src test script
forge build --sizes
forge test
```

## Pull Request Expectations

Each PR should:

- explain the problem and the fix
- keep one logical change per PR
- include tests or a clear validation command
- avoid unrelated formatting churn
- avoid generated files unless they are intentionally regenerated
- avoid adding private commercial, customer, sales, investor, or provider-credential material

## Security Issues

Do not open public issues for vulnerabilities. Follow `SECURITY.md`.

Security-sensitive changes should include tests for the failure mode being fixed.

## Dependency Changes

Open a separate PR for dependency changes when possible. Include:

- why the dependency is needed
- license
- maintenance status
- security considerations
- why an existing dependency or small local implementation is not enough

## Package README Standard

Every supported package should explain:

1. what it does
2. why it exists
3. install command
4. minimal usage
5. stability level
6. test/build command
7. contribution notes
8. security/provider caveats
