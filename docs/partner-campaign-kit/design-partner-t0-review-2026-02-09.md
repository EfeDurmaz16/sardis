# T0 Design Partner Readiness Review (Final)

Review date: **2026-02-09**  
Meeting owner: **Efe Baran Durmaz**  
Attendees: **Efe Baran Durmaz**  
Decision scope: paid design partner program on staging/testnet only

## 1) Decision

- Final decision: **Go**
- Effective start date: **2026-02-10**
- First cohort size: **1–2 partners**
- Pricing band: **$1.5k–$2k / month** (testnet, pre-prod)

## 2) Gate Review Snapshot

Source: `docs/release/design-partner-go-no-go-checklist.md`

- Gates reviewed: **G1–G10**
- Any non-green evidence: **Yes**
- Accepted as launch waiver: **Yes** (W-001, W-002, W-003, W-004)

## 3) Accepted Waivers

| Waiver ID | Gate | Why accepted | Expiry date | Owner |
|---|---|---|---|---|
| W-001 | G3 | Local Node test/build blocked by current machine DNS; CI will be source of truth | 2026-03-02 | Engineering |
| W-002 | G5 | Approval and edge-case depth acceptable for controlled beta while coverage expands | 2026-03-02 | Engineering/QA |
| W-003 | G6 | Protocol conformance depth accepted for design partner scope only | 2026-03-02 | Engineering/QA |
| W-004 | G7 | Staging audit checks accepted with weekly manual verification | 2026-03-02 | Engineering/QA |

## 4) Partner-Facing Constraints (explicit)

- Staging/testnet only
- No real-money movement
- No production SLA
- Known limitations are disclosed in writing before onboarding
- Weekly review cadence and incident escalation path are mandatory

## 5) Week-1 Action Plan

1. Open applications and shortlist first 5 candidate teams.
2. Send outbound invites using `design-partner/03-outbound-email-template.md`.
3. Publish X/Reddit announcement using `design-partner/02-x-reddit-announcements-tr-en.md`.
4. Onboard partner #1:
   - MCP `init` and `start`
   - 1 happy-path + 1 deny-path + 1 pending-approval test
5. Export first 24h audit trail and review reason-code quality.

## 6) Exit Criteria for Week-2 Continuation

- At least one partner fully integrated without manual DB intervention
- Policy decisions are reproducible with clear reason codes
- No unresolved critical incident in first 7 days

## 7) Sign-off

- Founder sign-off: **Efe Baran Durmaz / 2026-02-09**
- Engineering sign-off: **Efe Baran Durmaz / 2026-02-09**
- Operations sign-off: **Efe Baran Durmaz / 2026-02-09**
