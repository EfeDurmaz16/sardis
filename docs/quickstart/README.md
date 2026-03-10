# Sardis Quickstart — Your First Payment in 15 Minutes

This guide walks through the same 5-step workflow across every Sardis surface.
All examples use identical entity names, field names, and payloads so you can
switch surfaces without relearning anything.

---

## The Workflow

Every Sardis integration follows the same 5 steps:

1. **Create an Agent** — the identity that owns wallets and policies
2. **Create a Wallet** — a non-custodial MPC wallet tied to the agent
3. **Set a Spending Policy** — natural language rules enforced on every transaction
4. **Make a Payment** — execute a policy-gated payment
5. **View Evidence** — inspect the tamper-proof ledger entry

---

## Option A: Dashboard (No Code)

1. Sign up at [sardis.sh/signup](https://sardis.sh/signup)
2. Complete the onboarding wizard — it creates an Agent, a Wallet, and a
   default Policy in one flow
3. Go to **Sandbox → Make a test payment** and fill in any amount up to $100
4. Open **Evidence** in the sidebar to see the ledger entry, policy verdict,
   and transaction receipt

No API key is required for sandbox mode.

---

## Option B: Python SDK

### Install

```bash
pip install sardis-sdk
```

### Run

```python
import asyncio
from sardis import AsyncSardisClient

async def main():
    async with AsyncSardisClient(api_key="sk_...") as client:

        # 1. Create Agent
        agent = await client.agents.create(name="Quickstart Agent")
        print(f"Agent:  {agent.agent_id}")

        # 2. Create Wallet
        wallet = await client.wallets.create(
            agent_id=agent.agent_id,
            chain="base",
        )
        print(f"Wallet: {wallet.wallet_id}  address={wallet.address}")

        # 3. Set Policy
        policy = await client.policies.parse(
            text="Max $100 per transaction, $500 per day",
        )
        await client.policies.apply(
            wallet_id=wallet.wallet_id,
            policy=policy,
        )
        print(f"Policy: {policy.policy_id}")

        # 4. Make Payment
        payment = await client.payments.send(
            wallet_id=wallet.wallet_id,
            to="merchant_demo",
            amount="25.00",
            purpose="API credits",
        )
        print(f"Payment: {payment.payment_id}  status={payment.status}")

        # 5. View Evidence
        entry = await client.ledger.get(payment_id=payment.payment_id)
        print(f"Evidence: {entry.ledger_id}  anchored={entry.anchored_at}")

asyncio.run(main())
```

### Error handling

```python
from sardis.exceptions import PolicyViolationError, InsufficientBalanceError

try:
    payment = await client.payments.send(
        wallet_id=wallet.wallet_id,
        to="merchant_demo",
        amount="200.00",   # exceeds the $100/tx limit
        purpose="API credits",
    )
except PolicyViolationError as e:
    print(f"Blocked by policy: {e.message} (limit={e.limit})")
except InsufficientBalanceError as e:
    print(f"Insufficient balance: {e.message}")
```

---

## Option C: TypeScript SDK

### Install

```bash
npm install @sardis/sdk
# or
yarn add @sardis/sdk
```

### Run

```typescript
import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({ apiKey: 'sk_...' });

// 1. Create Agent
const agent = await client.agents.create({ name: 'Quickstart Agent' });
console.log(`Agent:  ${agent.agentId}`);

// 2. Create Wallet
const wallet = await client.wallets.create({
  agentId: agent.agentId,
  chain: 'base',
});
console.log(`Wallet: ${wallet.walletId}  address=${wallet.address}`);

// 3. Set Policy
const policy = await client.policies.parse({
  text: 'Max $100 per transaction, $500 per day',
});
await client.policies.apply({
  walletId: wallet.walletId,
  policy,
});
console.log(`Policy: ${policy.policyId}`);

// 4. Make Payment
const payment = await client.payments.send({
  walletId: wallet.walletId,
  to: 'merchant_demo',
  amount: '25.00',
  purpose: 'API credits',
});
console.log(`Payment: ${payment.paymentId}  status=${payment.status}`);

// 5. View Evidence
const entry = await client.ledger.get({ paymentId: payment.paymentId });
console.log(`Evidence: ${entry.ledgerId}  anchored=${entry.anchoredAt}`);
```

### Error handling

```typescript
import { PolicyViolationError, InsufficientBalanceError } from '@sardis/sdk';

try {
  await client.payments.send({
    walletId: wallet.walletId,
    to: 'merchant_demo',
    amount: '200.00',   // exceeds the $100/tx limit
    purpose: 'API credits',
  });
} catch (error) {
  if (error instanceof PolicyViolationError) {
    console.error(`Blocked by policy: ${error.message} (limit=${error.limit})`);
  } else if (error instanceof InsufficientBalanceError) {
    console.error(`Insufficient balance: ${error.message}`);
  } else {
    throw error;
  }
}
```

---

## Option D: REST API (cURL)

Replace `sk_...` with your API key and substitute IDs returned by each step.

```bash
# 1. Create Agent
curl -s -X POST https://api.sardis.sh/api/v2/agents \
  -H "X-API-Key: sk_..." \
  -H "Content-Type: application/json" \
  -d '{"name": "Quickstart Agent"}'
# → {"agent_id": "agent_...", "name": "Quickstart Agent", ...}

# 2. Create Wallet
curl -s -X POST https://api.sardis.sh/api/v2/wallets \
  -H "X-API-Key: sk_..." \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "agent_...", "chain": "base"}'
# → {"wallet_id": "wal_...", "address": "0x...", ...}

# 3a. Parse Policy
curl -s -X POST https://api.sardis.sh/api/v2/policies/parse \
  -H "X-API-Key: sk_..." \
  -H "Content-Type: application/json" \
  -d '{"text": "Max $100 per transaction, $500 per day"}'
# → {"policy_id": "pol_...", "rules": [...]}

# 3b. Apply Policy
curl -s -X POST https://api.sardis.sh/api/v2/policies/apply \
  -H "X-API-Key: sk_..." \
  -H "Content-Type: application/json" \
  -d '{"wallet_id": "wal_...", "policy_id": "pol_..."}'
# → {"ok": true}

# 4. Make Payment
curl -s -X POST https://api.sardis.sh/api/v2/payments \
  -H "X-API-Key: sk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "wal_...",
    "to": "merchant_demo",
    "amount": "25.00",
    "purpose": "API credits"
  }'
# → {"payment_id": "pay_...", "status": "success", "tx_hash": "0x...", ...}

# 5. View Evidence
curl -s https://api.sardis.sh/api/v2/ledger?payment_id=pay_... \
  -H "X-API-Key: sk_..."
# → {"ledger_id": "ldg_...", "anchored_at": "...", "verdict": "approved", ...}
```

---

## Option E: Sandbox (No API Key)

Try the full payment flow without creating an account. All sandbox calls are
simulated — no real funds move.

```bash
# Make a sandbox payment
curl -s -X POST https://api.sardis.sh/api/v2/sandbox/payment \
  -H "Content-Type: application/json" \
  -d '{"amount": 25.00, "merchant": "OpenAI API"}'
# → {"payment_id": "sandbox_pay_...", "status": "approved", ...}

# View the sandbox ledger
curl -s https://api.sardis.sh/api/v2/sandbox/ledger
# → [{"payment_id": "sandbox_pay_...", "amount": 25.00, "merchant": "OpenAI API", ...}]
```

The sandbox resets every 24 hours. To persist data, sign up for a free account
and use a `sk_test_...` key instead.

---

## What's Next?

| Goal | Where to go |
|------|------------|
| Real-time notifications | [Webhooks guide](../docs/api/webhooks.md) |
| Virtual card for your agent | [Cards docs](../docs/concepts/wallets.md#virtual-cards) |
| Connect Browser Use for autonomous shopping | [Browser Use integration](../docs/integrations/overview.md) |
| Multi-agent workflows with CrewAI | [CrewAI integration](../docs/integrations/overview.md) |
| MCP server for Claude / Cursor | [MCP server docs](../docs/integrations/mcp.md) |
| Full API reference | [sardis.sh/docs/api](https://sardis.sh/docs/api) |
| Python SDK reference | [Python SDK](../docs/sdks/python.md) |
| TypeScript SDK reference | [TypeScript SDK](../docs/sdks/typescript.md) |

---

## Entity Glossary

These names are consistent across every surface (dashboard labels, SDK method
names, REST field names, and webhook payloads).

| Entity | ID prefix | Description |
|--------|-----------|-------------|
| Agent | `agent_` | The AI agent identity. Owns wallets. |
| Wallet | `wal_` | Non-custodial MPC wallet. Holds funds. |
| Policy | `pol_` | Spending rules parsed from natural language. |
| Payment Intent | `pay_` | A request to move funds. Goes through policy check first. |
| Ledger Entry | `ldg_` | Immutable audit record for a completed payment. |
