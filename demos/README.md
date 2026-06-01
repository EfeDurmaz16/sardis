# Demos

Larger, end-to-end Sardis scenarios. These are more involved than the
single-concept scripts in [`../examples/`](../examples/) — they walk a full flow
with step-by-step terminal output. Start with `examples/` if you just want the
minimal API shape.

## Prerequisites

- Python 3.10+
- `pip install sardis` (or `pip install -e packages/sardis` from a checkout)
- Optional: `pip install rich` for nicer terminal output (demos degrade
  gracefully without it)

Standalone demos run against in-process Sardis primitives. Demos that hit the
hosted API need `export SARDIS_API_KEY=sk_live_...`; they fail fast with a clear
message if it is missing.

## Available demos

| Demo | What it walks through |
| --- | --- |
| [`demo_payment_flow.py`](demo_payment_flow.py) | Agent payment lifecycle: wallet → policy → AP2 mandate chain (Intent → Cart → Payment) → settlement → audit |
| [`demo_trust_scoring.py`](demo_trust_scoring.py) | KYA trust scoring and tier progression (NEW → BASIC → TRUSTED → VERIFIED) and how limits scale |
| [`demo_multi_agent.py`](demo_multi_agent.py) | Multi-agent patterns: split payment, shared-treasury group payment, cascade failover |
| [`demo_escrow.py`](demo_escrow.py) | Agent-to-agent escrow lifecycle: CREATED → FUNDED → DELIVERED → RELEASED (with dispute paths) |
| [`full_payment_demo.py`](full_payment_demo.py) | Full in-repo path through `sardis.core` / `sardis.chain` / `sardis.protocol` |

### Nested projects

| Project | What it is |
| --- | --- |
| [`demo-agent/`](demo-agent/) | A LangChain agent wired to the Sardis toolkit |
| [`langchain-agent-pay/`](langchain-agent-pay/) | LangChain agent that pays within policy limits |
| [`x402-payment/`](x402-payment/) | x402 paid-HTTP flow |
| [`agent-card-issue/`](agent-card-issue/) | Virtual-card issuance for an agent |
| [`arc-circle-mandate/`](arc-circle-mandate/), [`tempo-accounts-mandate/`](tempo-accounts-mandate/) | Mandate flows on specific rails |

Plus the standalone scripts `demo_payment_flow.py`-style files listed above and a
few rail-specific E2E scripts (`tempo_e2e_demo.py`, `sardis_connect_e2e_demo.py`,
`mvp_base_sepolia_demo.py`).

## Notes for contributors

- Import from `sardis` / `sardis.core` / `sardis.chain` / `sardis.protocol` /
  `sardis.integrations.<name>` — never the pre-consolidation `sardis_sdk`,
  `sardis_chain`, `sardis_protocol`, `sardis_langchain`, … packages.
- A demo that needs an API key should fail fast with a clear message, not fall
  back to a fake key.
- Keep a demo focused on one scenario; if you are demonstrating a single API
  call, it probably belongs in `examples/` instead.

## License

MIT — see [`../LICENSE`](../LICENSE).
