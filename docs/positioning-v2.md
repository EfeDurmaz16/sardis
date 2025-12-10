# Sardis V2: Positioning Document

**Payment Execution Layer for the AP2/TAP Ecosystem**

**Date:** December 2025  
**Audience:** Investors, AP2/TAP Community, Technical Partners  
**Status:** Strategic Product Definition

---

## The Shift: V1 → V2

### ❌ V1: "Stripe for AI Agents"

**Vision:**
- Universal payment infrastructure
- Product catalog & shopping cart
- Merchant marketplace
- E-commerce platform for agents

**Problem:**
- Too broad, unfocused
- Competing with established e-commerce platforms
- Not aligned with emerging standards (AP2, TAP, ACP)
- Unclear value proposition

---

### ✅ V2: "Payment Execution Layer for AP2/TAP"

**Vision:**
- Payment-method-agnostic execution & settlement layer
- Mandate enforcement engine
- Multi-chain routing & optimization
- Compliance & custody infrastructure
- Multiple funding rails (stablecoins, virtual cards, x402)

**Why This Works:**
- **Focused:** One critical layer, done exceptionally well
- **Aligned:** Built for AP2/TAP/ACP from day one — payment-method-agnostic like AP2
- **Defensible:** Protocol compliance creates moat
- **Scalable:** Execution layer scales with entire ecosystem
- **Flexible:** Supports emerging payment methods including x402

---

## The Market Opportunity

### AP2 Ecosystem Gap

**What AP2 Provides:**
- Intent & mandate framework
- User authorization model
- Payment-agnostic architecture (supports cards, crypto, bank transfers)
- Open protocol specification
- x402 compatibility for micropayments

**What AP2 Doesn't Provide:**
- Payment execution engine (for any payment method)
- Agent wallet infrastructure
- Multi-chain routing
- Custody & key management
- Compliance stack (KYC/AML)
- Fiat on-ramp (virtual cards)

**This is Sardis's opportunity.**

---

### AP2 and x402: Complementary, Not Competing

AP2 is designed to be **payment-method-agnostic**. x402 is an emerging payment method that AP2 supports. Sardis implements AP2 and therefore supports x402 as one of multiple payment rails:

```
┌─────────────────────────────────────────────────────────────┐
│                    AP2 PROTOCOL                              │
│   (Intent Mandate → Cart Mandate → Payment Mandate)          │
│                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │ Stablecoins │  │ Virtual     │  │    x402     │        │
│   │ (USDC/USDT) │  │ Cards       │  │ Micropay    │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                              │
│   ┌─────────────┐  ┌─────────────┐                         │
│   │ Bank Xfer   │  │ Credit Card │                         │
│   │ (Future)    │  │ (Future)    │                         │
│   └─────────────┘  └─────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

**Reference:** [google-agentic-commerce/a2a-x402](https://github.com/google-agentic-commerce/a2a-x402/)

---

### Market Size

**Agent Economy Projections:**
- 2025: $5B in agent-initiated transactions
- 2026: $50B
- 2027: $200B
- 2030: $1T+

**Payment Method Distribution (2027 Estimate):**
- Stablecoins: 25-35% ($50-70B)
- Virtual Cards (fiat): 40-50% ($80-100B)
- x402 Micropayments: 10-15% ($20-30B)
- Bank Transfers: 10-15% ($20-30B)

**Sardis Addressable Market:**
- At 0.5% execution fee: $100-500M revenue potential by 2027
- Plus: MPC custody, bridging, card interchange, gas optimization fees

---

## Sardis's Unique Position

### The Stack

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Commerce & Discovery (ACP)                        │
│  Players: Merchants, product feeds, search engines          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Intent & Authorization (AP2)                      │
│  Players: Google, PayPal, Mastercard, Visa                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Identity & Trust (TAP)                            │
│  Players: Visa, Cloudflare, identity providers              │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: PAYMENT EXECUTION (SARDIS) ⭐                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Stablecoin Settlement (Base, Polygon, Ethereum)      │  │
│  │  Virtual Card Funding (Lithic) — Fiat On-Ramp         │  │
│  │  x402 Micropayments                                   │  │
│  │  Future: ACH/SEPA Push Payments                       │  │
│  └───────────────────────────────────────────────────────┘  │
│  Gap: No AP2/TAP-native multi-payment execution layer       │
└─────────────────────────────────────────────────────────────┘
```

**Sardis occupies Layer 1:**
- Receives mandates from AP2
- Verifies identity via TAP
- Executes settlement via multiple rails (stablecoin, virtual card, x402)
- Returns settlement receipt

---

### Competitive Landscape

**Traditional Payment Processors (Stripe, PayPal):**
- ❌ No stablecoin support (except PayPal's PYUSD)
- ❌ No multi-chain capability
- ❌ No AP2/TAP integration
- ❌ High fees (2.9%)
- ✅ Card issuing available

**Crypto Payment Processors (Circle, Coinbase Commerce):**
- ⚠️ Limited agent support
- ❌ No AP2/TAP compliance
- ⚠️ Basic multi-chain (no optimization)
- ❌ No mandate enforcement
- ❌ No fiat on-ramp via cards

**x402 Providers (Orthogonal, etc.):**
- ✅ x402 micropayment support
- ❌ Single payment method only
- ❌ No virtual card funding
- ❌ Limited compliance infrastructure
- ⚠️ Narrow use case (API payments)

**Sardis:**
- ✅ AP2/TAP-native
- ✅ Multi-chain optimized (6+ chains)
- ✅ Mandate enforcement
- ✅ Compliance-first
- ✅ Low fees (0.25-0.75%)
- ✅ **Multi-payment-method support (stablecoin + virtual card + x402)**
- ✅ **Fiat on-ramp via pre-loaded virtual cards**

**Competitive Advantage: Payment-Method Agnostic + Protocol Compliance**

Being the first AP2/TAP-compliant **multi-payment** execution layer creates a **protocol moat**:
- Ecosystem partners integrate once, get all payment methods
- Network effects (more agents → more merchants → more agents)
- Standards compliance = trust + interoperability
- x402 support brings micropayment use cases without building from scratch

---

## Product Strategy

### Core Capabilities

**1. Mandate Enforcement**
- Validate AP2 mandates
- Cryptographic signature verification (Ed25519)
- Scope checking (amount, merchant, token, chain)
- Nonce tracking (replay prevention)
- TTL enforcement (expiration)

**2. Multi-Payment Settlement**

| Payment Method | Use Case | Provider | Status |
|---------------|----------|----------|--------|
| **Stablecoins** | Crypto-native payments | On-chain (Base, Polygon, etc.) | Core |
| **Virtual Cards** | Fiat on-ramp, traditional merchants | Lithic | New |
| **x402** | Micropayments, API access | AP2-compatible | New |
| **Bank Transfer** | High-value, enterprise | ACH/SEPA | Future |

**3. Multi-Chain Routing**
- 6+ chains (Base, Polygon, Solana, Ethereum, Arbitrum, Optimism)
- Intelligent routing (gas + speed optimization)
- Real-time settlement (<2s on L2)
- Cross-chain bridging (Chainlink CCIP, Axelar)

**4. Pre-Loaded Virtual Cards (NEW)**
- Issue virtual cards linked to agent wallets
- Fund cards from stablecoins or bank transfers
- Per-transaction, daily, and monthly spending limits
- Merchant category controls
- Real-time transaction webhooks
- Provider: Lithic (also used by Mercury, Brex, Ramp)

**5. x402 Micropayment Support (NEW)**
- Native support for x402 payment method
- Compatible with AP2 mandate structure
- Enables pay-per-API-call use cases
- Reference: google-agentic-commerce/a2a-x402

**6. MPC Custody**
- Turnkey integration
- Threshold signatures
- Agent wallet creation
- Key rotation
- Balance management

**7. Compliance & Risk**
- KYC/AML (Persona, Elliptic)
- Sanctions screening (OFAC, EU, UN)
- Transaction monitoring
- Immutable audit logs (Merkle tree)
- MSB licensing

**8. Developer Experience**
- SDKs (Python, JavaScript, Go, Rust)
- CLI tool
- Sandbox environment
- Webhooks
- API explorer
- Comprehensive docs

---

### What Sardis Does NOT Do

**❌ Product Catalog**
- Merchants manage their own catalogs
- ACP layer handles product discovery

**❌ Shopping Cart**
- Merchants/ACP handle cart management
- Sardis receives final payment mandate

**❌ Merchant Marketplace**
- Not building a marketplace
- Focus: execution infrastructure

**❌ Agent Marketplace**
- Agents built by developers
- Sardis provides payment rails

**This focus is our strength.**

---

## Business Model

### Revenue Streams

**1. Execution Fees (Primary)**
- 0.25% - 0.75% per stablecoin transaction
- Volume-based tiers
- Projected: $6M+ ARR by Year 3

**2. Virtual Card Revenue (NEW)**
- Card issuance fees: $0.50-2.00 per card
- Interchange share: 0.5-1.5% of card spend
- Projected: $1.8M+ ARR by Year 3

**3. x402 Micropayment Fees (NEW)**
- 0.1-0.3% per micropayment
- Optimized for high-volume, low-value
- Projected: $500K+ ARR by Year 3

**4. Bridging Fees**
- 0.1% for cross-chain transfers
- Projected: $5M+ ARR by Year 3

**5. MPC Custody**
- $5-50 per agent per month
- Based on transaction volume
- Projected: $1M+ ARR by Year 3

**6. Subscriptions**
- Developer: Free (100 executions/month)
- Startup: $99/month (5,000 executions)
- Growth: $499/month (50,000 executions)
- Enterprise: Custom

**7. Value-Added Services**
- Premium routing (fastest paths)
- Gas savings share
- Compliance reporting
- Dedicated MPC orgs

### Financial Projections

| Metric | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| **Execution Volume** | $50M | $500M | $2B |
| **Stablecoin Execution Fees** | $250K | $2M | $6M |
| **Card Issuance Fees** | $50K | $300K | $1M |
| **Card Interchange Share** | $25K | $200K | $800K |
| **x402 Fees** | $25K | $150K | $500K |
| **Bridging Fees** | $50K | $500K | $5M |
| **MPC Custody** | $100K | $500K | $1M |
| **Subscriptions** | $850K | $4.8M | $14M |
| **Total ARR** | **$1.35M** | **$8.45M** | **$28.3M** |

**Break-even:** Month 9  
**Gross Margin:** 70-80% (software business)  
**CAC Payback:** <6 months  

---

## Go-to-Market Strategy

### Phase 1: AP2/TAP Community (Months 1-6)

**Target:**
- AP2 working group members
- TAP protocol contributors
- Early adopters in agent economy

**Tactics:**
- Join AP2/TAP working groups
- Contribute to protocol specifications
- Publish reference implementations
- Sponsor hackathons

**Goal:** Become the de facto stablecoin execution layer for AP2/TAP

---

### Phase 2: Developer Ecosystem (Months 6-12)

**Target:**
- Agent framework developers (LangChain, AutoGPT, etc.)
- Payment integration developers
- Crypto-native developers

**Tactics:**
- Launch developer program
- Comprehensive SDKs + docs
- Sandbox environment
- Developer grants ($100K fund)
- Office hours + support

**Goal:** 500+ developers building on Sardis

---

### Phase 3: Enterprise Partners (Months 12-18)

**Target:**
- Payment processors (Stripe, PayPal, Adyen)
- Stablecoin issuers (Circle, Tether, PayPal)
- Enterprise platforms (Salesforce, ServiceNow)

**Tactics:**
- White-label offering
- Enterprise SLAs
- Dedicated support
- Custom integrations

**Goal:** 10+ enterprise partnerships

---

## Technical Roadmap

### Phase 1 (0-3 months): Foundation
- TAP identity (Ed25519)
- AP2 mandate enforcement
- KYC/AML integration
- Signature + nonce + TTL

**Investment:** $250K  
**Team:** 3 engineers, 1 compliance

---

### Phase 2 (3-6 months): Multi-Payment Execution
- MPC integration (Turnkey)
- Multi-chain settlement (3 chains)
- **Virtual card integration (Lithic)**
- **x402 payment method support**
- Gas optimization
- SDKs (Python, JS)
- Sandbox

**Investment:** $275K  
**Team:** 4 engineers, 1 DevOps

---

### Phase 3 (6-9 months): Scale
- Immutable audit ledger
- Full AML monitoring
- Webhooks + API explorer
- Advanced routing (6 chains)
- SLA infrastructure
- **Card spending controls & webhooks**

**Investment:** $250K  
**Team:** 5 engineers, 1 compliance, 1 DevOps

---

### Phase 4 (9-12 months): Certification
- AP2 compliance
- TAP certification
- ACP support
- **Full x402 compliance (reference: a2a-x402)**
- Multi-region

**Investment:** $200K  
**Team:** 6 engineers, 1 compliance, 1 DevOps

---

### Phase 5 (12-18 months): Enterprise
- 10+ chains
- Fraud ML
- SOC 2 / ISO 27001
- Enterprise SLA
- White-label
- **Additional card providers (Marqeta, Stripe Issuing)**

**Investment:** Revenue-funded  
**Team:** 8 engineers, 2 compliance, 2 DevOps

---

## Why Now?

### Market Timing

**1. AP2 Launch (December 2024)**
- Google, PayPal, Mastercard, Visa announced AP2
- 80+ companies committed
- Standard is live, ecosystem forming

**2. Stablecoin Regulation (GENIUS Act)**
- Clear regulatory framework emerging
- Compliance requirements defined
- Licensed operators will win

**3. Agent Economy Inflection**
- ChatGPT, Claude, Gemini have 100M+ users
- Agents moving from chat to action
- Payment capability is next frontier

**4. Multi-Chain Maturity**
- Base, Polygon, Solana have proven infrastructure
- Bridging protocols (CCIP, Axelar) are production-ready
- Gas costs are low enough for micropayments

**The stars are aligned. This is the moment.**

---

## Team & Execution

### Current Team
- Product Lead (you)
- 2-3 Engineers (current)
- Dashboard developer

### Needed Hires (Year 1)
- Compliance Officer (Month 1)
- Senior Backend Engineer (Month 2)
- DevOps Engineer (Month 4)
- Developer Advocate (Month 6)

### Advisors Needed
- Fintech legal counsel (MSB licensing)
- AP2/TAP protocol expert
- Crypto custody expert
- Compliance/AML expert

---

## Investment Ask

### Year 1 Budget: $950K

| Category | Amount | Notes |
|----------|--------|-------|
| **Engineering** | $600K | 3-6 FTE |
| **Infrastructure** | $100K | AWS, MPC, monitoring |
| **Legal & Compliance** | $150K | MSB licensing, KYC/AML |
| **Sales & Marketing** | $100K | Developer programs, events |

### Use of Funds

**Months 1-3:** Foundation ($250K)
- Hire compliance officer
- Build identity + mandate layer
- Integrate KYC/AML

**Months 4-6:** Execution ($250K)
- Hire senior engineer
- Integrate Turnkey MPC
- Launch SDKs + sandbox

**Months 7-9:** Scale ($250K)
- Hire DevOps engineer
- Multi-chain expansion
- Advanced routing

**Months 10-12:** Certification ($200K)
- AP2/TAP compliance
- SOC 2 audit
- Enterprise features

---

## Success Metrics

### Technical KPIs (Month 12)
- ✅ Settlement latency <2s (L2)
- ✅ 99.9% uptime
- ✅ >95% routing accuracy
- ✅ >99% bridge success rate
- ✅ >20% gas savings

### Business KPIs (Month 12)
- ✅ $50M execution volume
- ✅ 1,000 active agents
- ✅ 500 developers
- ✅ 10 AP2/TAP partners
- ✅ $1.25M ARR

### Compliance KPIs (Month 12)
- ✅ MSB license obtained
- ✅ SOC 2 Type II certified
- ✅ >95% KYC pass rate
- ✅ <1% AML false positives

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Regulatory shutdown** | Partner with licensed MSB, proactive compliance |
| **AP2/TAP standard changes** | Active participation in working groups |
| **MPC provider failure** | Multi-provider strategy, insurance |
| **Bridge exploits** | Use Chainlink CCIP (highest security) |
| **Competitor launch** | Protocol compliance moat, developer experience |

---

## Call to Action

### For Investors
✅ **Invest in the infrastructure layer of the agent economy**  
✅ **First-mover advantage in AP2/TAP stablecoin execution**  
✅ **Clear path to $26M ARR in 3 years**  
✅ **Protocol moat + network effects**  

### For AP2/TAP Community
✅ **Partner with us to build the stablecoin execution layer**  
✅ **Contribute to protocol specifications**  
✅ **Integrate Sardis as reference implementation**  

### For Developers
✅ **Build on Sardis for agent payment infrastructure**  
✅ **Access best-in-class SDKs and sandbox**  
✅ **Join developer program (launching Q1 2026)**  

---

## Conclusion

**Sardis V2 is not a marketplace.**  
**Sardis V2 is the payment execution layer for the agent economy.**

We are building the infrastructure that enables:
- AP2 mandates → executed
- TAP identity → verified
- **Multiple payment methods → unified settlement**
  - Stablecoins (USDC, USDT, PYUSD, EURC)
  - Pre-loaded virtual cards (fiat on-ramp)
  - x402 micropayments
- Agents → empowered to transact anywhere

**The agent economy needs payment rails.**  
**Sardis is building them — for every payment method.**  
**Join us.**

---

## Contact

**Product Lead:** [Your Name]  
**Email:** hello@sardis.network  
**Website:** sardis.network  
**GitHub:** github.com/sardis-network  
**Twitter:** @sardis_network  

**For Investment Inquiries:** invest@sardis.network  
**For Partnership Inquiries:** partners@sardis.network  
**For Developer Inquiries:** developers@sardis.network  

---

**Last Updated:** December 10, 2025  
**Version:** 2.1 (Multi-Payment Update)  
**Status:** Ready for presentation  

**Supporting Documents:**
- [Executive Summary V2](./executive-summary-v2.md)
- [Gap Analysis V2](./gap-analysis-v2.md)
- [Technical Architecture](./architecture.md)
- [Compliance Framework](./compliance.md)
