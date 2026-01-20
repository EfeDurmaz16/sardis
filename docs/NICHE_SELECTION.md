# Sardis Niche Selection Analysis

**Date:** January 2026  
**Status:** In Progress  
**Decision Deadline:** Week 4

---

## Executive Summary

This document evaluates three potential niche use cases for Sardis to focus on initially. The goal is to select ONE specific use case that:
1. Has real, validated demand
2. Can be addressed with MVP in 2-3 months
3. Has clear path to revenue
4. Leverages Sardis' core strengths (non-custodial, AP2/TAP, crypto-native)

---

## Evaluation Framework

Each niche will be evaluated on:
- **Demand:** Is there real, immediate demand?
- **Willingness to Pay:** Will customers pay for this?
- **Integration Complexity:** How hard is it to integrate?
- **Time to Revenue:** How quickly can we get paying customers?
- **Market Size:** What's the addressable market?
- **Competitive Moat:** Can we defend this position?
- **Sardis Fit:** Does this leverage our strengths?

**Scoring:** 1-5 scale (5 = best)

---

## Option A: API-to-API Payments (x402 Micropayments)

### Description
Enable AI API providers (OpenAI, Anthropic, specialized APIs) to accept micropayments per API call using x402 standard.

### Pros
- ✅ **Existing problem:** API providers need payment infrastructure
- ✅ **Lower barrier:** No merchant onboarding required
- ✅ **Crypto-native:** Leverages Sardis' blockchain strength
- ✅ **Immediate demand:** AI API providers actively looking for solutions
- ✅ **Recurring revenue:** Per-call payments = ongoing revenue stream
- ✅ **x402 standard:** Aligned with AP2/TAP ecosystem

### Cons
- ⚠️ **Smaller market initially:** Limited to API providers
- ⚠️ **x402 adoption:** Requires standard to be adopted
- ⚠️ **Micropayment economics:** Need to ensure fees are economical
- ⚠️ **Batching complexity:** Requires efficient batching for small payments

### Target Customers
- OpenAI (API payments)
- Anthropic (Claude API)
- Specialized AI APIs (image generation, voice, etc.)
- Agent framework APIs (LangChain, AutoGPT)

### Evaluation

| Criterion | Score | Notes |
|-----------|-------|-------|
| Demand | ⏳ TBD | Need customer interviews |
| Willingness to Pay | ⏳ TBD | Need customer interviews |
| Integration Complexity | 4/5 | x402 standard exists, but needs implementation |
| Time to Revenue | 4/5 | Can start with 1-2 API providers |
| Market Size | 3/5 | Smaller initially, but growing |
| Competitive Moat | 4/5 | x402 + AP2/TAP compliance |
| Sardis Fit | 5/5 | Perfect fit - crypto-native, micropayments |

**Preliminary Score:** 24/35 (pending customer interviews)

### Customer Interview Questions
1. Do you currently accept payments for API calls? How?
2. What are the pain points with current payment methods?
3. Would you pay for a micropayment infrastructure solution?
4. What's your expected API call volume?
5. What's your timeline for implementing payment infrastructure?
6. What are the blockers to implementing payments today?

### MVP Requirements
- [ ] x402 micropayment implementation
- [ ] API provider onboarding flow
- [ ] Per-call payment processing
- [ ] Batching and settlement
- [ ] API provider dashboard
- [ ] Webhook notifications

### Revenue Model
- Per-transaction fee: 0.1-0.3% of payment
- Monthly subscription: $99-499/month (based on volume)
- Setup fee: $0 (to reduce friction)

### Timeline to First Customer
- **Week 1-2:** Customer interviews
- **Week 3-4:** Niche decision
- **Week 5-8:** MVP development
- **Week 9-10:** Pilot with 1-2 customers
- **Week 11-12:** Launch with 3-5 customers

---

## Option B: Agent-to-Agent Payments (Crypto Native)

### Description
Enable direct payments between AI agents using crypto/stablecoins, with policy enforcement and AP2/TAP compliance.

### Pros
- ✅ **Crypto-native:** Perfect fit for Sardis' strengths
- ✅ **No merchant onboarding:** Agents pay each other directly
- ✅ **Clear use case:** Agents hiring other agents for services
- ✅ **Policy enforcement:** Natural fit for spending limits
- ✅ **AP2/TAP native:** Leverages protocol compliance

### Cons
- ⚠️ **Smaller market initially:** Requires both agents to use Sardis
- ⚠️ **Chicken & egg:** Need agents on both sides
- ⚠️ **Agent adoption:** Depends on agent framework adoption
- ⚠️ **Crypto complexity:** May be barrier for some users

### Target Customers
- LangChain agent developers
- AutoGPT users
- CrewAI developers
- Custom agent builders

### Evaluation

| Criterion | Score | Notes |
|-----------|-------|-------|
| Demand | ⏳ TBD | Need customer interviews |
| Willingness to Pay | ⏳ TBD | Need customer interviews |
| Integration Complexity | 3/5 | Requires SDK integration in agent frameworks |
| Time to Revenue | 3/5 | Longer sales cycle (framework integration) |
| Market Size | 4/5 | Growing agent ecosystem |
| Competitive Moat | 3/5 | First mover, but can be copied |
| Sardis Fit | 5/5 | Perfect fit - agent-native, crypto-native |

**Preliminary Score:** 18/35 (pending customer interviews)

### Customer Interview Questions
1. Do your agents need to pay other agents? How often?
2. What are the pain points with current payment methods?
3. Would you pay for agent-to-agent payment infrastructure?
4. What's your expected transaction volume?
5. What's your timeline for implementing payments?
6. What are the blockers to implementing payments today?

### MVP Requirements
- [ ] Agent wallet creation flow
- [ ] Direct agent-to-agent transfers
- [ ] Policy enforcement
- [ ] Agent discovery/registry
- [ ] Transaction history
- [ ] Webhook notifications

### Revenue Model
- Per-transaction fee: 0.25-0.75% of payment
- Monthly subscription: $49-299/month (based on volume)
- Setup fee: $0

### Timeline to First Customer
- **Week 1-2:** Customer interviews
- **Week 3-4:** Niche decision
- **Week 5-8:** MVP development
- **Week 9-10:** Pilot with 1-2 agent pairs
- **Week 11-12:** Launch with 3-5 agent pairs

---

## Option C: B2B Agent Subscriptions

### Description
Enable enterprise AI platforms and agent framework providers to offer subscription-based agent services with payment infrastructure.

### Pros
- ✅ **Recurring revenue:** Subscription model = predictable revenue
- ✅ **Enterprise customers:** Higher LTV, longer contracts
- ✅ **Clear value prop:** Enterprises need agent payment infrastructure
- ✅ **Scalable:** One enterprise customer = many agents

### Cons
- ⚠️ **Longer sales cycles:** Enterprise sales take 3-6 months
- ⚠️ **Enterprise features needed:** SSO, multi-tenant, compliance
- ⚠️ **Higher support burden:** Enterprise customers need more support
- ⚠️ **Competitive:** Stripe, PayPal already serve enterprises

### Target Customers
- Enterprise AI platforms (Salesforce, ServiceNow)
- Agent framework providers (LangChain Enterprise, AutoGPT Enterprise)
- Large enterprises with agent programs

### Evaluation

| Criterion | Score | Notes |
|-----------|-------|-------|
| Demand | ⏳ TBD | Need customer interviews |
| Willingness to Pay | ⏳ TBD | Need customer interviews |
| Integration Complexity | 2/5 | Requires enterprise features (SSO, multi-tenant) |
| Time to Revenue | 2/5 | Long sales cycles (3-6 months) |
| Market Size | 5/5 | Large enterprise market |
| Competitive Moat | 2/5 | Competing with established players |
| Sardis Fit | 3/5 | Good fit, but requires enterprise features |

**Preliminary Score:** 14/35 (pending customer interviews)

### Customer Interview Questions
1. Do you offer agent services to enterprise customers? How do they pay?
2. What are the pain points with current payment methods?
3. Would you pay for agent payment infrastructure? How much?
4. What enterprise features do you need? (SSO, multi-tenant, etc.)
5. What's your timeline for implementing payments?
6. What are the blockers to implementing payments today?

### MVP Requirements
- [ ] Subscription billing integration
- [ ] Enterprise features (multi-tenant, SSO)
- [ ] Usage-based pricing
- [ ] Enterprise dashboard
- [ ] Compliance reporting
- [ ] SLA guarantees

### Revenue Model
- Enterprise contracts: $50K-500K/year
- Per-agent fees: $10-50/month
- Setup fee: $10K-50K

### Timeline to First Customer
- **Week 1-2:** Customer interviews
- **Week 3-4:** Niche decision
- **Week 5-12:** MVP development (longer due to enterprise features)
- **Week 13-16:** Pilot with 1 enterprise customer
- **Week 17-20:** Launch with 2-3 enterprise customers

---

## Customer Interview Results

### API-to-API Payments (x402)
- [ ] Interview 1: [Company] - [Date] - [Key Findings]
- [ ] Interview 2: [Company] - [Date] - [Key Findings]
- [ ] Interview 3: [Company] - [Date] - [Key Findings]
- [ ] Interview 4: [Company] - [Date] - [Key Findings]
- [ ] Interview 5: [Company] - [Date] - [Key Findings]

**Summary:**
- Demand: ⏳ TBD
- Willingness to Pay: ⏳ TBD
- Integration Timeline: ⏳ TBD
- Blockers: ⏳ TBD

### Agent-to-Agent Payments
- [ ] Interview 1: [Company] - [Date] - [Key Findings]
- [ ] Interview 2: [Company] - [Date] - [Key Findings]
- [ ] Interview 3: [Company] - [Date] - [Key Findings]
- [ ] Interview 4: [Company] - [Date] - [Key Findings]
- [ ] Interview 5: [Company] - [Date] - [Key Findings]

**Summary:**
- Demand: ⏳ TBD
- Willingness to Pay: ⏳ TBD
- Integration Timeline: ⏳ TBD
- Blockers: ⏳ TBD

### B2B Agent Subscriptions
- [ ] Interview 1: [Company] - [Date] - [Key Findings]
- [ ] Interview 2: [Company] - [Date] - [Key Findings]
- [ ] Interview 3: [Company] - [Date] - [Key Findings]
- [ ] Interview 4: [Company] - [Date] - [Key Findings]
- [ ] Interview 5: [Company] - [Date] - [Key Findings]

**Summary:**
- Demand: ⏳ TBD
- Willingness to Pay: ⏳ TBD
- Integration Timeline: ⏳ TBD
- Blockers: ⏳ TBD

---

## Decision Matrix

| Criterion | Weight | Option A (x402) | Option B (A2A) | Option C (B2B) |
|-----------|--------|-----------------|----------------|----------------|
| Demand | 25% | ⏳ TBD | ⏳ TBD | ⏳ TBD |
| Willingness to Pay | 20% | ⏳ TBD | ⏳ TBD | ⏳ TBD |
| Time to Revenue | 20% | 4/5 | 3/5 | 2/5 |
| Market Size | 15% | 3/5 | 4/5 | 5/5 |
| Sardis Fit | 10% | 5/5 | 5/5 | 3/5 |
| Competitive Moat | 10% | 4/5 | 3/5 | 2/5 |
| **Weighted Score** | **100%** | **⏳ TBD** | **⏳ TBD** | **⏳ TBD** |

---

## Decision

**Selected Niche:** ⏳ TBD (Week 4)

**Rationale:**
[To be filled after customer interviews]

**Key Factors:**
1. [Factor 1]
2. [Factor 2]
3. [Factor 3]

**Risks:**
- [Risk 1]
- [Risk 2]

**Mitigation:**
- [Mitigation 1]
- [Mitigation 2]

---

## Next Steps

1. **Week 1-2:** Complete 15 customer interviews (5 per niche)
2. **Week 3:** Analyze interview results and update scores
3. **Week 4:** Make final decision and document rationale
4. **Week 5:** Begin MVP development for chosen niche

---

**Last Updated:** January 2026  
**Next Review:** After customer interviews (Week 2)
