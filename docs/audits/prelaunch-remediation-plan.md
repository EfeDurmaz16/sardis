# Sardis Pre-Launch Remediation Checklist

This checklist tracks remediation work for the pre-launch audit completed on 2026-02-13.

Legend:
- [ ] Not started
- [~] In progress
- [x] Done

## 1. README & First Impressions
- [x] Align Python quick-start with actual SDK API.
- [x] Align TypeScript quick-start with actual SDK API.
- [x] Remove hardcoded MCP tool count claims and source from runtime.
- [ ] Rework competitor comparison language to defensible, sourced claims.
- [ ] Update "What's New" to current factual state.
- [ ] Validate all external links and badge targets in a network-enabled check.

## 2. Code Quality & Consistency
- [ ] Reduce broad `except Exception` usage in production paths.
- [ ] Add/complete type hints on public Python APIs where missing.
- [ ] Normalize async API consistency (remove unnecessary async stubs or add awaits).
- [ ] Remove or reduce explicit `any` in TypeScript packages and dashboard.
- [ ] Standardize error typing and handling patterns across TS packages.

## 3. Security
- [~] Confirm no hardcoded secrets in tracked files with repeatable scanning.
- [x] Align env variable docs with runtime config names.
- [~] Review and harden API auth defaults (dev vs prod behavior).
- [x] Verify webhook signature checks are fail-closed for all providers.
- [~] Validate SQL query composition safety in all dynamic query builders.
- [x] Confirm production rate limiting hard-requires Redis.
- [x] Remove insecure cryptography placeholders from wallet modules.
- [x] Validate CORS policy and trusted origin handling.
- [ ] Run dependency CVE checks in CI (`pip-audit`, `npm audit` or equivalent).

## 4. SDK Accuracy
- [ ] Reconcile `sardis` root exports with documented API.
- [x] Fix Python SDK version constant mismatch.
- [x] Fix TypeScript SDK internal version constant mismatch.
- [x] Fix all broken examples in `examples/` to use real SDK methods.
- [x] Add SDK contract smoke tests for docs/examples.
- [x] Reconcile MCP tool definition/handler count mismatches.

## 5. Package Publishing Readiness
- [ ] Ensure every publishable package has complete metadata.
- [x] Resolve `workspace:` dependency for npm publish compatibility.
- [x] Synchronize package versions and internal version constants.
- [x] Add missing per-package LICENSE files.
- [x] Verify there are no private/internal-only dependencies in published manifests.

## 6. Test Coverage & CI
- [x] Tighten CI lint/type gates (remove `continue-on-error` and permissive flags).
- [x] Raise minimum coverage threshold from current baseline.
- [x] Add smoke tests for quick-start and examples.
- [ ] Confirm integration coverage for payment execution, policy enforcement, wallet lifecycle.
- [ ] Confirm smart contract tests still pass after changes.

## 7. Documentation Accuracy
- [x] Reconcile claims: tests count, chains count, tool count, package count, protocol count.
- [ ] Remove stale version references across README/landing/docs.
- [x] Add a central claims-evidence document with reproducible references.

## 8. Marketing & Launch Materials
- [ ] Remove/replace unverifiable claims in launch assets.
- [ ] Update product-hunt and social copy with verified metrics.
- [ ] Verify awesome-list targets and submission details (network-enabled run).

## 9. Infrastructure & Deployment
- [ ] Align Alembic migration head with SQL migration set.
- [ ] Verify Vercel config and deployment workflows are consistent.
- [ ] Remove brittle runtime path hacks where possible.
- [x] Ensure env var documentation matches actual runtime usage.

## 10. Investor Readiness
- [ ] Separate demo/simulated defaults from production narrative.
- [ ] Add objective proof points for all investor-facing claims.
- [ ] Provide clone-and-run script that validates first-run experience.
- [ ] Publish final remediation report with residual risks.
