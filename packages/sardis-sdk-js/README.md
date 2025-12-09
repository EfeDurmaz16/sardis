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

## Supported Chains

- Base (mainnet & Sepolia testnet)
- Polygon (mainnet & Amoy testnet)
- Ethereum (mainnet & Sepolia testnet)

## Supported Tokens

- USDC
- USDT
- PYUSD
- EURC

## TypeScript Support

This SDK is written in TypeScript and provides full type definitions for all API responses.

```typescript
import type {
  Payment,
  Hold,
  Webhook,
  Service,
  GasEstimate,
} from '@sardis/sdk';
```

## License

MIT
