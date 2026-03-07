# @sardis/stagehand

Sardis payment tools for [Stagehand](https://github.com/browserbase/stagehand) browser agents. Gives your AI browser agent policy-controlled access to a Sardis wallet for making real payments during web sessions.

## Install

```bash
npm install @sardis/stagehand @sardis/sdk
```

## Quickstart

**1. Configure environment**

```bash
export SARDIS_API_KEY=sk_...
export SARDIS_WALLET_ID=wallet_...
```

**2. Register tools with your Stagehand agent**

```typescript
import { Stagehand } from '@browserbasehq/stagehand';
import { createSardisTools } from '@sardis/stagehand';

const stagehand = new Stagehand({ env: 'BROWSERBASE' });
await stagehand.init();

const tools = createSardisTools({
  apiKey: process.env.SARDIS_API_KEY,
  walletId: process.env.SARDIS_WALLET_ID,
  chain: 'base',   // default
  token: 'USDC',   // default
});
```

**3. Use tools in your agent loop**

```typescript
// Check balance before acting
const balance = await tools.sardis_check_balance.execute({});
console.log(`Available: ${balance.balance} ${balance.token}`);

// Verify policy allows the spend
const policy = await tools.sardis_check_policy.execute({
  amount: 49.99,
  merchant: 'acme-shop.com',
});

if (policy.allowed) {
  // Execute the payment
  const result = await tools.sardis_pay.execute({
    amount: 49.99,
    merchant: 'acme-shop.com',
    purpose: 'SaaS subscription renewal',
  });
  console.log(result.transactionHash);
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `sardis_pay` | Execute a policy-controlled USDC payment |
| `sardis_check_balance` | Read current wallet balance |
| `sardis_check_policy` | Dry-run a spend against the wallet's spending policy |

## License

MIT
