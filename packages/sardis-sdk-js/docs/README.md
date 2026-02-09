# Sardis TypeScript SDK Documentation

The official TypeScript SDK for interacting with the Sardis payment platform.

## Installation

```bash
npm install @sardis/sdk
# or
yarn add @sardis/sdk
```

## Quick Start

```typescript
import { SardisClient } from '@sardis/sdk';

// Initialize client
const client = new SardisClient({
  apiKey: 'sk_your_api_key',
  baseUrl: 'https://api.sardis.sh', // Optional
});

// Execute a payment
const result = await client.payments.execute({
  fromWallet: 'wallet_001',
  destination: '0x1234567890123456789012345678901234567890',
  amount: 100.00,
  token: 'USDC',
  chain: 'base_sepolia',
});

console.log(`Transaction: ${result.chainTxHash}`);
```

## Configuration

### Environment Variables

```bash
SARDIS_API_KEY=sk_your_api_key
SARDIS_API_BASE_URL=https://api.sardis.sh
```

### Client Options

```typescript
const client = new SardisClient({
  apiKey: 'sk_...',
  baseUrl: 'https://api.sardis.sh',
  timeout: 30000,
  maxRetries: 3,
  retryDelay: 1000,
});
```

## Resources

- [Payments](./payments.md) - Execute and manage payments
- [Holds](./holds.md) - Pre-authorization and captures
- [Webhooks](./webhooks.md) - Event subscriptions
- [Marketplace](./marketplace.md) - A2A service marketplace
- [Transactions](./transactions.md) - Transaction status and history
- [Ledger](./ledger.md) - Audit trail access
- [Error Handling](./errors.md) - Exception handling

## Error Handling

```typescript
import { SardisClient, APIError, AuthenticationError, RateLimitError } from '@sardis/sdk';

try {
  const result = await client.payments.execute({...});
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.log('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.log(`Rate limited. Retry after ${error.retryAfter}s`);
  } else if (error instanceof APIError) {
    console.log(`API error: ${error.statusCode} - ${error.message}`);
  }
}
```

## TypeScript Support

The SDK is written in TypeScript and provides full type definitions:

```typescript
import { 
  SardisClient, 
  PaymentResult, 
  Hold, 
  Transaction 
} from '@sardis/sdk';

// Type-safe method calls
const result: PaymentResult = await client.payments.execute({
  fromWallet: 'wallet_001',
  destination: '0x...',
  amount: 100.00,
});

// IntelliSense for all properties
console.log(result.ledgerTxId);
console.log(result.chainTxHash);
```

## Browser and Node.js Support

The SDK works in both environments:

```typescript
// Node.js
import { SardisClient } from '@sardis/sdk';

// Browser (ESM)
import { SardisClient } from '@sardis/sdk';

// Browser (CommonJS)
const { SardisClient } = require('@sardis/sdk');
```

## Cleanup

```typescript
// Close client when done
await client.close();

// Or use the client in a try-finally block
try {
  const result = await client.payments.execute({...});
} finally {
  await client.close();
}
```

