# Quick Start Guide

Get Sardis running in under 2 minutes.

---

## Option 1: Run the Demo (30 seconds)

```bash
# Clone the repo
git clone https://github.com/your-org/sardis.git
cd sardis

# Run the demo
python examples/simple_payment.py
```

**Expected output:**
```
==================================================
Sardis Payment Protocol - Simple Demo
==================================================

1. Creating wallet with $50 USDC...
   Wallet ID: wallet_abc123
   Balance: $50 USDC

2. Executing payment of $2 to OpenAI API...
   Transaction ID: tx_def456
   Status: executed
   TX Hash: 0x...

3. Checking wallet balance...
   New Balance: $48 USDC
   Total Spent: $2

✓ Demo completed successfully!
```

---

## Option 2: Full Installation (2 minutes)

### Step 1: Clone and Install

```bash
git clone https://github.com/your-org/sardis.git
cd sardis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install the SDK
pip install -e .
```

### Step 2: Run Examples

```bash
# Simple payment
python examples/simple_payment.py

# Agent-to-agent transactions
python examples/agent_to_agent.py
```

### Step 3: Start the API (Optional)

```bash
# Install API dependencies
pip install -e packages/sardis-api

# Start server
uvicorn sardis_api.main:create_app --factory --port 8000

# Open API docs
open http://localhost:8000/api/v2/docs
```

---

## Your First Payment in Python

```python
from sardis import Wallet, Transaction

# Create a wallet
wallet = Wallet(initial_balance=100)

# Make a payment
tx = Transaction(
    from_wallet=wallet,
    to="merchant:example",
    amount=10
)
result = tx.execute()

# Check the result
print(f"Success: {result.success}")
print(f"New Balance: ${wallet.balance}")
```

---

## Your First Agent

```python
from sardis import Agent, Policy

# Create an agent with a spending policy
agent = Agent(
    name="My AI Assistant",
    policy=Policy(max_per_tx=50, max_total=500)
)

# Create a wallet
agent.create_wallet(initial_balance=200)

# Make a payment
result = agent.pay(
    to="openai:api",
    amount=5,
    purpose="GPT-4 API call"
)

print(f"Success: {result.success}")
print(f"Balance: ${agent.total_balance}")
```

---

## Next Steps

1. **Explore the API** — Start the server and check `/api/v2/docs`
2. **Read the Docs** — See `docs/` for architecture and integration guides
3. **Run Tests** — `pytest tests/` to verify everything works
4. **Deploy** — See `DEPLOYMENT_PLAN.md` for production setup

---

## Need Help?

- **Docs**: `docs/` folder
- **Examples**: `examples/` folder
- **Issues**: GitHub Issues
