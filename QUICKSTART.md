# Sardis Quick Start Guide

Get your AI agent making payments in under 5 minutes.

## Table of Contents

- [Option 1: Demo Mode (No Setup)](#option-1-demo-mode-no-setup)
- [Option 2: Local Development](#option-2-local-development)
- [Option 3: Production Deployment](#option-3-production-deployment)
- [Testing Your Integration](#testing-your-integration)
- [Integration Examples](#integration-examples)
- [Next Steps](#next-steps)

---

## Option 1: Demo Mode (No Setup)

Perfect for prototyping and demos. No API keys, no database, no blockchain.

### JavaScript/TypeScript

```bash
npm install @sardis/sdk
```

```typescript
import { Sardis } from '@sardis/sdk'

// Demo mode - no API key needed!
const sardis = new Sardis({ demo: true })

// Create a wallet
const wallet = await sardis.wallets.create({ chain: 'base' })
console.log(`Wallet: ${wallet.address}`)

// Fund it (simulated)
await sardis.wallets.fund(wallet.id, 1000)

// Check if payment is allowed
const policy = await sardis.policy.check({
  walletId: wallet.id,
  amount: 50,
  merchant: 'OpenAI',
  category: 'software'
})

if (policy.allowed) {
  // Execute payment
  const tx = await sardis.payments.create({
    walletId: wallet.id,
    to: '0xOpenAI...',
    amount: 50,
    memo: 'API credits'
  })
  console.log(`Payment: ${tx.id} - ${tx.status}`)
}
```

### Python

```bash
pip install sardis
```

```python
from sardis import Sardis

# Demo mode
sardis = Sardis(demo=True)

# Create wallet
wallet = sardis.wallets.create(chain="base")
print(f"Wallet: {wallet.address}")

# Fund and pay
sardis.wallets.fund(wallet.id, 1000)
tx = sardis.payments.create(
    wallet_id=wallet.id,
    to="0xOpenAI...",
    amount=50,
    memo="API credits"
)
print(f"Payment: {tx.id}")
```

### Run E2E Test

```bash
# Clone the repo
git clone https://github.com/sardis-labs/sardis.git
cd sardis

# Run demo test (no API needed)
npx tsx scripts/e2e-test.ts
```

**Expected output:**
```
============================================================
Sardis End-to-End Test
============================================================
Mode: DEMO (no API)

📦 Wallet Operations

  Create wallet... ✓
  Fund wallet with $500... ✓
  Check balance... ✓

📋 Policy Checks

  Policy allows $50 payment... ✓
  Policy blocks $600 (exceeds limit)... ✓
  Policy blocks gambling category... ✓

💳 Payment Execution

  Execute $50 payment to OpenAI... ✓
  Balance reduced to $450... ✓
  Payment blocked when exceeds balance... ✓

🔒 Hold Operations

  Create $100 hold... ✓
  Available balance reduced by hold... ✓
  Capture $80 of hold (partial)... ✓
  Capture remaining $20... ✓

📊 Spending Analytics

  Get spending summary... ✓

============================================================
Results: 14 passed, 0 failed
============================================================

✅ All tests passed! Agent payment flow is working.
```

---

## Option 2: Local Development

Full stack with PostgreSQL, Redis, and the API.

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- pnpm (or npm)

### Setup

```bash
# Clone
git clone https://github.com/sardis-labs/sardis.git
cd sardis

# Copy environment file
cp .env.example .env

# Start services
docker compose up -d

# Wait for healthy status
docker compose ps

# Check API
curl http://localhost:8000/health
```

**Services started:**
- PostgreSQL on port 5432
- Redis on port 6379
- Sardis API on port 8000

### Test with Real API

```bash
# Set your local API key (or use default)
export SARDIS_API_KEY=sk_test_demo

# Run tests against local API
SARDIS_API_KEY=sk_test_demo npx tsx scripts/e2e-test.ts
```

### Connect Your Agent

```typescript
import { Sardis } from '@sardis/sdk'

const sardis = new Sardis({
  apiKey: 'sk_test_demo',
  baseUrl: 'http://localhost:8000'  // Local API
})

// Now use real API calls
const wallet = await sardis.wallets.create({ chain: 'base' })
```

### View Logs & Database

```bash
# API logs
docker compose logs -f api

# Connect to database
docker compose exec postgres psql -U sardis -d sardis

# List wallets
SELECT * FROM wallets LIMIT 10;

# List transactions
SELECT * FROM transactions ORDER BY created_at DESC LIMIT 10;
```

### Cleanup

```bash
docker compose down     # Stop services
docker compose down -v  # Stop and remove volumes (fresh start)
```

---

## Option 3: Production Deployment

### 1. Database (Neon PostgreSQL)

```bash
# Create database at https://neon.tech
# Get connection string: postgresql://user:pass@host/sardis

# Initialize schema
psql $DATABASE_URL < scripts/init-db.sql
```

### 2. Cache (Upstash Redis)

```bash
# Create Redis at https://upstash.com
# Get REDIS_URL: redis://default:xxx@host:port
```

### 3. Deploy API

**Option A: Fly.io**

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and deploy
fly auth login
fly launch --config fly.toml

# Set secrets
fly secrets set \
  DATABASE_URL="postgresql://..." \
  REDIS_URL="redis://..." \
  TURNKEY_API_KEY="..." \
  TURNKEY_ORGANIZATION_ID="..."

# Deploy
fly deploy

# Check status
fly status
```

**Option B: Railway**

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and init
railway login
railway init

# Set environment variables in Railway dashboard
# Then deploy
railway up
```

### 4. Deploy Smart Contracts

For mainnet payments, deploy the smart contracts:

```bash
# Set up environment
cp .env.example .env
# Edit .env with:
# - PRIVATE_KEY (deployer wallet with ETH for gas)
# - BASE_RPC_URL (Alchemy/Infura RPC endpoint)
# - BASESCAN_API_KEY (for contract verification)

# Deploy to Base mainnet
./scripts/deploy-mainnet.sh base

# Save the contract addresses from output
# Update packages/sardis-chain/src/sardis_chain/config.py
```

### 5. Get Turnkey MPC Credentials

```bash
# Sign up at https://turnkey.com
# Create an organization
# Generate API credentials
# Add to your .env:
TURNKEY_API_KEY=tk_xxx
TURNKEY_ORGANIZATION_ID=org_xxx
TURNKEY_API_PRIVATE_KEY=xxx
```

### 6. Configure SDK for Production

```typescript
const sardis = new Sardis({
  apiKey: process.env.SARDIS_API_KEY,  // Your production key
  // baseUrl defaults to https://api.sardis.dev
})
```

---

## Testing Your Integration

### Basic Payment Flow

```typescript
async function testPaymentFlow() {
  const sardis = new Sardis({ demo: true })

  // 1. Create wallet for agent
  const wallet = await sardis.wallets.create({
    chain: 'base',
    metadata: { agent: 'my-ai-agent' }
  })

  // 2. Fund wallet
  await sardis.wallets.fund(wallet.id, 500)

  // 3. Check balance
  const balance = await sardis.wallets.getBalance(wallet.id)
  console.log(`Available: $${balance.available}`)

  // 4. Check policy before payment
  const check = await sardis.policy.check({
    walletId: wallet.id,
    amount: 25,
    merchant: 'Anthropic',
    category: 'ai_services'
  })

  if (!check.allowed) {
    console.log(`Blocked: ${check.reason}`)
    return
  }

  // 5. Execute payment
  const tx = await sardis.payments.create({
    walletId: wallet.id,
    to: '0xAnthropic...',
    amount: 25,
    merchant: 'Anthropic',
    category: 'ai_services',
    memo: 'Claude API credits'
  })

  console.log(`✓ Payment ${tx.id}: ${tx.status}`)
  console.log(`  Hash: ${tx.txHash}`)

  // 6. Check spending
  const spending = await sardis.spending.get(wallet.id)
  console.log(`Today: $${spending.today}`)
}
```

### Hold Flow (Pre-authorization)

```typescript
async function testHoldFlow() {
  const sardis = new Sardis({ demo: true })

  const wallet = await sardis.wallets.create({ chain: 'base' })
  await sardis.wallets.fund(wallet.id, 200)

  // 1. Create hold (like hotel pre-auth)
  const hold = await sardis.holds.create({
    walletId: wallet.id,
    amount: 150,
    merchant: 'Hotel',
    expiresIn: '24h'
  })
  console.log(`Hold: ${hold.id} for $${hold.amount}`)

  // 2. Check available balance (reduced by hold)
  const balance = await sardis.wallets.getBalance(wallet.id)
  console.log(`Available: $${balance.available}`)  // $50
  console.log(`Held: $${balance.held}`)            // $150

  // 3. Capture partial amount (actual charge)
  await sardis.holds.capture(hold.id, 120)
  console.log('Captured $120')

  // 4. Release remaining (void the rest)
  await sardis.holds.void(hold.id)
  console.log('Released remaining $30')
}
```

### Policy Examples

```typescript
// Block gambling
const policy = await sardis.policy.check({
  walletId: wallet.id,
  amount: 100,
  category: 'gambling'
})
// → { allowed: false, reason: 'Category gambling is blocked' }

// Exceeds single transaction limit ($500 default)
const policy2 = await sardis.policy.check({
  walletId: wallet.id,
  amount: 600
})
// → { allowed: false, reason: 'Exceeds single transaction limit of $500' }

// Exceeds daily limit ($1000 default)
const policy3 = await sardis.policy.check({
  walletId: wallet.id,
  amount: 200  // After $900 spent today
})
// → { allowed: false, reason: 'Would exceed daily limit of $1000' }
```

---

## Integration Examples

### Vercel AI SDK

```bash
npm install @sardis/ai-sdk ai @ai-sdk/openai
```

```typescript
import { generateText } from 'ai'
import { openai } from '@ai-sdk/openai'
import { createSardisTools, createSardisProvider } from '@sardis/ai-sdk'

// Create Sardis tools for AI
const sardisTools = createSardisTools({
  walletId: 'wallet_xxx',
  apiKey: process.env.SARDIS_API_KEY
})

// Use with any AI model
const result = await generateText({
  model: openai('gpt-4o'),
  tools: sardisTools,
  prompt: 'Pay $25 to OpenAI for API credits'
})

// The AI will:
// 1. Check policy (allowed?)
// 2. Check balance (sufficient?)
// 3. Execute payment
// 4. Return confirmation
```

### Claude MCP Server

```bash
# Install MCP server globally
npm install -g @sardis/mcp-server

# Or run from source
cd packages/sardis-mcp-server
npm install && npm run build
```

Add to Claude config (`~/.claude/config.json` or Claude Desktop settings):

```json
{
  "mcpServers": {
    "sardis": {
      "command": "sardis-mcp-server",
      "env": {
        "SARDIS_API_KEY": "sk_xxx",
        "SARDIS_WALLET_ID": "wallet_xxx"
      }
    }
  }
}
```

Now in Claude:
> "Pay $50 to Anthropic for Claude API access"

Claude will use the MCP tools to check policy, verify balance, and execute the payment.

### LangChain (Python)

```python
import os
import json
from langchain.agents import Tool
from sardis import Sardis

sardis = Sardis(api_key=os.environ["SARDIS_API_KEY"])
wallet_id = os.environ["SARDIS_WALLET_ID"]

tools = [
    Tool(
        name="check_balance",
        func=lambda _: json.dumps(sardis.wallets.get_balance(wallet_id).__dict__),
        description="Check wallet balance. No input needed."
    ),
    Tool(
        name="check_policy",
        func=lambda x: json.dumps(
            sardis.policy.check(wallet_id=wallet_id, **json.loads(x)).__dict__
        ),
        description="Check if payment is allowed. Input: JSON with amount, merchant (optional), category (optional)"
    ),
    Tool(
        name="make_payment",
        func=lambda x: json.dumps(
            sardis.payments.create(wallet_id=wallet_id, **json.loads(x)).__dict__
        ),
        description="Make a payment. Input: JSON with to, amount, merchant (optional), memo (optional)"
    ),
]

# Use with LangChain agent
from langchain.agents import initialize_agent, AgentType

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

agent.run("Pay $10 to OpenAI for API credits")
```

### Cursor/Windsurf

The Sardis MCP server works with any MCP-compatible editor:

```json
// .cursor/mcp.json or similar
{
  "servers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server"],
      "env": {
        "SARDIS_API_KEY": "sk_xxx",
        "SARDIS_WALLET_ID": "wallet_xxx"
      }
    }
  }
}
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Your AI Agent                          │
│                   (GPT-4, Claude, etc.)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Sardis SDK/MCP                          │
│              (TypeScript, Python, MCP Server)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Sardis API                             │
│                   (FastAPI + PostgreSQL)                    │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Policy    │  │   Wallet    │  │    Transaction      │ │
│  │   Engine    │  │   Manager   │  │      Service        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Turnkey MPC   │  │  Smart Contract │  │   Compliance    │
│  (Non-custodial)│  │   (Base/ETH)    │  │  (KYC/AML)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Next Steps

1. **Get API Keys**: Contact us at hello@sardis.dev for production access
2. **Configure Policies**: Set spending limits and category restrictions via API
3. **Enable Compliance**: Add KYC/AML for regulated use cases
4. **Set Up Monitoring**: Configure webhooks for transaction alerts
5. **Scale**: Deploy to multiple regions for low latency

## Troubleshooting

### "Policy violation" error
- Check if amount exceeds per-transaction limit ($500 default)
- Check if you've hit daily limit ($1000 default)
- Check if merchant category is blocked

### "Insufficient balance" error
- Fund the wallet with more USDC
- Check if balance is held by pending authorizations

### "Wallet not found" error
- Verify wallet ID is correct
- Check if wallet was created for correct chain

### API connection errors
- Verify `SARDIS_API_KEY` is set
- Check `baseUrl` if using local/staging environment
- Verify network connectivity

## Support

- **Documentation**: https://docs.sardis.dev
- **Discord**: https://discord.gg/sardis
- **Email**: support@sardis.dev
- **GitHub**: https://github.com/sardis-labs/sardis

---

Built with ❤️ for the AI agent economy.
