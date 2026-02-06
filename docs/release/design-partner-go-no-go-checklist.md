# Design Partner Go/No-Go Checklist (Staging/Testnet)

Decision scope: paid design partner program on staging/testnet with no real-money movement.
Baseline date: **February 6, 2026**.
Decision mode: **Controlled Beta Launch** (design partner only).

## Decision Calendar

- `T0` (Kickoff readiness review): February 9, 2026
- `T1` (First go/no-go): February 16, 2026
- `T2` (Scale decision: 2nd cohort or hold): March 2, 2026

## Gate Checklist

| Gate | Pass Criteria | Evidence / Command | Owner | Current Status |
|---|---|---|---|---|
| G1. Python SDK release readiness | Version match + tests green + package checks green | `./scripts/check_python_release_readiness.sh` | Eng | ✅ Green |
| G2. MCP runnable baseline | `init` + `start` flows documented and CLI path implemented | `packages/sardis-mcp-server/src/cli.ts`, `packages/sardis-mcp-server/README.md` | Eng | ✅ Implemented |
| G3. TS/JS SDK verification | MCP/SDK tests and builds pass in CI (or local if network fixed) | `.github/workflows/ci.yml` jobs + package test/build logs | Eng | ✅ Green (waiver W-001) |
| G4. npm/PyPI release automation | Tag/dispatch release workflows present and version checks enforced | `.github/workflows/release-npm.yml`, `.github/workflows/release-python-sdk.yml` | Eng | ✅ Green |
| G5. Policy enforcement sanity | Limit deny + merchant deny + approval pending scenarios pass | targeted integration tests + audit logs with reason codes | Eng/QA | ✅ Green (waiver W-002) |
| G6. Protocol sanity (AP2/UCP/TAP/x402 paths used by partners) | Required protocol tests are green, negative cases tracked | protocol test reports in CI artifacts | Eng/QA | ✅ Green (waiver W-003) |
| G7. Audit traceability | Every payment decision has timestamp, agent, policy version, reason code | ledger/audit API checks and exported logs | Eng/QA | ✅ Green (waiver W-004) |
| G8. Partner onboarding readiness | Start-to-end onboarding flow documented and rehearsed once internally | `docs/release/design-partner-staging-readiness.md` + dry run notes | Founder/Eng | ✅ Green |
| G9. Commercial guardrails | Testnet-only language, no SLA/production commitment in partner docs | signed doc set + invoice/terms template | Founder | ✅ Green |
| G10. Incident fallback | Defined rollback and support escalation process for partner incidents | runbook sections + incident channel ownership | Founder/Eng | ✅ Green |

## Minimum Go Rule (for paid staging partners)

Go allowed only if:

1. G1, G2, G4 are ✅
2. G3 is either ✅ in CI or has an approved temporary waiver with date-bound fix plan
3. G5, G7 are at least ⚠️ with explicit known limits disclosed to partners
4. G9 has finalized customer-facing language that clearly states testnet/pre-prod constraints

If any of the above fails: **No-Go**, continue closed pilot preparation only.

## Waiver Register (Controlled Beta)

| Waiver ID | Gate | Condition | Expiry |
|---|---|---|---|
| W-001 | G3 | Local Node test/build blocked by network on current machine; CI remains source of truth | 2026-03-02 |
| W-002 | G5 | Approval/lifecycle scenarios accepted for controlled beta while expanding edge-case coverage | 2026-03-02 |
| W-003 | G6 | Protocol negative/conformance depth accepted for design partner stage only | 2026-03-02 |
| W-004 | G7 | Audit verification accepted for staging scope with weekly manual review | 2026-03-02 |

## Current Recommended Decision

- **Recommendation as of February 6, 2026: Go (controlled beta, 1–2 partners max)**  
  Conditions:
  - Use explicit “staging/testnet only” contract language
  - Publish known limitations before onboarding
  - Keep weekly go/no-go review cadence and close waiver items before scaling

## T0 Decision Record

- T0 final review file: `docs/release/design-partner-t0-review-2026-02-09.md`
- Effective launch mode: `Go` (controlled beta)
- Cohort size cap until waiver expiry: `max 2 partners`

## Weekly Review Template

- Date:
- Reviewer(s):
- Changed gate statuses:
- New blockers:
- Partner-impacting risks:
- Decision: `Go` / `Conditional Go` / `No-Go`
- Actions due before next review:
