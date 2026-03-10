# Letter of Intent Template

## Partnership Agreement — Sardis Technologies, Inc.

---

**Document Type:** Letter of Intent (Non-Binding)
**Version:** 1.0
**Effective Date:** [DATE]

---

## Parties

**Sardis Technologies, Inc.** ("Sardis")
Address: [SARDIS_ADDRESS]
Contact: [SARDIS_CONTACT_NAME], [SARDIS_CONTACT_TITLE]
Email: [SARDIS_CONTACT_EMAIL]

**[PARTNER_COMPANY_NAME]** ("Partner")
Address: [PARTNER_ADDRESS]
Contact: [PARTNER_CONTACT_NAME], [PARTNER_CONTACT_TITLE]
Email: [PARTNER_CONTACT_EMAIL]

---

## 1. Purpose

This Letter of Intent sets forth the mutual understanding between Sardis and Partner regarding a proposed [COMMITMENT_LEVEL] relationship. This LOI is non-binding except for Sections 7 (Confidentiality) and 8 (Exclusivity), which shall be binding upon execution.

---

## 2. Commitment Level

- [ ] **Design Partner** -- Early access to pre-release features, direct engineering collaboration, product roadmap influence
- [ ] **Enterprise Customer** -- Production deployment with SLA guarantees, dedicated support, custom integration
- [ ] **Integration Partner** -- Technology integration, co-marketing, marketplace listing

---

## 3. Integration Scope

### 3.1 Technical Integration

**Integration Type:** [DESCRIPTION]

**Sardis Components:**
- [ ] sardis-sdk-python (Python SDK)
- [ ] sardis-sdk-js (TypeScript SDK)
- [ ] sardis-mcp-server (MCP protocol)
- [ ] sardis-api (REST API)
- [ ] Virtual card issuance (Stripe Issuing)
- [ ] Stablecoin payments (USDC/EURC on Base, Polygon, Ethereum, Arbitrum, Optimism)
- [ ] Natural language spending policies
- [ ] AP2 protocol (Agent Payment Protocol)
- [ ] Custom integration: [DESCRIBE]

**Partner Components:**
- [PARTNER_COMPONENT_1]
- [PARTNER_COMPONENT_2]
- [PARTNER_COMPONENT_3]

### 3.2 Integration Deliverables

| Deliverable | Owner | Target Date |
|-------------|-------|-------------|
| [DELIVERABLE_1] | [OWNER] | [DATE] |
| [DELIVERABLE_2] | [OWNER] | [DATE] |
| [DELIVERABLE_3] | [OWNER] | [DATE] |
| Integration testing complete | Joint | [DATE] |
| Production deployment | Joint | [DATE] |

---

## 4. Timeline

**Pilot Duration:** [30 / 60 / 90] days
**Pilot Start Date:** [DATE]
**Pilot End Date:** [DATE]
**Production Target:** [DATE]

### Milestones

| Phase | Duration | Activities |
|-------|----------|------------|
| Kickoff | Week 1 | Technical alignment, API key provisioning, sandbox access |
| Development | Weeks 2-[N] | Integration build, iterative testing |
| Testing | Weeks [N]-[N+2] | End-to-end testing, security review |
| Pilot Launch | Week [N+3] | Limited production rollout |
| Evaluation | Final 2 weeks | Performance review, go/no-go decision |

---

## 5. Pricing

### Sardis Pricing Tiers

| Tier | Monthly Fee | Transaction Fee | Included Wallets | Virtual Cards |
|------|-------------|-----------------|-------------------|---------------|
| **Free** | $0 | 1.5% | 5 | 2 |
| **Growth** | $99/mo | 0.8% | 50 | 25 |
| **Scale** | $499/mo | 0.4% | 500 | 250 |
| **Enterprise** | Custom | Custom | Unlimited | Unlimited |

**Selected Tier:** [TIER]
**Special Terms:** [DISCOUNT_OR_SPECIAL_PRICING]
**Pilot Pricing:** [FREE_DURING_PILOT / DISCOUNTED / STANDARD]

### Fee Structure

- **Stablecoin transfers:** [RATE] per transaction
- **Virtual card issuance:** $0.10 per card (Stripe Issuing)
- **Off-ramp (USDC to fiat):** 0.5% via Bridge
- **Cross-border FX:** Market rate + [SPREAD] via Lightspark Grid
- **API calls:** Unlimited (fair use)

---

## 6. Marketing & Co-Promotion

- [ ] Joint press release upon partnership announcement
- [ ] Partner logo on Sardis website and vice versa
- [ ] Joint case study upon successful pilot completion
- [ ] Co-authored technical blog post
- [ ] Joint webinar or conference presentation
- [ ] Product Hunt co-launch support
- [ ] Social media cross-promotion

---

## 7. Confidentiality (Binding)

Each party agrees to hold in confidence all non-public technical, business, and financial information disclosed by the other party during the term of this LOI and for a period of two (2) years following termination. This obligation does not apply to information that: (a) is or becomes publicly available through no fault of the receiving party; (b) was known to the receiving party prior to disclosure; (c) is independently developed without use of the disclosing party's information; or (d) is required to be disclosed by law or regulation.

---

## 8. Exclusivity (Binding)

During the pilot period, neither party shall enter into a substantially similar partnership with a direct competitor of the other party in the specific integration domain described in Section 3, without prior written consent. This exclusivity period expires [30] days after the conclusion of the pilot.

---

## 9. Non-Binding Nature

Except for Sections 7 and 8, this LOI is intended to express the mutual interest of the parties and does not create any binding obligation. A definitive agreement will be negotiated and executed separately.

---

## 10. Signatures

**Sardis Technologies, Inc.**

Signature: ______________________________
Name: [SARDIS_SIGNATORY_NAME]
Title: [SARDIS_SIGNATORY_TITLE]
Date: ______________________________

**[PARTNER_COMPANY_NAME]**

Signature: ______________________________
Name: [PARTNER_SIGNATORY_NAME]
Title: [PARTNER_SIGNATORY_TITLE]
Date: ______________________________

---

---

# Template Variations

---

## Variation A: Design Partner LOI

Use this variation for early-stage partners who will co-develop features and provide product feedback.

**Key modifications to the base template:**

### Section 2 -- Commitment Level
Select "Design Partner."

### Section 3 -- Integration Scope (Design Partner Additions)

**Design Partner Benefits:**
- Weekly engineering sync (30 min) with Sardis core team
- Private Slack/Discord channel for real-time collaboration
- Pre-release access to all new features (minimum 2 weeks before GA)
- Direct influence on product roadmap (quarterly roadmap review session)
- Priority bug fixes (P0/P1 within 24 hours, P2 within 72 hours)
- Named engineering contact for integration support

**Design Partner Obligations:**
- Provide written product feedback within 5 business days of feature release
- Participate in monthly NPS/satisfaction surveys
- Share anonymized usage metrics for product improvement
- Commit to minimum [X] API calls per month during pilot
- Provide testimonial/case study upon successful pilot completion

### Section 5 -- Pricing (Design Partner Terms)
- Pilot period: Free access to Growth tier features
- Post-pilot: 50% discount on selected tier for first 12 months
- No minimum commitment during pilot

### Additional Section -- Feedback Loop

Partner agrees to:
1. Designate a primary technical contact available for bi-weekly syncs
2. Report integration issues via shared GitHub repository or private issue tracker
3. Provide quarterly business impact metrics (transaction volume, user adoption)

---

## Variation B: Enterprise Customer LOI

Use this variation for production-grade deployments with SLA requirements.

**Key modifications to the base template:**

### Section 2 -- Commitment Level
Select "Enterprise Customer."

### Section 3 -- Integration Scope (Enterprise Additions)

**Service Level Agreement:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Uptime | 99.95% | Monthly, excluding scheduled maintenance |
| API Latency (p95) | < 200ms | Measured at Sardis edge |
| Transaction Settlement | < 30 seconds | On-chain confirmation |
| Card Authorization | < 3 seconds | Stripe Issuing webhook response |
| Support Response (P0) | < 1 hour | 24/7 for production incidents |
| Support Response (P1) | < 4 hours | Business hours |
| Support Response (P2) | < 24 hours | Business hours |

**Compliance & Security:**
- SOC 2 Type II audit report available upon NDA execution
- Annual penetration testing (report shared upon request)
- Data processing agreement (DPA) executed separately
- PCI DSS compliance maintained via Stripe Issuing delegation
- Non-custodial architecture (Turnkey MPC -- no private key access)

### Section 5 -- Pricing (Enterprise Terms)
- Minimum annual commitment: $[AMOUNT]
- Volume discount schedule: [DETAILS]
- Custom SLA pricing: [DETAILS]
- Dedicated infrastructure (optional): [PRICING]

### Additional Section -- Governance

- Quarterly business review (QBR) with executive sponsors
- Dedicated customer success manager
- 90-day written notice for material changes to API or pricing
- Joint incident response runbook

---

## Variation C: Integration Partner LOI

Use this variation for technology partnerships where both parties integrate with each other's platforms.

**Key modifications to the base template:**

### Section 2 -- Commitment Level
Select "Integration Partner."

### Section 3 -- Integration Scope (Integration Partner Additions)

**Bidirectional Integration:**

| Direction | Description | Owner |
|-----------|-------------|-------|
| Sardis -> Partner | [SARDIS_INTEGRATION_IN_PARTNER_PLATFORM] | Sardis |
| Partner -> Sardis | [PARTNER_INTEGRATION_IN_SARDIS_PLATFORM] | Partner |

**Marketplace Listing:**
- [ ] Sardis listed in Partner's marketplace/directory
- [ ] Partner listed in Sardis's integration directory
- [ ] Joint documentation page
- [ ] Example code/templates published

**Technical Requirements:**
- API versioning: Both parties maintain backward compatibility for minimum 12 months
- Webhook delivery: At-least-once with idempotency key support
- Authentication: OAuth 2.0 or API key with HMAC signing
- Rate limits: Minimum 1,000 requests/minute per tenant

### Section 5 -- Pricing (Integration Partner Terms)
- Revenue share: [X]% of incremental revenue attributable to integration
- Referral fee: $[AMOUNT] per qualified lead converted
- No platform fee for integration-driven transactions during first 12 months

### Section 6 -- Marketing (Integration Partner Additions)
- Joint launch announcement on both platforms
- Inclusion in partner ecosystem pages
- Co-sponsored developer hackathon (optional)
- Shared booth at [CONFERENCE_NAME] (optional)

### Additional Section -- Technical Maintenance

- Both parties designate an integration maintainer
- Breaking API changes communicated 90 days in advance
- Joint integration health dashboard
- Quarterly integration review and upgrade planning
