# Tempo Accounts + Sardis Mandate Demo

A minimal, self-contained demo showing how Sardis enforces spending mandates on
top of Tempo's native account abstraction — the cleanest story for why Sardis
is the governance layer on top of Tempo MPP.

## What this demo proves

Tempo ships with passkey-based account abstraction (type 0x76 transactions).
That solves the wallet creation problem — but it does **not** solve the
authority problem. Who is allowed to spend, how much, to whom, for how long?
That is the Sardis layer.

The demo walks through:

1. **Create a Tempo programmatic account** for an AI agent. Root key lives in
   Turnkey MPC. Sardis never holds keys.
2. **Issue a spending mandate** — machine-readable authority with seven
   dimensions (who, what, how much, which rails, how long, approval rules,
   revocation). Scope: `$100/day`, USDC only, cloud APIs only.
3. **Agent makes an allowed payment** ($50 to an authorized merchant) —
   passes the 12-check policy pipeline, settles on Tempo.
4. **Agent attempts a denied payment** ($200 — above per-tx limit) — blocked
   before it touches the chain. No gas burned, no custody risk.
5. **Revoke the mandate mid-stream** — agent's next payment fails even though
   the account is still live. This is the "kill switch" that corporate finance
   teams care about.
6. **Show the audit trail** — every decision (allow, deny, revoke) is logged
   and anchored on-chain.

Runs fully in-process. No Sardis API needed. No Turnkey credentials needed
(the demo uses a fake MPC client so you can run it offline).

## Why this matters for Tempo + Stripe MPP

Tempo MPP introduces "sessions" — OAuth-for-money. An agent authorizes a
spending cap, then streams micropayments. Sardis extends that primitive with:

- **Deterministic policy** — 12 sequential checks, fail-closed, no LLM in the
  execution path
- **Multi-dimensional authority** — not just an amount cap, but MCC filters,
  merchant allowlists, time windows, goal-drift detection
- **Lifecycle management** — mandates can be suspended, revoked, rotated, or
  scoped down mid-session
- **Compliance evidence** — every decision goes to a Merkle-anchored audit
  trail suitable for SOC2, PCI, and enterprise finance review

Put differently: Tempo solves "can the agent move money." Sardis solves
"should the agent move money, and how do we prove it afterwards."

## Run it

```bash
cd demos/tempo-accounts-mandate
uv sync
uv run python demo.py
```

Expected output: six pretty-printed sections, one per step. Green check for
allowed payments, red cross for denied ones. The demo is deterministic — same
output every run.

## Files

- `demo.py` — runnable script (~200 lines, self-contained)
- `pyproject.toml` — minimal deps: `sardis-wallet`, `sardis-core`, `rich`
- `.env.example` — optional env vars (fake defaults work offline)

## Next steps

If you want to run the same flow against live Tempo mainnet (chain_id 4217):

1. Set `TEMPO_RPC_URL=https://rpc.tempo.xyz` (already default)
2. Set `TURNKEY_API_KEY` + `TURNKEY_ORG_ID` to use real MPC custody
3. Set `SARDIS_API_URL=https://api.sardis.sh` to hit the hosted policy engine
4. Fund the programmatic account with a few USDC on Tempo

The demo script stays the same — it auto-detects live vs. offline mode.

## Questions

- Ryan Aubrey (raubrey@stripe.com) — MPP early access, Stripe partnership
- Matt Huang (Paradigm) — Tempo ecosystem
- Efe Baran Durmaz (efe@sardis.sh) — demo author

Built on Tempo mainnet. Custody by Turnkey. Policy by Sardis.
