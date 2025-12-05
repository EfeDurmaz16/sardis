# Sardis V2 — Stablecoin Execution Layer for AP2/TAP

Sardis is the agent-first stablecoin rail that turns AP2 mandates and TAP identities into deterministic on-chain settlement. We provide programmable wallets, mandate verification, policy enforcement, multi-chain routing, and immutable audit trails so autonomous agents can pay merchants with sub-cent precision.

## Capabilities
- **Agent Identity (TAP)** – Ed25519/ECDSA keys, nonce binding, replay protection, auditable VC proofs
- **Mandate System (AP2)** – Intent, Cart, Payment mandates signed as W3C Verifiable Credentials
- **Wallet & Policy Engine** – Multi-token (USDC/USDT/PYUSD/EURC), multi-chain (Base/Ethereum/Polygon/Solana/Arbitrum/Optimism) wallets with merchant/category budgets
- **Stablecoin Execution Engine** – Chain routing, fee quoting, CCIP/Wormhole bridging, deterministic receipts
- **Compliance & Audit** – GENIUS Act-aligned monitoring, sanctions/KYC, SAR hooks, Merkle anchored ledger
- **Developer Tooling** – REST API, CLI-ready SDKs (Python + TypeScript), sandbox + API explorer

## Repository Layout
| Module | Purpose | Stack |
| --- | --- | --- |
| `sardis-core` *(python import: `sardis_v2_core`)* | Shared data models, TAP identity helpers, config loader | Python + Pydantic, PyNaCl |
| `sardis-api` | FastAPI gateway exposing mandate + wallet endpoints | FastAPI, Uvicorn |
| `sardis-wallet` | Wallet registry + policy enforcement | Python |
| `sardis-protocol` | AP2/TAP/x402 mandate schemas + verification pipeline | Python |
| `sardis-ledger` | Append-only ledger + receipt anchors | Python |
| `sardis-chain` | Multi-chain executor + custody adapters | Python, Web3 |
| `sardis-compliance` | GENIUS Act compliance checks + SAR hooks | Python |
| `sardis-sdk-python` | Async Python SDK for agents | Python, httpx |
| `sardis-sdk-js` | TypeScript SDK for Node/edge runtimes | TypeScript, Axios |

Legacy AP1-era services live under `legacy/sardis_core` and remain importable via `import sardis_core` for backward compatibility, but all new work should target the V2 packages above.

## High-Level Architecture
```
                +------------------------------+
                |   TAP Identity Providers     |
                | (Turnkey / Fireblocks MPC)   |
                +---------------+--------------+
                                |
                                v
+-------------+      +----------+--------+      +------------------+
|  AP2 Agents |----->| sardis-protocol  |----->| sardis-wallet     |
|  (user sig) |      | (Mandate verify) |      | (policies, keys)  |
+-------------+      +----------+--------+      +---------+--------+
                                            policy pass/fail|
                                                            v
                                      +---------------------+---------------------+
                                      |        sardis-api (FastAPI)               |
                                      |  - mandate ingestion                      |
                                      |  - TAP binding validation                 |
                                      |  - DX endpoints                           |
                                      +------------+------------------------------+
                                                   |
                                                   v
                            +----------------------+--------------------+
                            |   sardis-chain (Tx executor & routing)    |
                            +----------------------+--------------------+
                                                   |
                                                   v
                           +-----------------------+--------------------+
                           |  sardis-ledger & sardis-compliance        |
                           |  - deterministic receipts (Merkle)        |
                           |  - SAR / audit feeds                      |
                           +-----------------------+--------------------+
                                                   |
                                                   v
                                         External monitors / issuers
```

### Audit + Replay Defense
```
Intent VC --> Cart VC --> Payment VC --> Ledger Entry --> Merkle Root --> VC Proof Hash
         ^            ^            ^              ^              ^
         |            |            |              |              |
    TAP nonce    TAP nonce    TAP nonce     Replay cache     Audit API
```

## Quick Start (Skeleton)
1. **Install Poetry/Hatch + Node 18** (or use `pip install -e` in module directories).
2. **Bootstrap core packages**
   ```bash
   cd sardis-core && pip install -e .
   cd ../sardis-wallet && pip install -e .
   # repeat for protocol/ledger/chain/compliance
   ```
3. **Install dev tooling (tests/AP2 helpers)**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt  # includes PyNaCl + pytest
   ```
4. **Run FastAPI service**
   ```bash
   cd ../sardis-api
   pip install -e .
   uvicorn sardis_api.main:create_app --factory --reload
   ```
5. **Use SDKs**
   - Python: `pip install -e sardis-sdk-python`
   - JS: `npm install && npm run build` inside `sardis-sdk-js` then import `SardisClient`

### AP2 Payment Flow (DX quick test)
```bash
source .venv/bin/activate
pytest tests/test_ap2_payment_api.py -q
```
The test builds a signed Intent+Cart+Payment bundle, hits `/api/v2/ap2/payments/execute`, and asserts the ledger + mandate archives persist to `./data/`. To hit the API manually:

```bash
curl -X POST http://localhost:8000/api/v2/ap2/payments/execute \
  -H 'content-type: application/json' \
  -d @./docs/examples/ap2_bundle.json
```
The response includes `ledger_tx_id`, `chain_tx_hash`, and `compliance_provider/rule` metadata for auditing.
See [docs/ap2-payment-flow.md](docs/ap2-payment-flow.md) for the full Intent → Cart → Payment walkthrough and SDK usage tips.

## Project Status

See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for detailed progress.

### Completed ✅
- Production ChainExecutor with Turnkey MPC integration
- PostgreSQL persistence for all services
- Webhook delivery system with retries
- A2A Marketplace for service discovery
- Rate limiting and structured logging
- API key authentication
- Operations runbook

### In Progress 🚧
- Security audit (external)
- Smart contract audit (external)
- KYC integration (Persona)
- Sanctions screening (Elliptic)

## Next Steps
1. **External Audits** - Security and smart contract audits before mainnet
2. **Compliance Integrations** - Persona KYC, Elliptic sanctions screening
3. **Mainnet Deployment** - Deploy to Base and Polygon mainnet after audits
4. **SDK Documentation** - Complete Python and TypeScript SDK docs
