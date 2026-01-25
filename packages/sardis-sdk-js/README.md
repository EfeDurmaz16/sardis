# Sardis TypeScript SDK

The official TypeScript SDK for the Sardis stablecoin execution layer. Enables AI agents to execute programmable payments using stablecoins across multiple chains.

## Installation

```bash
npm install @sardis/sdk
# or
yarn add @sardis/sdk
# or
pnpm add @sardis/sdk
```

## Quick Start

```typescript
import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({
  apiKey: 'your-api-key',
});

// Check API health
const health = await client.health();
console.log(`API Status: ${health.status}`);

// Execute a payment mandate
const result = await client.payments.executeMandate({
  mandate_id: 'mandate_123',
  subject: 'wallet_abc',
  destination: '0x...',
  amount_minor: 10000000, // $10.00 USDC (6 decimals)
  token: 'USDC',
  chain: 'base',
});
console.log(`Payment executed: ${result.tx_hash}`);
```

## Features

### Payments

Execute single mandates or full AP2 payment bundles:

```typescript
// Execute AP2 bundle (Intent → Cart → Payment)
const result = await client.payments.executeAP2(
  intentMandate,
  cartMandate,
  paymentMandate
);
```

### Holds (Pre-Authorization)

Create, capture, and void pre-authorization holds:

```typescript
// Create a hold
const hold = await client.holds.create({
  wallet_id: 'wallet_123',
  amount: '100.00',
  token: 'USDC',
  merchant_id: 'merchant_456',
  duration_hours: 24,
});

// Capture the hold (complete payment)
const captured = await client.holds.capture(hold.hold_id, '95.00');

// Or void the hold (cancel)
await client.holds.void(hold.hold_id);
```

### Webhooks

Manage webhook subscriptions for real-time events:

```typescript
// Create a webhook subscription
const webhook = await client.webhooks.create({
  url: 'https://your-server.com/webhooks',
  events: ['payment.completed', 'hold.captured'],
});

// List deliveries
const deliveries = await client.webhooks.listDeliveries(webhook.id);
```

### Marketplace (A2A)

Discover and interact with agent-to-agent services:

```typescript
// List available services
const services = await client.marketplace.listServices({
  category: 'ai',
});

// Create an offer
const offer = await client.marketplace.createOffer({
  service_id: 'service_123',
  consumer_agent_id: 'agent_456',
  total_amount: '50.00',
});

// Accept an offer (as provider)
await client.marketplace.acceptOffer(offer.id);
```

### Transactions

Get gas estimates and transaction status:

```typescript
// Estimate gas
const estimate = await client.transactions.estimateGas({
  chain: 'base',
  to_address: '0x...',
  amount: '100.00',
  token: 'USDC',
});
console.log(`Estimated cost: ${estimate.estimated_cost_wei} wei`);

// Check transaction status
const status = await client.transactions.getStatus('0x...', 'base');
```

### Ledger

Query the append-only ledger:

```typescript
// List ledger entries
const entries = await client.ledger.listEntries({ wallet_id: 'wallet_123' });

// Verify an entry
const verification = await client.ledger.verifyEntry('tx_123');
```

## Error Handling

The SDK provides typed exceptions for common error cases:

```typescript
import {
  SardisError,
  APIError,
  AuthenticationError,
  RateLimitError,
  InsufficientBalanceError,
} from '@sardis/sdk';

try {
  const result = await client.payments.executeMandate(mandate);
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited, retry after ${error.retryAfter} seconds`);
  } else if (error instanceof InsufficientBalanceError) {
    console.error(`Need ${error.required} ${error.currency}, have ${error.available}`);
  } else if (error instanceof APIError) {
    console.error(`API error [${error.code}]: ${error.message}`);
  }
}
```

## Configuration

```typescript
const client = new SardisClient({
  baseUrl: 'https://api.sardis.network', // API base URL (optional)
  apiKey: 'sk_live_...',                  // Your API key (required)
  timeout: 30000,                         // Request timeout in ms (optional)
  maxRetries: 3,                          // Max retry attempts (optional)
});
```

## Agents

Create and manage AI agents with spending policies:

```typescript
// Create an agent
const agent = await client.agents.create({
  name: 'Invoice Processing Agent',
  description: 'Processes invoices and pays vendors',
  spending_limits: {
    per_transaction: '500.00',
    daily: '5000.00',
    monthly: '50000.00',
  },
  policy: {
    blocked_categories: ['gambling', 'adult'],
    approval_threshold: '1000.00',
  },
});

// Update spending limits
await client.agents.update(agent.id, {
  spending_limits: { daily: '10000.00' },
});

// List agents
const agents = await client.agents.list({ is_active: true, limit: 50 });
```

## Wallets

Manage non-custodial MPC wallets:

```typescript
// Create a wallet for an agent
const wallet = await client.wallets.create({
  agent_id: agent.id,
  mpc_provider: 'turnkey', // or 'fireblocks'
  limit_per_tx: '500.00',
  limit_total: '10000.00',
});

// Get wallet balance (read from chain)
const balance = await client.wallets.getBalance(wallet.id, 'base', 'USDC');
console.log(`Balance: ${balance.balance} USDC`);

// Set chain address
await client.wallets.setAddress(wallet.id, 'base', '0x...');
```

## Supported Chains

| Chain | Mainnet | Testnet |
|-------|---------|---------|
| Base | `base` | `base_sepolia` |
| Polygon | `polygon` | `polygon_amoy` |
| Ethereum | `ethereum` | `ethereum_sepolia` |
| Arbitrum | `arbitrum` | `arbitrum_sepolia` |
| Optimism | `optimism` | `optimism_sepolia` |

> **Note:** Solana support is planned but not yet implemented.

## Supported Tokens

- **USDC** - USD Coin (Circle)
- **USDT** - Tether USD
- **PYUSD** - PayPal USD
- **EURC** - Euro Coin (Circle)

## TypeScript Support

This SDK is written in TypeScript and provides full type definitions for all API responses.

```typescript
import type {
  Chain,
  Token,
  MPCProvider,
  Payment,
  Hold,
  Webhook,
  Service,
  GasEstimate,
  Agent,
  Wallet,
  WalletBalance,
} from '@sardis/sdk';

// Type-safe chain selection
const chain: Chain = 'base';
const token: Token = 'USDC';
```

## Framework Integrations

### LangChain.js

```typescript
import { SardisToolkit } from '@sardis/sdk/integrations/langchain';

const toolkit = new SardisToolkit({ client });
const tools = toolkit.getTools();

// Use with LangChain agent
const agent = createOpenAIFunctionsAgent({ llm, tools, prompt });
```

### Vercel AI SDK

```typescript
import { sardisTools } from '@sardis/sdk/integrations/vercel-ai';

const tools = sardisTools(client);

// Use with Vercel AI
const { text } = await generateText({
  model: openai('gpt-4'),
  tools,
  messages,
});
```

### OpenAI Function Calling

```typescript
import { sardisFunctions, handleSardisCall } from '@sardis/sdk/integrations/openai';

// Get function definitions
const functions = sardisFunctions(client);

// Handle function calls
const result = await handleSardisCall(client, functionName, args);
```

## License

MIT
