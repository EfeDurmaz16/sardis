# Migrating from `@sardis/sdk` v1 to `sardis` v2

`sardis@2.0.0` consolidates `@sardis/sdk@1.x` and `@sardis/ai-sdk@1.x` into a
single npm package with subpath exports, drops axios in favor of native
`fetch`, and adds first-class TypeScript integrations for LangChain and
Mastra.

For most projects, migration is a single command:

```bash
npx sardis-migrate
```

This page documents the full diff, the codemod, and the deprecation timeline.

## The 60-second migration

1. Install the new package and remove the old ones:

   ```bash
   npm install sardis
   npm uninstall @sardis/sdk @sardis/ai-sdk
   ```

2. Run the codemod against your source tree:

   ```bash
   npx sardis-migrate                     # rewrites ./src and ./app
   npx sardis-migrate --dry src/          # preview without writing
   npx sardis-migrate --print src/foo.ts  # print transformed source to stdout
   ```

3. Re-run your type checker and test suite. The public method names are
   unchanged; only imports + the client constructor name rewrite.

If you used star-imports (`import * as sdk from "@sardis/sdk"`) the codemod
will surface a warning and leave the file untouched — those few call sites
need a manual rename.

## What changed

### One client, one entry point

```diff
- import { SardisClient } from "@sardis/sdk";
+ import { Sardis } from "sardis";

- const client = new SardisClient({ apiKey });
+ const client = new Sardis({ apiKey });
```

All resource namespaces are unchanged. `client.payments.executeMandate(...)`,
`client.wallets.transfer(...)`, `client.holds.create(...)`, etc. work
identically. The full error hierarchy (`APIError`, `RateLimitError`,
`AuthenticationError`, `TimeoutError`, ...) is re-exported from `sardis`.

### Native `fetch`, no axios

The HTTP core is now `globalThis.fetch` + `AbortController`. Consequences:

- Works on Node 18+, Cloudflare Workers, Vercel Edge, Deno, Bun, and modern
  browsers without polyfills.
- No more `ECONNABORTED` axios errors — timeouts surface as `TimeoutError`.
- Bundle size drops ~80 KB minzipped.

If you want to inject a custom fetch (test mocks, observability wrappers):

```ts
const sardis = new Sardis({
  apiKey: process.env.SARDIS_API_KEY!,
  fetch: (input, init) => mySpan.wrap(globalThis.fetch(input, init)),
});
```

### Vercel AI SDK provider lives at `sardis/ai-sdk`

The old `@sardis/ai-sdk` package re-implemented payments against axios
directly. `sardis/ai-sdk` now defers to the unified `Sardis` client
internally — exactly one HTTP surface, exactly one error hierarchy.

```diff
- import { createSardisTools } from "@sardis/ai-sdk";
- const tools = createSardisTools({ apiKey, walletId });
+ import { createSardis } from "sardis/ai-sdk";
+ const provider = createSardis({ apiKey, walletId });
+ const tools = provider.tools;
```

Or, more idiomatically:

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
  prompt: "Pay $20 for OpenAI credits",
});
```

`new SardisProvider(...)` is gone. Use `createSardis(...)` — the codemod
handles this.

### Subpath exports

| Subpath              | Purpose                                                       |
| -------------------- | ------------------------------------------------------------- |
| `sardis`             | Umbrella client, error classes, primary types                 |
| `sardis/core`        | `Engine`, low-level HTTP primitives — SDK-on-SDK builders     |
| `sardis/ai-sdk`      | Vercel AI SDK provider (`createSardis`)                       |
| `sardis/langchain`   | LangChain.js tools (`createSardisTools`) — NEW in v2          |
| `sardis/mastra`      | Mastra tools (`createSardisMastraTools`) — NEW in v2          |
| `sardis/protocol`    | AP2/TAP `Mandate.intent/cart/payment` builders                |
| `sardis/checkout`    | Server-side checkout helpers                                  |
| `sardis/wallet`      | Wallet creation, balance, transfer helpers                    |
| `sardis/cards`       | Virtual card helpers                                          |
| `sardis/ledger`      | Ledger entry types + Merkle proof verification                |
| `sardis/chain`       | Chain/token enums + explorer URL builders                     |
| `sardis/ucp`         | Universal Commerce Protocol client                            |
| `sardis/compliance`  | KYC + sanctions hit types                                     |
| `sardis/guardrails`  | Natural-language policy DSL                                   |
| `sardis/ramp`        | On/off-ramp quote + KYC handoff                               |
| `sardis/webhooks`    | Webhook signature verification (edge-safe)                    |
| `sardis/shims/node`  | Node-only HMAC helpers                                        |
| `sardis/shims/web`   | Web Crypto HMAC helpers (Cloudflare / Vercel Edge / Deno)     |

Tree-shake friendly: importing one subpath doesn't pull in the rest.

### New TypeScript surface (no Python-side equivalent yet)

- `sardis.pay({ from, to, amount })` — top-level shortcut that mirrors the
  Python `sardis_sdk.resources.pay` convenience. Builds the mandate
  internally; falls back to `sardis.payments.executeMandate` for the full
  AP2 flow.
- `sardis/langchain` — LangChain.js tool factory.
- `sardis/mastra` — Mastra tool factory.
- `sardis/protocol` — `Mandate.intent / cart / payment` builders that map
  camelCase TypeScript inputs to the snake_case wire shape AP2 requires.

### Closed parity gaps

- `sardis.facilityGate.*` — was missing in v1, present in Python.
- `sardis.pay()` — was missing in v1, present in Python.

## TS-Python parity table

| Python (`sardis_sdk`)                          | TypeScript (`sardis@2`)                                  |
| ---------------------------------------------- | -------------------------------------------------------- |
| `AsyncSardisClient(...)`                       | `new Sardis(...)`                                        |
| `SardisClient(...)` (sync)                     | *(none — TS is always async)*                            |
| `client.agents.*`                              | `sardis.agents.*`                                        |
| `client.payments.execute_mandate(...)`         | `sardis.payments.executeMandate(...)`                    |
| `client.payments.execute_ap2(...)`             | `sardis.payments.executeAP2(...)`                        |
| `client.holds.create(...)` / `capture` / `void`| `sardis.holds.create(...)` / `capture` / `void`          |
| `client.cards.issue(...)`                      | `sardis.cards.issue(...)`                                |
| `client.wallets.create(...)` / `balance`       | `sardis.wallets.create(...)` / `getBalance`              |
| `client.policies.parse(...)` / `apply`         | `sardis.policies.parse(...)` / `apply`                   |
| `client.escrow.*`                              | `sardis.escrow.*`                                        |
| `client.fx.quote(...)`                         | `sardis.fx.quote(...)`                                   |
| `client.ledger.entries.list(...)`              | `sardis.ledger.entries.list(...)`                        |
| `client.marketplace.*`                         | `sardis.marketplace.*`                                   |
| `client.kill_switch.*`                         | `sardis.killSwitch.*`                                    |
| `client.subscriptions_v2.*`                    | `sardis.subscriptions.*` (v2 routed internally)          |
| `client.facility_gate.*`                       | `sardis.facilityGate.*`                                  |
| `sardis_sdk.resources.pay(...)`                | `sardis.pay(...)`                                        |
| `sardis_sdk.integrations.openai`               | `sardis/ai-sdk` (Vercel AI SDK)                          |
| `sardis_sdk.integrations.langchain`            | `sardis/langchain`                                       |
| `sardis_sdk.integrations.llamaindex`           | *(not yet ported — tracked)*                             |
| `BulkOperations`                               | `sardis/core` — `Engine.batch`-style helpers             |
| `Paginator`                                    | `sardis.paginate(...)` async iterator                    |

Field-name conventions:

- TypeScript inputs are camelCase: `executeMandate({ mandateId, subjectId })`.
- The wire protocol stays snake_case (AP2 compatibility):
  `{ "mandate_id": "...", "subject_id": "..." }`.
- The Mandate builders in `sardis/protocol` do the snake↔camel mapping for
  you; raw `Record<string, unknown>` payloads pass through unchanged.

## Migration codemod reference

```bash
npx sardis-migrate                     # rewrite ./src and ./app in place
npx sardis-migrate src/ apps/web/      # rewrite specific paths
npx sardis-migrate --dry src/          # preview, do not write
npx sardis-migrate --print src/foo.ts  # transformed source to stdout
```

The codemod rewrites:

| Before                                                 | After                                              |
| ------------------------------------------------------ | -------------------------------------------------- |
| `from "@sardis/sdk"`                                   | `from "sardis"`                                    |
| `require("@sardis/sdk")`                               | `require("sardis")`                                |
| `import { SardisClient, ... } from "..."`              | `import { Sardis, ... } from "..."`                |
| `new SardisClient(...)`                                | `new Sardis(...)`                                  |
| Bare `SardisClient` identifier                         | `Sardis`                                           |
| `from "@sardis/ai-sdk"`                                | `from "sardis/ai-sdk"`                             |
| `import { createSardisTools }`                         | `import { createSardis }`                          |
| `createSardisTools(opts)`                              | `createSardis(opts).tools`                         |
| `import { SardisProvider }`                            | `import { createSardis }`                          |
| `new SardisProvider(opts)`                             | `createSardis(opts)`                               |

Idempotent — running the codemod twice produces the same output.

Edge cases the codemod does **not** handle:

- `import * as sdk from "@sardis/sdk"` — flagged with a warning, no rewrite.
- Aliased named imports (`import { SardisClient as Foo }`) — the import line
  is rewritten; references to the local alias `Foo` are left alone.
- Multi-line `createSardisTools(...)` calls with line breaks inside the
  argument tuple — leftover `__MIGRATE_TOOLS_CALL__` sentinel surfaces in
  the diff as a fail-loud signal. Reformat to single-line and re-run, or
  fix by hand.

## Deprecation timeline

| Package                  | Status on 2.0.0 launch | Action after 6 months on `latest` |
| ------------------------ | ---------------------- | --------------------------------- |
| `sardis@2`               | new                    | —                                 |
| `@sardis/sdk@1.2`        | re-export shim         | mark deprecated on npm            |
| `@sardis/ai-sdk@1.2`     | re-export shim         | mark deprecated on npm            |
| `@sardis/connect`        | already 0 downloads    | mark deprecated on npm            |
| `sardis-api-proxy`       | already 0 downloads    | mark deprecated on npm            |
| `@sardis/activepieces`   | unchanged, low-priority| deprecate after 1 quarter         |

`@sardis/sdk@1.2.x` and `@sardis/ai-sdk@1.2.x` re-export the new package
with a one-time deprecation warning printed on first import. No behavior
change — existing code keeps working through the transition.

## Verifying the migration

A successful migration produces:

```bash
$ pnpm typecheck   # no errors
$ pnpm test        # no regressions
$ pnpm run build   # output bundle smaller than before
```

If your test suite depended on `axios.isAxiosError(err)` to distinguish
network errors from API errors, replace it with the typed Sardis errors
re-exported at the package root:

```diff
- } catch (err) {
-   if (axios.isAxiosError(err)) { ... }
- }
+ } catch (err) {
+   if (err instanceof NetworkError) { ... }
+   if (err instanceof APIError) { ... }
+ }
```

`isSardisError(err)` and `isRetryableError(err)` are exported for
non-`instanceof` checks (useful across worker boundaries where the error
prototype isn't preserved).

## When in doubt

Open an issue at <https://github.com/EfeDurmaz16/sardis/issues> with the
output of `npx sardis-migrate --dry src/`. The TS-Python parity table above
is the authoritative cross-reference for what every Python method maps to
on the TypeScript side.
