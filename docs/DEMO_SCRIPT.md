# Sardis Video Demo Script

This document outlines a 2-minute video demo of Sardis for investor presentations.

---

## Setup (Before Recording)

```bash
# Terminal 1: Navigate to project
cd /path/to/sardis

# Ensure clean state
python examples/simple_payment.py  # Test it works
```

---

## Demo Script (2 minutes)

### Opening (10 seconds)

**Narration:**
> "Sardis is the payment protocol for AI agents. Let me show you how it works."

### Part 1: Simple Payment (30 seconds)

**Action:** Open terminal, run the demo

```bash
python examples/simple_payment.py
```

**Narration:**
> "In just a few lines of code, we create a wallet for an AI agent with $50, and execute a payment of $2 to an API provider."

**Show output:**
```
1. Creating wallet with $50 USDC...
   Wallet ID: wallet_abc123
   Balance: $50 USDC

2. Executing payment of $2 to OpenAI API...
   Transaction ID: tx_def456
   Status: executed
   TX Hash: 0x...

3. Checking wallet balance...
   New Balance: $48 USDC
```

**Narration:**
> "The wallet balance is automatically updated. Every transaction is recorded on-chain with a unique hash."

---

### Part 2: Agent-to-Agent (45 seconds)

**Action:** Run the A2A demo

```bash
python examples/agent_to_agent.py
```

**Narration:**
> "Now let's see two AI agents transacting with each other. Alice is a shopping bot. Bob provides data services."

**Show output:**
```
STEP 1: Creating AI Agents
  Created: Agent(Alice, 1 wallets, balance=200)
  Created: Agent(Bob, 1 wallets, balance=50)

STEP 2: Alice Pays Bob for Data Analysis
  Transaction ID: tx_789xyz
  Status: EXECUTED
  ✓ Payment successful!
    Alice's new balance: $175 USDC
    Bob's new balance: $75 USDC
```

**Narration:**
> "Alice pays Bob $25 for a data analysis service. The funds are transferred instantly."

**Show policy enforcement:**
```
STEP 3: Policy Enforcement Demo
  Attempting payment of $150 (exceeds Alice's $100 per-tx limit)...
  Status: REJECTED
  Reason: Amount 150 exceeds limit 100
  ✓ Policy correctly blocked the transaction!
```

**Narration:**
> "But when Alice tries to pay $150, the policy engine blocks it because it exceeds her per-transaction limit. This is how enterprises can give agents spending power with guardrails."

---

### Part 3: The Code (25 seconds)

**Action:** Show the code briefly

```python
from sardis import Agent, Policy

# Create agents with spending policies
alice = Agent(name="Shopping Bot", policy=Policy(max_per_tx=100))
bob = Agent(name="Data Service")

# Fund Alice's wallet
alice.create_wallet(initial_balance=200)

# Alice pays Bob
result = alice.pay(to=bob.agent_id, amount=25)
```

**Narration:**
> "This is the entire code. Create an agent, create a wallet, make a payment. The policy engine runs automatically. It's that simple."

---

### Closing (10 seconds)

**Narration:**
> "Sardis: programmable payments for the agent economy. Multi-chain, stablecoin-native, with built-in compliance. This is the infrastructure AI agents need to transact autonomously."

---

## Recording Tips

1. **Terminal font**: 16px minimum, dark theme for visibility
2. **Clear screen** before each command
3. **Pause** after each output to let viewers read
4. **Zoom in** on important output lines
5. **No fumbling**: Practice the commands 3x before recording

---

## Alternative: API Demo (Optional)

If you want to show the API:

**Terminal 1:**
```bash
uvicorn sardis_api.main:create_app --factory --port 8000
```

**Terminal 2:**
```bash
python examples/api_demo.py
```

**Show:**
- API health check
- Execute payment via REST
- Query transaction ledger
- API docs at `/api/v2/docs`

---

## Key Messages to Convey

1. **Working prototype** — This runs today
2. **Simple API** — 5 lines to make a payment
3. **Policy enforcement** — Agents have guardrails
4. **On-chain settlement** — Real blockchain transactions
5. **Multi-chain** — Base, Polygon, Ethereum support

---

## Recommended Tools

- **Screen recording**: Loom, OBS, or QuickTime
- **Terminal**: iTerm2 with oh-my-zsh
- **Resolution**: 1920x1080 minimum
- **Export**: MP4, H.264, 30fps



