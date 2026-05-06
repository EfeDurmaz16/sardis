# Sardis 150-Commit Operating System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Sardis from a large, credible but noisy monorepo into a sharper payment-control-plane product with clearer package boundaries, lower CI/PR maintenance cost, stronger live-surface evidence, and a narrower production-critical path.

**Architecture:** Keep the monorepo, but introduce an explicit operating system around it: package ownership, release gates, PR automation, docs provenance, live verification, and security-sensitive invariants. The product center should be the pre-execution financial authority layer; every package, demo, and doc should either support that path or move into archive/experimental status.

**Tech Stack:** Python 3.12/uv, TypeScript/pnpm, Solidity/Foundry, GitHub Actions, GitHub CLI, Vercel, Cloud Run, FastAPI, pytest, Vitest.

---

## Current Read

Sardis is not a toy repo. It has a large API surface, many integration packages, smart contracts, tests, release gates, public apps, investor/docs artifacts, and working CI. That is a strong founder signal.

The weakness is not lack of code. The weakness is operating clarity:

- The repo contains 44 package directories, 27 workflow files, 197 docs files, 236 test files, and many demos/canvases/research artifacts.
- Production-critical code, partner-readiness docs, investor material, generated canvases, SDK integrations, and old experiments live side by side.
- Dependency PR load is high. At the time of this plan there are 64 open Dependabot PRs, and repo-level auto-merge is disabled.
- The public narrative has drift risk: "payment OS", "financial authority layer", "control plane", "connect", "facility gate", "protocol stack", and "agent economy" are all present. These can coexist, but only if the repo clearly marks the canonical path.
- CI is broad and useful, but the maintenance burden is high because many checks run across surfaces that are not equally critical.
- Some tests intentionally use mocks, placeholders, or sandbox assumptions. That is fine when labeled, risky when it becomes external proof.

## What Is Wrong Or Missing

1. **No explicit production-critical spine.** The repo should declare the smallest end-to-end path Sardis must keep green: mandate -> policy -> approval -> execution intent -> evidence -> SDK/API surface.
2. **Too many equal-looking packages.** Framework integrations and experiments should not look as important as the API, core policy, ledger/evidence, SDKs, MCP, and checkout surfaces.
3. **Docs are high-volume but not strongly provenance-tagged.** Investor, design partner, compliance, architecture, and generated canvas docs need lifecycle metadata: canonical, generated, historical, experimental, or archived.
4. **Dependabot and release maintenance are still too manual.** The new auto-merge workflow helps, but repo settings block it. A local/CI PR triage command should become the default operator tool.
5. **Safety invariants are spread across tests instead of being first-class.** Policy-before-signing, deny-by-default, idempotency, webhook verification, evidence append-only behavior, and no-secret logging should have one invariant suite.
6. **Live readiness is not separate enough from local readiness.** Local green tests do not prove `api.sardis.sh`, docs, auth, billing, checkout, and demo surfaces are healthy.
7. **Generated/static outputs are mixed with source.** Canvases and `llms` outputs need a generator contract and stale-output detection.
8. **Package release story is too broad for early users.** The priority should be a minimal install path and one convincing integration path, then expand outward.
9. **Open-core boundary needs enforcement.** Docs describe boundaries, but package naming, exports, and README structure should make it impossible to misunderstand what is OSS vs commercial.
10. **There is no single "repo cockpit."** A maintainer should be able to run one command and see PR queue, CI health, release gate state, stale docs, generated drift, and live endpoints.

## 150 Atomic Commits

### Track 1: Repo Cockpit And PR Automation

- [ ] Commit 1: Add `scripts/pr_maintenance.py` to summarize open PRs, repo auto-merge settings, merge states, check counts, and Dependabot rebase candidates.
- [ ] Commit 2: Add tests for PR classification: conflict, stale, waiting-on-checks, blocked-by-policy, ready-for-review.
- [ ] Commit 3: Add a GitHub Actions workflow that runs PR maintenance in report-only mode daily and uploads Markdown output as an artifact.
- [ ] Commit 4: Add `make`/package script aliases for `repo:prs`, `repo:prs:json`, and `repo:dependabot:rebase`.
- [ ] Commit 5: Add `.github/dependabot.yml` grouping cleanup so duplicate Python package bumps across package directories are reduced.
- [ ] Commit 6: Add a repo setting runbook explaining that `allow_auto_merge` and `delete_branch_on_merge` must be enabled for true Dependabot automation.
- [ ] Commit 7: Add a dry-run merge queue script that lists green Dependabot PRs without merging them.
- [ ] Commit 8: Add a guarded `--merge-green-dependabot` mode that refuses to run unless auto-merge is enabled and all required checks are green.
- [ ] Commit 9: Add stale PR SLA labels: `needs-rebase`, `conflict`, `waiting-on-checks`, `blocked-by-policy`.
- [ ] Commit 10: Add a weekly issue template generated from the PR maintenance report.

### Track 2: Production-Critical Spine

- [ ] Commit 11: Add `docs/architecture/production-critical-spine.md` defining the minimal Sardis path.
- [ ] Commit 12: Add a root README section that links to the spine before listing integrations.
- [ ] Commit 13: Add package ownership metadata for `sardis-api`, `sardis-core`, `sardis-ledger`, `sardis-compliance`, SDKs, MCP, checkout, and contracts.
- [ ] Commit 14: Add `docs/architecture/package-boundaries.md` with canonical, integration, experimental, generated, and archived categories.
- [ ] Commit 15: Add a check that every package has a category and owner.
- [ ] Commit 16: Mark framework integrations as adapters around the spine, not product centers.
- [ ] Commit 17: Add a single end-to-end diagram for mandate -> policy -> approval -> execution -> evidence.
- [ ] Commit 18: Add API route map generation for production-critical routers.
- [ ] Commit 19: Add a check that production-critical routes have tests.
- [ ] Commit 20: Add a "what we do not own" boundary doc for FIDES/OAPS/OSP overlap.

### Track 3: Safety Invariant Suite

- [ ] Commit 21: Add `tests/invariants/test_policy_before_execution.py`.
- [ ] Commit 22: Add invariant coverage for deny-by-default on missing policy.
- [ ] Commit 23: Add invariant coverage for no signing before approval.
- [ ] Commit 24: Add invariant coverage for idempotency-key preservation on retries.
- [ ] Commit 25: Add invariant coverage for replay rejection.
- [ ] Commit 26: Add invariant coverage for webhook signature verification.
- [ ] Commit 27: Add invariant coverage for append-only evidence behavior.
- [ ] Commit 28: Add invariant coverage for no secret/private-key logging.
- [ ] Commit 29: Add invariant coverage for merchant/vendor allow/deny decisions.
- [ ] Commit 30: Add invariant suite to CI as a named required gate.

### Track 4: Live Readiness Separation

- [ ] Commit 31: Add `scripts/live_surface_check.py` with explicit checks for API health, docs URL, landing, dashboard login, and checkout demo.
- [ ] Commit 32: Add `docs/operations/live-surface-runbook.md`.
- [ ] Commit 33: Add environment-safe redaction for live-surface outputs.
- [ ] Commit 34: Add CI workflow manual dispatch for live-surface checks.
- [ ] Commit 35: Add recorded evidence artifact format for live-surface checks.
- [ ] Commit 36: Add tests for live-surface JSON parsing and failure classification.
- [ ] Commit 37: Add status taxonomy: local green, staging green, production green, unknown.
- [ ] Commit 38: Add `docs/audits/evidence/live-surface-latest.json` generated from safe sample data.
- [ ] Commit 39: Add a launch checklist gate that refuses "production ready" if live surface is unknown.
- [ ] Commit 40: Add a short README badge/table for current verified surfaces.

### Track 5: Docs Provenance And Cleanup

- [ ] Commit 41: Add frontmatter/provenance schema for docs: canonical, generated, historical, draft, investor, runbook.
- [ ] Commit 42: Add `scripts/audit/docs_provenance_check.py`.
- [ ] Commit 43: Apply provenance to root launch/readiness docs.
- [ ] Commit 44: Apply provenance to `docs/design-partner`.
- [ ] Commit 45: Apply provenance to investor docs.
- [ ] Commit 46: Apply provenance to generated canvases.
- [ ] Commit 47: Add generated-output source mapping for `llms.txt` and canvases.
- [ ] Commit 48: Add stale generated artifact check.
- [ ] Commit 49: Archive or mark old duplicate pitch decks as historical.
- [ ] Commit 50: Add `docs/INDEX.md` as the canonical docs entrypoint.

### Track 6: Package Release Hygiene

- [ ] Commit 51: Add version consistency check across Python packages.
- [ ] Commit 52: Add version consistency check across npm packages.
- [ ] Commit 53: Add package README completeness check.
- [ ] Commit 54: Add package license/metadata check.
- [ ] Commit 55: Add dry-run publish matrix for canonical packages only.
- [ ] Commit 56: Add separate dry-run publish matrix for adapter packages.
- [ ] Commit 57: Add package deprecation/experimental marker support.
- [ ] Commit 58: Add a package release runbook.
- [ ] Commit 59: Add changelog generation for canonical packages.
- [ ] Commit 60: Add a release blocker if package categories are missing.

### Track 7: API Boundary Hardening

- [ ] Commit 61: Add route inventory tests for `packages/sardis-api`.
- [ ] Commit 62: Add auth middleware bypass tests for all sensitive routers.
- [ ] Commit 63: Add explicit unauthenticated route allowlist.
- [ ] Commit 64: Add request ID propagation tests.
- [ ] Commit 65: Add idempotency middleware contract tests.
- [ ] Commit 66: Add structured API error shape tests.
- [ ] Commit 67: Add OpenAPI generation check.
- [ ] Commit 68: Add OpenAPI drift artifact.
- [ ] Commit 69: Add examples that call only public documented routes.
- [ ] Commit 70: Add API route ownership table.

### Track 8: Evidence Ledger And Auditability

- [ ] Commit 71: Add evidence event schema doc.
- [ ] Commit 72: Add append-only store invariant tests.
- [ ] Commit 73: Add tamper-evidence hash chain tests.
- [ ] Commit 74: Add evidence export sample.
- [ ] Commit 75: Add evidence redaction rules.
- [ ] Commit 76: Add audit event taxonomy.
- [ ] Commit 77: Add reconciliation evidence fixture.
- [ ] Commit 78: Add audit trail docs for one complete payment flow.
- [ ] Commit 79: Add CLI command to print evidence for a test transaction.
- [ ] Commit 80: Add CI gate for evidence schema compatibility.

### Track 9: SDK Experience

- [ ] Commit 81: Add a single canonical Python SDK quickstart test.
- [ ] Commit 82: Add a single canonical JS SDK quickstart test.
- [ ] Commit 83: Add typed error mapping parity between Python and JS SDKs.
- [ ] Commit 84: Add SDK retry/idempotency examples.
- [ ] Commit 85: Add SDK no-network unit tests where possible.
- [ ] Commit 86: Add SDK contract tests against API fixture responses.
- [ ] Commit 87: Add docs that clarify which SDK is canonical.
- [ ] Commit 88: Add install-size/dependency notes.
- [ ] Commit 89: Add MCP quickstart that uses the same canonical flow.
- [ ] Commit 90: Add compatibility table for integrations.

### Track 10: Frontend And Demo Surfaces

- [ ] Commit 91: Add a demo inventory doc: landing, dashboard, checkout, canvas, API docs.
- [ ] Commit 92: Add Playwright smoke for landing first viewport.
- [ ] Commit 93: Add Playwright smoke for dashboard unauth/auth boundary.
- [ ] Commit 94: Add Playwright smoke for checkout demo.
- [ ] Commit 95: Remove stale generated frontend build artifacts from source control if any remain.
- [ ] Commit 96: Add generated artifact ignore rules.
- [ ] Commit 97: Add frontend env var validation.
- [ ] Commit 98: Add frontend health endpoint or static version marker.
- [ ] Commit 99: Add visual regression baseline for the canonical demo.
- [ ] Commit 100: Add demo runbook for a design partner call.

### Track 11: Dependency And Security Posture

- [ ] Commit 101: Add dependency risk categories: runtime-critical, dev-only, integration-only, experimental.
- [ ] Commit 102: Add dependency allowlist for payment/signing/auth packages.
- [ ] Commit 103: Add lockfile drift check.
- [ ] Commit 104: Add npm audit triage notes.
- [ ] Commit 105: Add Python dependency vulnerability triage notes.
- [ ] Commit 106: Add action pinning policy.
- [ ] Commit 107: Pin or document any unpinned GitHub Actions.
- [ ] Commit 108: Add secret-scan fixture allowlist tests.
- [ ] Commit 109: Add supply-chain scorecard runbook.
- [ ] Commit 110: Add package provenance/signing verification notes.

### Track 12: Contracts And Chain Boundary

- [ ] Commit 111: Add contracts responsibility doc: what contracts enforce vs API policy.
- [ ] Commit 112: Add forge invariant for mandate compliance.
- [ ] Commit 113: Add forge invariant for refund protocol.
- [ ] Commit 114: Add gas ceiling comments explaining thresholds.
- [ ] Commit 115: Add deployment manifest schema check.
- [ ] Commit 116: Add chain adapter fail-closed tests.
- [ ] Commit 117: Add nonce manager race-condition tests.
- [ ] Commit 118: Add live-chain conformance evidence schema.
- [ ] Commit 119: Add mainnet/testnet separation guard.
- [ ] Commit 120: Add chain simulator docs for demos.

### Track 13: Compliance And Provider Readiness

- [ ] Commit 121: Add provider capability schema.
- [ ] Commit 122: Add provider capability validation tests.
- [ ] Commit 123: Add compliance pack index.
- [ ] Commit 124: Add PCI/PAN boundary check.
- [ ] Commit 125: Add issuer compliance gate fixtures.
- [ ] Commit 126: Add provider live lane scorecard generator tests.
- [ ] Commit 127: Add dispute/refund runbook to canonical flow.
- [ ] Commit 128: Add provider outage drill fixture.
- [ ] Commit 129: Add reconciliation chaos fixture.
- [ ] Commit 130: Add design-partner readiness dashboard artifact.

### Track 14: Archive And Noise Reduction

- [ ] Commit 131: Add archive policy: archive before delete, preserve provenance.
- [ ] Commit 132: Move old outreach drafts into `docs/archive` or mark as draft.
- [ ] Commit 133: Move old investor HTML/PDF duplicates into historical grouping.
- [ ] Commit 134: Mark old canvases as generated/historical where applicable.
- [ ] Commit 135: Remove checked-in local build caches.
- [ ] Commit 136: Add CI check preventing `.tsbuildinfo`, `_astro`, `.next`, and similar generated outputs.
- [ ] Commit 137: Consolidate duplicate launch checklists into one index.
- [ ] Commit 138: Consolidate duplicate readiness scripts or document why each exists.
- [ ] Commit 139: Add `docs/archive/README.md`.
- [ ] Commit 140: Add cleanup report with before/after file counts.

### Track 15: Commercial Focus And OSS Signal

- [ ] Commit 141: Add `docs/product/design-partner-critical-path.md`.
- [ ] Commit 142: Add one canonical demo script for a technical buyer.
- [ ] Commit 143: Add one canonical OSS contribution list tied to MCP, x402, AP2, and SDK tooling.
- [ ] Commit 144: Add GitHub issues for high-signal external contributions.
- [ ] Commit 145: Add `CONTRIBUTING.md` focused on useful Sardis contributions.
- [ ] Commit 146: Add `SECURITY.md` with payment/security disclosure scope.
- [ ] Commit 147: Add `ROADMAP.md` with now/next/later tied to the production-critical spine.
- [ ] Commit 148: Add `docs/product/not-yet-production.md` for honest caveats.
- [ ] Commit 149: Add `docs/product/pricing-and-open-core-boundary.md`.
- [ ] Commit 150: Add a final repo health report comparing PR count, docs provenance coverage, package metadata coverage, and live-surface evidence before/after.

## First Implementation Slice

Start with Track 1 because it reduces operational drag immediately and is low risk:

- Add `scripts/pr_maintenance.py`.
- Add `tests/test_pr_maintenance.py`.
- Run `uv run pytest tests/test_pr_maintenance.py -q`.
- Run `python3 scripts/pr_maintenance.py --repo EfeDurmaz16/sardis --json`.
- Commit as `ops: add PR maintenance report command`.

## Verification Standard

Every commit must include one of:

- focused unit test,
- CI workflow syntax check,
- local command output,
- generated evidence artifact,
- or a documented manual smoke path.

Payment, signing, auth, webhook, policy, wallet, evidence, and compliance changes require tests that prove fail-closed behavior.
