# Sardis: Payment Rails for the AI Agent Economy

**The infrastructure layer that enables AI agents to become economic actors.**

---

## The Problem

AI agents are becoming autonomous economic participants - shopping, trading, paying for services. But today's payment infrastructure (Visa, PayPal, Stripe) was built for humans with credit cards, not for AI agents making thousands of micro-transactions per second.

**Current limitations:**
- No programmatic spending controls
- No agent-to-agent payments
- High fees (2.9%+) kill micropayment economics
- No cryptographic identity for AI agents
- No policy enforcement at the protocol level

---

## The Solution

**Sardis is the Stripe for AI Agents** - programmable payment rails with:

### Core Features (Built & Working)
- **Programmable Wallets** - Per-agent spending policies, limits, and rules
- **Multi-Chain Support** - Base, Polygon, Ethereum, Arbitrum, Optimism, Solana
- **Stablecoin Native** - USDC, USDT, PYUSD, EURC (no volatile crypto)
- **Low Fees** - 0.3-1% vs 2.9% (Stripe)
- **Policy Engine** - Enforce spending limits, merchant rules, time windows
- **Real-time Webhooks** - Event-driven architecture with retry logic

### Protocol Compliance
- **AP2** (Google's Agent Payment Protocol)
- **TAP** (Visa's Trust Anchor Protocol)
- **ACP** (OpenAI's Agent Commerce Protocol)

---

## Why Now?

### The Market is Forming
- **OpenAI** launched Operator - agents that buy things
- **Google** published AP2 - standardizing agent payments
- **Anthropic** building Claude-based commerce agents
- **Microsoft** integrating payments into Copilot

### The Economics Work
- **$1T+ market** by 2030 (agent economy)
- First-mover in infrastructure = network effects
- Protocol-level integration creates moats

---

## Traction & Status

### Built & Working
- API with full payment flow
- 6 blockchain networks integrated
- 5 stablecoin tokens supported
- 170+ passing tests
- Live transaction simulation
- Dashboard with real-time monitoring

### Ready to Deploy
- Smart contracts for Base Sepolia
- MPC signing integration (Turnkey)
- KYC/AML integration (Persona, Elliptic)

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI AGENTS                               │
│  (OpenAI Operator, Claude, Custom Agents)                   │
└────────────────────────┬────────────────────────────────────┘
                         │ SDK / API
┌────────────────────────▼────────────────────────────────────┐
│                    SARDIS PROTOCOL                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Wallets  │  │ Policies │  │ Mandates │  │ Webhooks │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Ledger   │  │Compliance│  │  Holds   │  │ API Keys │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ Chain Executor
┌────────────────────────▼────────────────────────────────────┐
│                  BLOCKCHAIN LAYER                            │
│   Base  │  Polygon  │  Arbitrum  │  Optimism  │  Solana    │
└─────────────────────────────────────────────────────────────┘
```

---

## Business Model

| Revenue Stream | Fee | Example |
|----------------|-----|---------|
| Transaction fees | 0.3-1% | $0.30 on $100 payment |
| Subscription (Pro) | $99/mo | Developer access |
| Enterprise | $499/mo | SLA, support, custom |
| Marketplace | 10% | Agent-to-agent services |

### Unit Economics
- **Gross margin:** 80%+ (stablecoin rails)
- **CAC:** $50 (developer-led growth)
- **LTV:** $2,400+ (2-year retention)

---

## Competitive Landscape

| Feature | Sardis | Stripe | Circle | Chimoney |
|---------|--------|--------|--------|----------|
| AI-native APIs | ✅ | ❌ | ❌ | ⚠️ |
| Multi-chain | ✅ | ❌ | ⚠️ | ⚠️ |
| Policy engine | ✅ | ❌ | ❌ | ❌ |
| AP2/TAP compliant | ✅ | ❌ | ❌ | ❌ |
| Fees | 0.3-1% | 2.9% | 1% | 1.5% |

---

## Team Background

Building Sardis from first principles, with deep experience in:
- Fintech infrastructure
- Blockchain protocols
- AI/ML systems
- Payment compliance

---

## The Ask

**Raising:** Pre-seed round
**Use of funds:**
- Engineering team expansion
- MSB licensing (compliance)
- Go-to-market (developer relations)

---

## Contact

**GitHub:** [github.com/EfeDurmaz16/sardis](https://github.com/EfeDurmaz16/sardis)
**Demo:** Run `python examples/simple_payment.py`

---

*The agentic economy is inevitable. We're building the rails.*



