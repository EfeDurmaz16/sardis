# Sardis Fiat Ramp SDK

[![npm version](https://img.shields.io/npm/v/@sardis/ramp.svg)](https://www.npmjs.com/package/@sardis/ramp)
[![npm downloads](https://img.shields.io/npm/dm/@sardis/ramp.svg)](https://www.npmjs.com/package/@sardis/ramp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)

Bridge crypto wallets to traditional banking with fiat on/off ramp functionality. Enable AI agents and applications to fund wallets from bank accounts and withdraw to fiat.

**Supports multiple providers:**
- **Onramper** - Aggregator with 100+ payment providers (Moonpay, Transak, Ramp, Simplex, etc.)
- **Bridge.xyz** - Direct integration for ACH/wire transfers

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Onramper Integration](#onramper-integration)
- [Bridge Integration](#bridge-integration)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [TypeScript Support](#typescript-support)
- [License](#license)

## Installation

```bash
npm install @sardis/ramp
# or
yarn add @sardis/ramp
# or
pnpm add @sardis/ramp
```

## Quick Start

### Option 1: Onramper (Recommended)

Onramper aggregates 100+ payment providers, offering the best rates and widest coverage.

```typescript
import { SardisOnramper } from '@sardis/ramp';

const onramper = new SardisOnramper({
  apiKey: 'your-onramper-api-key',
  sardisKey: 'your-sardis-api-key',
  mode: 'production',
});

// Get widget URL to fund a Sardis wallet
const { widgetUrl } = await onramper.fundWallet({
  walletId: 'wallet_123',
  fiatAmount: 100,
  fiatCurrency: 'USD',
});

// Open widget in new window or embed in iframe
window.open(widgetUrl, '_blank');

// Or get the best quote programmatically
const quote = await onramper.getBestQuote({
  sourceCurrency: 'USD',
  destinationCurrency: 'USDC',
  amount: 100,
  network: 'base',
});

console.log(`Best rate: $100 → ${quote.destinationAmount} USDC via ${quote.provider}`);
```

### Option 2: Bridge.xyz (Direct)

For direct ACH/wire transfers with predictable fees.

```typescript
import { SardisFiatRamp } from '@sardis/ramp';

const ramp = new SardisFiatRamp({
  sardisKey: 'your-sardis-api-key',
  bridgeKey: 'your-bridge-api-key',
  environment: 'sandbox',
});

// Fund a wallet from a bank account
const funding = await ramp.fundWallet({
  walletId: 'wallet_123',
  amountUsd: 100,
  method: 'bank',
});

console.log('ACH Instructions:', funding.achInstructions);
console.log('Estimated arrival:', funding.estimatedArrival);
```

## Onramper Integration

### Widget Integration

The easiest way to integrate fiat on-ramp is via the Onramper widget:

```typescript
import { SardisOnramper } from '@sardis/ramp';

const onramper = new SardisOnramper({
  apiKey: process.env.ONRAMPER_API_KEY,
  sardisKey: process.env.SARDIS_API_KEY,
});

// Generate widget URL
const url = onramper.getWidgetUrl({
  walletAddress: '0x...',
  network: 'base',
  fiatCurrency: 'USD',
  cryptoCurrency: 'USDC',
  fiatAmount: 100,
  darkMode: true,
  color: 'FF6B35', // Sardis orange
});

// Or get iframe HTML
const iframe = onramper.getWidgetIframe({
  walletAddress: '0x...',
  network: 'base',
  fiatAmount: 100,
  width: '400px',
  height: '600px',
});
```

### Get Quotes

Compare rates from all providers:

```typescript
// Get all quotes
const quotes = await onramper.getQuotes({
  sourceCurrency: 'EUR',
  destinationCurrency: 'USDC',
  amount: 200,
  network: 'base',
});

quotes.forEach(q => {
  console.log(`${q.provider}: €200 → ${q.destinationAmount} USDC (fee: €${q.fees.total})`);
});

// Or get just the best quote
const best = await onramper.getBestQuote({
  sourceCurrency: 'TRY',
  destinationCurrency: 'USDC',
  amount: 5000,
  network: 'base',
});
```

### Supported Assets

```typescript
// Get supported fiat currencies
const fiats = await onramper.getSupportedFiats();
// ['USD', 'EUR', 'GBP', 'TRY', ...]

// Get supported crypto on a network
const cryptos = await onramper.getSupportedCryptos('base');
// ['USDC', 'ETH', 'USDT', ...]

// Get payment methods for a country
const methods = await onramper.getSupportedPaymentMethods('TR');
// ['creditCard', 'bankTransfer', ...]
```

### Webhooks

Handle transaction updates:

```typescript
// In your webhook handler
app.post('/webhooks/onramper', (req, res) => {
  const signature = req.headers['x-onramper-signature'];

  if (!onramper.verifyWebhookSignature(req.body, signature, WEBHOOK_SECRET)) {
    return res.status(401).send('Invalid signature');
  }

  const { event, transaction } = onramper.parseWebhookPayload(req.body);

  if (event === 'transaction.completed') {
    console.log(`Received ${transaction.destinationAmount} USDC`);
    // Credit user account, send notification, etc.
  }

  res.status(200).send('OK');
});
```

---

## Bridge Integration

### Fund Wallets (On-Ramp)

Fund Sardis wallets from fiat sources including bank transfers, wire transfers, and cards.

```typescript
// Fund via bank transfer (ACH)
const bankFunding = await ramp.fundWallet({
  walletId: 'wallet_123',
  amountUsd: 500,
  method: 'bank',
});

// Returns ACH deposit instructions
console.log(bankFunding.achInstructions);
// {
//   accountNumber: '...',
//   routingNumber: '...',
//   bankName: '...',
//   accountHolder: '...',
//   reference: '...'
// }

// Fund via crypto (direct deposit)
const cryptoFunding = await ramp.fundWallet({
  walletId: 'wallet_123',
  amountUsd: 1000,
  method: 'crypto',
});

console.log('Deposit to:', cryptoFunding.depositAddress);
console.log('Chain:', cryptoFunding.chain);
```

### Withdraw to Bank (Off-Ramp)

Withdraw funds from crypto wallets to traditional bank accounts.

```typescript
const withdrawal = await ramp.withdrawToBank({
  walletId: 'wallet_123',
  amountUsd: 250,
  bankAccount: {
    accountHolderName: 'John Doe',
    accountNumber: '1234567890',
    routingNumber: '021000021',
    accountType: 'checking', // or 'savings'
  },
});

console.log('Transaction hash:', withdrawal.txHash);
console.log('Payout ID:', withdrawal.payoutId);
console.log('Estimated arrival:', withdrawal.estimatedArrival);
console.log('Fee:', withdrawal.fee);
```

### Pay Merchants in Fiat

Pay merchants and vendors in USD directly from crypto wallets.

```typescript
const payment = await ramp.payMerchantFiat({
  walletId: 'wallet_123',
  amountUsd: 99.99,
  merchant: {
    name: 'ACME Corp',
    bankAccount: {
      accountHolderName: 'ACME Corp',
      accountNumber: '9876543210',
      routingNumber: '021000021',
    },
    category: 'software', // Optional: for policy validation
  },
});

if (payment.status === 'completed') {
  console.log('Payment ID:', payment.paymentId);
  console.log('Merchant received:', payment.merchantReceived);
} else if (payment.status === 'pending_approval') {
  console.log('Requires approval:', payment.approvalRequest);
}
```

### Check Transfer Status

Monitor the status of funding and withdrawal operations.

```typescript
// Check funding status
const fundingStatus = await ramp.getFundingStatus('transfer_abc123');

// Check withdrawal status
const withdrawalStatus = await ramp.getWithdrawalStatus('payout_xyz789');
```

## API Reference

### `SardisFiatRamp`

#### Constructor

```typescript
new SardisFiatRamp(config: RampConfig)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sardisKey` | `string` | Yes | Your Sardis API key |
| `bridgeKey` | `string` | Yes | Your Bridge API key |
| `environment` | `'sandbox' \| 'production'` | No | Environment (default: sandbox) |
| `sardisUrl` | `string` | No | Custom Sardis API URL |
| `bridgeUrl` | `string` | No | Custom Bridge API URL |
| `timeout` | `number` | No | Request timeout in ms (default: 30000) |

#### Methods

| Method | Description |
|--------|-------------|
| `fundWallet(params)` | Fund a wallet from fiat sources |
| `withdrawToBank(params)` | Withdraw funds to a bank account |
| `payMerchantFiat(params)` | Pay a merchant in USD |
| `getWallet(walletId)` | Get wallet details |
| `getFundingStatus(transferId)` | Check funding transfer status |
| `getWithdrawalStatus(payoutId)` | Check withdrawal payout status |

### Types

```typescript
type FundingMethod = 'bank' | 'card' | 'crypto';

interface BankAccount {
  accountHolderName: string;
  accountNumber: string;
  routingNumber: string;
  accountType?: 'checking' | 'savings';
  bankName?: string;
  // For international wires
  swiftCode?: string;
  iban?: string;
  bankAddress?: string;
}

interface FundingResult {
  type: 'crypto' | 'fiat';
  // For crypto deposits
  depositAddress?: string;
  chain?: string;
  token?: string;
  // For fiat deposits
  paymentLink?: string;
  achInstructions?: ACHDetails;
  wireInstructions?: WireDetails;
  estimatedArrival?: Date;
  feePercent?: number;
  transferId?: string;
}

interface WithdrawalResult {
  txHash: string;
  payoutId: string;
  estimatedArrival: Date;
  fee: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

interface PaymentResult {
  status: 'completed' | 'pending_approval' | 'failed';
  paymentId?: string;
  merchantReceived?: number;
  fee?: number;
  txHash?: string;
  approvalRequest?: Record<string, unknown>;
  error?: string;
}
```

## Configuration

### Environment Variables

You can also configure the SDK using environment variables:

```bash
SARDIS_API_KEY=your-sardis-key
BRIDGE_API_KEY=your-bridge-key
SARDIS_ENVIRONMENT=sandbox
```

### Custom URLs

For enterprise deployments or testing, you can specify custom API URLs:

```typescript
const ramp = new SardisFiatRamp({
  sardisKey: 'your-key',
  bridgeKey: 'your-bridge-key',
  sardisUrl: 'https://api.custom-sardis.example.com/v2',
  bridgeUrl: 'https://api.custom-bridge.example.com/v0',
});
```

## Error Handling

The SDK provides typed errors for common failure cases:

```typescript
import { SardisFiatRamp, RampError, PolicyViolation } from '@sardis/ramp';

try {
  const result = await ramp.withdrawToBank({
    walletId: 'wallet_123',
    amountUsd: 10000,
    bankAccount: { ... },
  });
} catch (error) {
  if (error instanceof PolicyViolation) {
    console.error('Policy violation:', error.message);
    // Handle policy rejection (e.g., spending limit exceeded)
  } else if (error instanceof RampError) {
    console.error(`Ramp error [${error.code}]:`, error.message);
    // Handle other ramp-specific errors
  } else {
    console.error('Unexpected error:', error);
  }
}
```

### Error Types

| Error | Description |
|-------|-------------|
| `RampError` | Base error class for all ramp errors |
| `PolicyViolation` | Payment violates wallet spending policy |

## TypeScript Support

This package is written in TypeScript and exports all types:

```typescript
import type {
  RampConfig,
  FundingMethod,
  FundingResult,
  WithdrawalResult,
  PaymentResult,
  BankAccount,
  MerchantAccount,
  ACHDetails,
  WireDetails,
  Wallet,
} from '@sardis/ramp';
```

## Requirements

- Node.js 18.0.0 or higher
- TypeScript 4.7+ (optional, for type definitions)

## Support

- [Documentation](https://docs.sardis.network)
- [GitHub Issues](https://github.com/sardis-network/sardis/issues)
- [Discord Community](https://discord.gg/sardis)

## License

MIT - see [LICENSE](./LICENSE) for details.
