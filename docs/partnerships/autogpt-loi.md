# Letter of Intent -- Sardis x AutoGPT

## Design Partnership Agreement

---

**Document Type:** Letter of Intent (Non-Binding)
**Version:** 1.0
**Effective Date:** [DATE]
**Reference:** SARDIS-LOI-AUTOGPT-2026-001

---

## Parties

**Sardis Technologies, Inc.** ("Sardis")
Contact: [SARDIS_CONTACT_NAME], CEO
Email: [SARDIS_CONTACT_EMAIL]

**AutoGPT (Significant Gravitas Ltd.)** ("AutoGPT")
Contact: [AUTOGPT_CONTACT_NAME], [AUTOGPT_CONTACT_TITLE]
Email: [AUTOGPT_CONTACT_EMAIL]

---

## 1. Purpose

This Letter of Intent sets forth the mutual understanding between Sardis and AutoGPT regarding a proposed Design Partner relationship. Sardis provides the Payment OS for the Agent Economy -- infrastructure enabling AI agents to make real financial transactions through non-custodial MPC wallets with natural language spending policies. AutoGPT is the leading open-source autonomous AI agent platform with 180,000+ GitHub stars, enabling developers to build and deploy AI agents that accomplish complex tasks independently.

Together, the parties intend to equip AutoGPT agents with secure, policy-controlled financial capabilities through the `sardis-autogpt` block integration, enabling autonomous agents to make real payments, manage budgets, and interact with the financial system while operating within human-defined guardrails.

This LOI is non-binding except for Sections 7 (Confidentiality) and 8 (Exclusivity), which shall be binding upon execution.

---

## 2. Commitment Level

**Selected:** Design Partner

AutoGPT will serve as a Design Partner, providing early product feedback on the sardis-autogpt blocks, co-developing the payment block interface, and influencing Sardis's product roadmap for autonomous agent payment capabilities.

---

## 3. Integration Scope

### 3.1 Technical Integration

**Integration Type:** AutoGPT block plugin for agent payment capabilities

**Sardis Components:**
- `sardis-autogpt` package (AutoGPT block integration -- existing)
- sardis-sdk-python (Python SDK)
- sardis-api (REST API)
- Natural language spending policy engine
- Non-custodial MPC wallets (Turnkey)
- Virtual card issuance (Stripe Issuing)

**AutoGPT Components:**
- AutoGPT block framework (input/output schema, block registry)
- AutoGPT agent runtime
- AutoGPT marketplace / block directory

### 3.2 Existing Integration: sardis-autogpt Blocks

The `sardis-autogpt` package provides three production-ready blocks:

**SardisPayBlock** (`sardis-pay-block`)
- Executes policy-controlled payments from a Sardis wallet
- Input: API key, wallet ID, amount, merchant, purpose, token
- Output: APPROVED/BLOCKED status, transaction ID, status message
- Enforces spending policies before execution

**SardisBalanceBlock** (`sardis-balance-block`)
- Checks current balance and remaining spending limits
- Input: API key, wallet ID, token
- Output: Balance, remaining limit, token type
- Enables agents to make budget-aware decisions

**SardisPolicyCheckBlock** (`sardis-policy-check-block`)
- Pre-flight check: will a payment pass policy?
- Input: API key, wallet ID, amount, merchant
- Output: Allowed (boolean), reason
- Enables agents to plan before spending

### 3.3 Pilot Deliverables

| Deliverable | Owner | Target Date |
|-------------|-------|-------------|
| sardis-autogpt blocks stabilization (v1.0) | Sardis | Pilot Day 14 |
| AutoGPT marketplace listing draft | AutoGPT | Pilot Day 21 |
| Multi-step payment workflow templates | Joint | Pilot Day 35 |
| Virtual card block (create/fund/spend) | Sardis | Pilot Day 42 |
| Budget management block (set limits, track spend) | Sardis | Pilot Day 49 |
| End-to-end testing with AutoGPT benchmark suite | Joint | Pilot Day 63 |
| Marketplace listing live | AutoGPT | Pilot Day 70 |
| Documentation and tutorials | Joint | Pilot Day 77 |
| Joint launch announcement | Joint | Pilot Day 84 |
| Production deployment | Joint | Pilot Day 90 |

### 3.4 Phase 2 Blocks (Post-Pilot)

| Block | Description | Priority |
|-------|-------------|----------|
| SardisCardBlock | Create and manage virtual cards for online purchases | High |
| SardisSubscriptionBlock | Manage recurring payments and subscriptions | Medium |
| SardisInvoiceBlock | Generate and pay invoices | Medium |
| SardisMultiAgentBudgetBlock | Allocate budgets across agent teams | High |
| SardisComplianceBlock | KYC/AML status check before high-value transactions | Low |

---

## 4. Timeline

**Pilot Duration:** 90 days
**Pilot Start Date:** [DATE]
**Pilot End Date:** [DATE + 90 days]
**Production Target:** [DATE + 100 days]

### Milestones

| Phase | Duration | Activities |
|-------|----------|------------|
| Kickoff | Week 1 | Technical alignment, sandbox provisioning, block review |
| Block Stabilization | Weeks 2-3 | Finalize block schemas, error handling, test coverage |
| Workflow Templates | Weeks 4-5 | Multi-step agent payment workflows |
| New Blocks | Weeks 6-7 | Virtual card and budget management blocks |
| Integration Testing | Weeks 8-9 | AutoGPT benchmark suite, edge cases, error scenarios |
| Marketplace & Docs | Weeks 10-11 | Marketplace listing, tutorials, example agents |
| Launch Preparation | Week 12 | Joint announcement, blog post, social media |
| Pilot Evaluation | Week 13 | Performance review, production go/no-go |

---

## 5. Pricing

**Selected Tier:** Scale ($499/mo)

**Pilot Terms:**
- Free access to Sardis Scale tier during 90-day pilot
- Post-pilot: Scale tier at 40% discount ($299/mo) for first 12 months
- Transaction fees: 0.4% (Scale tier standard)
- 500 included wallets, 250 virtual cards
- No minimum volume commitment during pilot

**Volume Expectations:**
- Pilot: 100-500 agent wallets, 1,000-5,000 transactions
- Post-pilot Year 1: 5,000+ agent wallets, 50,000+ transactions
- Revenue share on AutoGPT marketplace premium listing: [TO_BE_NEGOTIATED]

---

## 6. Marketing & Co-Promotion

### Co-Marketing for Launch

- [x] Joint press release: "AutoGPT Agents Can Now Make Real Payments with Sardis"
- [x] Partner logos on respective websites
- [x] Joint case study with transaction volume and use case data
- [x] Co-authored blog post: "Giving Autonomous Agents Financial Capabilities, Safely"
- [x] Product Hunt co-launch support (mutual upvotes, comments, maker presence)
- [x] Social media campaign (Twitter/X, LinkedIn, Reddit r/AutoGPT)
- [x] YouTube demo video: "AutoGPT Agent Buys a Domain and Deploys a Website"
- [ ] Joint conference talk at [AI_CONFERENCE_NAME]
- [ ] AutoGPT community showcase (Discord/GitHub Discussions)

### Content Calendar

| Week | Content | Platform | Owner |
|------|---------|----------|-------|
| Pilot Week 4 | Teaser: "Something big is coming to AutoGPT" | Twitter/X | AutoGPT |
| Pilot Week 8 | Technical deep-dive blog post | Engineering blogs | Joint |
| Pilot Week 10 | Demo video: agent purchasing workflow | YouTube | Joint |
| Pilot Week 12 | Partnership announcement | All platforms | Joint |
| Pilot Week 13 | Product Hunt launch | Product Hunt | Joint |
| Post-pilot Month 1 | Case study with metrics | Websites | Joint |

### Community Engagement

- Sardis sponsors AutoGPT community hackathon with payment integration track
- AutoGPT features Sardis blocks in "Getting Started with Agent Commerce" tutorial
- Joint AMA in AutoGPT Discord server

---

## 7. Confidentiality (Binding)

Each party agrees to hold in confidence all non-public technical, business, and financial information disclosed by the other party during the term of this LOI and for a period of two (2) years following termination. This obligation does not apply to information that: (a) is or becomes publicly available through no fault of the receiving party; (b) was known to the receiving party prior to disclosure; (c) is independently developed without use of the disclosing party's information; or (d) is required to be disclosed by law or regulation.

Open-source code contributions made to the `sardis-autogpt` package under its published license are not considered confidential information.

---

## 8. Exclusivity (Binding)

During the pilot period, neither party shall enter into a substantially similar partnership with a direct competitor in the specific integration domain (autonomous agent payment infrastructure) without prior written consent. This exclusivity expires 30 days after pilot conclusion.

For clarity:
- Sardis shall not partner with a competing autonomous agent framework (but may integrate with complementary agent frameworks such as CrewAI, LangChain, etc., which serve different market segments).
- AutoGPT shall not partner with a competing agent payment infrastructure provider during the exclusivity period.

---

## 9. Non-Binding Nature

Except for Sections 7 and 8, this LOI is intended to express the mutual interest of the parties and does not create any binding obligation. A definitive agreement will be negotiated and executed separately upon successful pilot completion.

---

## 10. Signatures

**Sardis Technologies, Inc.**

Signature: ______________________________
Name: [SARDIS_SIGNATORY_NAME]
Title: CEO
Date: ______________________________

**AutoGPT (Significant Gravitas Ltd.)**

Signature: ______________________________
Name: [AUTOGPT_SIGNATORY_NAME]
Title: [AUTOGPT_SIGNATORY_TITLE]
Date: ______________________________
