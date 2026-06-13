# sardis

[![npm](https://img.shields.io/npm/v/sardis?color=CB3837&logo=npm&logoColor=white)](https://www.npmjs.com/package/sardis)
[![npm downloads](https://img.shields.io/npm/dm/sardis.svg)](https://www.npmjs.com/package/sardis)
[![Bundle size](https://img.shields.io/bundlephobia/minzip/sardis?label=gzipped)](https://bundlephobia.com/package/sardis)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/XMA9JwDJ)

Official **TypeScript SDK** for [Sardis](https://sardis.sh) — the Payment OS for the Agent Economy.

One package, Stripe-style namespaced resources, AP2 mandate builders, first-party adapters for Vercel AI SDK / LangChain.js / Mastra, and runtime-agnostic webhooks. Native `fetch` core — runs on Node 18+, Cloudflare Workers, Vercel Edge, Deno, Bun, and modern browsers.

---

## Install

```bash
npm install sardis
# or
pnpm add sardis
# or
bun add sardis
```

---

## 30-second quickstart

```ts
import { Sardis } from "sardis";

const sardis = new Sardis({ apiKey: process.env.SARDIS_API_KEY! });

// One-liner — wraps wallets.transfer
await sardis.pay({
  from: "wallet_abc",
  to: "merchant_xyz",
  amount: "25.00",
});

// Read a balance
const balance = await sardis.wallets.getBalance("wallet_abc");

// Holds — authorize, then capture
const hold = await sardis.holds.create({ walletId: "wallet_abc", amount: "50.00" });
await sardis.holds.capture(hold.holdId, { amount: "42.00" });
```

---

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
// Hand `tools` to any LangChain agent — each tool implements
// { name, description, schema, invoke } per @langchain/core/tools.
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

---

## AP2 mandate flow (Intent → Cart → Payment)

For agentic-commerce mandates, build the chain explicitly and drop down to `payments.executeAP2`:

```ts
import { Mandate } from "sardis/protocol";

const intent = Mandate.intent({
  subjectId: "agent_abc",
  description: "Purchase OpenAI credits",
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

---

## Subpath exports

Tree-shake friendly — importing one subpath does not pull in the rest.

| Subpath | Purpose | Gzipped |
| --- | --- | --- |
| `sardis` | Unified client + namespaced resources | ≤ 30 KB |
| `sardis/ai-sdk` | Vercel AI SDK provider | ≤ 8 KB |
| `sardis/langchain` | LangChain.js tools | ≤ 8 KB |
| `sardis/mastra` | Mastra tools | ≤ 8 KB |
| `sardis/protocol` | AP2 / TAP mandate builders | — |
| `sardis/webhooks` | Runtime-agnostic webhook verification | ≤ 5 KB |
| `sardis/shims/web` | `hmacSha256Hex`, `timingSafeEqual` for edge | ≤ 2 KB |
| `sardis/shims/node` | Same primitives backed by Node crypto | — |
| `sardis/cards`, `sardis/ledger`, `sardis/chain`, `sardis/ucp`, `sardis/compliance`, `sardis/guardrails`, `sardis/checkout`, `sardis/wallet`, `sardis/ramp`, `sardis/core` | Domain subpaths | — |

---

## Resources on the client

Stripe-style, namespaced — every resource shares the same engine (retry, timeout, telemetry, structured errors):

`payments` · `wallets` · `agents` · `holds` · `cards` · `policies` · `webhooks` · `transactions` · `ledger` · `treasury` · `approvals` · `killSwitch` · `evidence` · `simulation` · `paymentObjects` · `funding` · `fx` · `subscriptionsV2` · `escrow` · `batch` · `streaming` · `mandateDelegation` · `usage` · `facilityGate` · `marketplace` · `checkout` · `groups` · `ucp` · `a2a`

Plus `sardis.pay({ ... })` as the one-liner shortcut over `wallets.transfer`.

---

## Errors

Every failed request throws a typed error. Status codes map to dedicated
subclasses (same shape as the Anthropic SDK), and all of them extend `APIError`
so you can catch broadly or narrowly:

```ts
import {
  Sardis,
  APIError,
  RateLimitError,
  NotFoundError,
  AuthenticationError,
} from "sardis";

try {
  await sardis.agents.get("agent_missing");
} catch (err) {
  if (err instanceof RateLimitError) {
    console.log(`retry after ${err.retryAfter}s`);
  } else if (err instanceof NotFoundError) {
    console.log("no such agent");
  } else if (err instanceof APIError) {
    console.log(err.statusCode, err.request_id); // quote request_id to support
  }
}
```

| Status | Error class |
| --- | --- |
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 403 | `PermissionDeniedError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` |
| 422 | `UnprocessableEntityError` |
| 429 | `RateLimitError` |
| 5xx | `InternalServerError` |
| connection drop | `APIConnectionError` |
| timeout | `APIConnectionTimeoutError` |
| `signal` abort | `APIUserAbortError` |

Connection-level aliases (`APIConnectionError`, `APIConnectionTimeoutError`,
`APIUserAbortError`) mirror Anthropic-SDK naming; they are the same classes as
`NetworkError` / `TimeoutError` / `AbortError`.

---

## Auto-pagination

`listPage(...)` returns a `Page` that is directly async-iterable, so you can
stream every item across every page without ever touching a cursor:

```ts
// Stream every agent across all pages.
for await (const agent of sardis.agents.listPage({ limit: 50 })) {
  console.log(agent.id);
}

// Or one page at a time.
let page = await sardis.wallets.listPage({ agentId: "agent_abc" });
for (const wallet of page.data) console.log(wallet.id);
while (page.hasNextPage()) {
  page = await page.getNextPage();
}

// Or iterate page objects.
for await (const p of (await sardis.agents.listPage()).iterPages()) {
  console.log(p.data.length);
}
```

---

## Per-request options

Any method takes an optional final options argument:

```ts
await sardis.agents.create(
  { name: "treasurer" },
  {
    idempotencyKey: "agent-create-2026-06-13", // Idempotency-Key on writes
    maxRetries: 5,                              // override client default
    timeout: 10_000,                            // ms
    headers: { "X-Trace": "abc" },
    signal: controller.signal,                  // AbortController
  },
);
```

---

## Edge & webhooks

The SDK ships no axios, no polyfills — just `fetch`.

```ts
import { constructEvent } from "sardis/webhooks";

const event = await constructEvent(rawBody, signature, secret);
```

For edge runtimes:

```ts
import { hmacSha256Hex, timingSafeEqual } from "sardis/shims/web";
```

---

## Migrating from `@sardis/sdk` v1

```bash
npx sardis-migrate
```

Rewrites:

- `import { SardisClient } from "@sardis/sdk"` → `import { Sardis } from "sardis"`
- `new SardisClient(opts)` → `new Sardis(opts)`
- `import { createSardisTools } from "@sardis/ai-sdk"` → `import { createSardis } from "sardis/ai-sdk"`
- `createSardisTools(opts)` → `createSardis(opts).tools`
- `new SardisProvider(opts)` → `createSardis(opts)`

Full diff: [migration guide](https://sardis.sh/docs/ts-migration).

---

## Documentation

- [docs.sardis.sh](https://docs.sardis.sh)
- [Getting started](https://docs.sardis.sh/getting-started)
- [API reference](https://docs.sardis.sh/api)
- [Framework guides](https://docs.sardis.sh/frameworks)
- [Examples](https://github.com/EfeDurmaz16/sardis/tree/main/examples)

## License

MIT.
