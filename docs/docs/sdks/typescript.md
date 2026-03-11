# TypeScript SDK

Official TypeScript/JavaScript SDK for Sardis Payment OS.

## Installation

```bash
npm install @sardis/sdk
```

Or with yarn:

```bash
yarn add @sardis/sdk
```

## Quick Start

```typescript
import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({ apiKey: 'sk_...' });

// Create wallet
const wallet = await client.wallets.create({
  name: 'my-agent',
  chain: 'base',
  policy: 'Max $500/day',
});

// Execute payment
const payment = await client.payments.execute({
  walletId: wallet.id,
  to: '0x1234...',
  amount: '50',
  token: 'USDC',
});

console.log(`TX: ${payment.txHash}`);
```

## Client Initialization

### Basic

```typescript
import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({ apiKey: 'sk_...' });
```

### With Options

```typescript
const client = new SardisClient({
  apiKey: 'sk_...',
  environment: 'production', // or 'testnet'
  timeout: 30000, // Request timeout in ms
  maxRetries: 3, // Retry failed requests
  simulation: false, // Enable simulation mode
});
```

### Environment Variables

```typescript
// Set in .env file
// SARDIS_API_KEY=sk_...

const client = new SardisClient({
  apiKey: process.env.SARDIS_API_KEY!,
});
```

## Wallets

### Create Wallet

```typescript
const wallet = await client.wallets.create({
  name: 'my-agent-wallet',
  chain: 'base',
  policy: 'Max $500/day, only SaaS vendors',
  metadata: {
    department: 'engineering',
    costCenter: 'CC-1234',
  },
});

console.log(`Wallet: ${wallet.id}`);
console.log(`Address: ${wallet.address}`);
```

### Get Wallet

```typescript
const wallet = await client.wallets.get('wallet_abc123');

console.log(`Name: ${wallet.name}`);
console.log(`Trust Score: ${wallet.trustScore}`);
```

### List Wallets

```typescript
const { wallets, total } = await client.wallets.list({
  limit: 100,
  offset: 0,
  status: 'active',
});

wallets.forEach((wallet) => {
  console.log(`${wallet.name}: ${wallet.address}`);
});
```

### Update Policy

```typescript
await client.wallets.updatePolicy('wallet_abc123', {
  policy: 'Max $1000/day, SaaS and cloud only',
});
```

### Freeze/Unfreeze

```typescript
// Freeze
await client.wallets.freeze('wallet_abc123', {
  reason: 'Suspected compromise',
});

// Unfreeze
await client.wallets.unfreeze('wallet_abc123');
```

### Delete Wallet

```typescript
await client.wallets.delete('wallet_abc123');
```

## Payments

### Execute Payment

```typescript
const payment = await client.payments.execute({
  walletId: 'wallet_abc123',
  to: '0x1234567890abcdef1234567890abcdef12345678',
  amount: '50.00',
  token: 'USDC',
  purpose: 'API credits',
  metadata: {
    invoiceId: 'INV-001',
  },
});

console.log(`Payment: ${payment.id}`);
console.log(`TX: ${payment.txHash}`);
console.log(`Status: ${payment.status}`);
```

### Get Payment

```typescript
const payment = await client.payments.get('payment_xyz789');

console.log(`Amount: ${payment.amount} ${payment.token}`);
console.log(`Block: ${payment.blockNumber}`);
```

### List Payments

```typescript
const { payments } = await client.payments.list({
  walletId: 'wallet_abc123',
  status: 'success',
  limit: 50,
});

payments.forEach((payment) => {
  console.log(`${payment.createdAt}: ${payment.amount} ${payment.token}`);
});
```

### Simulate Payment

```typescript
const result = await client.payments.simulate({
  walletId: 'wallet_abc123',
  to: '0x...',
  amount: '5000',
  token: 'USDC',
});

if (result.wouldSucceed) {
  console.log('Payment would succeed');
} else {
  console.log(`Would fail: ${result.violation?.message}`);
}
```

### Estimate Gas

```typescript
const estimate = await client.payments.estimateGas({
  walletId: 'wallet_abc123',
  to: '0x...',
  amount: '50',
  token: 'USDC',
});

console.log(`Gas cost: $${estimate.totalCostUsd}`);
```

## Balances

### Get Balance

```typescript
const balance = await client.balances.get('wallet_abc123', 'USDC');

console.log(`Balance: ${balance} USDC`);
```

### Get All Balances

```typescript
const balances = await client.balances.getAll('wallet_abc123');

Object.entries(balances).forEach(([token, amount]) => {
  console.log(`${token}: ${amount}`);
});
```

## Trust & KYA

### Get Trust Score

```typescript
const trust = await client.kya.getTrustScore('wallet_abc123');

console.log(`Score: ${trust.score}/100`);
console.log(`Level: ${trust.level}`);
```

### Trust History

```typescript
const history = await client.kya.trustHistory('wallet_abc123', {
  days: 30,
});

history.forEach((entry) => {
  console.log(`${entry.date}: ${entry.score} (${entry.reason})`);
});
```

### KYA Analysis

```typescript
const analysis = await client.kya.analyze('wallet_abc123');

console.log(`Trust Score: ${analysis.trustScore}`);
console.log(`Risk Factors: ${analysis.riskFactors}`);
console.log(`Recommendations: ${analysis.recommendations}`);
```

## Ledger

### List Entries

```typescript
const { entries } = await client.ledger.list({
  walletId: 'wallet_abc123',
  startDate: '2026-02-01',
  endDate: '2026-02-28',
});

entries.forEach((entry) => {
  console.log(`${entry.timestamp}: ${entry.type} ${entry.amount} ${entry.token}`);
});
```

### Reconcile

```typescript
const report = await client.ledger.reconcile('wallet_abc123', {
  date: '2026-02-21',
});

console.log(`Opening: ${report.openingBalance}`);
console.log(`Credits: ${report.totalCredits}`);
console.log(`Debits: ${report.totalDebits}`);
console.log(`Closing: ${report.closingBalance}`);
```

### Export

```typescript
const exportJob = await client.ledger.export({
  walletId: 'wallet_abc123',
  format: 'csv',
  startDate: '2026-01-01',
  endDate: '2026-12-31',
});

// Poll for completion
while (exportJob.status === 'processing') {
  await new Promise((resolve) => setTimeout(resolve, 2000));
  exportJob = await client.ledger.getExport(exportJob.id);
}

if (exportJob.status === 'complete') {
  console.log(`Download: ${exportJob.downloadUrl}`);
}
```

## Webhooks

### Create Webhook

```typescript
const webhook = await client.webhooks.create({
  url: 'https://your-app.com/sardis-webhook',
  events: [
    'wallet.payment.success',
    'wallet.payment.failed',
    'wallet.policy.violated',
  ],
  secret: 'whsec_example_placeholder', // nosecret,
});

console.log(`Webhook: ${webhook.id}`);
```

### List Webhooks

```typescript
const { webhooks } = await client.webhooks.list();

webhooks.forEach((webhook) => {
  console.log(`${webhook.id}: ${webhook.url}`);
});
```

### Delete Webhook

```typescript
await client.webhooks.delete('webhook_abc123');
```

## Error Handling

```typescript
import {
  SardisError,
  PolicyViolationError,
  InsufficientBalanceError,
  InvalidRequestError,
  AuthenticationError,
} from '@sardis/sdk';

try {
  const payment = await client.payments.execute({
    walletId: 'wallet_abc123',
    to: '0x...',
    amount: '10000',
    token: 'USDC',
  });
} catch (error) {
  if (error instanceof PolicyViolationError) {
    console.error(`Policy error: ${error.message}`);
    console.error(`Limit: ${error.limit}`);
    console.error(`Attempted: ${error.attempted}`);
  } else if (error instanceof InsufficientBalanceError) {
    console.error(`Balance error: ${error.message}`);
  } else if (error instanceof AuthenticationError) {
    console.error(`Auth error: ${error.message}`);
  } else if (error instanceof SardisError) {
    console.error(`Sardis error: ${error.message}`);
  } else {
    throw error;
  }
}
```

## TypeScript Types

Full TypeScript support:

```typescript
import type {
  Wallet,
  Payment,
  LedgerEntry,
  TrustScore,
  Webhook,
} from '@sardis/sdk';

const wallet: Wallet = await client.wallets.create({
  name: 'typed-wallet',
  chain: 'base',
});

const payments: Payment[] = (
  await client.payments.list({ walletId: wallet.id })
).payments;
```

## Zod Validation

Runtime validation with Zod:

```typescript
import { z } from 'zod';
import { WalletSchema, PaymentSchema } from '@sardis/sdk/schemas';

// Validate wallet data
const walletData = WalletSchema.parse({
  name: 'my-wallet',
  chain: 'base',
  policy: 'Max $500/day',
});

// Validate payment data
const paymentData = PaymentSchema.parse({
  walletId: 'wallet_abc123',
  to: '0x...',
  amount: '50',
  token: 'USDC',
});
```

## Pagination

```typescript
// Manual pagination
let offset = 0;
const limit = 100;

while (true) {
  const { payments, hasMore } = await client.payments.list({
    walletId: 'wallet_abc123',
    limit,
    offset,
  });

  if (!payments.length) break;

  payments.forEach((payment) => console.log(payment.id));

  if (!hasMore) break;
  offset += limit;
}

// Or use async iterator
for await (const payment of client.payments.iterate({ walletId: 'wallet_abc123' })) {
  console.log(payment.id);
}
```

## Logging

```typescript
import { SardisClient } from '@sardis/sdk';
import pino from 'pino';

const logger = pino({ level: 'debug' });

const client = new SardisClient({
  apiKey: 'sk_...',
  logger,
});
```

## Next.js Integration

```typescript
// app/api/sardis/route.ts
import { SardisClient } from '@sardis/sdk';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const client = new SardisClient({
    apiKey: process.env.SARDIS_API_KEY!,
  });

  const { walletId, amount, to } = await request.json();

  try {
    const payment = await client.payments.execute({
      walletId,
      to,
      amount,
      token: 'USDC',
    });

    return NextResponse.json({ success: true, payment });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: (error as Error).message },
      { status: 400 }
    );
  }
}
```

## Express.js Integration

```typescript
import express from 'express';
import { SardisClient } from '@sardis/sdk';

const app = express();
const client = new SardisClient({ apiKey: process.env.SARDIS_API_KEY! });

app.post('/payments', async (req, res) => {
  try {
    const payment = await client.payments.execute({
      walletId: req.body.walletId,
      to: req.body.to,
      amount: req.body.amount,
      token: 'USDC',
    });

    res.json({ success: true, payment });
  } catch (error) {
    res.status(400).json({
      success: false,
      error: (error as Error).message,
    });
  }
});

app.listen(3000);
```

## Testing

```typescript
import { SardisClient } from '@sardis/sdk';
import { describe, it, expect } from 'vitest';

describe('Sardis SDK', () => {
  const client = new SardisClient({
    apiKey: 'sk_test_...',
    simulation: true, // No real transactions
  });

  it('creates a wallet', async () => {
    const wallet = await client.wallets.create({
      name: 'test-wallet',
      chain: 'base_sepolia',
    });

    expect(wallet.id).toMatch(/^wallet_/);
    expect(wallet.chain).toBe('base_sepolia');
  });
});
```

## Best Practices

1. **Use environment variables** for API keys
2. **Handle errors explicitly** with proper types
3. **Enable retries** for production
4. **Use TypeScript** for type safety
5. **Set timeouts** appropriately
6. **Enable logging** for debugging
7. **Use simulation mode** for testing
8. **Validate inputs** with Zod schemas

## Next Steps

- [Python SDK](python.md) - Python SDK reference
- [CLI Reference](cli.md) - Command-line tool
- [API Reference](../api/rest.md) - Raw HTTP API
