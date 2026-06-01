# create-sardis-app

Scaffold a minimal AI agent that uses **Sardis as a money tool** — your agent
gets a wallet, a budget, and a guard that decides whether it may spend.

```bash
npm create sardis-app@latest my-sardis-agent
# or
npx create-sardis-app my-sardis-agent
```

## What it scaffolds

A small TypeScript project that demonstrates the four things an agent needs to
spend safely, with **zero money at risk** until you provide a live key against a
funded wallet:

| File | What it shows | Needs a key? |
| --- | --- | --- |
| `src/setup.ts` | Give the agent a wallet (`wallets.create`) and set a budget in plain English (`policies.apply`). | Yes (sandbox key is fine). |
| `src/guard.ts` | The spend-decision engine deciding **ALLOW + DENY**, fully offline (`@sardis/reference`). | **No.** |
| `src/agent.ts` | A guarded-spend agent loop — Vercel AI SDK + the Sardis `sardis/ai-sdk` tools, whose system prompt enforces "check policy before paying". | Yes (+ `OPENAI_API_KEY`). |

The generated project imports only the shipping Sardis packages:

- [`sardis`](https://www.npmjs.com/package/sardis) — the TypeScript SDK (wallet, policy, pay).
- `sardis/ai-sdk` — the Vercel AI SDK provider (`sardis_check_policy`, `sardis_pay`, …).
- `@sardis/reference` — the pure, offline spend-decision engine.

## The guard is the point

`src/guard.ts` runs the same ordered checks the production backend uses
(amount → scope → MCC/category → per-tx limit → total → time windows → merchant
rules → execution context), but **pure**: no network, no key, no funds. It
answers "is this agent allowed to spend this?" before any transfer happens. The
generated example shows an allowed $5 spend, a denied $120 spend (over the
per-transaction limit), and a denied gambling-MCC spend.

## Generated layout

```
my-sardis-agent/
├── package.json        # deps: sardis, @sardis/reference, ai, @ai-sdk/openai, zod
├── tsconfig.json       # ES2022, strict, bundler
├── .env.example        # SARDIS_API_KEY (placeholder), SARDIS_WALLET_ID, OPENAI_API_KEY
├── .gitignore
├── README.md
└── src/
    ├── setup.ts        # wallet + budget
    ├── guard.ts        # offline ALLOW/DENY demo
    └── agent.ts        # guarded-spend agent loop
```

## License

MIT
