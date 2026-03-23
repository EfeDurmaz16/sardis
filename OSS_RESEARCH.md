# Sardis Open Source Tool Research

> 48 tools analyzed | 2026-03-23 | License + need + comparison for each

## Summary: What To Adopt

### Adopt Now (Days)
| Tool | License | Why | Effort |
|------|---------|-----|--------|
| **Sigstore** | Apache-2.0 | Sign Docker images + SDK packages for supply chain trust | Days |
| **OpenSSF Scorecard** | Apache-2.0 | Security score (0-10) for investor decks + SOC2 | Hours |
| **OpenTelemetry** | Apache-2.0 | Instrument payment pipeline — trace every phase | Days |
| **k6** | Apache-2.0 | Load test 47+ API endpoints, prove latency claims | Days |
| **PostHog** (expand) | MIT | Already in landing — add to dashboard + checkout | Hours |

### Adopt Next Month
| Tool | License | Why | Effort |
|------|---------|-----|--------|
| **Langfuse** | MIT | Trace agent reasoning → payment decision chains. Product differentiator. | Days-Weeks |
| **Convoy** | MPL-2.0 | Replace hand-rolled webhooks with enterprise-grade delivery | Weeks |
| **Coinbase AgentKit** | Apache-2.0 | Build sardis-agentkit adapter for ecosystem alignment | Days |
| **Infisical** | MIT | Centralized secrets when team grows past 1 person | Days |

### Adopt Pre-Enterprise
| Tool | License | Why | Effort |
|------|---------|-----|--------|
| **Hatchet** | MIT | Replace ad-hoc background jobs with durable Postgres queue | Weeks |
| **OpenFGA or SpiceDB** | Apache-2.0 | Zanzibar-style auth when multi-org complexity grows | Weeks |
| **Metabase** | AGPL (internal OK) | Internal BI dashboards pointed at Neon PostgreSQL | Days |

### Already Integrated
| Tool | Status |
|------|--------|
| **Foundry** | Contracts toolchain — active |
| **Viem** | Checkout UI — active |
| **Lit Protocol** | Tertiary signer — active |
| **PostHog** | Landing page analytics — active |
| **PgBouncer** | Via Neon connection pooler — active |
| **Safe Smart Accounts** | v1.4.1 wallet infrastructure — active |

---

## License Warnings — DO NOT USE

| Tool | License | Risk |
|------|---------|------|
| **c15t** | GPL-3.0 | Must open-source all linked code |
| **Citus** | AGPL-3.0 | Must open-source entire SaaS backend |
| **circom/snarkjs** | GPL-3.0 | Copyleft propagates to Sardis code |
| **Unkey** | AGPL-3.0 | Network copyleft — must open-source modifications |
| **Metabase** | AGPL-3.0 | OK for internal use, NOT for embedding in product |

## Safe Alternatives for Blocked Tools

| Blocked Tool | Problem | Safe Alternative | License | Notes |
|---|---|---|---|---|
| **c15t** (GPL-3.0) | Cookie consent | **CookieConsent by Orestbida** | MIT | Lightweight, customizable, or build 20-line banner in Next.js |
| **Citus** (AGPL-3.0) | PostgreSQL sharding | **Neon autoscaling** | Managed | Already using. Also: native `PARTITION BY RANGE` on org_id |
| **circom/snarkjs** (GPL-3.0) | ZK proof circuits | **Noir** (Aztec) | MIT | Modern ZK DSL in Rust. Also: **Halo2** (MIT/Apache), **SP1** (Apache-2.0), **Risc Zero** (Apache-2.0) |
| **Unkey** (AGPL-3.0) | API key management | **Sardis current system** | Own code | Already production-grade. Also: **Zuplo** (proprietary, free tier) |
| **Metabase** (AGPL-3.0) | BI dashboards | **Apache Superset** | Apache-2.0 | Full BI platform. Also: **Redash** (BSD-2), **Evidence** (MIT) |
| **Dradis** (GPLv2) | Pentest reporting | **OWASP ZAP** | Apache-2.0 | Automated security testing. Also: **Nuclei** (MIT) |

## License Caution — Conditional Use
| Tool | License | Condition |
|------|---------|-----------|
| **Vault** | BSL-1.1 | OK for internal secrets, cannot compete with HashiCorp |
| **Redpanda** | BSL-1.1 | OK for internal streaming, cannot offer as service |
| **Convoy** | MPL-2.0 | Modifications to Convoy files must be shared; Sardis code unaffected |
| **Dradis** | GPLv2 | OK as internal tool, cannot distribute |

---

## Full Analysis (48 Tools)

### Policy & Authorization

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 1 | **OPA** | Apache-2.0 | No | Sardis 12-gate engine is purpose-built for payments. OPA is generic. |
| 2 | **Cedar** | Apache-2.0 | No | Formal verification is nice but Sardis policies are already deterministic. Future consideration for enterprise. |
| 3 | **Cerbos** | Apache-2.0 | No | Sardis RBAC (705 lines) already has custom roles + resource permissions. |
| 4 | **OPAL** | Apache-2.0 | No | Real-time policy sync only needed with distributed policy agents. Sardis is monolith. |
| 5 | **OpenFGA** | Apache-2.0 | Later | Zanzibar-style auth for mandate delegation trees. Post-Series A. |
| 6 | **SpiceDB** | Apache-2.0 | Later | Same as OpenFGA. Better API design, smaller community. |

### Identity & Credentials

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 7 | **Veramo** | Apache-2.0 | No | Sardis has custom TAP identity (identity.py, fides_did.py). W3C VC compat could help enterprise later. |
| 8 | **Hyperledger Aries** | Apache-2.0 | No | **ARCHIVED** since April 2025. Migrated to Open Wallet Foundation. Dead project. |
| 9 | **Hyperledger Identus** | Apache-2.0 | No | Cloud-hosted SSI. Sardis identity is on-chain (ERC-8004). Different approach. |
| 10 | **DIDComm** | Apache-2.0 | No | Agent-to-agent messaging spec. Interesting for protocol layer, not urgent. |

### Compliance & Privacy

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 11 | **c15t** | **GPL-3.0** | **SKIP** | License incompatible with proprietary software. |
| 12 | **Sigstore** | Apache-2.0 | **YES** | Sign Docker images + SDK packages. Zero code changes. CI/CD only. |
| 13 | **OpenSSF Scorecard** | Apache-2.0 | **YES** | GitHub Action producing 0-10 security score. Hours of setup. |

### API & Key Management

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 14 | **Unkey** | **AGPL-3.0** | **SKIP** | License risk. Sardis already has full API key system. |
| 15 | **Infisical** | MIT | Later | Secrets management when team grows. Python SDK plugs into existing SecretsProvider. |

### Orchestration & Workflows

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 16 | **Temporal** | MIT | No | Overkill — requires Cassandra/MySQL cluster. Sardis orchestrator completes in seconds. |
| 17 | **Hatchet** | MIT | Later | Postgres-native task queue. Good for background jobs (webhooks, reconciliation). |

### Event Streaming & Messaging

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 18 | **Redpanda** | BSL-1.1 | No | Event streaming for millions of events/sec. Sardis processes payments synchronously. |
| 19 | **NATS** | Apache-2.0 | No | Upstash Redis already handles pub/sub. NATS adds operational burden. |
| 20 | **Benthos** | MIT | No | ETL tool, not payment pipeline. Category mismatch. |

### Webhooks

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 21 | **Convoy** | MPL-2.0 | **YES** | Replace hand-rolled webhooks with circuit breaking, endpoint health, delivery dashboard. |

### Audit & Verification

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 22 | **Google Trillian** | Apache-2.0 | No | Sardis has custom Merkle tree + blockchain anchoring. Trillian requires Go server + own DB. |
| 23 | **circom/snarkjs** | **GPL-3.0** | **SKIP** | License risk. Use Noir (MIT) or Halo2 (MIT/Apache) if ZKP needed later. |

### Database & Caching

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 24 | **Citus** | **AGPL-3.0** | **SKIP** | License dealbreaker for SaaS. Use Neon autoscaling + table partitioning instead. |
| 25 | **KeyDB** | BSD-3 | No | Upstash Redis is serverless with zero ops. Valkey (Linux Foundation) is better if self-hosting later. |
| 26 | **PgBouncer** | ISC | Done | Already via Neon connection pooler. |

### Secrets Management

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 27 | **HashiCorp Vault** | BSL-1.1 | No | GCP Secret Manager is simpler for Cloud Run. Vault for multi-cloud/on-prem later. |

### Observability

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 28 | **OpenTelemetry** | Apache-2.0 | **YES** | Highest priority. Trace payment pipeline phases. Auto-instrument FastAPI. |
| 29 | **SigNoz** | MIT | No | Self-hosted observability backend. Use managed Grafana Cloud free tier instead. |
| 30 | **Langfuse** | MIT | **YES** | Trace agent reasoning → payment decisions. Product differentiator for AI agent payments. |

### Wallet & MPC

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 31 | **Coinbase CDP/AgentKit** | Apache-2.0 | **YES** | Build sardis-agentkit adapter. Ecosystem alignment (x402, World ID). |
| 32 | **Coinbase cb-mpc** | MIT | No | Raw MPC primitives. Sardis uses managed providers. |
| 33 | **Lit Protocol** | MIT | Done | Already integrated as tertiary signer. |
| 34 | **Privy** | Proprietary | No | Consumer embedded wallets. Wrong problem space for AI agents. |
| 35 | **Openfort** | MIT | Watch | Overlapping positioning. Potential alternative signer. |
| 36 | **Web3Auth** | MIT | No | Social login wallets. Not for programmatic agent wallets. |

### Payment Infrastructure

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 37 | **Mojaloop** | Apache-2.0 | No | Fiat interbank settlement. Completely different domain. |
| 38 | **Hyperswitch** | Apache-2.0 | Later | Multi-processor fiat routing. Only if Sardis adds fiat rails beyond Stripe. |

### Networking

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 39 | **libp2p** | MIT | No | P2P networking. Sardis is centralized API. Architecture mismatch. |

### Dev Tools & CI/CD

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 40 | **k6** | Apache-2.0 | **YES** | Load test APIs. Prove latency claims for investors. |
| 41 | **Dagger** | Apache-2.0 | Later | Programmable CI/CD. Current shell scripts work for solo founder. |
| 42 | **Viem** | MIT | Done | Already in checkout UI. |
| 43 | **Foundry** | MIT/Apache | Done | Already the contracts toolchain. |

### Analytics & Dashboards

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 44 | **Metabase** | AGPL-3.0 | Internal | Point at Neon for internal BI. Cannot embed in product (AGPL). |
| 45 | **PostHog** | MIT | Expand | Already in landing. Add to dashboard + checkout. |

### Misc

| # | Tool | License | Need? | Verdict |
|---|------|---------|-------|---------|
| 46 | **Lockness** | Apache-2.0 | No | Raw MPC/TSS Rust libs. Sardis uses managed providers. |
| 47 | **Dradis** | GPLv2 | Later | Pentest reporting. Post-SOC2. OK as internal tool. |
| 48 | **Bitcoin Core** | MIT | No | Different chain model (UTXO). Interesting patterns but not actionable. |

---

## Sardis Competitive Moats (Already Better Than OSS)

These Sardis implementations are **competitive advantages** that no single OSS tool replaces:

1. **12-Gate Spending Policy Engine** (`spending_policy.py`, 842 lines) — purpose-built for AI agent payments. OPA/Cedar are generic.
2. **TAP Identity + FIDES DID** (`identity.py`, `fides_did.py`) — agent-specific identity with on-chain ERC-8004. Veramo/Aries are generic SSI.
3. **Merkle-Anchored Ledger** (`sardis-ledger/`) — blockchain-anchored audit trail. Trillian is off-chain only.
4. **AP2 Mandate Verification** (`ap2.py`) — Google/PayPal/Mastercard standard. No OSS equivalent.
5. **Multi-Provider Wallet Failover** (Turnkey → Circle → Lit) — no single OSS tool provides this.
6. **Pre-Execution Pipeline** (`pre_execution_pipeline.py`) — composable hooks (KYA, AGIT, FIDES). Custom architecture.

---

## Implementation Roadmap

```
Week 1: Sigstore + OpenSSF Scorecard + k6 (CI/CD, no code changes)
Week 2: OpenTelemetry (instrument payment pipeline)
Week 3: Langfuse (agent reasoning traces)
Week 4: Convoy (enterprise webhooks) + Infisical (secrets)
Month 2: Hatchet (background jobs) + AgentKit adapter
Month 3+: OpenFGA/SpiceDB (mandate trees) + Metabase (internal BI)
```
