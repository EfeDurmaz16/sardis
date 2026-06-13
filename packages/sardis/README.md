# sardis

[![PyPI](https://img.shields.io/pypi/v/sardis?color=3776AB&logo=python&logoColor=white)](https://pypi.org/project/sardis/)
[![Python](https://img.shields.io/pypi/pyversions/sardis)](https://pypi.org/project/sardis/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/XMA9JwDJ)

**Payment OS for the Agent Economy** — the official Python SDK, CLI, and runtime primitives for [Sardis](https://sardis.sh).

`sardis` is the single Python entry point to the Sardis financial authority layer: a Stripe-style client (`Sardis` / `AsyncSardis`) for the hosted API, plus lazy-loaded submodules (`sardis.core`, `sardis.chain`, `sardis.protocol`, `sardis.guardrails`, …) for running mandates, policies, ledger writes, and provider adapters in-process. Submodules and AI framework integrations load only on first access, so `import sardis` stays fast.

---

## Install

```bash
pip install sardis                              # core SDK + CLI
pip install "sardis[langchain]"                 # + LangChain adapter
pip install "sardis[crewai,openai-agents,adk]"  # multiple framework extras
pip install "sardis[chain]"                     # + web3 / eth-account (on-chain)
pip install "sardis[postgres,redis]"            # + persistent stores
pip install "sardis[all]"                       # everything
```

Requires Python 3.11+.

---

## Quickstart

```python
from sardis import Sardis

client = Sardis(api_key="sk_live_...")

# Unified pay — auto-routes cheapest chain (USDC default)
result = client.pay.execute(
    to="0xabc...",            # address, wallet ID, or merchant domain
    amount="25.00",
    currency="USDC",
    chain="base",             # explicit chain wins; omit to auto-route
)
print(result["tx_hash"])

# Cross-currency (USDC → EURC auto-swap)
result = client.pay.execute(to="merchant@eu", amount="100.00", currency="EUR")
print(result["fx"])

# Full AP2 mandate flow (Intent → Cart → Payment)
result = client.payments.execute_mandate(mandate)

# Holds (authorize without capture)
hold = client.holds.create(wallet_id="wallet_abc", amount="50.00")
client.holds.capture(hold.hold_id, amount="42.00")
```

Async-native counterpart:

```python
import asyncio
from sardis import AsyncSardis

async def main():
    async with AsyncSardis(api_key="sk_live_...") as client:
        wallet = await client.wallets.create(name="agent-1", chain="base")
        balance = await client.wallets.get_balance(wallet.wallet_id)
        print(balance)

asyncio.run(main())
```

---

## Resources on the client

Namespaced, Stripe-style, available on both `Sardis` and `AsyncSardis`:

`agents` · `wallets` · `payments` · `pay` · `holds` · `cards` · `policies` · `approvals` · `kill_switch` · `evidence` · `transactions` · `ledger` · `treasury` · `webhooks` · `marketplace` · `simulation` · `exceptions` · `facility_gate` · `funding` · `fx` · `escrow` · `batch` · `subscriptions_v2` · `mandate_delegation` · `groups`

All resources share the same engine — connection pooling, exponential-backoff retry, telemetry, structured errors (`SardisError`, `AuthenticationError`, `RateLimitError`, `ValidationError`, …) — wired through `sardis._client`.

---

## Anthropic-style ergonomics

If you already use the official Anthropic Python SDK, the Sardis client feels identical.

```python
import sardis
from sardis import Sardis

# Retries + timeout are first-class constructor args (exponential backoff on
# 429 / 5xx / connection errors).
client = Sardis(api_key="sk_live_...", max_retries=4, timeout=20.0)

# Per-call overrides without mutating the base client.
strict = client.with_options(max_retries=0, timeout=5.0)
strict.pay.execute(to="0xabc...", amount="10.00")

# A layered, Anthropic-named error hierarchy:
#   SardisError
#   └─ APIError
#      ├─ APIStatusError
#      │  ├─ BadRequestError (400)        ├─ ConflictError (409)
#      │  ├─ AuthenticationError (401)    ├─ UnprocessableEntityError (422)
#      │  ├─ PermissionDeniedError (403)  ├─ RateLimitError (429)
#      │  ├─ NotFoundError (404)          └─ InternalServerError (5xx)
#      └─ APIConnectionError
#         └─ APITimeoutError
try:
    client.pay.execute(to="0xabc...", amount="10.00")
except sardis.RateLimitError as exc:
    print("retry after", exc.retry_after)
except sardis.APIStatusError as exc:
    print(exc.status_code, exc.message)
```

Writes (`POST` / `PUT` / `PATCH` / `DELETE`) automatically carry a stable
`Idempotency-Key` so transparent retries never double-execute; pass your own via
a `RequestContext(idempotency_key=...)` to override it.

---

## Submodules

`import sardis.<name>` to use the runtime primitives directly (lazy-loaded — no startup cost if unused):

| Submodule | What it gives you |
| --- | --- |
| `sardis.core` | Domain models, config, pre-execution pipeline, attestation envelopes |
| `sardis.protocol` | AP2 / TAP mandate builders and verifiers |
| `sardis.guardrails` | Policy engine, deterministic NL-to-policy, ML fraud signals |
| `sardis.compliance` | KYC / AML hooks (BYO provider) |
| `sardis.cards` | Card provider adapter contract |
| `sardis.chain` | On-chain execution (requires `sardis[chain]`) |
| `sardis.wallet` | Wallet management, MPC helpers |
| `sardis.ledger` | Append-only audit ledger |
| `sardis.checkout` | Hosted checkout primitives |
| `sardis.ramp` | Fiat on/off-ramp adapters |
| `sardis.ucp` | UCP MCP transport (experimental) |
| `sardis.integrations` | LangChain, CrewAI, OpenAI Agents, ADK, A2A, AutoGPT, Browser-use, Composio, … |
| `sardis.cli` | The `sardis` / `sardis-cli` entry points |

---

## CLI

Installing the package exposes two equivalent entry points:

```bash
sardis --help
sardis-cli --help
```

---

## Framework integrations

```python
# LangChain
from sardis.integrations.langchain import SardisToolkit
toolkit = SardisToolkit(api_key="sk_live_...", wallet_id="wallet_abc")
tools = toolkit.get_tools()

# CrewAI
from sardis.integrations.crewai import sardis_tools
agent = Agent(name="treasurer", tools=sardis_tools(api_key="sk_live_..."))

# OpenAI Agents SDK
from sardis.integrations.openai_agents import as_openai_tools

# Google ADK
from sardis.integrations.adk import sardis_adk_tools
```

Install only the extras you use: `pip install "sardis[langchain]"`, etc.

---

## Migrating from v1.x

```python
# Old (still works via deprecation shim — removed 2026-11-23)
from sardis_sdk import SardisClient
from sardis_langchain import SardisToolkit

# New (v2)
from sardis import Sardis
from sardis.integrations.langchain import SardisToolkit
```

Legacy aliases `SardisClient` / `AsyncSardisClient` resolve to `Sardis` / `AsyncSardis` for one release. Full diff and timeline: [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md).

---

## Documentation

- [docs.sardis.sh](https://docs.sardis.sh) — full reference
- [Getting started](https://docs.sardis.sh/getting-started)
- [API reference](https://docs.sardis.sh/api)
- [Policy language](https://docs.sardis.sh/policies)
- [Framework guides](https://docs.sardis.sh/frameworks)
- [Examples on GitHub](https://github.com/EfeDurmaz16/sardis/tree/main/examples)
- [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) · [`CHANGELOG.md`](CHANGELOG.md)

## License

MIT — see [`LICENSE`](LICENSE).
