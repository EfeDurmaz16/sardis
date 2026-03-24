# Sardis Labs — Investor Due Diligence Report

Date: March 2026 | Prepared for: Prospective Investors
Company: Sardis Labs, Inc. (Delaware C-corp, incorporated March 2026)

---

## Executive Summary

Sardis is the Payment OS for the Agent Economy — infrastructure enabling AI agents to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies.

**Overall Assessment:**

| Category | Score | Notes |
|----------|-------|-------|
| Architecture & Code Quality | 8/10 | 225K LOC, 12+ modular packages, well-separated concerns |
| Market Timing | 9/10 | AP2, MPP, x402 all live; Ramp Agent Cards launched March 2026; NIST AI agent standards Feb 2026 |
| Competitive Moat | 8/10 | NLP policy engine + 15 compliance modules + 15 framework integrations — unique combination |
| Team Risk | 6/10 | Solo founder (mitigated by exceptional output velocity and CC-augmented development) |
| Revenue Risk | 5/10 | Pre-revenue, but 50K SDK installs and live framework integrations de-risk adoption |

---

## 1. Code Metrics

| Metric | Value |
|--------|-------|
| Total LOC | 225,000+ |
| Languages | Python (primary), TypeScript, Solidity, SQL |
| Monorepo packages | 12+ |
| API routers | 47+ |
| Database tables | 50+ |
| Test coverage | ~70% target, integration + unit + contract tests |
| Framework integrations | 15 (OpenAI, Claude/MCP, CrewAI, LangChain, AutoGPT, Vercel AI SDK, Browser Use, n8n, Activepieces, Composio, AgentKit, Stagehand, OpenClaw, E2B, GPT Actions) |
| SDK installs | 50,000+ (PyPI + npm combined) |
| Smart contracts | 3 core (SardisWalletFactory, SardisAgentWallet, SardisEscrow) |

**Architecture highlights:**
- Domain-driven design with clear package boundaries
- Provider abstraction for all external services (Turnkey, Didit, Elliptic, etc.)
- Async/await throughout with proper error propagation
- PaymentOrchestrator as single execution path (no bypasses)
- Fail-closed compliance checks

## 2. Commit Velocity

| Period | Commits | Observation |
|--------|---------|-------------|
| 12 months (total) | 700+ | Solo founder + Claude Code augmentation |
| March 2026 (month) | 150+ | Highest velocity month: dashboard migration, MPP hackathon, TDD remediation |
| Weekly average | ~15 | Consistent output, not burst-driven |

All commits are atomic and well-described. Git history shows disciplined engineering practice.

## 3. Security Posture

| Control | Status |
|---------|--------|
| Non-custodial architecture | Turnkey MPC signing — no private key storage |
| API key hashing | SHA-256, never stored in plaintext |
| Webhook signatures | HMAC-SHA256, required in non-dev environments |
| AGIT (Agent Goal Integrity Testing) | Fail-closed by default |
| Rate limiting | Redis-backed, enforced in non-dev environments |
| Replay protection | Mandate-level dedup cache |
| Gitleaks CI | Pre-commit hook for secret scanning |
| OAuth CSRF protection | State parameter validation |
| Admin authorization | Fail-closed (no admin access without explicit role) |
| Database | Column whitelists on updates, parameterized queries |

**Not yet completed:**
- SOC2 Type II audit (planned with DSALTA, ~$15K)
- Formal smart contract audit (contracts use OpenZeppelin, Foundry-tested)
- Penetration testing

## 4. Scalability Assessment

| Component | Current | Path to Scale |
|-----------|---------|---------------|
| API | FastAPI on Cloud Run | Horizontal scaling via Cloud Run auto-scale |
| Database | Neon serverless PostgreSQL | Neon handles connection pooling and scaling |
| Cache | Upstash Redis | Serverless, scales on demand |
| Chain execution | 6 EVM chains via Alchemy RPC | Add chains by configuration, not code |
| MPC signing | Turnkey | Enterprise-grade, handles millions of keys |
| Compliance | 6 AML providers, Didit KYC | Provider abstraction enables swap/add |

**Bottleneck risk:** Chain execution latency (block confirmation times). Mitigated by multi-chain routing to select fastest available chain.

## 5. Team Risk

**Founder:** Efe Baran Durmaz, 20
- Bilkent University, BS Information Systems (2023-2027)
- Full merit scholarship, 3.53 GPA, top 0.04% on national exam (1,405th / 3.5M)
- Nokia AI/Backend Engineer (2025)
- 49 public repos, polyglot (Python, TS, Rust, Go, Solidity, Java, C++)

**Mitigants:**
- CC-augmented development multiplies effective output by 5-10x
- Modular architecture means any package can be handed to a new hire
- Clear documentation and CLAUDE.md configuration
- Advisory relationships with Coinbase, Base, Stripe, Circle engineers

**Key hire needed:** Senior backend engineer with fintech/compliance experience.

## 6. Regulatory Assessment

| Jurisdiction | Status |
|--------------|--------|
| US (Federal) | Money transmission analysis needed. Non-custodial architecture may exempt from MSB registration. Legal review budgeted ($2-5K). |
| US (State) | State-by-state MTL analysis required if custodial features added. Currently non-custodial. |
| EU (MiCA) | MiCA compliance module built. CASP tracking, Article 66 reporting, 72h SAR filing implemented. |
| FATF | Travel Rule (Rec. 16) implemented via Notabene integration. |

**Key risk:** Regulatory classification of spending mandates as a custodial service. Mitigated by non-custodial MPC architecture where users control signing keys via Turnkey.

## 7. Market Landscape

| Player | Raised | Relationship to Sardis |
|--------|--------|----------------------|
| Ramp Agent Cards | Public co | Fiat-only competitor, no stablecoin |
| Alter | $40M | Identity-only, complementary |
| Stripe MPP | Protocol | Sardis is MPP-native (early access) |
| Coinbase AgentKit | Product | Distribution channel, not competitor |
| Locus (YC F25) | YC | AI payment safety, overlapping thesis |
| Orthogonal (YC W26) | YC | Pivoted to API marketplace, no longer payments |

**Market timing signal:** March 2026 saw simultaneous launches of Ramp Agent Cards, Stripe MPP, and Tempo mainnet. The agent payments category is forming now.

## 8. Traction

| Metric | Value |
|--------|-------|
| SDK installs | 50,000+ |
| Framework integrations | 15 (3 live in marketplaces) |
| Activepieces | Live and deployed |
| CrewAI | PR waiting to merge |
| AutoGPT | In discussions with founding engineer |
| Advisory relationships | Coinbase, Base, Stripe, Bridge, Lightspark, Solana, Circle |
| MPP early access | Granted (via Ryan Aubrey, Stripe) |
| MPP Hackathon | Sardis Guard Intelligence Plane built and deployed |

## 9. Financial Model

| Tier | Price | Target Customers (90d) |
|------|-------|----------------------|
| Free | $0 | 500 signups |
| Developer | $29/mo | 50 |
| Growth | $199/mo | 10 |
| Business | $499/mo | 3 |
| Enterprise | Custom | 1 |

**Revenue projection (90 days):** $5K-10K MRR if targets hit.
**Usage revenue:** 0.1-0.5% per transaction adds to SaaS base.
**Path to $1M ARR:** 200 Growth + 20 Business + 5 Enterprise customers.

## 10. Use of Funds (Pre-Seed)

| Category | Allocation |
|----------|-----------|
| Engineering hires (2) | 50% |
| Legal (MTL analysis, ToS, compliance review) | 15% |
| Infrastructure (mainnet deployment, RPC, hosting) | 10% |
| SOC2 + security audit | 10% |
| GTM (developer advocacy, conferences, content) | 10% |
| Buffer | 5% |

---

## Summary

Sardis is a technically differentiated platform with strong market timing. The combination of NLP spending mandates, 15 compliance modules, 15 framework integrations, and Merkle-anchored audit trails is unique in the market. The primary risks are solo-founder concentration and pre-revenue status. Both are addressable with capital: hire a senior engineer and execute the GTM plan to convert 50K SDK installs into paying customers.

The agent economy needs payment infrastructure. Sardis is the most complete platform being built for this market.
