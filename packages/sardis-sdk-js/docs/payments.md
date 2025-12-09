# Payments

Execute and manage stablecoin payments on supported chains.

## Execute Payment

```typescript
const result = await client.payments.execute({
  fromWallet: 'wallet_001',
  destination: '0x1234567890123456789012345678901234567890',
  amount: 100.00,
  token: 'USDC',
  chain: 'base_sepolia',
  purpose: 'Product purchase',
});
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `fromWallet` | string | Yes | Source wallet ID |
| `destination` | string | Yes | Destination address |
| `amount` | number | Yes | Amount to send |
| `token` | string | No | Token (default: USDC) |
| `chain` | string | No | Chain (default: base_sepolia) |
| `purpose` | string | No | Payment description |
| `idempotencyKey` | string | No | Unique key for deduplication |

### Response

```typescript
interface PaymentResult {
  ledgerTxId: string;
  chainTxHash: string;
  chain: string;
  status: 'pending' | 'confirmed' | 'failed';
  amount: string;
  token: string;
  complianceProvider: string;
}
```

## Execute AP2 Mandate

Execute a full AP2 mandate bundle:

```typescript
const result = await client.payments.executeMandate({
  intent: {
    mandateId: 'intent_001',
    issuer: 'user_123',
    subject: 'agent_456',
    // ... full intent mandate
  },
  cart: {
    mandateId: 'cart_001',
    // ... full cart mandate
  },
  payment: {
    mandateId: 'payment_001',
    // ... full payment mandate
  },
});
```

## Get Payment Status

```typescript
const status = await client.payments.getStatus({
  txHash: '0x1234567890abcdef...',
  chain: 'base_sepolia',
});

console.log(`Status: ${status.status}`);
console.log(`Confirmations: ${status.confirmations}`);
```

## Estimate Gas

```typescript
const estimate = await client.payments.estimateGas({
  chain: 'base_sepolia',
  amount: 100.00,
  token: 'USDC',
});

console.log(`Gas limit: ${estimate.gasLimit}`);
console.log(`Estimated cost: ${estimate.estimatedCostWei} wei`);
```

## Supported Chains

| Chain | Chain ID | Tokens |
|-------|----------|--------|
| `base_sepolia` | 84532 | USDC |
| `base` | 8453 | USDC |
| `polygon_amoy` | 80002 | USDC |
| `polygon` | 137 | USDC, USDT |
| `ethereum_sepolia` | 11155111 | USDC |

## Idempotency

```typescript
// First call
const result1 = await client.payments.execute({
  fromWallet: 'wallet_001',
  destination: '0x...',
  amount: 100.00,
  idempotencyKey: 'order_12345',
});

// Second call returns cached result
const result2 = await client.payments.execute({
  fromWallet: 'wallet_001',
  destination: '0x...',
  amount: 100.00,
  idempotencyKey: 'order_12345',
});

// result1.ledgerTxId === result2.ledgerTxId
```

## React Integration

```tsx
import { useSardis } from '@sardis/sdk/react';

function PaymentButton() {
  const { client, isLoading, error } = useSardis();

  const handlePayment = async () => {
    try {
      const result = await client.payments.execute({
        fromWallet: 'wallet_001',
        destination: '0x...',
        amount: 50.00,
      });
      console.log('Payment successful:', result.chainTxHash);
    } catch (err) {
      console.error('Payment failed:', err);
    }
  };

  return (
    <button onClick={handlePayment} disabled={isLoading}>
      Pay $50.00
    </button>
  );
}
```

