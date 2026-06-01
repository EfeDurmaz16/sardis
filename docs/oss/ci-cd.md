# Public CI/CD Map

This map explains which public checks protect the open-source Sardis surface.
The public repository must give contributors fast, deterministic feedback
without requiring hosted-product secrets, customer data, deployment
credentials, or managed-provider accounts. The Sardis service (the FastAPI API,
the payment engine, and their deployment pipelines) lives in a private
repository and is not part of this OSS surface.

## Required Public Gates

| Gate | Workflow | Job | What it proves | Local command |
| --- | --- | --- | --- | --- |
| Contributor surface | `.github/workflows/ci.yml` | `Contributor Gate` | OSS/private boundary, stale API paths, source-layout invariants, generated-artifact hygiene, public doc links, CI inventory, workflow secret scoping, workflow toolchain drift, package maturity, contribution map coverage, root-test backlog drift, and a small bootstrap smoke suite. | `pnpm run check:contributor` |
| Python SDK client | `.github/workflows/ci.yml` | `Python Lint & Test` | Ruff lint over the repo and the public thin-client SDK test suite. | `pnpm run lint`; `uv run pytest packages/sardis/tests/ -q` |
| TypeScript SDK and MCP | `.github/workflows/ci.yml` | `TypeScript SDK Build & Type Check` | Umbrella SDK build, SDK typecheck, SDK tests, and MCP server build. | `pnpm run build:ts-sdks`; `pnpm run test:ts-sdks`; `pnpm run build:mcp` |
| Contracts | `.github/workflows/ci.yml` | `Contracts Strict Forge` | Foundry formatting, contract build size report, and full contract test suite. | `cd contracts && forge fmt --check src test script && forge build --sizes && forge test` |
| Secret scanning | `.github/workflows/secret-scan.yml` | `Scan for secrets` | Gitleaks blocks obvious credentials and key material from PRs. | `bash scripts/detect-secrets.sh` when available locally |
| Static and dependency security | `.github/workflows/security-scan.yml` | `Python Dependency Vulnerabilities`, `Static Application Security Testing` | Python dependency audit and Bandit SAST over the public SDK source. | Run workflow or equivalent local tools |
| CodeQL | `.github/workflows/codeql.yml` | `Analyze (${{ matrix.language }})` | GitHub CodeQL analysis for Python and TypeScript/JavaScript. | GitHub Actions |
| OpenSSF Scorecard | `.github/workflows/scorecard.yml` | `Scorecard analysis` | OpenSSF scorecard SARIF generation/upload. | GitHub Actions |
| Release dry-run | `.github/workflows/release-dry-run.yml` | `Engineering Readiness Gate`, `NPM Package Dry Run`, `PyPI Package Dry Run` | Public release checks that do not require private provider/customer systems. | `pnpm run check:release-readiness` |

## Non-Public Or Optional Workflows

- Backend deployment, hosted dashboard, approval inbox, customer operations,
  billing operations, GTM, investor, and provider-certification workflows live
  in the private service repository, not here.
- Scheduled uptime and monitoring workflows are operational signals for the
  hosted service and are not part of the public contributor gate.

## Workflow Inventory

Every workflow file must be listed here so public CI/CD scope changes are
reviewable. Required PR checks belong in the required-gates table above; the
inventory below classifies the rest of the workflow surface.

| Workflow | Class | Public contribution role |
| --- | --- | --- |
| `.github/workflows/ci.yml` | required gate | Primary public PR gate: contributor gate, SDK lint/test, TypeScript build, contracts, landing build. |
| `.github/workflows/codeql.yml` | security analysis | CodeQL static analysis for Python and TypeScript/JavaScript. |
| `.github/workflows/scorecard.yml` | security analysis | OpenSSF Scorecard SARIF generation/upload. |
| `.github/workflows/secret-scan.yml` | security gate | Gitleaks secret scanning on PRs. |
| `.github/workflows/security-scan.yml` | security analysis | Python dependency audit and Bandit SAST over the public SDK source. |
| `.github/workflows/release-dry-run.yml` | release verification | Dry-runs the publish pipeline on release-touching changes. |
| `.github/workflows/release-sardis-py.yml` | publish-only | Publishes the umbrella `sardis` Python package with release credentials. |
| `.github/workflows/release-sardis-npm.yml` | publish-only | Publishes the umbrella `sardis` npm package with release credentials. |
| `.github/workflows/dependabot-auto-merge.yml` | maintainer automation | Handles trusted dependency-update housekeeping, not a contributor gate. |
| `.github/workflows/pr-maintenance.yml` | maintainer automation | Produces PR maintenance reports. |

## Branch Protection Source

Branch protection expected checks are recorded in
`.github/required-checks.json`. Keep that file focused on jobs that run for
normal public pull requests. Publish-only and maintainer-automation workflows
can still protect their surfaces, but they should not be required for every
external contribution unless they run reliably on every PR without private
credentials.

## Local First Loop

Start with:

```bash
pnpm run doctor
pnpm run check:contributor
```

Then run the narrow package gate from `docs/oss/contribution-map.md` for the
area you changed. Do not widen a small docs or SDK PR into deployment or
provider-operation validation unless the PR actually touches those surfaces.

## CI Maintenance Rules

- Keep public CI credential-free unless a job is explicitly marked publish-only.
- Jobs triggered by `pull_request` or `pull_request_target` must not use private
  publish, provider, or operations secrets unless the job has a job-level
  condition that excludes public PR events.
- Workflows triggered by `pull_request` or `pull_request_target` must use
  explicit least-privilege permissions instead of `permissions: read-all`.
- Workflows that use private publish, provider, or operations secrets must use
  explicit least-privilege permissions instead of `permissions: read-all`.
- Pin or constrain tool versions in workflow files, especially Node, pnpm,
  Python, uv, Foundry, and security scanners.
- Public workflows that install JavaScript dependencies must use Node 22, pnpm
  9.15.4 when explicitly pinned, and `pnpm install --frozen-lockfile`.
- Add new required gates to this document and to `pnpm run check:contributor`
  when they protect public contribution quality.
- Do not let generated artifacts, local caches, or private docs become required
  inputs for public CI.
