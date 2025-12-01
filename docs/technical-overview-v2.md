# Sardis V2 Technical Overview

## Layered Architecture
```
+---------------------------------------------------------------------------------+
| Presentation / SDKs                                                             |
|  - sardis-sdk-python (agents, CLI)                                              |
|  - sardis-sdk-js (browser/Node/edge)                                            |
+---------------------------------------------------------------------------------+
| API & Orchestration                                                             |
|  - sardis-api (FastAPI)                                                         |
|  - Auth (API keys + TAP signature headers)                                      |
+---------------------------------------------------------------------------------+
| Protocol & Policy                                                               |
|  - sardis-protocol (AP2/TAP/x402 schemas, VC verification)                      |
|  - sardis-wallet (policy enforcement, key routing)                              |
+---------------------------------------------------------------------------------+
| Execution & Persistence                                                         |
|  - sardis-chain (chain routing, custody, bridging)                              |
|  - sardis-ledger (append-only Merkle log)                                       |
|  - sardis-compliance (KYC/AML, SAR, consent ledger)                             |
+---------------------------------------------------------------------------------+
| Infrastructure                                                                  |
|  - Turnkey / Fireblocks MPC                                                     |
|  - PostgreSQL + Redis (ledger, replay cache)                                    |
|  - Observability stack                                                          |
+---------------------------------------------------------------------------------+
```

## Mandate Lifecycle (AP2/TAP Alignment)
1. **Intent Mandate**
   - User signs TAP-bound VC (purpose=`intent`, TTL=5 min)
   - Contains merchant hints and spending scope
2. **Cart Mandate**
   - Issued when agent builds cart; includes line items + taxes; inherits Intent hash chain
3. **Payment Mandate**
   - Final VC referencing cart hash + deterministic settlement target
4. **Verification** (`sardis-protocol`)
   - Validate VC signature + TAP nonce + expiration
   - Replay cache keyed by `mandate_id`
   - Domain + purpose binding enforced prior to policy evaluation
5. **Policy & Compliance**
   - `sardis-wallet` ensures per-agent rules (whitelists, budgets)
   - `sardis-compliance` checks sanctions, KYC state, SAR heuristics
6. **Execution**
   - `sardis-chain` selects optimal route (L2 vs L1, bridging if needed)
   - On success returns deterministic receipt with `audit_anchor = merkle(tx_fields)`
7. **Ledgering**
   - `sardis-ledger` appends event, updates Merkle root, emits Kafka/SQS feed

## Data Stores
| Store | Purpose | Technology |
| --- | --- | --- |
| Replay Cache | Prevent mandate reuse | Redis (nonce TTL = 24h) |
| Policy DB | Agent wallet + budgets | Postgres JSONB |
| Ledger | Append-only audit log | Postgres partition + Merkle anchor |
| Compliance Events | SAR/Sanctions pipeline | Kafka topic + S3 archive |

## Chain Execution Strategy (x402)
- **Routing Inputs**: mandate token, destination chain, merchant preference, fee ceiling
- **Algorithm**: evaluate on-chain gas/fee quotes, check bridging if merchant chain differs, fallback to stable L2 (Base/Arbitrum) + cross-chain settlement receipt via CCIP/Wormhole
- **Micropayments**: sub-cent flows handled by batching + aggregator accounts on Base, finalizing via net settlement receipts
- **Receipts**: deterministic JSON hashed -> `audit_anchor`; anchor hashed into Merkle tree stored in ledger + optionally published on Base for public attestation

## Compliance Blueprint (GENIUS Act)
- **KYC/AML**: persona_id stored per agent; payment execution blocked until verified
- **Sanctions Screening**: call risk vendor per destination address + merchant
- **Token Controls**: `sardis-chain` enforces freeze/burn actions via admin wallets
- **SAR**: events scored, flagged transactions appended to `compliance_case` table; API supports export to FinCEN XML
- **Consent Management**: GDPR/CCPA consent receipts stored as VC referencing ledger IDs

## Developer Experience
- FastAPI + OpenAPI 3.1 spec published at `/api/v2/openapi.json`
- SDKs wrap TAP signing: Python uses `PyNaCl`; JS uses `tweetnacl`
- CLI (coming soon) issues mandates via `sardis-sdk-python`
- Sandbox environment uses deterministic seeds + mock MPC provider for reproducible tests
