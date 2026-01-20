# Sardis Positioning & Messaging Guide

**Version:** 2.0 (Post-Pivot)  
**Date:** January 11, 2026  
**Status:** Ready for Use

---

## Core Positioning

### Tagline

**"Sardis: Agent Wallet & Payment OS for the Agent Economy"**

### One-Liner

> The operating system for agent payments. Choose your mode: on-chain, checkout, or API.

### Elevator Pitch (30 seconds)

"Sardis is the infrastructure layer that enables AI agents to make payments. We provide non-custodial wallets with spending limits, policy enforcement, and AP2/TAP compliance. Agents can pay on-chain via stablecoins, or through checkout buttons that route to Stripe, PayPal, and other PSPs. Think of us as the 'Stripe for agents' - but we never hold funds, so there's minimal compliance burden."

---

## Value Propositions

### For Agent Framework Developers (Core OS)

**Headline:** "Give your AI agents programmable wallets with spending limits"

**Key Benefits:**
- ✅ Non-custodial MPC wallets (no compliance burden)
- ✅ AP2/TAP mandate verification (protocol-compliant)
- ✅ Spending policy engine (limits, allowlists, time windows)
- ✅ Python + TypeScript SDKs (5-minute integration)

**Use Cases:**
- LangChain plugin for agent payments
- AutoGPT extension with budget controls
- CrewAI agent-to-agent transactions
- Custom agent frameworks

**Messaging:**
> "Add programmable payment capabilities to your agents in 10 lines of code. Sardis handles wallet management, policy enforcement, and mandate verification - you focus on building agents."

### For Merchants (Checkout Surface)

**Headline:** "Accept agent payments via any PSP - Stripe, PayPal, Coinbase, Circle"

**Key Benefits:**
- ✅ Multi-PSP routing (not locked to one provider)
- ✅ Policy-based approval (automatic spending limit checks)
- ✅ "Pay with Agent" button (one-line integration)
- ✅ Payment analytics (agent payment insights)

**Use Cases:**
- E-commerce platforms accepting agent payments
- API providers charging agents per-call
- SaaS platforms with agent subscriptions
- Marketplaces with agent buyers

**Messaging:**
> "Accept payments from AI agents without changing your existing payment infrastructure. Sardis routes agent payments to your preferred PSP (Stripe, PayPal, etc.) while handling policy checks and compliance."

---

## Product Modes

### Mode 1: Agent Wallet OS (Core)

**What it is:** Non-custodial wallet infrastructure for agents

**Who it's for:** Agent framework developers

**Key Features:**
- Agent identity management (TAP)
- MPC wallet abstraction
- Spending policy engine
- AP2/TAP mandate verification
- Python + TypeScript SDKs

**Pricing:** SaaS subscription ($99-999/mo) + usage-based

### Mode 2: Agentic Checkout (Surface)

**What it is:** PSP routing layer for merchant payments

**Who it's for:** Merchants, e-commerce platforms

**Key Features:**
- Multi-PSP support (Stripe, PayPal, Coinbase, Circle)
- Checkout button/widget
- Policy-based routing
- Merchant dashboard
- Payment analytics

**Pricing:** Transaction fee (0.25-0.75%) + optional subscription

### Mode 3: On-Chain (Surface)

**What it is:** Direct blockchain settlement

**Who it's for:** Crypto-native use cases

**Key Features:**
- Multi-chain support (Base, Polygon, Ethereum, etc.)
- Stablecoin payments (USDC, USDT, PYUSD, EURC)
- Real-time settlement
- Gas optimization

**Pricing:** Transaction fee (0.25-0.75%)

---

## Competitive Positioning

### vs. Circle

| Aspect | Circle | Sardis |
|--------|--------|--------|
| Focus | USDC infrastructure | Agent payments |
| AP2/TAP | ❌ | ✅ |
| Non-custodial | ❌ (custodial) | ✅ |
| PSP routing | ❌ | ✅ |
| Agent-native | ❌ | ✅ |

**Differentiation:** "Circle owns USDC, but we own agent payment infrastructure. We're the only platform with AP2/TAP compliance and multi-PSP routing."

### vs. Stripe

| Aspect | Stripe | Sardis |
|--------|--------|--------|
| Focus | Human payments | Agent payments |
| AP2/TAP | ❌ | ✅ |
| Policy engine | ❌ | ✅ |
| Agent identity | ❌ | ✅ |
| Multi-PSP | ❌ (Stripe only) | ✅ |

**Differentiation:** "Stripe is for humans. Sardis is for agents. We understand agent behavior, spending patterns, and mandate-based authorization."

### vs. Coinbase Commerce

| Aspect | Coinbase | Sardis |
|--------|----------|--------|
| Focus | Crypto payments | Agent payments |
| AP2/TAP | ❌ | ✅ |
| PSP routing | ❌ | ✅ |
| Policy engine | ❌ | ✅ |
| Agent-native | ❌ | ✅ |

**Differentiation:** "Coinbase Commerce is crypto-first. Sardis is agent-first, with support for both crypto and traditional PSPs."

---

## Investor Messaging

### Problem

"AI agents are becoming autonomous, but they can't pay for anything. Current payment infrastructure requires human approval, which breaks the agent autonomy model. AP2/TAP protocols define what agents can do, but there's no infrastructure to actually execute payments."

### Solution

"Sardis is the settlement execution layer for the agent economy. We provide non-custodial wallets with policy enforcement, AP2/TAP compliance, and multi-PSP routing. Agents can pay on-chain or through checkout buttons - we never hold funds, so compliance is minimal."

### Market

- **TAM:** $200B agent transactions by 2027
- **SAM:** $40-80B requiring programmable execution
- **SOM:** $2B target (5% SAM share) = $10M revenue

### Traction

- [ ] 10+ agent framework integrations
- [ ] 50+ merchant signups
- [ ] $10K+ MRR
- [ ] AP2 working group participation

### Ask

"$1M seed round to:
1. Complete checkout surface (Stripe, PayPal connectors)
2. Scale developer relations (LangChain, AutoGPT partnerships)
3. Build merchant acquisition (Shopify App Store, Stripe marketplace)
4. Achieve $50K MRR in 12 months"

---

## Developer Messaging

### GitHub README

```markdown
# Sardis

**Agent Wallet & Payment OS for the Agent Economy**

Sardis enables AI agents to make payments with programmable wallets, 
spending limits, and AP2/TAP compliance.

## Quick Start

```python
from sardis import Agent, Wallet, Policy

# Create agent with spending policy
agent = Agent(
    name="Shopping Bot",
    policy=Policy(max_per_tx=100, daily_limit=500)
)

# Create non-custodial wallet
wallet = await agent.create_wallet()

# Execute payment (policy-checked, AP2-verified)
result = await wallet.pay(
    to="merchant_123",
    amount=Decimal("50.00"),
    mandate=ap2_mandate,
)
```

## Features

- ✅ Non-custodial MPC wallets
- ✅ AP2/TAP mandate verification
- ✅ Spending policy engine
- ✅ Multi-PSP checkout routing
- ✅ Python + TypeScript SDKs

## Use Cases

- Agent framework plugins (LangChain, AutoGPT, CrewAI)
- E-commerce agent payments
- API provider micropayments
- Agent-to-agent transactions
```

### Documentation Site

**Homepage:**
- Hero: "The OS for Agent Payments"
- Subhead: "Non-custodial wallets, policy enforcement, AP2/TAP compliance"
- CTA: "Get Started" → Quick start guide

**Features Page:**
- Agent Wallet OS (core)
- Agentic Checkout (surface)
- On-Chain Mode (surface)
- SDKs & Integrations

**Use Cases:**
- Agent Framework Integration
- Merchant Payment Acceptance
- API Provider Micropayments
- Enterprise Agent Budgets

---

## Marketing Messages

### Social Media

**Twitter/X:**
- "AI agents need to pay. Sardis makes it happen. 🚀"
- "The operating system for agent payments. Non-custodial. AP2-compliant. Multi-PSP."
- "Stripe for agents. But we never hold funds. 🎯"

**LinkedIn:**
- "The agent economy needs payment infrastructure. Sardis fills the gap between AP2 authorization and settlement execution."
- "Reducing compliance burden by 80% with non-custodial architecture. Agents can pay, merchants can accept, developers can integrate."

### Content Marketing

**Blog Topics:**
1. "Why Agents Need Non-Custodial Wallets"
2. "AP2/TAP: The Future of Agent Payments"
3. "Building Agent Payment Infrastructure: Lessons Learned"
4. "Compliance-Free Agent Payments: How We Did It"

**Case Studies:**
1. "How LangChain Integrated Sardis for Agent Payments"
2. "Shopify Merchant Accepts $10K in Agent Payments"
3. "API Provider Charges Agents Per-Call with Sardis"

---

## Sales Messaging

### Developer Sales (Core OS)

**Discovery Call:**
- "What agent framework are you building?"
- "How do agents currently make payments?"
- "What's your biggest pain point with agent payments?"

**Demo:**
1. Show agent creation (5 lines of code)
2. Show wallet creation (non-custodial)
3. Show policy configuration (spending limits)
4. Show payment execution (AP2 mandate)
5. Show SDK integration (LangChain example)

**Objection Handling:**
- "Too complex" → "5-minute integration, we handle the complexity"
- "Compliance concerns" → "Non-custodial = minimal compliance"
- "Already using Stripe" → "We route to Stripe, add agent-native features"

### Merchant Sales (Checkout)

**Discovery Call:**
- "Do you accept payments from AI agents?"
- "What PSP do you currently use?"
- "What's your agent payment volume?"

**Demo:**
1. Show checkout button (one-line embed)
2. Show policy check (automatic approval)
3. Show PSP routing (Stripe, PayPal, etc.)
4. Show merchant dashboard (analytics)
5. Show webhook handling (payment completion)

**Objection Handling:**
- "Don't need another PSP" → "We route to your existing PSP, add agent features"
- "Compliance concerns" → "PSP handles compliance, we handle agent logic"
- "Low agent volume" → "Start free, scale as volume grows"

---

## Press Kit

### Company Description

"Sardis is the payment infrastructure for the agent economy. We provide non-custodial wallets with spending limits, policy enforcement, and AP2/TAP compliance. Agents can pay on-chain via stablecoins or through checkout buttons that route to Stripe, PayPal, and other PSPs."

### Founder Bio

"[Name] is the founder of Sardis, the payment infrastructure for AI agents. Previously [background]. Sardis enables agents to make payments with minimal compliance burden through non-custodial architecture."

### Key Metrics (When Available)

- SDK downloads: X,XXX
- Agent framework integrations: XX
- Merchant signups: XXX
- Transaction volume: $XXX,XXX
- MRR: $XX,XXX

---

## FAQ

### Q: Do you hold funds?

**A:** No. Sardis is non-custodial. We never hold funds. Wallets are sign-only, and balances are read from the blockchain or PSP.

### Q: What's the difference between Agent Wallet OS and Checkout?

**A:** Agent Wallet OS is the core infrastructure (wallets, policies, mandates). Checkout is a surface layer that routes to PSPs. You can use just the OS, just Checkout, or both.

### Q: Do I need MSB/MTL licenses?

**A:** No. Because we're non-custodial, we don't require money transmitter licenses. PSP partners handle compliance.

### Q: Which PSPs do you support?

**A:** Currently Stripe (live), with PayPal, Coinbase Commerce, and Circle coming soon.

### Q: How does AP2/TAP work?

**A:** AP2 defines payment mandates (what agents can pay). TAP defines agent identity (who the agent is). Sardis verifies both and executes settlement.

---

**Document Status:** Ready for Use  
**Last Updated:** January 11, 2026  
**Next Review:** After first customer feedback
