# Arc + Circle + Sardis Mandate Demo

A minimal, self-contained demo showing how Sardis enforces spending
mandates on **Arc testnet** using **Circle developer-controlled wallets**.
The cleanest Arc-native story for why Sardis is the governance layer
on top of the Circle stablecoin stack.

## What this demo proves

Arc is Circle's USDC-native L1. Testnet is live; mainnet is on the 2026
roadmap. The ecosystem page already lists the Anthropic Claude Agent SDK
as a published partner — but there is no published answer for
**who enforces scoped authority when an AI agent spends on Arc**.

That is Sardis.

This demo walks through:

1. **Provision a Circle developer-controlled wallet on Arc testnet**
   for an AI agent. Non-custodial via Circle's entity-secret
   encryption — Sardis holds no raw keys, Circle holds no raw keys.
2. **Issue a spending mandate** with 7 dimensions of authority
   (what, how much per tx, how much per day, which merchants, which
   rails, how long, how to revoke).
3. **Agent makes an allowed payment** (USDC under the mandate cap) —
   passes the Sardis policy pipeline, signed by Circle, settled on
   Arc testnet.
4. **Agent attempts a denied payment** (above per-tx limit) — blocked
   by Sardis before it touches the chain. Circle never sees it, no
   gas burned.
5. **Revoke the mandate mid-session** — kill switch works even
   though the Circle wallet is still live.
6. **Show the audit trail** — every decision is logged and
   Merkle-anchored on Base in production.

Runs fully in-process. No real Circle API key needed unless you set
`CIRCLE_API_KEY` to exercise live mode. The default offline mode uses
a fake Circle client so this is cheap to run in CI or during a
technical walkthrough.

## Why this matters for the Arc Architects Program

Arc's thesis is stablecoin-native programmable money. Sardis is the
layer that makes programmable money **safe for autonomous agents**:

- **Deterministic policy** — 12 sequential checks, fail-closed, no
  LLM in the execution path
- **Multi-dimensional authority** — not just an amount cap, but MCC
  filters, merchant allowlists, time windows, goal-drift detection
- **Lifecycle management** — mandates can be suspended, revoked,
  rotated, or scoped down mid-session without re-issuing the wallet
- **Compliance evidence** — every decision anchored to a
  tamper-evident audit trail suitable for SOC2 / PCI / enterprise
  finance review
- **Framework coverage** — the same mandate layer works with
  CrewAI, LangChain, AutoGPT, Browser Use, Composio, OpenAI Agents
  SDK, Claude Agent SDK, Vercel AI SDK, n8n, Activepieces, E2B, MCP

Put differently: Arc provides the rail. Circle wallets provide the
custody. Sardis provides the authority, the policy, and the audit.
The three fit together cleanly.

## Run it

```bash
cd demos/arc-circle-mandate
uv sync
uv run python demo.py
```

Expected output: six pretty-printed sections, one per step. Green
check for allowed payments, red cross for denied ones. Deterministic
— same output every run unless you flip `ARC_LIVE=1`.

## Files

- `demo.py` — runnable script (~230 lines, self-contained)
- `pyproject.toml` — minimal deps: `sardis-wallet`, `rich`
- `.env.example` — optional env vars (fake defaults work offline)

## Next steps — live Arc testnet

Set these to exercise the live path:

```bash
export CIRCLE_API_KEY="<your Circle API key, format PREFIX:ID:SECRET>"
export CIRCLE_ENTITY_SECRET="<your 32-byte entity secret, hex>"
export ARC_LIVE=1
```

Then fund the resulting Arc testnet address with the Arc faucet
(https://arc.network/faucet when it ships) and re-run the demo.
The script auto-detects live vs offline mode.

## Questions

- **Dylan Casey** (dylan.casey@circle.com) — VP Product, Circle
  Payments Network and Arc. Product owner for the Arc roadmap.
- **Matt Stafford** (matt.stafford@circle.com) — VP Arc Network and
  Onchain Partnerships. Ecosystem partnership lead.
- **Efe Baran Durmaz** (efe@sardis.sh) — demo author, Sardis Labs
  founder.

Built for the Arc Architects Program submission. Policy by Sardis.
Custody by Circle. Settlement on Arc.
