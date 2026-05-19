# Contributing to Sardis

Sardis is an open-source financial authority layer for AI agents. The best contributions improve the shared protocol, SDKs, policy/evidence primitives, MCP tooling, examples, tests, and public documentation.

The hosted dashboard, managed provider operations, sales material, investor material, and customer-specific workflows are outside the public contribution path.

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

- `README.md`
- `docs/oss/goal.md`
- `docs/oss/public-private-boundary.md`
- `docs/oss/contribution-map.md`
- `docs/oss/ci-cd.md`
- `docs/packages.md`
- `docs/development.md`
- `docs/oss/testing.md`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `SUPPORT.md`

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
pnpm --filter @sardis/sdk typecheck
pnpm --filter @sardis/mcp-server build
uv run pytest apps/api/tests/test_merchant_checkout.py -q
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
