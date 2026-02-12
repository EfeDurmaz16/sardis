# @sardis/ai-sdk

[![npm version](https://img.shields.io/npm/v/@sardis/ai-sdk.svg)](https://www.npmjs.com/package/@sardis/ai-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Sardis payment tools for Vercel AI SDK** - Enable AI agents to make payments with policy guardrails.

## Features

- 🔧 **Drop-in tools** for Vercel AI SDK (`generateText`, `streamText`)
- 💰 **Payments** - Execute stablecoin payments on-chain
- 🔒 **Holds** - Pre-authorize funds for variable amounts
- 📋 **Policy checks** - Verify payments before execution
- 📊 **Spending analytics** - Track budgets and limits
- 🛡️ **Built-in guardrails** - Prevent unauthorized spending

## Installation

```bash
npm install @sardis/ai-sdk ai
# or
pnpm add @sardis/ai-sdk ai
# or
yarn add @sardis/ai-sdk ai
```

## Quick Start

### Basic Usage

```typescript
import { generateText } from 'ai'
import { openai } from '@ai-sdk/openai'
import { createSardisTools } from '@sardis/ai-sdk'

const tools = createSardisTools({
  apiKey: process.env.SARDIS_API_KEY!,
  walletId: 'wallet_abc123',
})

const { text, toolResults } = await generateText({
  model: openai('gpt-4o'),
  tools,
  prompt: 'Pay $50 to merchant_xyz for API credits',
})

console.log(text)
// "I've successfully paid $50 to merchant_xyz. Transaction ID: tx_abc123"
```

### With SardisProvider (Recommended)

```typescript
import { generateText } from 'ai'
import { openai } from '@ai-sdk/openai'
import { SardisProvider } from '@sardis/ai-sdk'

const sardis = new SardisProvider({
  apiKey: process.env.SARDIS_API_KEY!,
  walletId: 'wallet_abc123',
  enableLogging: true,
  onTransaction: async (event) => {
    // Log all transactions to your database
    await db.transactions.insert(event)
  },
})

const { text } = await generateText({
  model: openai('gpt-4o'),
  tools: sardis.tools,
  system: sardis.systemPrompt, // Includes payment guidelines
  prompt: 'Check my balance and pay $25 for API credits',
})
```

### Direct API Access

```typescript
import { SardisProvider } from '@sardis/ai-sdk'

const sardis = new SardisProvider({
  apiKey: process.env.SARDIS_API_KEY!,
  walletId: 'wallet_abc123',
})

// Check balance
const balance = await sardis.getBalance()
console.log(`Available: $${balance.available}`)

// Execute payment
const result = await sardis.pay({
  to: 'merchant_openai',
  amount: 50,
  memo: 'API credits',
})

if (result.success) {
  console.log(`Paid! TX: ${result.txHash}`)
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `sardis_pay` | Execute a payment from the wallet |
| `sardis_create_hold` | Create a hold (pre-authorization) |
| `sardis_capture_hold` | Capture a previously created hold |
| `sardis_void_hold` | Void/cancel a hold |
| `sardis_check_policy` | Check if payment is allowed by policy |
| `sardis_get_balance` | Get wallet balance |
| `sardis_get_spending` | Get spending summary |

## Configuration Options

```typescript
createSardisTools({
  // Required
  apiKey: string,
  walletId: string,

  // Optional
  agentId?: string,           // Agent identifier
  baseUrl?: string,           // Custom API URL
  simulationMode?: boolean,   // Test without real transactions
  maxPaymentAmount?: number,  // Max single payment limit
  blockedCategories?: string[], // Block merchant categories
  allowedMerchants?: string[], // Whitelist mode
})
```

## Tool Sets

```typescript
import {
  createSardisTools,        // Full tool set (7 tools)
  createMinimalSardisTools, // Just pay + balance
  createReadOnlySardisTools, // No payments, analytics only
} from '@sardis/ai-sdk'
```

## Policy Enforcement

Sardis automatically enforces spending policies:

```typescript
const tools = createSardisTools({
  apiKey: '...',
  walletId: '...',
  maxPaymentAmount: 100,  // Block payments over $100
  blockedCategories: ['gambling', 'adult'],
  allowedMerchants: ['openai', 'anthropic', 'aws'], // Whitelist
})

// This will fail with policy violation
const result = await generateText({
  model: openai('gpt-4o'),
  tools,
  prompt: 'Pay $500 to some_casino',
})
// Result: "Payment blocked: Amount $500 exceeds maximum allowed payment of $100"
```

## Holds (Pre-authorization)

Use holds when the final amount isn't known:

```typescript
const { text } = await generateText({
  model: openai('gpt-4o'),
  tools: sardis.tools,
  prompt: `
    I need to book a hotel room for 2 nights at approximately $150/night.
    Create a hold for the estimated total, then when I confirm the
    exact price of $287.50, capture that amount.
  `,
})
```

## Streaming

Works with `streamText` too:

```typescript
import { streamText } from 'ai'

const result = streamText({
  model: openai('gpt-4o'),
  tools: sardis.tools,
  prompt: 'Pay $25 to merchant_abc',
})

for await (const chunk of result.textStream) {
  process.stdout.write(chunk)
}
```

## Framework Support

Works with any model provider supported by Vercel AI SDK:

```typescript
import { openai } from '@ai-sdk/openai'
import { anthropic } from '@ai-sdk/anthropic'
import { google } from '@ai-sdk/google'

// Works with all providers
generateText({ model: openai('gpt-4o'), tools: sardis.tools, ... })
generateText({ model: anthropic('claude-3-5-sonnet-20241022'), tools: sardis.tools, ... })
generateText({ model: google('gemini-1.5-pro'), tools: sardis.tools, ... })
```

## TypeScript

Full TypeScript support with exported types:

```typescript
import type {
  SardisToolsConfig,
  PaymentResult,
  HoldResult,
  PolicyCheckResult,
  BalanceResult,
  TransactionEvent,
} from '@sardis/ai-sdk'
```

## Error Handling

```typescript
const result = await sardis.pay({
  to: 'merchant',
  amount: 1000,
})

if (!result.success) {
  console.error(`Payment failed: ${result.error}`)
  // "Payment failed: Amount exceeds daily spending limit"
}
```

## Related Packages

- [`@sardis/sdk`](https://www.npmjs.com/package/@sardis/sdk) - Full TypeScript SDK
- [`@sardis/mcp-server`](https://www.npmjs.com/package/@sardis/mcp-server) - MCP Server for Claude
- [`@sardis/ramp`](https://www.npmjs.com/package/@sardis/ramp) - Fiat on/off ramps

## Links

- [Documentation](https://sardis.sh/docs)
- [API Reference](https://sardis.sh/docs/api)
- [GitHub](https://github.com/sardis-project/sardis)
- [Discord](https://discord.gg/XMA9JwDJ)

## License

MIT © [Sardis](https://sardis.sh)
