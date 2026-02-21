# Sardis Demo Scripts

Interactive demonstrations of Sardis Payment OS capabilities with beautiful terminal output.

## 🎯 Overview

These demos showcase key Sardis features for GTM (Go-To-Market) purposes. Each demo runs in **mock mode** by default (no API key required) and supports production mode with real API keys.

## 📋 Prerequisites

### Required
- Python 3.10+
- Sardis SDK: `pip install sardis` or install from source

### Optional (for beautiful output)
```bash
pip install rich
```

Without `rich`, demos run with basic terminal output.

## 🚀 Quick Start

```bash
# Clone the repo
cd sardis/demos

# Run any demo in mock mode (no API key needed)
python demo_payment_flow.py
python demo_trust_scoring.py
python demo_multi_agent.py
python demo_escrow.py

# Run in production mode (requires API key)
SARDIS_API_KEY=sk_your_key_here python demo_payment_flow.py
```

## 📦 Available Demos

### 1. Payment Flow Demo (`demo_payment_flow.py`)

**What it demonstrates:**
- Complete agent payment lifecycle
- Non-custodial wallet creation with MPC
- Spending policy enforcement
- AP2 protocol mandate chain (Intent → Cart → Payment)
- On-chain USDC settlement
- Immutable audit trail

**Key concepts:**
- Policy-based spending limits
- Multi-party computation (MPC) wallet security
- Google/PayPal/Mastercard AP2 protocol compliance
- Dual-layer audit (PostgreSQL + blockchain anchor)

**Run it:**
```bash
python demo_payment_flow.py
```

**Sample output:**
```
╔══════════════════════════════════════════════════════════╗
║              Sardis Payment Flow Demo                   ║
╚══════════════════════════════════════════════════════════╝

Step 1: Create Agent Wallet
  ● Concept: Agent wallets use MPC (Multi-Party Computation)
  ● Security: Private keys are never stored
  ✓ Wallet created successfully!

Step 2: Execute Payment
  ✓ PAYMENT SUCCESSFUL
  Transaction ID: tx_abc123
  Amount: $25.00 USDC
  Merchant: openai.com
```

---

### 2. Trust Scoring Demo (`demo_trust_scoring.py`)

**What it demonstrates:**
- KYA (Know Your Agent) trust scoring system
- Trust tier progression (NEW → BASIC → TRUSTED → VERIFIED)
- Spending limit increases with trust level
- Trust score factor breakdown
- KYC verification impact

**Key concepts:**
- Transaction history scoring
- Volume-based trust building
- Account age factor
- KYC verification bonus
- Reliability metrics

**Trust tiers:**
| Tier | Score Range | Daily Limit | Per-TX Limit |
|------|-------------|-------------|--------------|
| 🔴 NEW | 0-25 | $100 | $25 |
| 🟡 BASIC | 25-50 | $500 | $100 |
| 🔵 TRUSTED | 50-75 | $2,500 | $500 |
| 🟢 VERIFIED | 75-100 | $10,000 | $2,500 |

**Run it:**
```bash
python demo_trust_scoring.py
```

**Sample output:**
```
Step 1: Register New Agent
  Trust Score: [████░░░░░░░░░░░░] 20/100
  Tier: NEW

Step 4: Long-term Trust Growth (90 days)
  Trust Score: [████████████████████] 85/100
  Tier: VERIFIED
  ✓ Daily limit increased from $100 → $10,000
```

---

### 3. Multi-Agent Payment Demo (`demo_multi_agent.py`)

**What it demonstrates:**
- Three advanced multi-agent payment patterns
- Split payment (shared costs)
- Group payment (shared treasury)
- Cascade payment (automatic failover)

**Scenarios:**

#### Scenario 1: Split Payment
- **Use case:** Multiple agents share purchase costs
- **Example:** 3 agents split a $75 API subscription equally
- **Features:** Atomic execution, individual policy enforcement

#### Scenario 2: Group Payment
- **Use case:** Team with shared budget pool
- **Example:** Marketing team with $500 shared treasury
- **Features:** Group spending policies, unified audit trail

#### Scenario 3: Cascade Payment
- **Use case:** High availability with automatic failover
- **Example:** Primary agent → Secondary → Tertiary fallback
- **Features:** Zero downtime, priority-based routing

**Run it:**
```bash
python demo_multi_agent.py
```

**Sample output:**
```
Scenario 1: Split Payment
  Purchase: $75 Data API Subscription
  ├─ Agent-A pays $25.00
  ├─ Agent-B pays $25.00
  └─ Agent-C pays $25.00
  ✓ Split payment completed successfully!

Scenario 3: Cascade Payment
  Priority 1: Primary Agent ($15)
    ✗ Insufficient balance → Cascade
  Priority 2: Secondary Agent ($100)
    ✓ Payment executed
```

---

### 4. Escrow Flow Demo (`demo_escrow.py`)

**What it demonstrates:**
- Agent-to-Agent (A2A) trustless payments
- Smart contract escrow lifecycle
- Proof of delivery verification
- Dispute resolution options
- Automated release mechanism

**Escrow state machine:**
```
CREATED → FUNDED → DELIVERED → RELEASED
            ↓          ↓
        CANCELLED  DISPUTED → REFUNDED
```

**Key concepts:**
- Trustless transactions (no prior relationship needed)
- On-chain fund locking
- Cryptographic proof of delivery
- Automated release on verification
- Multi-path dispute resolution

**Run it:**
```bash
python demo_escrow.py
```

**Sample output:**
```
Step 1: Create Escrow Agreement
  Buyer: Agent A (Data Collection)
  Seller: Agent B (ML Processing)
  Amount: $100.00 USDC
  Deliverable: Processed dataset

Step 2: Agent A Funds Escrow
  ✓ $100 USDC locked in smart contract

Step 3: Agent B Delivers Service
  ✓ Proof of delivery submitted

Step 4: Verify and Release Payment
  ✓ PAYMENT RELEASED
  Agent B received $100.00 USDC
```

---

## 🎨 Features

All demos include:

- ✅ **Mock mode** - Run without API keys for testing/demos
- ✅ **Beautiful output** - Rich terminal UI with colors, tables, progress bars
- ✅ **Step-by-step explanations** - Educational comments throughout
- ✅ **Real concepts** - Production-ready patterns and flows
- ✅ **Error handling** - Graceful degradation without rich library
- ✅ **Keyboard interrupt** - Clean exit with Ctrl+C

## 🔧 Production Mode

To run demos with real Sardis API:

```bash
# Set your API key
export SARDIS_API_KEY=sk_your_key_here

# Or inline
SARDIS_API_KEY=sk_... python demo_payment_flow.py
```

Get your API key at: https://sardis.sh/signup

## 📊 Demo Comparison

| Demo | Best For | Duration | Complexity |
|------|----------|----------|------------|
| Payment Flow | Understanding basics | 30 sec | ⭐ Simple |
| Trust Scoring | KYA system | 45 sec | ⭐⭐ Medium |
| Multi-Agent | Advanced patterns | 60 sec | ⭐⭐⭐ Advanced |
| Escrow | A2A transactions | 60 sec | ⭐⭐⭐ Advanced |

## 🎓 Learning Path

**Recommended order:**

1. **Start with Payment Flow** - Understand basic Sardis concepts
2. **Try Trust Scoring** - Learn about agent reputation
3. **Explore Multi-Agent** - See coordination patterns
4. **Advanced: Escrow** - Master trustless A2A payments

## 📖 Documentation

- **Docs:** https://sardis.sh/docs
- **API Reference:** https://sardis.sh/api
- **SDK Guide:** https://sardis.sh/docs/sdk
- **Discord:** https://discord.gg/sardis

## 🐛 Troubleshooting

### ImportError: No module named 'sardis'

```bash
# Install from PyPI
pip install sardis

# Or install from source
cd sardis
pip install -e .
```

### Rich library not found

```bash
pip install rich
```

Demos work without rich, but output is less beautiful.

### API key errors

Make sure you're using a valid API key:
```bash
export SARDIS_API_KEY=sk_test_... # For testing
export SARDIS_API_KEY=sk_live_... # For production
```

Or run in mock mode (no API key needed).

## 🎬 Recording Demos

These demos are perfect for:

- **Sales demos** - Show live to prospects
- **Video tutorials** - Record for YouTube/social
- **Conference talks** - Live demos at events
- **Documentation** - Screenshot for docs
- **Onboarding** - Train new users

Tips for recording:
```bash
# Use rich for best visuals
pip install rich

# Full screen terminal
# Dark background recommended
# Font: Monaco, Menlo, or Fira Code

# Run demo
python demo_payment_flow.py
```

## 🤝 Contributing

Have ideas for new demos? Open an issue or PR!

Ideas:
- DeFi integration demo
- Cross-chain payment demo
- Subscription payment demo
- Virtual card demo
- Compliance workflow demo

## 📝 License

MIT License - See [LICENSE](../LICENSE)

---

**Built with ❤️ by the Sardis team**

🌐 Website: https://sardis.sh
🐦 Twitter: https://twitter.com/sardis_sh
💬 Discord: https://discord.gg/sardis
