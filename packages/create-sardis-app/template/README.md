# __APP_NAME__

A Next.js + Vercel AI SDK + Sardis example. Ships a chat UI whose agent can pay, hold, and check policy via Sardis tools.

## Setup

```bash
cp .env.example .env.local
# add SARDIS_API_KEY, SARDIS_WALLET_ID, OPENAI_API_KEY
npm install
npm run dev
```

Open http://localhost:3000 and ask the agent to send a payment.

## How it works

- `src/lib/sardis.ts` constructs a Sardis AI-SDK provider via `createSardis(...)` and exports it.
- `src/app/api/chat/route.ts` is the streaming chat endpoint. It passes `sardis.tools` and `sardis.systemPrompt` to `streamText`.
- `src/app/page.tsx` is a minimal chat UI using `useChat()` from `ai/react`.

The agent's available tools are:
- `sardis_pay` — send a stablecoin payment
- `sardis_create_hold` / `sardis_capture_hold` / `sardis_void_hold` — pre-auth flow
- `sardis_get_balance` — read wallet balance
- `sardis_check_policy` — gate prospective spend

See https://sardis.sh/docs for the full surface.
