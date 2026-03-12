# Sardis Product Strategy and Feature Prioritization

Date: 2026-03-10
Prepared as: product strategy, workflow friction analysis, and feature roadmap memo

## A. Executive Summary

### Bottom line
- Sardis already has more product surface than most early companies in the category. The problem is not idea scarcity. The problem is workflow completion and product truth.
- The product is strongest where it acts as a deterministic control plane: policy enforcement, approvals, simulation, audit evidence, fail-closed execution, and operator controls.
- The product is weakest where a real operator needs one coherent path from setup to trusted live usage. Several high-value surfaces are still mock, partially wired, or mismatched between dashboard and API.
- The next roadmap should optimize for one thing: make Sardis feel operationally trustworthy for one narrow workflow and one real buyer, instead of continuing to broaden rails and protocol surfaces.
- The single most important product move now is to build a complete operator workflow for **policy -> simulation -> approval -> execution -> evidence -> exception recovery**.

### Product maturity call
- Stage: pre-PMF to early design-partner stage
- Best product objective now: reduce trust friction and shorten time-to-first-controlled-live-lane
- Wrong objective now: more protocol breadth, more dashboards, or more speculative identity surfaces

## B. Product Understanding Report

### What the product actually is
Sardis is a trust and control layer between AI-agent intent and payment execution. The real product is not the wallet itself and not the rail itself. The real product is the deterministic decision boundary that decides whether money should move, under what policy, with which approvals, with which evidence, and with what fallback.

Direct evidence:
- README positions Sardis around trust, policy, and fail-closed execution rather than generic payment APIs. [README.md](/Users/efebarandurmaz/sardis/README.md#L4)
- The maturity table shows the highest-confidence surfaces are policy, attestation, AP2 verification, and pre-execution pipeline, while checkout, x402, cards, and multi-chain are behind them in maturity. [README.md](/Users/efebarandurmaz/sardis/README.md#L69)
- The architecture centers every payment on a single `PaymentOrchestrator` and `PreExecutionPipeline`. [README.md](/Users/efebarandurmaz/sardis/README.md#L178)

Inference:
- Sardis should be optimized as an operator-grade control plane for agentic spend and execution, not as a broad “payment OS” in product priorities.

Confidence: high

### What it is not
- Not yet a fully complete multi-rail global payment platform
- Not yet a mature enterprise admin system across all operator surfaces
- Not yet a finished identity or trust-network platform
- Not yet a polished self-serve developer product despite strong SDK distribution signals

### Core user personas
1. Platform / infra engineer building agentic spend or payment workflows
2. AI or ops lead trying to introduce autonomous payments without losing control
3. Finance / risk / compliance stakeholder who needs approvals, evidence, and recoverability
4. Design partner product team experimenting with agent checkout, cards, or A2A flows

### Core user flows
1. Developer flow
   - Discover Sardis through SDK, docs, or playground
   - Create agent and wallet
   - Define or parse policy
   - Simulate a transaction
   - Run a live or sandbox payment
   - Read result and adjust policy

2. Operator flow
   - Review pending approvals and exceptions
   - Inspect evidence bundle for completed or denied transaction
   - Trigger kill switch or guardrail action if needed
   - Export audit evidence or support artifacts

3. Merchant / service flow
   - Register merchant or service
   - Accept agent payments through checkout, API, or marketplace
   - Reconcile settlements and webhooks

### Current strengths
- Deterministic policy and control semantics
- Rich technical architecture and broad integration surface
- Fail-closed posture
- Evidence, attestation, ledger, and reconciliation thinking
- Strong simulation and approval concepts
- Good developer acquisition surfaces: SDKs, integrations, playground

### Current weaknesses
- Operator workflow fragmentation
- Partial dashboard/API wiring on critical trust surfaces
- Heavy onboarding and deployment burden
- Too many high-concept admin pages are still mock or placeholder
- Merchant / payee / counterparty setup is underdeveloped relative to enterprise trust needs
- Too much category breadth competes with the main wedge

### Product maturity assessment

| Area | Assessment | Why |
|---|---|---|
| Core control plane | Strongest area | Policy, attestation, orchestration, ledger, fail-closed defaults are real and central |
| Sandbox / demo acquisition | Good | Playground and demo flows exist and map to the story well |
| Operator console | Uneven | Some pages use live hooks, others remain mock or mismatched |
| Approval workflow | Conceptually strong, operationally incomplete | API exists, but dashboard shape and route mismatches degrade trust |
| Evidence / audit UX | Important and differentiated, but incomplete | Evidence router exists, but client routing is inconsistent |
| Identity / trust network | Early | High-concept pages still mock or placeholder |
| Cards / checkout / fiat expansion | Valuable but not ready to drive roadmap | Pilot or partner-dependent in product truth |

## C. Workflow Friction Analysis

### Friction 1: The “trust workflow” is broken across surfaces

What the friction is:
- The highest-value operator workflow is fragmented across policies, simulation, approvals, evidence, kill switch, and exceptions.
- Some of those surfaces are real, but the dashboard and client wiring is inconsistent enough that the operator journey cannot be trusted as a coherent system.

Who feels it:
- Design partners
- Technical operators
- Enterprise buyers doing diligence

When it happens:
- During pilot evaluation
- During incident review
- During approval handling
- During audit or support requests

Why it matters:
- Sardis wins only if users believe it is safer and more observable than stitching rails directly.
- If the operator experience is inconsistent, the whole trust story weakens.

Direct evidence:
- `ApprovalsPage` assumes arrays, but the approvals API returns object envelopes with `approvals`, `total`, `limit`, and `offset`. [dashboard/src/pages/Approvals.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/Approvals.tsx#L78), [packages/sardis-api/src/sardis_api/routers/approvals.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/approvals.py#L398)
- The dashboard deny action calls `/reject`, while the approval API exposes `/deny` for approval records. [dashboard/src/api/client.ts](/Users/efebarandurmaz/sardis/dashboard/src/api/client.ts#L738), [packages/sardis-api/src/sardis_api/routers/approvals.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/approvals.py#L333)
- Evidence client paths do not match the evidence router paths. [dashboard/src/api/client.ts](/Users/efebarandurmaz/sardis/dashboard/src/api/client.ts#L746), [packages/sardis-api/src/sardis_api/routers/evidence.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/evidence.py#L81), [packages/sardis-api/src/sardis_api/routers/evidence.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/evidence.py#L217)
- Simulation client sends `agent_id`, but the simulation API expects `sender_agent_id`. [dashboard/src/api/client.ts](/Users/efebarandurmaz/sardis/dashboard/src/api/client.ts#L763), [packages/sardis-api/src/sardis_api/routers/simulation.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/simulation.py#L21)

Inference:
- The highest-leverage product work is not a new feature. It is a workflow completion and contract integrity project.

Severity:
- Very high

Impact:
- Blocks adoption, trust, and expansion

Confidence:
- High

### Friction 2: Core admin pages over-promise product maturity

What the friction is:
- Several pages that support the strongest narrative are still mock or placeholder.

Who feels it:
- Enterprise evaluators
- Design partners
- Internal GTM

When it happens:
- During product walkthroughs
- During diligence
- During operator onboarding

Why it matters:
- These pages map directly to Sardis’ moat narrative: guardrails, confidence routing, identity, audit anchors, goal drift.
- If they are mock, the product feels more aspirational than operational.

Direct evidence:
- Agent identity page uses mock data and has implementation-pending forms. [dashboard/src/pages/AgentIdentity.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/AgentIdentity.tsx#L17), [dashboard/src/pages/AgentIdentity.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/AgentIdentity.tsx#L503)
- Guardrails page uses mock data. [dashboard/src/pages/Guardrails.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/Guardrails.tsx#L18)
- Confidence router page uses mock data. [dashboard/src/pages/ConfidenceRouter.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/ConfidenceRouter.tsx#L17)
- Audit anchors page uses mock data. [dashboard/src/pages/AuditAnchors.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/AuditAnchors.tsx#L17)
- Goal drift page uses mock data. [dashboard/src/pages/GoalDrift.tsx](/Users/efebarandurmaz/sardis/dashboard/src/pages/GoalDrift.tsx#L30)

Inference:
- Sardis should reduce the number of “headline” pages and fully operationalize a smaller set.

Severity:
- High

Impact:
- Trust, conversion, enterprise readiness

Confidence:
- High

### Friction 3: Policy simulation is confusing and partially misleading

What the friction is:
- Sardis has multiple policy-related surfaces: natural-language parse, preview/apply/check, DSL compile/validate/simulate, simulation API, dashboard playground, and demo.
- The distinction between “simulate the live control plane” and “simulate this proposed policy definition” is not clean enough.

Who feels it:
- Developers
- Operators trying to validate policies before rollout

When it happens:
- Onboarding
- Policy creation
- Pre-launch testing

Why it matters:
- Policy is the wedge. If policy authoring and validation are confusing, activation suffers.

Direct evidence:
- `policy_simulation.py` advertises simulation against a provided policy definition, but the implementation builds a generic `ExecutionIntent` and never uses `body.definition`. [packages/sardis-api/src/sardis_api/routers/policy_simulation.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/policy_simulation.py#L150)
- The simulation API separately dry-runs the control plane, which is conceptually different. [packages/sardis-api/src/sardis_api/routers/simulation.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/simulation.py#L44)

Inference:
- Sardis needs one canonical policy authoring and validation flow with explicit modes:
  - parse policy
  - test against hypothetical scenarios
  - compare against live policy
  - promote to production

Severity:
- High

Impact:
- Activation and trust

Confidence:
- High

### Friction 4: Onboarding from sandbox to production is too heavy

What the friction is:
- Real production deployment requires many third-party services, environment variables, webhooks, and security setup steps.

Who feels it:
- Developers
- Solutions engineers
- Design partners

When it happens:
- First implementation
- Pilot launch
- Production hardening

Why it matters:
- Sardis may get installs and demos, but lose teams before they reach live usage.

Direct evidence:
- Production deployment guide requires GCP, Neon, Upstash, Alchemy, Turnkey, KYC, AML, onramp, OAuth, contracts, migrations, and multiple production env vars. [docs/PRODUCTION_DEPLOYMENT.md](/Users/efebarandurmaz/sardis/docs/PRODUCTION_DEPLOYMENT.md#L16)

Inference:
- The missing feature is a guided onboarding ladder, not another rail.

Severity:
- High

Impact:
- Activation and pilot conversion

Confidence:
- High

### Friction 5: Counterparty setup is underdeveloped for real business workflows

What the friction is:
- Safe money movement in business workflows usually starts with a trusted counterparty or vendor setup flow, not only raw destination entry.

Who feels it:
- Procurement-style buyers
- Enterprise operators
- A2A partners

When it happens:
- Merchant registration
- Vendor approval
- Payee reuse
- Service discovery

Why it matters:
- Competitors and adjacent products make payees, vendors, and service directories explicit. Sardis has some merchant and marketplace primitives, but the trust workflow around them is not the main operator journey yet.

Direct evidence:
- Merchant APIs cover merchant creation, bank account setup, and checkout links, but not a richer vendor / payee review workflow. [packages/sardis-api/src/sardis_api/routers/merchants.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/merchants.py#L1)
- Marketplace supports service discovery and offers, but is still a separate surface rather than a unified trusted counterparty model. [packages/sardis-api/src/sardis_api/routers/marketplace.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/marketplace.py#L1)

Inference:
- Sardis needs a unified trusted counterparties layer: approved merchants, approved payees, approved A2A peers, and reusable trust evidence.

Severity:
- Medium-high

Impact:
- Activation, trust, enterprise adoption

Confidence:
- Medium-high

### Friction 6: Exception handling exists conceptually, but operational recovery is weak

What the friction is:
- Exceptions matter enormously in trust products, but the API appears stateful and in-memory, and the route is not clearly integrated into the main app.

Who feels it:
- Operators
- Support
- Finance / audit stakeholders

When it happens:
- Failed payment recovery
- Incident review
- Live pilot operations

Why it matters:
- A payment control product is judged by failure handling, not only successful flow demos.

Direct evidence:
- Exceptions API uses a shared in-memory workflow engine. [packages/sardis-api/src/sardis_api/routers/exceptions.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/exceptions.py#L23)
- The dashboard has exception hooks and pages, but the router is not visibly included in `main.py`. [dashboard/src/hooks/useApi.ts](/Users/efebarandurmaz/sardis/dashboard/src/hooks/useApi.ts#L360), [packages/sardis-api/src/sardis_api/main.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/main.py)

Inference:
- Sardis is missing a durable exception center tied to retries, approvals, fallbacks, and evidence.

Severity:
- Medium-high

Impact:
- Retention, trust, enterprise hardening

Confidence:
- Medium-high

## D. Candidate Feature Map

### 1. Canonical Control Center
- Type: core product gap / enterprise trust feature / retention feature
- One-line description: unified operator workflow for policy decisions, pending approvals, transaction evidence, kill-switch actions, and exceptions in one timeline
- Problem solved: today the trust workflow is fragmented and partly inconsistent
- User: platform operator, AI ops lead, finance/risk reviewer
- Workflow improved: review and manage real transactions end to end
- Why it matters: this is Sardis’ product truth
- Likely impact: very high
- Likely complexity: medium-high
- Risks: could become overbuilt if it tries to cover every future surface at once
- Confidence: high

### 2. Policy Lifecycle Manager
- Type: core product gap / UX improvement / differentiation feature
- One-line description: versioned policy authoring with parse, scenario tests, diff, validation, rollout, and rollback
- Problem solved: policy creation and policy simulation are split across multiple surfaces with unclear semantics
- User: developer, operator, solutions engineer
- Workflow improved: author -> test -> approve -> deploy -> monitor policy changes
- Why it matters: policy is the wedge
- Likely impact: very high
- Likely complexity: medium
- Risks: avoid turning it into a generic no-code rules engine too early
- Confidence: high

### 3. Guided Live-Lane Onboarding
- Type: UX improvement / activation feature / internal ops feature
- One-line description: step-by-step environment and partner readiness wizard from sandbox to controlled production lane
- Problem solved: production onboarding is too heavy and distributed across docs
- User: developer, solutions engineer, design partner
- Workflow improved: setup, credentials, health checks, pilot readiness
- Why it matters: converts installs into real usage
- Likely impact: very high
- Likely complexity: medium
- Risks: requires careful environment modeling and clear “not ready” states
- Confidence: high

### 4. Trusted Counterparties
- Type: core product gap / enterprise trust feature / expansion feature
- One-line description: unified model for approved vendors, merchants, payees, and A2A peers with policy linkage and evidence
- Problem solved: safe payment systems need trusted payee onboarding, not just destination strings
- User: ops, procurement-style buyers, platform teams
- Workflow improved: who can the agent pay and under what trust conditions
- Why it matters: makes Sardis safer and more business-legible
- Likely impact: high
- Likely complexity: medium-high
- Risks: could sprawl into full procurement suite if not scoped tightly
- Confidence: medium-high

### 5. Durable Exception Center
- Type: retention feature / enterprise trust feature / internal ops feature
- One-line description: persistent exception queue with root cause, retry policy, escalation, fallback rail, and linked evidence
- Problem solved: failure handling is not yet strong enough to make the product feel complete
- User: operators, support, finance
- Workflow improved: failed transaction recovery
- Why it matters: live trust products are judged by failure recovery
- Likely impact: high
- Likely complexity: medium
- Risks: can turn into generic ticketing if not tightly coupled to execution flows
- Confidence: high

### 6. Reliability Scorecards and SLO Surface
- Type: enterprise trust feature / differentiation feature
- One-line description: productized provider and rail reliability views tied to routing and incident posture
- Problem solved: operator confidence depends on knowing whether a rail or provider is healthy
- User: operators, enterprise buyers
- Workflow improved: routing confidence and incident decisions
- Why it matters: fits Sardis’ “observable” positioning
- Likely impact: medium-high
- Likely complexity: medium
- Risks: limited value if data quality is thin
- Confidence: medium-high

### 7. Evidence Export Bundles
- Type: enterprise trust feature / monetization feature
- One-line description: one-click export of policy, approvals, receipt, ledger, webhook, and exception artifacts for a transaction or incident
- Problem solved: audit proof exists conceptually but needs a finished buyer-facing surface
- User: enterprise operator, compliance reviewer, support
- Workflow improved: diligence, dispute, incident review
- Why it matters: converts technical depth into customer-visible trust
- Likely impact: high
- Likely complexity: medium
- Risks: must be precise and tamper-evident
- Confidence: high

### 8. Approval Routing and SLA Configuration
- Type: UX improvement / enterprise trust feature
- One-line description: configure approver groups, quorum, urgency routing, and escalation timelines in a usable admin flow
- Problem solved: approval infrastructure exists, but operator configuration is not yet a polished product
- User: ops lead, finance, admin
- Workflow improved: human-in-the-loop governance
- Why it matters: approval is one of the clearest reasons to buy Sardis
- Likely impact: high
- Likely complexity: medium
- Risks: role model and org model can become complex quickly
- Confidence: medium-high

### 9. Live Policy Outcome Feedback
- Type: retention feature / UX improvement
- One-line description: show how often policies block, approve, or escalate, and recommend edits based on real activity
- Problem solved: users need feedback loops to refine policies
- User: developer, operator
- Workflow improved: policy tuning after deployment
- Why it matters: improves time-to-confidence and retention
- Likely impact: medium-high
- Likely complexity: medium
- Risks: recommendations must remain deterministic and explainable
- Confidence: high

### 10. Design Partner Templates
- Type: activation feature / internal ops feature
- One-line description: packaged templates for procurement, travel/expense, agent API purchases, and A2A escrow pilots
- Problem solved: too much user effort is spent translating Sardis into their workflow
- User: solutions engineer, design partner, founder-led sales
- Workflow improved: first live use case setup
- Why it matters: helps convert curiosity into scoped pilots
- Likely impact: high
- Likely complexity: low-medium
- Risks: should stay opinionated and narrow
- Confidence: high

### 11. Unified Developer Quickstart
- Type: UX improvement / activation feature
- One-line description: one quickstart path that uses the same entities, payload shapes, and terminology across SDKs, dashboard, and API
- Problem solved: too many surfaces and nouns raise cognitive load
- User: developer
- Workflow improved: first 15 minutes
- Why it matters: installs only matter if activation works
- Likely impact: high
- Likely complexity: low-medium
- Risks: documentation-only changes will not be enough without contract cleanup
- Confidence: high

### 12. Merchant / Service Trust Profiles
- Type: differentiation feature / trust feature
- One-line description: store proof, policy compatibility, settlement preference, and recent reliability for merchants and A2A services
- Problem solved: users need more context before allowing autonomous payments
- User: operators, procurement-style evaluators
- Workflow improved: payee approval and policy scoping
- Why it matters: bridges merchant, service discovery, and policy trust
- Likely impact: medium-high
- Likely complexity: medium
- Risks: requires careful scope
- Confidence: medium

### 13. Hosted Secure Checkout Hardening
- Type: expansion feature / enterprise trust feature
- One-line description: finish the secure embedded checkout path with approvals, evidence exports, and incident controls
- Problem solved: current checkout value is real but still pilot-grade
- User: design partners, merchants
- Workflow improved: controlled browser or card-based execution
- Why it matters: strategically valuable, but not first priority
- Likely impact: medium-high
- Likely complexity: high
- Risks: PCI and provider dependencies
- Confidence: medium

### 14. Cross-Rail Fallback Rules
- Type: differentiation feature / trust feature
- One-line description: operator-defined fallback behavior when a preferred rail fails or becomes unsafe
- Problem solved: control planes need deterministic degraded modes
- User: operator, enterprise buyer
- Workflow improved: incident-time continuity
- Why it matters: strong fit with Sardis narrative
- Likely impact: medium
- Likely complexity: high
- Risks: can explode in complexity without clear first rail pairs
- Confidence: medium

### 15. More Protocol and Trust-Graph Surfaces
- Type: expansion feature
- One-line description: more work on FIDES, UCP MCP transport, wider protocol support, and richer identity graph UI
- Problem solved: future ecosystem breadth
- User: future ecosystem partners
- Workflow improved: not core for current buyers
- Why it matters: long-term strategic optionality
- Likely impact: low now
- Likely complexity: high
- Risks: distracts from the wedge
- Confidence: high

## E. Competitor and Adjacent Feature Analysis

### Direct competitors

#### Payman
What they do well:
- Explicit user-facing flows for wallets, payees, policies, approvals, playground, and AI-agent payment tutorials
- Cleaner product mental model around “who gets paid” and “who approves”

Evidence:
- Payman docs include dashboard sections for wallets, payees, approval requests, and policies. https://docs.paymanai.com/overview/introduction
- Policies are framed explicitly as a “financial firewall” with built-in system policies and approval thresholds. https://docs.paymanai.com/dashboard-guide/policies

What matters:
- Payees are explicit, not implicit
- Approval and policy are visible end-user concepts
- Invite-only onboarding and KYC are part of the flow

What not to copy blindly:
- Sardis should not reduce itself to a narrower wallet-and-payee tool
- Payman’s breadth is simpler because its category framing is narrower

Takeaway:
- Payees and policy UX are now table stakes for serious agent payment products

#### Skyfire
What they do well:
- Makes trust legible through verified sellers, service discovery, tokenized pay flows, and buyer onboarding
- Productizes service discovery and transaction trust instead of keeping them as hidden primitives

Evidence:
- Skyfire docs expose a searchable directory, verified sellers, token creation flows, and a verified service guarantee. https://docs.skyfire.xyz/docs/service-discovery, https://docs.skyfire.xyz/docs/verified-service-guarantee

What matters:
- Trusted counterparty discovery
- Clear token/payment semantics
- Buyer onboarding and API key creation are explicit product steps

What not to copy blindly:
- The guarantee layer is specific to Skyfire’s marketplace and token model
- Sardis should copy the operator clarity, not the exact market structure

Takeaway:
- Directory, verified counterparties, and dispute posture make trust tangible

#### Natural
What they do well:
- Broad and ambitious market framing around payments between agents, businesses, and consumers
- Public signals show investment in agent identity, observability, and risk/credit

Evidence:
- Homepage and careers reference agent identity & observability and risk & credit roles. https://www.natural.co/
- Memo frames the opportunity around closing the loop on payments in business workflows. https://www.natural.co/blog/agentic-payments-memo

What matters:
- The market is converging on identity + observability + risk as core features

What not to copy blindly:
- Broad rails-first ambition without tight workflow focus

Takeaway:
- Observability and risk are strategic differentiators, but Sardis should attach them to one wedge workflow first

### Adjacent competitors

#### Stripe Issuing
What they do well:
- Real-time authorizations, spending controls, virtual cards, physical cards, digital wallet support, and clear card lifecycle management

Evidence:
- Official docs cover issuing, spending controls, virtual cards, and digital wallet support. https://docs.stripe.com/issuing, https://docs.stripe.com/issuing/controls/spending-controls, https://docs.stripe.com/issuing/cards/virtual

What matters:
- Merchant/category/country controls are table stakes on the card layer
- Card lifecycle and secure display flows matter

What not to copy blindly:
- Sardis should not become a generic card program manager

Takeaway:
- Sardis must orchestrate card controls into its trust workflow, not try to out-build Stripe on card operations

#### Ramp
What they do well:
- End-to-end approval workflows, vendor onboarding, purchase-order-linked virtual cards, and reconciliation-friendly flows

Evidence:
- Ramp support docs show vendor approvals, vendor onboarding inside approval workflows, and virtual cards on POs. https://support.ramp.com/hc/en-us/articles/31702539953171-Vendor-Approvals, https://support.ramp.com/hc/en-us/articles/36171535964563-Vendor-Onboarding-in-Procurement, https://support.ramp.com/hc/en-us/articles/47229197248787-Virtual-Cards-on-Purchase-Orders

What matters:
- New vendor approval should be linked to payment approval
- Virtual cards become more useful when tied to a real upstream workflow

What not to copy blindly:
- Full procurement suite scope

Takeaway:
- Sardis should borrow the logic of “counterparty approval is part of spend approval”

#### Zip
What they do well:
- Intake, workflow routing, vendor management, visibility, and procurement orchestration from request to pay

Evidence:
- Zip platform pages stress intake management, workflow engine, vendor management, spend insights, and AI-powered orchestration. https://ziphq.com/platform-overview, https://ziphq.com/blog/intake-management, https://ziphq.com/

What matters:
- Users need one front door
- Routing and visibility beat scattered admin surfaces

What not to copy blindly:
- Full source-to-pay platform ambition

Takeaway:
- Sardis needs a single front door for risky financial actions, not a scattered admin menu

#### Paid
What they do well:
- Clear signal tracking, billing visibility, reporting, and value receipts for AI workflows

Evidence:
- Paid docs emphasize signal tracking, flexible billing, invoice generation, revenue ops dashboards, and value receipts. https://docs.paid.ai/documentation/introduction/how-paid-streamlines-billing-for-ai-agents, https://paid.ai/product/billing

What matters:
- Usage and outcome visibility make abstract AI systems legible

What not to copy blindly:
- Full billing and revenue ops scope

Takeaway:
- Sardis can productize “value receipts” and evidence receipts for trust, not only billing

### Table-stakes features now
- Clear payee / merchant / service setup
- Policy authoring with templates and approval thresholds
- Human approval workflow
- Simulation / testing before live execution
- Webhooks and transaction visibility
- Transaction history and evidence
- Reliable onboarding path from test to live

### Strategic differentiators
- Deterministic policy lifecycle and explainability
- Unified operator control center across rails
- Evidence exports with policy, approvals, and audit chain
- Counterparty trust + policy linkage
- Exception recovery and fallback under one control plane

### Features that matter later
- Rich trust-graph UI
- Broad protocol expansion beyond current commercial wedge
- More advanced multi-chain and consumer-shopping surfaces
- Broad marketplace and rating features

### Features that are likely noise right now
- Additional decorative dashboard sections without live data
- More protocol names in the UI
- More chain support before live operator flows are complete
- High-concept identity or reputation surfaces without operational use

## F. Prioritized Feature Table

| Feature | Bucket | User Impact | Business Impact | Strategic Importance | Complexity | Confidence | PMF Relevance |
|---|---|---:|---:|---:|---:|---:|---:|
| Canonical Control Center | Build now | 10 | 10 | 10 | 7 | 9 | 10 |
| Policy Lifecycle Manager | Build now | 10 | 9 | 10 | 6 | 9 | 10 |
| Guided Live-Lane Onboarding | Build now | 9 | 10 | 9 | 6 | 9 | 10 |
| Durable Exception Center | Build now | 8 | 9 | 9 | 6 | 8 | 9 |
| Evidence Export Bundles | Build now | 8 | 9 | 9 | 5 | 9 | 9 |
| Trusted Counterparties | Build soon | 9 | 8 | 9 | 7 | 7 | 9 |
| Approval Routing and SLA Config | Build soon | 8 | 8 | 8 | 6 | 8 | 8 |
| Live Policy Outcome Feedback | Build soon | 8 | 8 | 8 | 5 | 8 | 8 |
| Design Partner Templates | Build soon | 8 | 8 | 7 | 4 | 9 | 8 |
| Unified Developer Quickstart | Build soon | 8 | 7 | 7 | 4 | 9 | 8 |
| Reliability Scorecards and SLO Surface | Build later | 7 | 7 | 8 | 6 | 7 | 7 |
| Merchant / Service Trust Profiles | Build later | 7 | 7 | 8 | 6 | 6 | 7 |
| Hosted Secure Checkout Hardening | Build later | 7 | 8 | 8 | 8 | 6 | 6 |
| Cross-Rail Fallback Rules | Do not build yet | 6 | 7 | 8 | 8 | 6 | 6 |
| More Protocol and Trust-Graph Surfaces | Do not build | 3 | 4 | 5 | 8 | 8 | 3 |

## G. Recommended Roadmap

### Next 2 to 4 weeks

#### 1. Contract Integrity Sweep
What gets built:
- Fix dashboard/API mismatches for approvals, evidence, simulation, and approval list shapes
- Remove or hide broken or misleading buttons until live paths are functional

Why now:
- This is the highest-trust leverage work in the product

Dependencies:
- Frontend and API contract alignment

Expected user impact:
- The product feels less fake and more dependable immediately

Expected business impact:
- Better demos, better design-partner confidence, better internal product truth

Success:
- Approval actions work end to end
- Evidence views resolve real transactions
- Simulation uses the correct payloads and returns useful output

#### 2. Single “Go Live Safely” Onboarding Flow
What gets built:
- Guided setup wizard for sandbox, test, and controlled live mode
- Health checks for required credentials and providers
- Visible readiness gates

Why now:
- Deployment burden is currently too high for the likely stage of buyers

Dependencies:
- Existing health and deployment checks

Expected user impact:
- Reduced setup confusion and lower drop-off

Expected business impact:
- Higher pilot conversion from SDK installs and demos

Success:
- One partner can follow the flow without founder hand-holding

#### 3. Policy Lifecycle v1
What gets built:
- Policy parse, preview, scenario test, apply, and rollback in one coherent UI
- Version history and diffs

Why now:
- Policy is the wedge and current flows are too fragmented

Dependencies:
- Existing parse/apply/check APIs, plus cleanup

Expected user impact:
- Faster time-to-confidence

Expected business impact:
- Higher activation and retention

Success:
- Users can create and validate a safe policy without reading docs or asking for help

### Next 1 to 2 months

#### 4. Canonical Control Center
What gets built:
- Unified timeline for approvals, transactions, evidence, exceptions, and rail status

Why now:
- Turns Sardis into a believable operator product

Dependencies:
- Contract integrity sweep
- Exception persistence

Expected user impact:
- Easier operation and incident response

Expected business impact:
- Stronger enterprise trust and demo quality

Success:
- Operators can resolve a failed or risky transaction from one place

#### 5. Evidence Export Bundles
What gets built:
- One-click export for policy, approval, ledger, receipt, and exception artifacts

Why now:
- Converts deep infrastructure into visible buyer value

Dependencies:
- Evidence routing cleanup

Expected user impact:
- Easier audit, support, and diligence review

Expected business impact:
- Stronger enterprise close motion

Success:
- A design partner can hand an evidence bundle to compliance or finance without manual stitching

#### 6. Durable Exception Center
What gets built:
- Persistent exception store, retry policies, escalation states, linked approvals, and fallback notes

Why now:
- Recovery quality is part of the product’s credibility

Dependencies:
- API wiring and persistence

Expected user impact:
- Better failure handling and confidence

Expected business impact:
- Better retention and fewer founder-led interventions

Success:
- Exceptions survive restarts and can be resolved through a repeatable flow

### Next quarter

#### 7. Trusted Counterparties
What gets built:
- Approved vendors / payees / merchants / peers
- Counterparty trust state linked to policy rules and approvals

Why now:
- Safe business automation usually requires trusted counterparties

Dependencies:
- Merchant and marketplace primitives

Expected user impact:
- Safer and more legible payment operations

Expected business impact:
- Better fit for procurement, expense, and A2A buyer workflows

Success:
- Agents can be constrained to explicit approved counterparties with reusable trust data

#### 8. Approval Routing and SLA Config
What gets built:
- Org-level approver groups, quorum rules, escalation paths, urgency handling

Why now:
- Needed for real organizational use, not just demos

Dependencies:
- Approval data model cleanup

Expected user impact:
- Faster and more realistic human-in-the-loop operations

Expected business impact:
- Higher readiness for enterprise pilots

Success:
- Non-founder operators can configure approval flows without custom code

### Later-stage bets
- Reliability scorecards and provider routing surfaces
- Checkout hardening for embedded secure purchase flows
- Cross-rail fallback policies
- Broader marketplace and trust profile layers
- More protocol and trust-graph work only after wedge proof

## H. Top Feature Specs

### 1. Canonical Control Center

#### User problem
Operators cannot easily answer:
- what happened
- why it was allowed or blocked
- who approved it
- what evidence exists
- what to do next

#### Feature goal
Provide one operational view for the full control-plane lifecycle.

#### Success criteria
- 80% of common operator actions completed from one area
- Zero manual stitching across approvals, evidence, and exceptions for pilot customers
- Faster incident triage and approval resolution times

#### Key UX requirements
- Timeline view grouped by transaction or workflow
- Clear status states: simulated, pending approval, approved, denied, executed, failed, recovered
- Linked evidence and approval records
- Action buttons for approve, deny, retry, export, freeze

#### Edge cases
- Multiple approvals
- Partial evidence availability
- Fallback rail attempts
- Duplicate webhook deliveries
- Transactions without on-chain settlement yet

#### Risks
- Overbuilding into generic SOC / SIEM tooling

#### Rollout notes
- Start with one workflow: AP2 or checkout or on-chain payment

#### MVP
- Transaction-centric timeline with approvals, evidence, and exception actions

#### V2
- Rail health overlays, alerting, and cross-workflow views

### 2. Policy Lifecycle Manager

#### User problem
Users can parse policies and check them, but they lack one trustworthy authoring and deployment path.

#### Feature goal
Make policy creation deterministic, testable, and deployable with confidence.

#### Success criteria
- Users can create a working policy without documentation assistance
- Policy-related support questions drop
- More policies are tested before live use

#### Key UX requirements
- Natural-language input plus structured preview
- Scenario library with pass / deny / approval outcomes
- Version history and rollback
- Warnings for unsupported or ambiguous policies

#### Edge cases
- NL parser ambiguity
- Conflicting limits
- Merchant and MCC mismatches
- Policy changes on active workflows

#### Risks
- Confusing “AI policy generation” with trusted deterministic enforcement

#### Rollout notes
- Separate “draft” and “live” policies

#### MVP
- Parse, preview, scenario-test, apply, rollback

#### V2
- Recommended edits based on live outcome telemetry

### 3. Guided Live-Lane Onboarding

#### User problem
Moving from sandbox to live is operationally heavy and easy to misconfigure.

#### Feature goal
Turn onboarding from a docs scavenger hunt into a guided setup flow.

#### Success criteria
- Faster time from first install to first live controlled transaction
- Higher pilot completion rate
- Fewer founder-led setup sessions

#### Key UX requirements
- Clear stage progression: sandbox, test, pilot, production
- Credential readiness checks
- Provider connection status
- Required vs optional integrations
- Health checks and “why blocked” explanations

#### Edge cases
- Missing partner approvals
- Partial provider availability
- Org-specific policy requirements

#### Risks
- Could become a generic settings dump if not tightly sequenced

#### Rollout notes
- Build for design-partner onboarding first

#### MVP
- Readiness checklist with live validation and next-step guidance

#### V2
- Environment templates and one-click starter configs

### 4. Durable Exception Center

#### User problem
Operators need consistent recovery when transactions fail, not only logs and retries.

#### Feature goal
Make exception handling a first-class workflow with durable state and guided actions.

#### Success criteria
- Exceptions persist and can be resolved or escalated reliably
- Reduced manual intervention for common recovery cases

#### Key UX requirements
- Exception queue
- Root cause category
- Suggested strategy
- Linked policy, approval, and transaction evidence
- Retry / escalate / resolve / freeze actions

#### Edge cases
- Repeated retries
- Retry strategy invalidation after policy changes
- Multi-rail fallback ambiguity

#### Risks
- If retry actions are not actually executable, the UI becomes cosmetic

#### Rollout notes
- Start with read-only plus guided actions, then add live retry execution

#### MVP
- Persistent queue with resolution tracking

#### V2
- Automated retry and fallback policies

## I. Strategic Product Judgment

### Single most important missing feature right now
- Canonical operator workflow for policy -> approval -> execution -> evidence -> exception

### Feature that would improve activation the most
- Guided live-lane onboarding

### Feature that would improve retention the most
- Durable exception center

### Feature that would improve trust the most
- Evidence export bundles tied to a real control center

### Feature that would best support monetization
- Enterprise-grade evidence exports and approval routing config

### Feature that would most strengthen differentiation
- Policy lifecycle manager with deterministic testability and deployment control

### Feature founders are most likely to overvalue incorrectly
- More protocol / identity graph / chain expansion

### Feature that would be impressive but strategically wrong right now
- Rich FIDES trust-graph UI or broad protocol marketplace expansion

### Feature that would make the product feel dramatically more complete
- Trusted counterparties linked to policy and approval workflows

## J. Final Recommendation

### What to build first
1. Contract integrity sweep across approvals, evidence, simulation, and dashboard hooks
2. Guided live-lane onboarding
3. Policy lifecycle manager
4. Canonical control center
5. Durable exception center

### What to delay
- Checkout hardening beyond the narrowest pilot need
- Reliability scorecards as a major product surface
- Rich merchant/service trust profiles beyond basic approved-counterparty workflows

### What to cut or hide
- Mock-heavy admin pages that are not yet backed by real data
- Any menu item that creates a false sense of product maturity
- Extra protocol or trust-graph storytelling inside the product before the control workflow is complete

### What to simplify
- The number of nouns and surfaces around policy and simulation
- The developer path from SDK install to first meaningful safe transaction
- The operator path from risky event to evidence and recovery

### What the product should optimize for right now
- Time-to-first-trusted-live-lane

### Mistakes to avoid
- Shipping more “platform breadth” before control-plane workflows are finished
- Letting dashboard promises outrun operational truth
- Building procurement-suite complexity instead of a narrow approved-counterparty model
- Treating more rails as the same as more product value

### Learning goals for the next feature cycle
1. Can users author, test, and deploy policies without founder involvement?
2. Can a design partner move from sandbox to a controlled live lane in a predictable way?
3. Do operators trust Sardis more after using evidence and exception workflows?
4. Which wedge workflow pulls hardest: procurement, expense, API purchases, or A2A escrow?

