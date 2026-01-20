# Sardis Pivot Options

**Date:** January 2026  
**Status:** Prepared (Plan B)  
**Purpose:** Alternative strategies if primary market timing is off

---

## Executive Summary

This document outlines pivot options for Sardis if the agent economy adoption is slower than expected, or if market validation reveals insufficient demand. These options leverage existing Sardis infrastructure while targeting different markets or use cases.

**Trigger Conditions:**
- Market validation shows <50% demand
- Agent economy adoption slower than expected
- Revenue projections not met after 6-12 months
- Competitive pressure from big players

---

## Pivot Option 1: Developer Tools (Payment Simulation)

### Description
Pivot from production payment infrastructure to developer tools for testing and simulating agent payments.

### Value Proposition
"Test and simulate agent payments without real money. Build AP2/TAP-compliant payment flows in a sandbox environment."

### Target Market
- Agent framework developers (LangChain, AutoGPT, CrewAI)
- Payment integration developers
- QA/testing teams
- Educational institutions

### Product Features
- Payment simulation engine
- AP2/TAP mandate testing
- Policy engine testing
- Multi-chain simulation
- Test data generation
- Integration testing tools

### Revenue Model
- **SaaS Subscriptions:**
  - Free: 100 simulations/month
  - Developer: $29/month (1,000 simulations)
  - Team: $99/month (10,000 simulations)
  - Enterprise: $499/month (unlimited)
- **Usage-based:** $0.01 per simulation after free tier

### Pros
- ✅ **Minimal compliance:** No real money = no MSB/MTL
- ✅ **Lower risk:** No fund custody, no security concerns
- ✅ **Faster to market:** Can launch in 2-3 months
- ✅ **Clear demand:** Developers need testing tools
- ✅ **Recurring revenue:** SaaS model

### Cons
- ⚠️ **Smaller market:** Limited to developers
- ⚠️ **Lower revenue:** $29-499/month vs. transaction fees
- ⚠️ **Less defensible:** Easier to copy
- ⚠️ **Path to production unclear:** May not lead to production use

### Implementation
- **Timeline:** 2-3 months
- **Team:** 1-2 engineers
- **Budget:** $50-100K
- **Key Changes:**
  - Remove real payment execution
  - Add simulation engine
  - Add test data generation
  - Add integration testing tools

### Success Metrics
- 100+ paying customers in 6 months
- $10K+ MRR in 12 months
- 50%+ conversion from free to paid

### Go-to-Market
- Developer communities (Discord, GitHub)
- Agent framework partnerships
- Content marketing (tutorials, blog posts)
- Free tier to drive adoption

---

## Pivot Option 2: Compliance-Only (Agent Identity Verification)

### Description
Pivot from payment infrastructure to agent identity verification and KYC for agents.

### Value Proposition
"Verify agent identity and authorization. Get compliance-ready agent identity infrastructure with TAP compliance."

### Target Market
- Agent platforms (LangChain, AutoGPT)
- Enterprise AI platforms
- Compliance-conscious enterprises
- Regulated industries (finance, healthcare)

### Product Features
- Agent identity verification (TAP-compliant)
- Public key management
- Domain authorization
- Nonce management
- Audit logging
- Compliance reporting

### Revenue Model
- **Per-Agent Fees:**
  - $5-50 per agent per month (based on volume)
- **Enterprise Contracts:**
  - $50K-500K/year (unlimited agents)
- **Setup Fee:**
  - $5K-25K (one-time)

### Pros
- ✅ **Lightweight compliance:** Identity only, no payments
- ✅ **Clear demand:** Enterprises need agent identity
- ✅ **Recurring revenue:** Per-agent fees
- ✅ **High LTV:** Enterprise customers
- ✅ **Defensible:** TAP compliance creates moat

### Cons
- ⚠️ **Smaller market:** Limited to enterprises
- ⚠️ **Longer sales cycles:** Enterprise sales (3-6 months)
- ⚠️ **Lower revenue potential:** $5-50/agent vs. transaction fees
- ⚠️ **Less exciting:** Less "sexy" than payments

### Implementation
- **Timeline:** 3-4 months
- **Team:** 1-2 engineers + 1 compliance
- **Budget:** $100-200K
- **Key Changes:**
  - Remove payment execution
  - Focus on identity/verification
  - Add compliance reporting
  - Add enterprise features (SSO, multi-tenant)

### Success Metrics
- 10+ enterprise customers in 12 months
- $50K+ ARR in 12 months
- 90%+ customer retention

### Go-to-Market
- Enterprise sales
- Compliance conferences
- Partnership with agent platforms
- Case studies and white papers

---

## Pivot Option 3: Infrastructure-Only (MPC Wallet Abstraction)

### Description
Pivot from payment infrastructure to pure infrastructure: MPC wallet abstraction and policy engine (no payment processing).

### Value Proposition
"MPC wallet infrastructure for developers. Build your own payment solution on top of our wallet and policy engine."

### Target Market
- Developers building payment solutions
- Fintech startups
- Crypto-native companies
- Agent framework developers

### Product Features
- MPC wallet abstraction (Turnkey, Fireblocks)
- Policy engine API
- Mandate verification (AP2/TAP)
- Multi-chain support
- SDKs (Python, TypeScript, Go, Ruby)
- Developer tools

### Revenue Model
- **API Usage Fees:**
  - $0.01-0.10 per API call
  - Volume discounts
- **Monthly Subscriptions:**
  - Developer: $99/month (10K calls)
  - Growth: $499/month (100K calls)
  - Enterprise: Custom

### Pros
- ✅ **Minimal compliance:** Infrastructure only, no payments
- ✅ **Developer-focused:** Clear target market
- ✅ **Scalable:** API usage = revenue
- ✅ **Defensible:** MPC + policy engine = technical moat
- ✅ **Flexible:** Customers build on top

### Cons
- ⚠️ **Smaller market:** Limited to developers
- ⚠️ **Lower revenue per customer:** $99-499/month vs. transaction fees
- ⚠️ **More competition:** Competing with MPC providers
- ⚠️ **Path to payments unclear:** May not lead to payment use

### Implementation
- **Timeline:** 2-3 months
- **Team:** 1-2 engineers
- **Budget:** $50-100K
- **Key Changes:**
  - Remove payment execution
  - Focus on infrastructure APIs
  - Add more SDKs (Go, Ruby)
  - Add developer documentation

### Success Metrics
- 50+ developer customers in 6 months
- $20K+ MRR in 12 months
- 80%+ API usage growth

### Go-to-Market
- Developer communities
- Hacker News, Product Hunt
- Technical blog posts
- Open source components

---

## Pivot Option 4: Enterprise Only (B2B Agent Payments)

### Description
Pivot from general agent payments to enterprise-only B2B agent payment infrastructure.

### Value Proposition
"Enterprise agent payment infrastructure. Secure, compliant, and scalable payment infrastructure for enterprise AI programs."

### Target Market
- Large enterprises with agent programs
- Enterprise AI platforms (Salesforce, ServiceNow)
- Regulated industries (finance, healthcare, government)

### Product Features
- Enterprise agent payment infrastructure
- Full compliance (MSB/MTL if needed)
- Enterprise features (SSO, multi-tenant, RBAC)
- SLA guarantees (99.99% uptime)
- Dedicated support
- White-label options

### Revenue Model
- **Enterprise Contracts:**
  - $100K-1M/year (based on volume)
- **Per-Agent Fees:**
  - $10-100 per agent per month
- **Setup Fee:**
  - $25K-100K (one-time)

### Pros
- ✅ **High revenue:** $100K-1M contracts
- ✅ **High LTV:** Enterprise customers stay longer
- ✅ **Defensible:** Enterprise features create moat
- ✅ **Clear demand:** Enterprises need agent payments
- ✅ **Less competition:** Fewer players in enterprise

### Cons
- ⚠️ **Long sales cycles:** 6-12 months
- ⚠️ **High compliance burden:** Full MSB/MTL if needed
- ⚠️ **High support burden:** Enterprise customers need more support
- ⚠️ **Slower growth:** Fewer customers, longer sales cycles

### Implementation
- **Timeline:** 6-12 months
- **Team:** 3-5 engineers + 1-2 sales + 1 compliance
- **Budget:** $500K-1M
- **Key Changes:**
  - Add enterprise features (SSO, multi-tenant)
  - Full compliance (MSB/MTL)
  - Enterprise sales process
  - Dedicated support team

### Success Metrics
- 5+ enterprise customers in 12 months
- $500K+ ARR in 18 months
- 95%+ customer retention

### Go-to-Market
- Enterprise sales team
- Industry conferences
- Partnership with enterprise platforms
- Case studies and references

---

## Comparison Matrix

| Criterion | Option 1: Dev Tools | Option 2: Compliance | Option 3: Infrastructure | Option 4: Enterprise |
|-----------|---------------------|----------------------|-------------------------|----------------------|
| **Market Size** | Medium | Small | Medium | Small |
| **Revenue Potential** | Low ($10K MRR) | Medium ($50K ARR) | Medium ($20K MRR) | High ($500K ARR) |
| **Time to Market** | 2-3 months | 3-4 months | 2-3 months | 6-12 months |
| **Compliance Burden** | Minimal | Lightweight | Minimal | Full |
| **Competitive Moat** | Low | Medium | Medium | High |
| **Scalability** | High | Medium | High | Low |
| **Team Size** | 1-2 | 2-3 | 1-2 | 5-8 |
| **Budget** | $50-100K | $100-200K | $50-100K | $500K-1M |
| **Risk Level** | Low | Medium | Low | High |

---

## Decision Framework

### When to Pivot

**Trigger Conditions:**
1. Market validation shows <50% demand after 10+ interviews
2. Revenue <$10K MRR after 6 months
3. Agent economy adoption slower than expected
4. Competitive pressure from big players
5. Burn rate unsustainable with current trajectory

### Which Pivot to Choose

**Choose Option 1 (Dev Tools) if:**
- Developer demand is strong
- Need fast pivot (2-3 months)
- Limited budget ($50-100K)
- Want to stay in agent ecosystem

**Choose Option 2 (Compliance) if:**
- Enterprise demand is strong
- Can handle longer sales cycles
- Have compliance expertise
- Want higher LTV customers

**Choose Option 3 (Infrastructure) if:**
- Developer demand is strong
- Want to stay technical
- Can compete with MPC providers
- Want scalable API model

**Choose Option 4 (Enterprise) if:**
- Enterprise demand is strong
- Have enterprise sales capability
- Can handle full compliance
- Have sufficient funding ($500K+)

---

## Implementation Plan (If Pivot Needed)

### Week 1-2: Decision
- [ ] Review market validation results
- [ ] Assess current traction
- [ ] Choose pivot option
- [ ] Communicate pivot to team/investors

### Week 3-4: Planning
- [ ] Create detailed pivot plan
- [ ] Update product roadmap
- [ ] Update positioning/messaging
- [ ] Update financial projections

### Week 5-8: Development
- [ ] Build pivot MVP
- [ ] Update documentation
- [ ] Update marketing materials
- [ ] Prepare for launch

### Week 9-12: Launch
- [ ] Launch pivot product
- [ ] Migrate existing customers (if applicable)
- [ ] New customer acquisition
- [ ] Measure success metrics

---

## Risk Mitigation

### Risks of Pivoting
1. **Customer Confusion:** Existing customers may be confused
2. **Team Morale:** Pivot may demotivate team
3. **Investor Relations:** Investors may question strategy
4. **Time Loss:** Pivot takes time away from original plan

### Mitigation
1. **Clear Communication:** Explain pivot rationale clearly
2. **Customer Migration:** Help existing customers transition
3. **Team Alignment:** Get team buy-in on pivot
4. **Investor Updates:** Regular updates on pivot progress

---

## Conclusion

These pivot options provide alternative paths if the primary agent payment market doesn't materialize as expected. The key is to:
1. **Validate early:** Don't wait too long to pivot
2. **Choose wisely:** Pick pivot that leverages existing strengths
3. **Execute quickly:** Move fast once decision is made
4. **Measure success:** Track metrics to validate pivot

**Recommendation:** Keep these options ready, but focus on primary market validation first. Only pivot if validation clearly shows insufficient demand.

---

**Last Updated:** January 2026  
**Next Review:** After market validation (Week 8)
