# Sardis Pre-Launch Execution Checklist

Date: 2026-02-14  
Scope: README, SDK parity, security hardening, package readiness, landing/docs sync, release gates

## Phase 0: Claims + Docs Parity (Completed)

- [x] `P0-01` Add machine-verifiable claims checker (`scripts/audit/claims_check.py`)  
  Commit: `925c06f`
- [x] `P0-02` Fix README TypeScript quickstart to real SDK methods  
  Commit: `1fa76c3`
- [x] `P0-03` Normalize README MCP claim from 46 to 52 tools  
  Commit: `789ace9`
- [x] `P0-04` Align `examples/vercel_ai_payment.ts` with current SDK  
  Commit: `4abc864`
- [x] `P0-05` Sync landing SDK docs (Python + TypeScript) with actual APIs  
  Commit: `8ab562f`
- [x] `P0-06` Sweep docs/marketing/landing MCP count consistency (52 tools)  
  Commit: `c67105d`

## Phase 1: Package Metadata + Publishing Hygiene (Completed)

- [x] `P1-01` Align Python SDK runtime version constant with package metadata  
  Commit: `2a7e834`
- [x] `P1-02` Align TypeScript SDK runtime version constant with package metadata  
  Commit: `7be88c1`
- [x] `P1-03` Update `@sardis/ai-sdk` workspace dependency range to current SDK  
  Commit: `4c678a7`
- [x] `P1-04` Add missing LICENSE files across Python subpackages  
  Commit: `97cc17a`

## Phase 2: Security Hardening (Completed)

- [x] `P2-01` Enforce timestamped Onramper webhook signature verification with replay window  
  Commit: `55c5f30`
- [x] `P2-02` Update webhook tests for timestamp headers and stale timestamp rejection  
  Included in: `55c5f30`

## Phase 3: Landing/Changelog/Blog/Roadmap Sync (Completed)

- [x] `P3-01` Add v0.8.7 release entry to landing changelog  
- [x] `P3-02` Update roadmap current milestone with launch-hardening security item  
- [x] `P3-03` Add launch-hardening blog post and route  
- [x] `P3-04` Add post to blog listing  
  Commit: `2b08bb0`

## Phase 4: Release Gates (Completed)

- [x] Run non-strict release readiness gate (`scripts/check_release_readiness.sh`)  
  Result: PASS
- [x] Run strict readiness gate (`STRICT_MODE=1 bash ./scripts/check_release_readiness.sh`)  
  Result: PASS
- [x] Run claims checker baseline  
  Result: `52` MCP tools, `19` packages, `758/820` selected/total tests collected

## Phase 5: Checklist Infra (Completed)

- [x] `P5-02` Add `docs/design-partner/staging-hardening-checklist.json` and wire gate evidence
- [x] `P5-03` Run strict readiness (`STRICT_MODE=1`) with checklist gate enabled

## Phase 6: Remaining High-Priority Tasks (Open)

- [ ] `P6-01` Install and run full CVE tooling (`trufflehog`, `safety`, registry-enabled `pnpm audit`)
- [x] `P6-02` Add CI/runtime guard for Node engine mismatch (Node `22.x` pinned in workflows + root engines)
- [x] `P6-03` Stabilize `tests/test_e2e_full_flow.py` against current router/dependency behavior
- [ ] `P6-04` Capture evidence links for investor-facing claims (tests/chains/protocols/package counts)

## Suggested Commit Order for Open Tasks

1. `chore(security): enable full cve and secret scanning gates`
2. `docs(evidence): add investor-proof appendix for public claims`
