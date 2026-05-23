# sardis

Official TypeScript SDK for [Sardis](https://sardis.sh) — the Payment OS for the Agent Economy.

```bash
npm install sardis
```

## 30-second quickstart

```ts
import { Sardis } from "sardis";

const sardis = new Sardis({ apiKey: process.env.SARDIS_API_KEY! });

// Send a stablecoin payment
await sardis.pay({
  from: "wallet_abc",
  to: "merchant_xyz",
  amount: "25.00",
});

// Read balance
const balance = await sardis.wallets.getBalance("wallet_abc");
```

## With Vercel AI SDK

```ts
import { createSardis } from "sardis/ai-sdk";
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";

const sardis = createSardis({
  apiKey: process.env.SARDIS_API_KEY!,
  walletId: "wallet_abc",
});

await generateText({
  model: openai("gpt-4o"),
  tools: sardis.tools,
  system: sardis.systemPrompt,
  prompt: "Pay $20 for OpenAI credits to openai.com",
});
```

## With LangChain.js

```ts
import { createSardisTools } from "sardis/langchain";

const tools = createSardisTools({
  apiKey: process.env.SARDIS_API_KEY!,
  walletId: "wallet_abc",
});

// Pass `tools` to a LangChain agent. Each tool has `{ name, description,
// schema, invoke }` matching @langchain/core/tools.
```

## With Mastra

```ts
import { Agent } from "@mastra/core";
import { createSardisMastraTools } from "sardis/mastra";

const agent = new Agent({
  name: "treasurer",
  model: openai("gpt-4o"),
  tools: createSardisMastraTools({
    apiKey: process.env.SARDIS_API_KEY!,
    walletId: "wallet_abc",
  }),
});
```

## What's included

- `sardis` — unified client with namespaced resources (Stripe-style)
- `sardis/ai-sdk` — Vercel AI SDK provider
- `sardis/langchain` — LangChain.js tools
- `sardis/mastra` — Mastra tools
- `sardis/protocol` — AP2 mandate builders (`Mandate.intent()`, `Mandate.cart()`, `Mandate.payment()`)
- `sardis/cards`, `sardis/ledger`, `sardis/chain`, `sardis/ucp`, `sardis/compliance`, `sardis/guardrails`, `sardis/checkout`, `sardis/wallet`, `sardis/ramp`, `sardis/webhooks` — domain subpaths
- `sardis/shims/node`, `sardis/shims/web` — runtime crypto shims

## AP2 mandate flow (Intent → Cart → Payment)

For payments that need the full mandate chain — required for AP2-compliant agent commerce — drop down to `sardis.payments.executeMandate(...)`:

```ts
import { Mandate } from "sardis/protocol";

const intent = Mandate.intent({
  subjectId: "agent_abc",
  description: "Purchase OpenAI credits for code generation",
  maxAmount: "100.00",
  domain: "openai.com",
});

const cart = Mandate.cart({
  intentId: intent.intent_id,
  merchantId: "openai",
  items: [{ name: "GPT-4 credits", amount: "20.00" }],
});

const payment = Mandate.payment({
  cartId: cart.cart_id,
  amount: "20.00",
  destination: "merchant_openai",
});

await sardis.payments.executeAP2(intent, cart, payment);
```

## Edge runtime support

`sardis` runs on Node 18+, Cloudflare Workers, Vercel Edge, Deno, Bun, and modern browsers. The HTTP core uses native `fetch` — no axios, no polyfills.

For webhook signature verification at the edge, use `sardis/shims/web`:

```ts
import { hmacSha256Hex, timingSafeEqual } from "sardis/shims/web";
```

Or use the runtime-agnostic helper:

```ts
import { constructEvent } from "sardis/webhooks";

const event = await constructEvent(rawBody, signature, secret);
```

## Migration from `@sardis/sdk` v1

```bash
npx sardis-migrate
```

This rewrites:

- `import { SardisClient } from "@sardis/sdk"` → `import { Sardis } from "sardis"`
- `new SardisClient(...)` → `new Sardis(...)`
- `import { createSardisTools } from "@sardis/ai-sdk"` → `import { createSardis } from "sardis/ai-sdk"`
- `createSardisTools(opts)` → `createSardis(opts).tools`
- `new SardisProvider(opts)` → `createSardis(opts)`

See [the migration guide](https://sardis.sh/docs/ts-migration) for the full diff.

## Bundle size

| Subpath           | gzipped |
| ----------------- | ------- |
| `sardis`          | ≤ 30 KB |
| `sardis/ai-sdk`   | ≤ 8 KB  |
| `sardis/langchain`| ≤ 8 KB  |
| `sardis/mastra`   | ≤ 8 KB  |
| `sardis/webhooks` | ≤ 5 KB  |
| `sardis/shims/web`| ≤ 2 KB  |

Tree-shake friendly; importing one subpath does not pull in the rest.

## License

MIT
