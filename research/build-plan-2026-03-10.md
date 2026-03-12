# Sardis 4-6 Week Build Plan

Date: 2026-03-10
Prepared as: execution plan derived from product strategy and repo review

## A. Executive Summary

This plan is designed to make Sardis feel **real, trustworthy, and operable** for one design-partner workflow within 4 to 6 weeks.

The plan does not optimize for more breadth. It optimizes for:
- contract integrity
- operator trust
- faster pilot onboarding
- visible policy correctness
- durable failure handling

### Ship goal
By the end of this cycle, a design partner should be able to:
1. onboard to a controlled live lane
2. define and test a policy
3. run a transaction that may auto-approve or request approval
4. inspect evidence
5. recover from an exception
6. trust what the dashboard says

### What this cycle is explicitly not for
- more protocol breadth
- richer identity graph UI
- more chain surfaces
- broad consumer checkout expansion
- adding more admin pages before the existing ones are real

## B. Operating Assumptions

### Product assumption
The core wedge is governed AI payments for B2B workflows, not generic rail expansion.

### Team assumption
This plan assumes a small team or founder-led build. Each ticket includes a suggested owner role, but many can collapse into one person if needed.

Suggested roles:
- `FE`: frontend engineer
- `BE`: backend / platform engineer
- `FD`: founder or staff full-stack owner
- `SE`: solutions / implementation engineer
- `PD`: product / design owner

If the team is effectively one technical founder, the real owners are:
- `FD-primary`
- `SE-secondary` only where customer setup is involved

## C. Workstreams

### Workstream 1: Contract Truth
Goal:
- make the dashboard and API agree on routes, payloads, and shapes

Why first:
- broken trust UX kills the whole control-plane story

### Workstream 2: Policy Lifecycle
Goal:
- make policy authoring, testing, deployment, and rollback one coherent workflow

Why second:
- policy is the wedge and currently spread across too many surfaces

### Workstream 3: Operator Control Workflow
Goal:
- make approvals, evidence, and exceptions feel like one operational system

Why third:
- this is what design partners and enterprise evaluators will actually judge

### Workstream 4: Guided Live-Lane Onboarding
Goal:
- convert sandbox curiosity into controlled live usage

Why fourth:
- deployment burden is too high for current maturity

### Workstream 5: Cut / Hide / Simplify
Goal:
- remove visible product fiction

Why always:
- mock-heavy admin surfaces damage trust faster than missing features do

## D. Sequence Overview

### Week 1
- Contract truth sweep
- Hide or gate broken / mock trust pages
- Define one canonical workflow and one canonical entity model

### Week 2
- Policy lifecycle MVP
- Scenario testing
- Live-lane onboarding wizard skeleton

### Week 3
- Approval + evidence path end to end
- Evidence export MVP
- Exceptions API and UI persistence decisions

### Week 4
- Canonical control center MVP
- Durable exception center MVP
- Design-partner template pack

### Week 5
- Guided live-lane onboarding complete
- Trusted counterparty foundation
- QA, instrumentation, and docs cleanup

### Week 6
- Hardening
- operator walkthrough polish
- customer pilot validation
- cut list enforcement

## E. Ticket Backlog

## P0: Must Ship This Cycle

### T-001 Align approvals client and API routes
- Priority: `P0`
- Owner: `FE + BE`
- Problem:
  - dashboard deny uses `/reject`
  - API exposes `/deny`
  - list responses are object envelopes, UI assumes arrays
- Evidence:
  - [client.ts](/Users/efebarandurmaz/sardis/dashboard/src/api/client.ts#L738)
  - [approvals.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/approvals.py#L333)
  - [Approvals.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/Approvals.tsx#L78)
- Deliverable:
  - one correct typed approval contract across API client, hooks, and page
- Acceptance criteria:
  - approve works
  - deny works
  - pending list renders correctly
  - history list renders correctly
  - dashboard stats derive from real response shape
- Effort: `1-2 days`
- Dependency: none

### T-002 Align evidence client and API routes
- Priority: `P0`
- Owner: `FE + BE`
- Problem:
  - evidence API client points at routes that do not match the evidence router
- Evidence:
  - [client.ts](/Users/efebarandurmaz/sardis/dashboard/src/api/client.ts#L746)
  - [evidence.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/evidence.py#L81)
  - [evidence.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/evidence.py#L217)
- Deliverable:
  - typed client methods for transaction evidence and policy decision evidence using actual route structure
- Acceptance criteria:
  - transaction evidence lookup works from dashboard
  - policy decision list works
  - policy decision detail works
  - empty states are explicit and not misleading
- Effort: `1-2 days`
- Dependency: none

### T-003 Align simulation payloads and semantics
- Priority: `P0`
- Owner: `FE + BE`
- Problem:
  - dashboard sends `agent_id`
  - simulation API expects `sender_agent_id`
  - policy DSL simulate endpoint does not actually use the supplied definition
- Evidence:
  - [client.ts](/Users/efebarandurmaz/sardis/dashboard/src/api/client.ts#L763)
  - [simulation.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/simulation.py#L21)
  - [policy_simulation.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/policy_simulation.py#L150)
- Deliverable:
  - explicit distinction between:
    - live control-plane simulation
    - draft policy scenario test
- Acceptance criteria:
  - simulation uses correct payloads
  - policy scenario testing actually respects draft policy definitions
  - labels in UI make the difference obvious
- Effort: `2-3 days`
- Dependency: none

### T-004 Decide exceptions architecture and make it real
- Priority: `P0`
- Owner: `BE`
- Problem:
  - exceptions flow exists in client and UI
  - API uses in-memory engine
  - router is not visibly wired into app composition
- Evidence:
  - [client.ts](/Users/efebarandurmaz/sardis/dashboard/src/api/client.ts#L789)
  - [hooks/useApi.ts](/Users/efebarandurmaz/sardis/dashboard/src/hooks/useApi.ts#L360)
  - [Exceptions.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/Exceptions.tsx#L17)
  - [main.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/main.py#L94)
- Deliverable:
  - either fully wire exceptions with persistence
  - or hide the exceptions UI until durable implementation exists
- Acceptance criteria:
  - no dead-end exceptions UI remains
  - exception list and actions have real backing data
- Effort: `2-4 days`
- Dependency: T-001 and T-002 optional

### T-005 Gate or remove mock trust pages from the main nav
- Priority: `P0`
- Owner: `FD + PD`
- Problem:
  - several high-trust pages are mock and imply maturity that does not exist
- Evidence:
  - [AgentIdentity.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/AgentIdentity.tsx#L17)
  - [Guardrails.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/Guardrails.tsx#L18)
  - [ConfidenceRouter.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/ConfidenceRouter.tsx#L17)
  - [AuditAnchors.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/AuditAnchors.tsx#L17)
  - [GoalDrift.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/GoalDrift.tsx#L30)
- Deliverable:
  - feature-flagged nav
  - “coming soon” only in internal/demo mode, not in standard product mode
- Acceptance criteria:
  - public or design-partner-facing product only shows real workflows
- Effort: `0.5-1 day`
- Dependency: none

### T-006 Define canonical control workflow and entity glossary
- Priority: `P0`
- Owner: `FD + PD`
- Problem:
  - too many overlapping nouns: wallet, merchant, service, payee, policy simulation, approval workflow, evidence bundle
- Deliverable:
  - one internal source of truth for:
    - primary workflow
    - primary actor
    - primary entities
    - status model
- Acceptance criteria:
  - docs, dashboard labels, and API terminology all use the same entity names
- Effort: `1 day`
- Dependency: none

## P1: Should Ship This Cycle

### T-101 Policy lifecycle manager MVP
- Priority: `P1`
- Owner: `FD + FE`
- Problem:
  - parse, preview, apply, check, DSL compile, DSL simulate, and demo are fragmented
- Deliverable:
  - one policy page with:
    - natural language input
    - structured preview
    - scenario tests
    - deploy
    - rollback
- Acceptance criteria:
  - user can create a policy from scratch and safely test it
  - user can compare current live policy with draft
  - user can roll back to previous version
- Effort: `4-6 days`
- Dependency: T-003, T-006

### T-102 Guided live-lane onboarding wizard
- Priority: `P1`
- Owner: `FE + SE`
- Problem:
  - production deployment requires too many services and hidden prerequisites
- Evidence:
  - [PRODUCTION_DEPLOYMENT.md](/Users/efebarandurmaz/sardis/docs/PRODUCTION_DEPLOYMENT.md#L16)
- Deliverable:
  - staged onboarding flow:
    - sandbox ready
    - test integration ready
    - controlled live lane ready
  - provider and environment health checks
- Acceptance criteria:
  - partner can see what is missing and why
  - onboarding shows required vs optional integrations
  - onboarding links directly to the next safe step
- Effort: `4-5 days`
- Dependency: T-006

### T-103 Evidence export bundle MVP
- Priority: `P1`
- Owner: `BE + FE`
- Problem:
  - evidence exists, but not yet as a clean exportable artifact
- Deliverable:
  - export bundle containing:
    - policy decision
    - approval state
    - execution receipt
    - ledger artifacts
    - side effects
    - exception state if present
- Acceptance criteria:
  - one-click export from transaction detail
  - export clearly marks unavailable sections
  - bundle format is stable and shareable with auditors or partners
- Effort: `3-4 days`
- Dependency: T-002

### T-104 Canonical control center MVP
- Priority: `P1`
- Owner: `FE`
- Problem:
  - current operator flow is split across too many pages
- Deliverable:
  - one view that combines:
    - pending approvals
    - recent risky transactions
    - exceptions
    - evidence links
    - kill-switch status
- Acceptance criteria:
  - operator can action common trust events from one place
  - no duplicate “where do I click” decisions for common cases
- Effort: `4-5 days`
- Dependency: T-001, T-002, T-004, T-005

### T-105 Design-partner templates
- Priority: `P1`
- Owner: `SE + PD`
- Problem:
  - users still have to translate Sardis into their workflow manually
- Deliverable:
  - opinionated templates for:
    - procurement-style API purchases
    - travel / expense approval flow
    - A2A escrow / service payment
- Acceptance criteria:
  - each template includes policy defaults, approval defaults, and evidence expectations
- Effort: `2-3 days`
- Dependency: T-101

### T-106 Hide or merge duplicate simulation surfaces
- Priority: `P1`
- Owner: `FD + FE`
- Problem:
  - too many pages imply overlapping value
- Deliverable:
  - one primary simulation entry point
  - secondary flows only if clearly scoped to draft policy testing
- Acceptance criteria:
  - product has one obvious place to answer “what would happen if…”
- Effort: `1-2 days`
- Dependency: T-003, T-101

## P2: Nice If Time Allows

### T-201 Trusted counterparty foundation
- Priority: `P2`
- Owner: `BE + FE`
- Problem:
  - Sardis lacks a unified approved-vendor / payee / merchant / peer trust layer
- Deliverable:
  - minimal trusted counterparties model with:
    - status
    - policy linkage
    - approval requirement
    - basic metadata
- Acceptance criteria:
  - policy can reference a trusted counterparty set
  - operator can see whether a destination is approved or not
- Effort: `4-6 days`
- Dependency: T-006

### T-202 Approval routing configuration
- Priority: `P2`
- Owner: `BE + FE`
- Problem:
  - approvals exist, but admin configuration is still too implicit
- Deliverable:
  - configure quorum, urgency, distinct reviewers, and fallback reviewer groups
- Acceptance criteria:
  - no code change required to alter common approval rules
- Effort: `3-4 days`
- Dependency: T-001

### T-203 Live policy feedback loop
- Priority: `P2`
- Owner: `BE`
- Problem:
  - users need to know how policies are behaving in real use
- Deliverable:
  - policy outcome analytics:
    - allowed
    - denied
    - approval required
    - most common deny reasons
- Acceptance criteria:
  - operator can improve policy from observed behavior rather than guesswork
- Effort: `3 days`
- Dependency: T-101

## F. Week-by-Week Plan

## Week 1: Product Truth

### Goal
Make the visible product stop lying.

### Scope
- T-001
- T-002
- T-003
- T-005
- T-006

### Exit criteria
- dashboard/API contract mismatches fixed
- mock trust pages gated or removed from main flow
- one canonical workflow agreed

## Week 2: Policy Workflow

### Goal
Make policy creation and testing coherent.

### Scope
- T-101 begin
- T-106
- T-102 begin

### Exit criteria
- draft vs live policy distinction is explicit
- policy scenario testing works
- onboarding wizard shell exists

## Week 3: Operational Evidence

### Goal
Make approvals and evidence work like a real system.

### Scope
- T-101 finish
- T-103
- T-004 decide and start

### Exit criteria
- approval flow works end to end
- transaction evidence and policy decision evidence are accessible
- exception architecture decision is made and implemented or hidden

## Week 4: Operator Center

### Goal
Give operators one real place to work.

### Scope
- T-104
- T-004 finish
- T-102 continue

### Exit criteria
- operator can handle core review flow from one place
- exceptions are durable or intentionally absent

## Week 5: Pilot Conversion

### Goal
Reduce founder dependency during partner setup.

### Scope
- T-102 finish
- T-105
- T-201 if capacity remains

### Exit criteria
- onboarding supports a live-lane checklist
- at least one template maps directly to a pilot workflow

## Week 6: Hardening and Packaging

### Goal
Turn the work into a shippable pilot narrative.

### Scope
- QA regression
- documentation cleanup
- polish and instrumentation
- T-202 or T-203 only if cycle is green

### Exit criteria
- demo and live pilot use the same real workflow
- GTM can sell the actual product without caveats

## G. Suggested Ownership

## If there is a small team

### Founder / backend owner
- T-003
- T-004
- T-006
- T-101 backend
- T-103 backend

### Frontend owner
- T-001
- T-002
- T-005
- T-101 frontend
- T-102
- T-104

### Solutions / implementation owner
- T-102 content and readiness checks
- T-105 templates
- pilot validation

### Product / design owner
- T-006 terminology
- T-005 cut list
- T-104 operator information architecture

## If this is still mostly a solo-founder build

### Sequence for one person
1. T-001, T-002, T-003, T-005, T-006
2. T-101
3. T-102
4. T-004
5. T-103
6. T-104
7. T-105

Do not start T-201, T-202, or T-203 until the first six items are real.

## H. Success Metrics

### Product truth metrics
- zero known broken dashboard-to-API routes in the core workflow
- zero visible mock pages in the primary operator experience

### Activation metrics
- time from first login to first successful policy test
- time from first login to first controlled live transaction
- percentage of users who complete onboarding checklist

### Trust metrics
- approval action success rate
- evidence retrieval success rate
- exception action success rate
- number of transactions with exportable evidence bundles

### Pilot readiness metrics
- number of partner setups completed without founder intervention
- number of workflows using template packs
- median time to resolve an exception

## I. Cut List

These should be delayed, hidden, or explicitly moved out of the main cycle:
- richer FIDES trust graph UX
- deeper protocol expansion
- broad marketplace polish
- advanced multi-chain routing UX
- any new dashboard page that starts with mock data
- more card or checkout expansion unless required by a signed pilot

## J. Risks

### Risk 1: founder keeps adding breadth mid-cycle
- Severity: high
- Mitigation:
  - freeze this plan for 2 weeks at a time

### Risk 2: onboarding wizard becomes a settings dump
- Severity: medium
- Mitigation:
  - design as staged readiness, not generic configuration

### Risk 3: control center becomes a generic admin dashboard
- Severity: medium
- Mitigation:
  - only include actions tied to the canonical workflow

### Risk 4: exceptions remain half-real
- Severity: high
- Mitigation:
  - either persist them properly or remove them from user-facing product

## K. Final Recommendation

If you do only five things in the next 4 to 6 weeks, do these:
1. Fix contract and route mismatches
2. Hide mock trust pages
3. Ship one real policy lifecycle flow
4. Ship one real operator control center
5. Ship one guided live-lane onboarding path

That is the shortest path to making Sardis feel dramatically more complete without falling into feature bloat.

