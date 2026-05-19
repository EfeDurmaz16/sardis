# Public CI/CD Map

This map explains which public checks protect the open-source Sardis surface.
The public repository must give contributors fast, deterministic feedback
without requiring hosted-product secrets, customer data, dashboard deployment
credentials, or managed-provider accounts.

## Required Public Gates

| Gate | Workflow | Job | What it proves | Local command |
| --- | --- | --- | --- | --- |
| Contributor surface | `.github/workflows/ci.yml` | `Contributor Gate` | OSS/private boundary, stale API paths, generated-artifact hygiene, public doc links, CI inventory, workflow secret scoping, package maturity, contribution map coverage, root-test backlog drift, and a small API/bootstrap smoke suite. | `pnpm run check:contributor` |
| Python API and core packages | `.github/workflows/ci.yml` | `Python Lint & Test` | Ruff, maintained API tests, package-owned core/ledger/chain suites, and OpenAPI route snapshot stability. | `pnpm run check:openapi`; `uv run pytest packages/api/tests/ -q` |
| API-focused integration gate | `.github/workflows/test-api.yml` | `API Lint & Test` | API/core lint, package API tests against test Postgres, and Facility Gate tabletop/readiness artifacts. | `uv run pytest packages/api/tests/ -q` |
| TypeScript SDK and MCP | `.github/workflows/ci.yml` | `TypeScript SDK Build & Type Check` | SDK build, SDK typecheck, SDK tests, and MCP server build. | `pnpm run build:ts-sdks`; `pnpm run test:ts-sdks`; `pnpm run build:mcp` |
| Contracts | `.github/workflows/ci.yml` | `Contracts Strict Forge` | Foundry formatting, contract build size report, and full contract test suite. | `cd contracts && forge fmt --check src test script && forge build --sizes && forge test` |
| Secret scanning | `.github/workflows/secret-scan.yml` | `Scan for secrets` | Gitleaks blocks obvious credentials and key material from PRs. | `bash scripts/detect-secrets.sh` when available locally |
| Static and dependency security | `.github/workflows/security-scan.yml` | `Python Dependency Vulnerabilities`, `Container Image Vulnerabilities`, `Static Application Security Testing` | Python dependency audit, container scan, and Bandit SAST over API/core surfaces. | Run workflow or equivalent local tools |
| CodeQL | `.github/workflows/codeql.yml` | `Analyze (${{ matrix.language }})` | GitHub CodeQL analysis for Python and TypeScript/JavaScript. | GitHub Actions |
| OpenSSF Scorecard | `.github/workflows/scorecard.yml` | `Scorecard analysis` | OpenSSF scorecard SARIF generation/upload. | GitHub Actions |
| Release dry-run | `.github/workflows/release-dry-run.yml` | release dry-run jobs | Public release checks that do not require private provider/customer systems. | `pnpm run check:release-readiness` |

## Non-Public Or Optional Workflows

- Deployment workflows may exist for public API or landing surfaces, but normal
  OSS contribution should not require private hosted-product credentials.
- Hosted dashboard, approval inbox, customer operations, billing operations,
  GTM, investor, and provider-certification workflows belong in a private
  product repository.
- Scheduled uptime and monitoring workflows are operational signals, not a
  required local contributor gate.

## Workflow Inventory

Every workflow file must be listed here so public CI/CD scope changes are
reviewable. Required PR checks belong in the required-gates table above; the
inventory below classifies the rest of the workflow surface.

| Workflow | Class | Public contribution role |
| --- | --- | --- |
| `.github/workflows/ci-integrations.yml` | optional PR/package integration | Builds and tests integration packages when their surfaces change. |
| `.github/workflows/dependabot-auto-merge.yml` | maintainer automation | Handles trusted dependency-update housekeeping, not a contributor gate. |
| `.github/workflows/deploy-api-cloudrun.yml` | deploy-only | Deploys the public API surface; must not be required for ordinary PRs. |
| `.github/workflows/deploy-landing.yml` | deploy-only | Deploys the public landing site; must not be required for protocol/package PRs. |
| `.github/workflows/deploy.yml` | deploy-only | Legacy broader deploy workflow; keep outside required OSS PR checks. |
| `.github/workflows/fuzz.yml` | scheduled/manual security | Fuzzing signal for maintainers; useful but not a fast contributor gate. |
| `.github/workflows/monitoring.yml` | scheduled operations | Runtime monitoring signal, not a contributor gate. |
| `.github/workflows/nightly-sandbox-e2e.yml` | scheduled integration | Sandbox provider E2E signal; may need secrets and must stay outside required PR checks. |
| `.github/workflows/pr-maintenance.yml` | maintainer automation | Produces PR maintenance reports. |
| `.github/workflows/publish.yml` | publish-only | Publishes packages with release credentials. |
| `.github/workflows/release-npm.yml` | publish-only | Publishes npm packages with release credentials. |
| `.github/workflows/release-python-integrations.yml` | publish-only | Publishes Python integration packages with release credentials. |
| `.github/workflows/release-python-sdk.yml` | publish-only | Publishes the Python SDK with release credentials. |
| `.github/workflows/sign-artifacts.yml` | release/security | Signs release artifacts; not a contributor gate. |
| `.github/workflows/uptime-graphs.yml` | scheduled operations | Generates uptime graph artifacts. |
| `.github/workflows/uptime-response-time.yml` | scheduled operations | Captures response-time telemetry. |
| `.github/workflows/uptime-static-site.yml` | scheduled operations | Checks static site uptime. |
| `.github/workflows/uptime-summary.yml` | scheduled operations | Summarizes uptime signals. |
| `.github/workflows/uptime.yml` | scheduled operations | Runs uptime checks. |

## Branch Protection Source

Branch protection expected checks are recorded in
`.github/required-checks.json`. Keep that file focused on jobs that run for
normal public pull requests. Path-limited, scheduled, deploy, publish, and
operations-only workflows can still protect their surfaces, but they should not
be required for every external contribution unless they run reliably on every
PR without private credentials.

## Local First Loop

Start with:

```bash
pnpm run doctor
pnpm run check:contributor
```

Then run the narrow package gate from `docs/oss/contribution-map.md` for the
area you changed. Do not widen a small docs or SDK PR into hosted deployment,
dashboard, or provider-operation validation unless the PR actually touches
those surfaces.

## CI Maintenance Rules

- Keep public CI credential-free unless a job is explicitly marked deploy-only
  or publish-only.
- Jobs triggered by `pull_request` or `pull_request_target` must not use
  private deploy, publish, provider, or operations secrets unless the job has a
  job-level condition that excludes public PR events.
- Workflows that use private deploy, publish, provider, or operations secrets
  must use explicit least-privilege permissions instead of `permissions:
  read-all`.
- Keep dashboard/product deployment out of required OSS PR checks.
- Pin or constrain tool versions in workflow files, especially Node, pnpm,
  Python, uv, Foundry, and security scanners.
- Add new required gates to this document and to `pnpm run check:contributor`
  when they protect public contribution quality.
- Do not let generated artifacts, local caches, or private docs become required
  inputs for public CI.
