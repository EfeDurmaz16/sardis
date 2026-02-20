---
name: sardis-payments
version: 1.0.0
description: "Payment OS for AI Agents - Send payments, manage wallets, enforce spending policies with natural language"
author: Sardis
homepage: https://sardis.sh
repository: https://github.com/sardis-labs/sardis
license: MIT
tags:
  - payments
  - fintech
  - wallet
  - crypto
  - USDC
  - stablecoin
  - spending-policy
  - agent-payments
  - virtual-cards
  - compliance
  - KYA
requires:
  env:
    - SARDIS_API_KEY
  packages:
    - sardis
capabilities:
  - wallet_management
  - payment_execution
  - policy_enforcement
  - balance_checking
  - card_management
  - spending_analytics
---

# Sardis - Payment OS for AI Agents

> AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

Sardis provides complete payment infrastructure for AI agents with non-custodial MPC wallets, natural language spending policies, and compliance-first design.

## Quick Setup

```bash
pip install sardis
export SARDIS_API_KEY=sk_your_key_here
```

## Available Commands

### Wallet Management

```bash
# Create a new agent wallet with natural language policy
sardis wallets create --name "procurement-agent" --chain base --token USDC \
  --policy "Max $500/day, only Amazon and OpenAI, no weekends"

# Check wallet balance
sardis wallets balance --wallet wallet_abc123

# List all wallets
sardis wallets list
```

### Payment Execution

```bash
# Execute a payment (policy automatically enforced)
sardis payments execute \
  --wallet wallet_abc123 \
  --to 0xRecipientAddress \
  --amount 25.00 \
  --token USDC \
  --purpose "OpenAI API credits"

# Check transaction status
sardis payments list --wallet wallet_abc123
```

### Policy Management

```bash
# Check if a payment would be allowed (dry-run)
sardis policies check --wallet wallet_abc123 --amount 50.00 --vendor "openai.com"

# List active policies
sardis policies list --wallet wallet_abc123
```

### Virtual Cards

```bash
# Issue a virtual card for real-world purchases
sardis cards create --agent agent_abc123 --limit 500 --merchant-category "software"

# List cards
sardis cards list --agent agent_abc123

# Freeze a card
sardis cards freeze --card card_abc123
```

### Spending Analytics

```bash
# Get spending summary
sardis spending summary --agent agent_abc123 --period month

# Spending by vendor
sardis spending by-vendor --agent agent_abc123 --period week
```

## Python SDK Usage

```python
from sardis import SardisClient

# Initialize client
client = SardisClient(api_key="sk_...")

# Create agent wallet with natural language policy
wallet = client.wallets.create(
    name="my-shopping-agent",
    chain="base",
    token="USDC",
    policy="Max $100 per transaction, $500/day, only verified merchants"
)

# Execute payment
tx = wallet.pay(
    to="0xMerchantAddress",
    amount="25.00",
    purpose="Monthly SaaS subscription"
)
print(f"Payment {tx.status}: {tx.tx_hash}")

# Check remaining budget
balance = wallet.balance
print(f"Available: {balance.available} USDC")
print(f"Daily remaining: {balance.daily_remaining} USDC")
```

## Framework Integrations

Sardis works with all major AI agent frameworks:

| Framework | Package | Install |
|-----------|---------|---------|
| LangChain | `sardis-langchain` | `pip install sardis-langchain` |
| CrewAI | `sardis-crewai` | `pip install sardis-crewai` |
| OpenAI | `sardis-openai` | `pip install sardis-openai` |
| Google ADK | `sardis-adk` | `pip install sardis-adk` |
| Claude | `sardis-agent-sdk` | `pip install sardis-agent-sdk` |
| Vercel AI | `@sardis/ai-sdk` | `npm install @sardis/ai-sdk` |
| MCP | `@sardis/mcp-server` | `npx @sardis/mcp-server start` |

### LangChain Example

```python
from sardis_langchain import SardisToolkit

toolkit = SardisToolkit(api_key="sk_...")
tools = toolkit.get_tools()

# Use with any LangChain agent
agent = create_react_agent(llm, tools)
```

### CrewAI Example

```python
from sardis_crewai import SardisPayTool, SardisCheckBalanceTool

procurement_agent = Agent(
    role="Procurement Specialist",
    tools=[SardisPayTool(), SardisCheckBalanceTool()],
)
```

## Supported Chains & Tokens

| Chain | Tokens |
|-------|--------|
| Base | USDC, EURC |
| Polygon | USDC, USDT, EURC |
| Ethereum | USDC, USDT, PYUSD, EURC |
| Arbitrum | USDC, USDT |
| Optimism | USDC, USDT |

## Key Features

- **Non-Custodial**: MPC wallets via Turnkey - agents control their own keys
- **Natural Language Policies**: "Max $100/day, only Amazon" - parsed automatically
- **KYA (Know Your Agent)**: Compliance-first agent identity verification
- **Multi-Chain**: Base, Polygon, Ethereum, Arbitrum, Optimism
- **Virtual Cards**: Stripe Issuing integration for real-world purchases
- **Audit Trail**: Append-only ledger with hash-chain integrity
- **AP2 Protocol**: Google/PayPal/Mastercard Agent Payment Protocol support

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs
- GitHub: https://github.com/sardis-labs/sardis
- API Reference: https://api.sardis.sh/v2/docs
