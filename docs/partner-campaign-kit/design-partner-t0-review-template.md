# T0 Design Partner Readiness Review Template

Review date: `YYYY-MM-DD`  
Meeting owner: `Name`  
Attendees: `Name, Name`  
Decision scope: paid design partner program on staging/testnet only

## 1) Decision

- Final decision: `Go` / `Conditional Go` / `No-Go`
- Effective start date: `YYYY-MM-DD`
- First cohort size: `1` or `2`
- Pricing band: `$1.5k` or `$2k` monthly

## 2) Gate Review Snapshot

Use `docs/release/design-partner-go-no-go-checklist.md`.

- Gates reviewed: `G1 ... G10`
- Any non-green evidence: `Yes/No`
- If yes, accepted as launch waiver: `Yes/No`

## 3) Accepted Waivers (if any)

| Waiver ID | Gate | Why accepted | Expiry date | Owner |
|---|---|---|---|---|
| W-001 | G3 | Example: local Node network blocked, CI used as source of truth | YYYY-MM-DD | Eng |

## 4) Partner-Facing Constraints (must be explicit)

- Testnet/pre-prod only
- No real-money movement
- No production SLA
- Known limitations disclosed in writing
- Weekly review cadence and incident escalation path

## 5) Week-1 Action Plan

1. Onboard partner #1 and complete MCP `init` + `start`.
2. Run happy path + deny path + pending approval path.
3. Export first 24h audit trail and validate readability.
4. Collect partner feedback and convert to prioritized backlog.

## 6) Exit Criteria for Week-2 Continuation

- Integration completed without manual DB intervention
- Policy decisions are reproducible with clear reason codes
- No unresolved critical incident in first 7 days

## 7) Sign-off

- Founder sign-off: `Name / Date`
- Engineering sign-off: `Name / Date`
- Operations sign-off: `Name / Date`
