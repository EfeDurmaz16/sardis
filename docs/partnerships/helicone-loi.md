# Letter of Intent -- Sardis x Helicone

## Design Partnership Agreement

---

**Document Type:** Letter of Intent (Non-Binding)
**Version:** 1.0
**Effective Date:** [DATE]
**Reference:** SARDIS-LOI-HELICONE-2026-001

---

## Parties

**Sardis Technologies, Inc.** ("Sardis")
Contact: [SARDIS_CONTACT_NAME], CEO
Email: [SARDIS_CONTACT_EMAIL]

**Helicone, Inc.** ("Helicone")
Contact: [HELICONE_CONTACT_NAME], [HELICONE_CONTACT_TITLE]
Email: [HELICONE_CONTACT_EMAIL]

---

## 1. Purpose

This Letter of Intent sets forth the mutual understanding between Sardis and Helicone regarding a proposed Design Partner relationship. Sardis provides the Payment OS for the Agent Economy -- infrastructure enabling AI agents to make real financial transactions through non-custodial MPC wallets with natural language spending policies. Helicone provides the leading AI observability and monitoring platform. Together, the parties intend to enable AI developers to observe, monitor, and control the financial actions of their AI agents in a unified workflow.

This LOI is non-binding except for Sections 7 (Confidentiality) and 8 (Exclusivity), which shall be binding upon execution.

---

## 2. Commitment Level

**Selected:** Design Partner

Helicone will serve as a Design Partner, providing early product feedback, co-developing the observability integration, and influencing Sardis's product roadmap for agent payment monitoring capabilities.

---

## 3. Integration Scope

### 3.1 Technical Integration

**Integration Type:** Composio tool marketplace connection + observability data bridge

**Sardis Components:**
- sardis-composio package (Composio tool marketplace integration)
- sardis-api (REST API -- transaction events, policy decisions, audit trail)
- sardis-ledger (append-only audit log for payment events)
- Natural language spending policy engine
- AP2 protocol event stream

**Helicone Components:**
- Helicone observability dashboard
- Custom properties API (for Sardis payment metadata)
- Prompt and request logging infrastructure
- Cost tracking and analytics engine

### 3.2 Integration Architecture

```
AI Agent (e.g., AutoGPT, CrewAI, OpenAI Agents)
    |
    |-- LLM calls --> Helicone Proxy --> LLM Provider
    |
    |-- Payment calls --> Sardis API --> Blockchain/Cards
    |
    +-- Unified Dashboard: Helicone shows both LLM cost + Sardis payment cost
```

**Data Flow:**
1. Sardis emits structured payment events (transaction initiated, policy evaluated, approved/declined, settled)
2. Events are tagged with Helicone session/request IDs via Composio context propagation
3. Helicone displays payment events inline with LLM call traces
4. Combined cost view: LLM inference cost (Helicone) + payment amount (Sardis)

### 3.3 Integration Deliverables

| Deliverable | Owner | Target Date |
|-------------|-------|-------------|
| Sardis Composio tool registration | Sardis | Pilot Day 7 |
| Helicone custom property schema for payment events | Helicone | Pilot Day 14 |
| Event bridge: Sardis ledger events -> Helicone | Sardis | Pilot Day 21 |
| Unified cost dashboard prototype | Helicone | Pilot Day 35 |
| End-to-end integration testing | Joint | Pilot Day 42 |
| Documentation and examples | Joint | Pilot Day 50 |
| Production deployment | Joint | Pilot Day 56 |

---

## 4. Timeline

**Pilot Duration:** 60 days
**Pilot Start Date:** [DATE]
**Pilot End Date:** [DATE + 60 days]
**Production Target:** [DATE + 75 days]

### Milestones

| Phase | Duration | Activities |
|-------|----------|------------|
| Kickoff | Week 1 | Technical alignment, API key exchange, sandbox provisioning |
| Development Sprint 1 | Weeks 2-3 | Composio tool registration, event schema design |
| Development Sprint 2 | Weeks 4-5 | Event bridge implementation, dashboard prototype |
| Integration Testing | Weeks 6-7 | End-to-end testing with real agent workflows |
| Documentation & Polish | Week 8 | Docs, examples, blog post draft |
| Pilot Evaluation | Week 8-9 | Performance review, go/no-go for production |

---

## 5. Pricing

**Selected Tier:** Growth ($99/mo)

**Pilot Terms:**
- Free access to Sardis Growth tier during 60-day pilot
- Post-pilot: Growth tier at 30% discount ($69/mo) for first 12 months
- Transaction fees: 0.8% (Growth tier standard)
- No minimum volume commitment during pilot

**Helicone Terms:**
- Sardis receives Helicone Pro tier access during pilot (reciprocal)
- Post-pilot pricing negotiated based on usage volume

---

## 6. Marketing & Co-Promotion

### Mutual Marketing Commitments

- [x] Joint press release upon partnership announcement
- [x] Partner logo on respective websites (integration/partner pages)
- [x] Joint case study upon successful pilot completion
- [x] Co-authored technical blog post: "Observing AI Agent Payments: Sardis + Helicone"
- [x] Social media cross-promotion (Twitter/X, LinkedIn)
- [ ] Joint webinar: "Building Observable AI Agents with Financial Capabilities"
- [ ] Product Hunt mutual upvote support

### Content Calendar

| Week | Content | Platform | Owner |
|------|---------|----------|-------|
| Pilot Week 4 | Partnership announcement | Twitter/X, LinkedIn | Joint |
| Pilot Week 6 | Technical blog post | Both engineering blogs | Joint |
| Pilot Week 8 | Demo video | YouTube, Twitter/X | Joint |
| Post-pilot | Case study | Websites | Joint |

---

## 7. Confidentiality (Binding)

Each party agrees to hold in confidence all non-public technical, business, and financial information disclosed by the other party during the term of this LOI and for a period of two (2) years following termination. This obligation does not apply to information that: (a) is or becomes publicly available through no fault of the receiving party; (b) was known to the receiving party prior to disclosure; (c) is independently developed without use of the disclosing party's information; or (d) is required to be disclosed by law or regulation.

---

## 8. Exclusivity (Binding)

During the pilot period, neither party shall enter into a substantially similar partnership with a direct competitor in the specific integration domain (AI agent payment observability) without prior written consent. This exclusivity expires 30 days after pilot conclusion.

For clarity:
- Sardis shall not partner with a competing AI observability platform for a similar payment-tracing integration during the exclusivity period.
- Helicone shall not partner with a competing agent payment infrastructure provider for a similar observability integration during the exclusivity period.

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

**Helicone, Inc.**

Signature: ______________________________
Name: [HELICONE_SIGNATORY_NAME]
Title: [HELICONE_SIGNATORY_TITLE]
Date: ______________________________
