# Sardis Executive Summary (V2)

**Payment Execution Layer for the AP2/TAP Ecosystem**

**Version:** 2.1 (Multi-Payment Update)  
**Date:** December 2025  
**Status:** Strategic Product Definition

---

## The Opportunity

Google, PayPal, Mastercard, Visa, Coinbase, ve 80+ sektör lideri **AP2 (Agentic Payments Protocol v2)** standardını açıkladı. Bu standart agent economy için intent, mandate ve authorization katmanını tanımlıyor.

**Ama kritik bir katman eksik: Payment execution & settlement.**

AP2 **payment-agnostic** tasarlanmış (kart, ACH, stablecoin, x402 destekler) ama **execution engine yok:**
- Agent wallet infrastructure yok
- Mandate enforcement yok
- Multi-chain routing yok
- Compliance stack yok
- MPC custody integration yok
- Fiat on-ramp (virtual cards) yok

**Sardis bu boşluğu dolduruyor — tüm ödeme metodları için.**

---

## Sardis'in Yeni Konumlandırması

### ❌ V1 (Eski Vizyon)
"Stripe for AI Agents" — E-ticaret platformu benzeri, product catalog, shopping cart, merchant features

### ✅ V2 (Yeni Vizyon)

⭐ **Sardis = AP2/TAP uyumlu Multi-Payment Execution Layer**

**"Payment Settlement Infrastructure for Autonomous Agents"**

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT ECONOMY STACK                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Commerce (ACP)                                     │
│  - Product discovery, cart, checkout                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Intent & Authorization (AP2)                       │
│  - Mandate creation, user consent                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Identity & Trust (TAP)                             │
│  - Agent identity, signatures                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: PAYMENT EXECUTION (SARDIS) ⭐                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Stablecoin Settlement (USDC, USDT, PYUSD, EURC)      │  │
│  │  Virtual Card Funding (Lithic) — Fiat On-Ramp         │  │
│  │  x402 Micropayments                                   │  │
│  │  Future: ACH/SEPA Push Payments                       │  │
│  └───────────────────────────────────────────────────────┘  │
│  - Multi-chain routing, compliance, MPC custody              │
└─────────────────────────────────────────────────────────────┘
```

---

## What Sardis Does

### Core Functions

**1. Mandate Enforcement**
- AP2 mandates → Sardis validates and executes
- Cryptographic signature verification (Ed25519)
- Scope, amount, expiration checking
- Nonce + TTL replay protection

**2. Multi-Payment Settlement**

| Payment Method | Use Case | Provider | Status |
|---------------|----------|----------|--------|
| **Stablecoins** | Crypto-native payments | On-chain (Base, Polygon, etc.) | Core |
| **Virtual Cards** | Fiat on-ramp, traditional merchants | Lithic | New |
| **x402** | Micropayments, API access | AP2-compatible | New |
| **Bank Transfer** | High-value, enterprise | ACH/SEPA | Future |

**3. Pre-Loaded Virtual Cards (NEW)**
- Issue virtual cards linked to agent wallets
- Fund cards from stablecoins or bank transfers
- Per-transaction, daily, monthly spending limits
- Merchant category controls
- Real-time transaction webhooks
- Provider: Lithic (Mercury, Brex, Ramp kullanıyor)

**4. x402 Micropayment Support (NEW)**
- Native support for x402 payment method
- Compatible with AP2 mandate structure
- Enables pay-per-API-call use cases
- Reference: google-agentic-commerce/a2a-x402

**5. Multi-Chain Routing**
- Optimal routing across 6+ chains (Base, Polygon, Solana, Ethereum, Arbitrum, Optimism)
- Gas optimization (20%+ savings)
- Cross-chain bridging (Chainlink CCIP, Axelar)
- Real-time settlement (<2s on L2)

**6. MPC Custody**
- Turnkey integration for secure key management
- Threshold signatures
- Agent wallet creation and management
- Balance tracking and limits

**7. Compliance & Risk**
- KYC/AML (Persona, Elliptic)
- Sanctions screening (OFAC, EU, UN)
- Transaction monitoring
- Immutable audit logs (Merkle tree)

**8. Developer Tools**
- SDKs (Python, JavaScript, Go, Rust)
- CLI tool
- Sandbox environment
- Webhooks
- API explorer

---

## Current State vs. Target

| Component | Today | 18 Months | Gap |
|-----------|-------|-----------|-----|
| **Cryptographic Identity** | ❌ None | ✅ TAP-compliant | 🔴 Critical |
| **Mandate Enforcement** | ❌ None | ✅ AP2-compliant | 🔴 Critical |
| **On-Chain Settlement** | ❌ Simulated | ✅ Real (6+ chains) | 🔴 Critical |
| **Virtual Card Integration** | ❌ None | ✅ Lithic integrated | 🟠 High |
| **x402 Support** | ❌ None | ✅ Full x402 compliance | 🟠 High |
| **MPC Custody** | ❌ None | ✅ Turnkey integrated | 🔴 Critical |
| **Compliance** | ❌ None | ✅ MSB-licensed, SOC 2 | 🔴 Critical |
| **Developer Tools** | ❌ None | ✅ Full SDK suite | 🟠 High |
| **Cross-Chain Routing** | ❌ None | ✅ Optimized routing | 🟠 High |

---

## 18-Month Roadmap

### Phase 1 (0–3 months): Identity & Compliance
- TAP-compatible identity (Ed25519)
- AP2 mandate enforcement
- KYC/AML integration
- Signature + nonce + TTL protections

**Investment:** $250K  
**Team:** 3 engineers, 1 compliance officer

---

### Phase 2 (3–6 months): Multi-Payment Execution
- MPC integration (Turnkey)
- Multi-chain settlement (Base, Polygon, Solana)
- **Virtual card integration (Lithic)**
- **x402 payment method support**
- Gas optimization
- Developer SDKs (Python, JS)
- Sandbox environment

**Investment:** $275K  
**Team:** 4 engineers, 1 DevOps

---

### Phase 3 (6–9 months): Enterprise Readiness
- Immutable audit ledger
- Full AML monitoring
- Webhooks + API explorer
- Advanced routing
- SLA infrastructure
- **Card spending controls & webhooks**

**Investment:** $250K  
**Team:** 5 engineers, 1 compliance, 1 DevOps

---

### Phase 4 (9–12 months): Protocol Interoperability
- AP2 full compliance
- TAP certification
- ACP delegated payments
- **Full x402 compliance (reference: a2a-x402)**
- Multi-region deployment

**Investment:** $200K  
**Team:** 6 engineers, 1 compliance, 1 DevOps

---

### Phase 5 (12–18 months): Scale
- 10+ chain support
- Advanced fraud ML
- PCI/SOC2/ISO27001
- Enterprise SLA
- White-label options
- **Additional card providers (Marqeta, Stripe Issuing)**

**Investment:** Revenue-funded  
**Team:** 8 engineers, 2 compliance, 2 DevOps

---

## Financial Projections

### Revenue Model

**Stablecoin Execution Fees:** 0.25% – 0.75% (volume-based)  
**Virtual Card Issuance:** $0.50-2.00 per card  
**Card Interchange Share:** 0.5-1.5% of card spend  
**x402 Micropayment Fees:** 0.1-0.3% per payment  
**Bridging Fees:** 0.1% (cross-chain)  
**Gas Abstraction:** Variable (pass-through + 10%)  
**MPC Custody:** $5-50/agent/month  

**Subscriptions:**
- Developer: Free (100 executions/month)
- Startup: $99/month (5,000 executions)
- Growth: $499/month (50,000 executions)
- Enterprise: Custom (unlimited)

### 3-Year Forecast

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
| **Active Agents** | 1,000 | 5,000 | 20,000 |
| **Paying Customers** | 500 | 2,000 | 5,000 |
| **Break-even** | Month 9 | ✓ | ✓ |

### Year 1 Budget: $975K

- Engineering (3-6 FTE): $600K
- Infrastructure (AWS, MPC, Lithic, monitoring): $125K
- Legal & Compliance: $150K
- Sales & Marketing: $100K

---

## Competitive Positioning

### vs. Traditional Payment Processors

| Feature | Stripe | PayPal | Sardis |
|---------|--------|--------|--------|
| **AI Agent Support** | ❌ | ⚠️ AP2 only | ✅ Native |
| **Stablecoin Settlement** | ❌ | ⚠️ PYUSD only | ✅ 4+ tokens |
| **Virtual Card Issuing** | ✅ | ❌ | ✅ (Lithic) |
| **Multi-Chain** | ❌ | ❌ | ✅ 6+ chains |
| **x402 Support** | ❌ | ❌ | ✅ |
| **Execution Fee** | 2.9% | 2.9% | 0.25-0.75% |
| **Mandate Enforcement** | ❌ | ⚠️ AP2 | ✅ AP2 + TAP |
| **Crypto Identity** | ❌ | ❌ | ✅ TAP-compliant |

**Advantage:** 3-10x cheaper, multi-payment-method, agent-first

---

### vs. Crypto Payment Processors

| Feature | Circle | Coinbase Commerce | Sardis |
|---------|--------|-------------------|--------|
| **Agent-Native** | ❌ | ❌ | ✅ |
| **AP2/TAP Support** | ❌ | ❌ | ✅ |
| **Virtual Cards (Fiat On-Ramp)** | ❌ | ❌ | ✅ |
| **x402 Micropayments** | ❌ | ❌ | ✅ |
| **Multi-Chain Routing** | ⚠️ Limited | ⚠️ Limited | ✅ Optimized |
| **Mandate Enforcement** | ❌ | ❌ | ✅ |
| **Developer SDKs** | ✅ | ✅ | ✅ |
| **Execution Fee** | 0.3-1% | 1% | 0.25-0.75% |

**Advantage:** Agent-first design, protocol compliance, multi-payment support

---

### vs. x402 Providers (Orthogonal, etc.)

| Feature | x402 Providers | Sardis |
|---------|----------------|--------|
| **x402 Support** | ✅ | ✅ |
| **Stablecoin Support** | ❌ | ✅ |
| **Virtual Cards** | ❌ | ✅ |
| **Multi-Chain** | Limited | ✅ 6+ chains |
| **Full AP2 Compliance** | ❌ | ✅ |
| **Compliance Stack** | Limited | ✅ Full |

**Advantage:** Multi-payment platform vs single-method provider

---

## Key Differentiators

### 1. Protocol-Native
✅ Built for AP2/TAP from day one  
✅ Mandate enforcement engine  
✅ Cryptographic identity (Ed25519)  
✅ x402 micropayment support  

### 2. Multi-Payment-Method (NEW)
✅ Stablecoins (USDC, USDT, PYUSD, EURC)  
✅ Pre-loaded virtual cards (Lithic) — fiat on-ramp  
✅ x402 micropayments  
✅ Future: ACH/SEPA bank transfers  

### 3. Multi-Chain Optimized
✅ 6+ chains (Base, Polygon, Solana, Ethereum, Arbitrum, Optimism)  
✅ Intelligent routing (gas + speed optimization)  
✅ Cross-chain bridging (Chainlink CCIP, Axelar)  
✅ 20%+ gas savings  

### 4. Compliance-First
✅ KYC/AML from day one  
✅ MSB licensing roadmap  
✅ SOC 2 Type II certification  
✅ Immutable audit logs  

### 5. Developer Experience
✅ Best-in-class SDKs (Python, JS, Go, Rust)  
✅ Comprehensive sandbox  
✅ CLI tool  
✅ Webhooks + API explorer  

### 6. Cost-Effective
✅ 0.25-0.75% execution fees (vs. 2.9% for Stripe)  
✅ Gas optimization (20%+ savings)  
✅ Free tier for developers  

---

## Success Metrics

### Technical KPIs

| Metric | Target | Timeline |
|--------|--------|----------|
| Settlement Latency (L2) | <2s | Month 6 |
| Settlement Latency (L1) | <15s | Month 6 |
| Routing Accuracy | >95% optimal | Month 6 |
| Bridge Success Rate | >99% | Month 9 |
| Gas Savings | >20% | Month 6 |
| API Uptime | 99.9% | Month 6 |

### Business KPIs

| Metric | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| Execution Volume | $50M | $500M | $2B |
| ARR | $1.25M | $7.8M | $26M |
| Active Agents | 1,000 | 5,000 | 20,000 |
| AP2/TAP Partners | 10 | 50 | 200 |

### Compliance KPIs

| Metric | Target | Timeline |
|--------|--------|----------|
| KYC Pass Rate | >95% | Month 3 |
| AML False Positives | <1% | Month 6 |
| MSB License | Obtained | Month 11 |
| SOC 2 Type II | Certified | Month 12 |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Regulatory Shutdown** | 🔴 Critical | Partner with licensed MSB, proactive compliance |
| **AP2/TAP Standard Changes** | 🟠 High | Active participation in working groups |
| **MPC Provider Failure** | 🔴 Critical | Multi-provider strategy, insurance |
| **Bridge Exploits** | 🟠 High | Use Chainlink CCIP (highest security) |
| **Competitor Launch** | 🟠 High | Focus on protocol compliance, developer experience |

---

## Immediate Next Steps (30 Days)

### Week 1: Foundation
- [ ] Review V2 positioning with team
- [ ] Engage fintech legal counsel
- [ ] Join AP2/TAP working groups
- [ ] Set up project management

### Week 2: Identity
- [ ] Implement Ed25519 agent identity
- [ ] Build signature verification
- [ ] Create mandate database schema
- [ ] Add nonce tracking

### Week 3: Compliance
- [ ] Integrate KYC provider (Persona)
- [ ] Add sanctions screening (Elliptic)
- [ ] Implement transaction monitoring
- [ ] Partner with MSB

### Week 4: Execution
- [ ] Begin Turnkey MPC integration
- [ ] Design routing engine
- [ ] Create SDK prototypes
- [ ] Set up sandbox environment

---

## Call to Action

### For Executives
✅ Approve V2 positioning  
✅ Secure $950K Year 1 funding  
✅ Engage AP2/TAP communities  
✅ Hire compliance officer  

### For Product Team
✅ Review [Gap Analysis V2](./gap-analysis-v2.md)  
✅ Execute [Roadmap V2](./roadmap-v2.md)  
✅ Build Phase 1 (identity + compliance)  

### For Engineering
✅ Implement cryptographic identity  
✅ Build mandate enforcement  
✅ Integrate Turnkey MPC  
✅ Create developer SDKs  

---

## Conclusion

**Sardis V2 is not a marketplace.**  
**Sardis V2 is the payment execution layer for the agent economy.**

Compatible with AP2, TAP, ACP, and x402, Sardis provides the missing infrastructure for **multi-payment-method** agent payments:

✅ Mandate enforcement  
✅ Cryptographic identity  
✅ Multi-chain settlement  
✅ **Pre-loaded virtual cards (fiat on-ramp)**  
✅ **x402 micropayments**  
✅ Compliance & risk  
✅ Developer tools  

**The agent economy needs payment rails — for every payment method.**  
**Sardis is building them.**

---

**Last Updated:** December 10, 2025  
**Next Review:** January 15, 2026  
**Status:** Ready for execution  

**For Full Details:**
- [Gap Analysis V2](./gap-analysis-v2.md) - Comprehensive feature analysis
- [Roadmap V2](./roadmap-v2.md) - Detailed 18-month plan
- [Standards Comparison V2](./standards-comparison-v2.md) - AP2/TAP compliance matrices
