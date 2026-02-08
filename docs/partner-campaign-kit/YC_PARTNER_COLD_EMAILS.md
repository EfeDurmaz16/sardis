# YC Partner Cold Emails — Post-Application Outreach
## Sardis: Payment OS for AI Agents

> **Strateji:** YC başvurusunu yaptıktan SONRA gönder. Başvuru önce, email sonra. Her email partner'ın özel background'ına göre kişiselleştirilmiş. Hepsini aynı gün gönderme — 2-3 güne yay.

> **Email pattern:** `firstname@ycombinator.com`

---

## TIER 1 — EN YÜKSEK RELEVANCE (Önce bunları gönder)

---

### 1. Harshita Arora — Visiting Partner
**Background:** AtoB co-founder (YC S20) — trucking için payment OS. 16 yaşında crypto app yapmış, $125M+ raise etmiş.
**Neden #1:** Sardis'in birebir paraleli. O trucking için payment OS yaptı, sen AI agent'lar için.

**To:** harshita@ycombinator.com
**Subject:** Payment OS for AI agents — same thesis as AtoB, different vertical

Hi Harshita,

Just submitted our YC application for Sardis — payment infrastructure for AI agents.

I think you'll get this immediately because you built the same thing for a different vertical. AtoB is payment OS for trucking. Sardis is payment OS for AI agents. Same core insight: an underserved actor needs programmable financial rails.

The difference is our "driver" hallucinates. An AI agent recently spent $8,000 on courses it "thought would be helpful." No 2FA, no friction, just gone. So we built non-custodial MPC wallets, virtual card issuing through Lithic, and natural language spending policies enforced on-chain — 1,516 lines of Solidity on Base Sepolia.

Testnet live, design partners onboarding, paid beta at $1.5-2K/mo.

Would love 15 minutes if this resonates. I think you'd see the parallels faster than anyone at YC.

Best,
Efe Baran Durmaz
sardis.sh

---

### 2. Jon Xu — General Partner
**Background:** FutureAdvisor co-founder (YC S10) — robo-advisor, acquired by BlackRock. MIT CS.
**Neden:** Doğrudan fintech deneyimi. Financial infra + compliance anlıyor.

**To:** jon@ycombinator.com
**Subject:** Non-custodial payment infra for AI agents

Hi Jon,

Just submitted our YC application for Sardis.

You built FutureAdvisor — automated financial management that people could trust. We're solving the same trust problem for a new type of user: AI agents.

Agents can reason but they hallucinate financially. One recently spent $8,000 on courses it "thought would be helpful." There's no infrastructure that lets agents spend within approved policies.

Sardis provides non-custodial MPC wallets (Turnkey), virtual card issuing (Lithic), and natural language spending policies enforced in Solidity smart contracts. Not just API-level — on-chain enforcement. We also implement three protocol standards: TAP (identity), AP2 (mandate chain — Google/Visa/MC standard), and x402 (HTTP 402 settlement).

19 packages, 77+ test files, testnet live on Base Sepolia. Design partners onboarding now.

Your fintech background at FutureAdvisor and BlackRock is exactly the lens I'd love feedback through.

Best,
Efe
sardis.sh

---

### 3. Andrew Miklas — General Partner
**Background:** PagerDuty co-founder/CTO (YC S10, NYSE:PD). High-availability infra expert.
**Neden:** Payment sistemi = uptime kritik. Infra mimarisi anlıyor.

**To:** andrew@ycombinator.com
**Subject:** Payment infrastructure for AI agents — reliability-first architecture

Hi Andrew,

Just submitted our YC application for Sardis — payment OS for AI agents.

As PagerDuty's founding CTO, you know that infrastructure must be bulletproof. Payment infrastructure for autonomous agents needs to be even more so — because there's no human in the loop to catch failures.

We built Sardis with a fail-closed architecture: Turnkey MPC for non-custodial custody, multi-RPC chain execution with failover, compliance checks that block by default (Persona KYC + Elliptic sanctions), and spending limits enforced at the smart contract level — not just API-level.

An AI agent can't drain a wallet even if our API is compromised. The Solidity contracts enforce limits independently.

19 packages, 21 FastAPI router modules, 3 deployed smart contracts, 77+ test files. Testnet live, design partners onboarding.

Would value your perspective on the infrastructure design.

Best,
Efe
sardis.sh

---

### 4. Christopher Golda — Visiting Partner
**Background:** BackType co-founder (YC S08), acquired by Twitter. Apache Storm creator. Early Coinbase investor.
**Neden:** Distributed systems + crypto/fintech ilgisi (Coinbase early investor).

**To:** christopher@ycombinator.com
**Subject:** Distributed payment infrastructure for AI agents

Hi Christopher,

Just submitted our YC application for Sardis.

Given your background in distributed real-time systems (Apache Storm, Lambda Architecture) and early conviction in crypto payments (Coinbase seed), I think Sardis sits right at the intersection.

We're building payment infrastructure for AI agents — non-custodial MPC wallets, multi-chain execution across 5 EVM networks with multi-RPC failover, and real-time policy enforcement. The challenge is essentially a distributed consensus problem: how do you let autonomous agents transact while enforcing spending constraints in real-time?

Our approach: natural language policies parsed once, enforced deterministically — both at API level and on-chain through Solidity contracts. Plus three protocol implementations (TAP identity, AP2 mandate chains, x402 HTTP settlement) that nobody else has together.

Testnet live on Base Sepolia, design partners onboarding.

Would love your take on the architecture.

Best,
Efe
sardis.sh

---

## TIER 2 — STRONG RELEVANCE

---

### 5. Grey Baker — Visiting Partner
**Background:** GoCardless early team (YC S11, payments infra), Dependabot creator (acquired by GitHub). Cambridge economics.
**Neden:** Payments infra + developer tools. Tam Sardis'in iki bacağı.

**To:** grey@ycombinator.com
**Subject:** Open-core payment infra for AI agents — GoCardless meets MCP

Hi Grey,

Just submitted our YC application for Sardis.

Your GoCardless + Dependabot background is rare: payments infrastructure AND developer tools. Sardis lives at exactly that intersection.

We're building payment OS for AI agents — open-core model where Python SDK, TypeScript SDK, MCP server, and CLI are all MIT. The money layer (policy engine, MPC custody, compliance) is proprietary. Think Stripe's model: client libraries open, backend closed.

The developer experience matters because we're targeting the same community you served with Dependabot — developers integrating payment capabilities into their AI agents. pip install sardis, 5 minutes to first transaction.

Testnet live, 36-tool MCP server for Claude/Cursor integration, design partners onboarding.

Best,
Efe
sardis.sh

---

### 6. Nicolas Dessaigne — General Partner
**Background:** Algolia co-founder — search API, 1.75 trillion searches/year, 17K+ customers.
**Neden:** Developer API/infra scaling master. SDK/DX anlıyor.

**To:** nicolas@ycombinator.com
**Subject:** Payment API for AI agents — developer-first infrastructure

Hi Nicolas,

Just submitted our YC application for Sardis.

You built Algolia into the standard for search APIs. We're building the standard for AI agent payment APIs.

Same playbook: developer-first, API-centric, open SDK (MIT), managed backend. An agent developer does pip install sardis and gets wallets, payments, policies, compliance in one integration. MCP server with 36 tools means Claude and Cursor users get native payment capabilities.

The difference from traditional payment APIs: our users aren't human. They hallucinate. So we built natural language spending policies enforced on-chain, not just API-level. An agent can't overspend even if it "decides" to.

Testnet live, 21 FastAPI router modules, 19 packages. Design partners onboarding now.

Your experience scaling Algolia's developer adoption is exactly the lens I'd love.

Best,
Efe
sardis.sh

---

### 7. Garry Tan — President & CEO
**Background:** Coinbase first seed check writer. Initialized Capital co-founder. Palantir early employee.
**Neden:** YC CEO + crypto/fintech conviction. En yüksek profil ama en meşgul kişi.

**To:** garry@ycombinator.com
**Subject:** Payment infra for AI agents — the Coinbase moment for agent economy

Hi Garry,

Just submitted our YC application for Sardis.

You wrote Coinbase's first seed check because you saw that crypto needed trusted infrastructure. The agent economy is at the same inflection point. AI agents can reason and act, but they can't be trusted with money. An agent recently spent $8,000 on courses it "thought would be helpful." No 2FA, no human in the loop.

Sardis is the trust layer: non-custodial MPC wallets, virtual card issuing, natural language spending policies enforced on-chain. Three protocol standards implemented (TAP/AP2/x402 — we're the only project with all three). Open-core — MIT SDK, proprietary money layer.

Solo founder, full-time, testnet live on Base Sepolia. Design partners onboarding now.

Best,
Efe
sardis.sh

---

### 8. Diana Hu — General Partner
**Background:** Escher Reality CTO (YC S17), acquired by Niantic. Carnegie Mellon ML/CV.
**Neden:** AI/ML derinliği. Agent teknolojisini anlıyor.

**To:** diana@ycombinator.com
**Subject:** Solving financial hallucinations in AI agents

Hi Diana,

Just submitted our YC application for Sardis.

Your ML background at Carnegie Mellon and experience building AI systems at Niantic gives you a unique lens on this: AI agents hallucinate — not just text, but financial decisions. An agent recently spent $8,000 on purchases it "thought would be helpful."

We call these "financial hallucinations." Agents WILL make bad spending decisions. The question is whether infrastructure catches it before money moves.

Sardis provides non-custodial wallets, virtual cards, and natural language spending policies. The policies are written by humans in plain English — "max $100 per transaction, only whitelisted vendors" — parsed once, enforced deterministically. No AI in the enforcement loop. The LLM writes the rules, pure logic enforces them.

19 packages, 3 smart contracts, testnet live. Design partners onboarding.

Best,
Efe
sardis.sh

---

### 9. David Lieb — General Partner
**Background:** Bump co-founder (YC S09, 150M+ users), built Google Photos AI. Stanford AI Lab.
**Neden:** AI researcher + product at massive scale.

**To:** david@ycombinator.com
**Subject:** Payment infrastructure for autonomous AI agents

Hi David,

Just submitted our YC application for Sardis.

Your work on background AI systems (from Bump to Google Photos) is actually relevant to what we're building: infrastructure that operates autonomously. Sardis is payment infrastructure for AI agents — the financial layer that runs without human intervention.

The core problem: agents make financial decisions, and sometimes those decisions are wrong. OpenClaw spent $8,000 on courses because the agent "thought they'd be helpful." We solve this with non-custodial MPC wallets and natural language spending policies enforced on-chain.

What excites me most: agent-to-agent payments. A CFO agent orchestrating spending across an agent swarm — approving, denying, rebalancing budgets autonomously. We've deployed escrow contracts for this on Base Sepolia.

Testnet live, design partners onboarding, paid beta starting.

Best,
Efe
sardis.sh

---

### 10. Christina Gilbert — Visiting Partner
**Background:** OneSchema co-founder/CEO (YC S21) — AI data pipelines for developers.
**Neden:** AI infra + developer tools. Sardis'in developer experience açısı.

**To:** christina@ycombinator.com
**Subject:** Developer infrastructure for AI agent payments

Hi Christina,

Just submitted our YC application for Sardis.

OneSchema solves the data pipeline problem for AI systems. Sardis solves the payment pipeline problem. Same developer audience, same integration model — drop-in infrastructure that just works.

We built an open-core payment OS for AI agents: MIT-licensed SDKs (Python + TypeScript), MCP server with 36 tools for Claude/Cursor integration, and a CLI. The managed backend handles MPC custody, compliance, and policy enforcement.

The developer experience is core to our strategy. pip install sardis, create a wallet, set a natural language spending policy, issue a virtual card — 5 minutes to first transaction. Because if agent developers can't integrate payments in an afternoon, they won't.

Testnet live, 21 API modules, design partners onboarding.

Best,
Efe
sardis.sh

---

### 11. James Evans — Visiting Partner
**Background:** Command AI co-founder/CEO (YC S20) — AI agent platform, acquired by Amplitude.
**Neden:** Doğrudan AI agent deneyimi. 20M user'a scale etmiş.

**To:** james@ycombinator.com
**Subject:** The missing infrastructure layer for AI agents that spend

Hi James,

Just submitted our YC application for Sardis.

You built AI agents at Command AI that served 20M users. You've seen firsthand what agents can and can't do. Here's the next capability gap: agents that need to spend money.

An OpenClaw agent spent $8,000 on courses it "thought would be helpful." No guardrails, no approval flow, just autonomous spending gone wrong. This will keep happening as agents get more autonomous.

Sardis is the payment layer: non-custodial wallets, virtual cards, natural language spending policies. "Max $100/tx, only cloud providers, no weekends" — parsed once, enforced deterministically. Plus an MCP server with 36 tools so agents can do payments natively.

Your experience building and scaling agent infrastructure is exactly the perspective I'd value.

Best,
Efe
sardis.sh

---

### 12. Francois Chaubard — Visiting Group Partner
**Background:** Focal Systems founder (YC W16) — retail AI/CV. Stanford AI researcher.
**Neden:** AI researcher + applied AI for commerce/retail.

**To:** francois@ycombinator.com
**Subject:** Applying AI to financial safety — payment infrastructure for agents

Hi Francois,

Just submitted our YC application for Sardis.

You applied AI to retail operations at Focal Systems. We're applying it to financial operations for AI agents — specifically, preventing agents from making bad spending decisions.

We call it "financial hallucinations." Just as LLMs hallucinate text, they hallucinate financial decisions. An agent spent $8,000 on purchases it "thought would be helpful." Our approach: natural language spending policies written by humans, enforced deterministically by on-chain smart contracts. The AI writes the rules, pure logic enforces them.

Non-custodial MPC wallets, virtual card issuing, three protocol implementations (TAP/AP2/x402), and an MCP server for native agent integration.

Testnet live, design partners onboarding.

Best,
Efe
sardis.sh

---

## TIER 3 — GOOD TO REACH

---

### 13. Jared Friedman — Managing Partner
**Background:** Scribd co-founder/CTO (YC S06). Harvard CS. Bridgewater.
**Neden:** Infra scaling + managing partner = high leverage.

**To:** jared@ycombinator.com
**Subject:** Sardis — payment infrastructure for AI agents (YC application submitted)

Hi Jared,

Just submitted our YC application for Sardis — payment OS for AI agents.

Quick thesis: agents hallucinate financially. One recently spent $8,000 autonomously. No infrastructure exists to let agents spend within approved policies.

We built it: non-custodial MPC wallets, virtual cards (Lithic), natural language policies enforced on-chain, three protocol standards (TAP/AP2/x402). Open-core — MIT SDK, proprietary money layer.

19 packages, 1,516 lines Solidity, testnet live, design partners onboarding.

Would value any guidance on the application.

Best,
Efe
sardis.sh

---

### 14. Harj Taggar — Managing Partner
**Background:** Auctomatic co-founder (YC W07), Triplebyte co-founder (YC S15). YC's first non-founder partner.

**To:** harj@ycombinator.com
**Subject:** Sardis YC application — payment infra for AI agents

Hi Harj,

Just submitted our YC application for Sardis.

We're building payment infrastructure for AI agents — non-custodial wallets, virtual cards, natural language spending policies enforced on-chain. The problem: agents make bad financial decisions (one spent $8,000 on courses it "thought would be helpful"). No infrastructure catches this before money moves.

19 packages, 3 smart contracts on Base Sepolia, 77+ test files, MCP server with 36 tools. Open-core model — MIT SDK, proprietary backend.

Solo founder, full-time, testnet live, design partners onboarding.

Applied before with a different idea (agentic memory infra) — rejected twice. This time the product is real and the market timing is right.

Best,
Efe
sardis.sh

---

### 15. Gustaf Alströmer — General Partner
**Background:** Airbnb Growth team founding member. $118B combined YC portfolio value.

**To:** gustaf@ycombinator.com
**Subject:** Growing a developer platform in agent economy

Hi Gustaf,

Just submitted our YC application for Sardis — payment infrastructure for AI agents.

Your growth expertise is relevant here because we're building a developer platform with a classic flywheel: open-source SDK (MIT) drives adoption → more agent integrations → more transactions → more revenue from the managed service.

The product: non-custodial wallets, virtual cards, natural language spending policies. MCP server with 36 tools means any Claude/Cursor user gets payments natively. pip install sardis, 5 minutes to first transaction.

Testnet live, design partners onboarding, paid beta at $1.5-2K/mo.

Best,
Efe
sardis.sh

---

### 16. Tyler Bosmeny — General Partner
**Background:** Clever co-founder/CEO (YC S12) — SSO for K-12. Acquired for $500M. 50% of US students.

**To:** tyler@ycombinator.com
**Subject:** Sardis — compliance-first payment infra for AI agents

Hi Tyler,

Just submitted our YC application for Sardis.

You built Clever in a compliance-heavy environment (K-12 education). We're building in another one: financial infrastructure for AI agents.

Our approach is compliance-first: Persona KYC, Elliptic sanctions screening, fail-closed by default. Non-custodial MPC wallets so we never hold private keys. On-chain spending limits enforced in Solidity, not just our API. This matters because regulators will come for agent payments — we're building to be ready.

Testnet live, design partners onboarding, open-core model (MIT SDK, proprietary backend).

Best,
Efe
sardis.sh

---

### 17. Ankit Gupta — General Partner
**Background:** Reverie Labs co-founder (YC W18) — ML for drug discovery. Acquired by Ginkgo Bioworks. ICML published.

**To:** ankit@ycombinator.com
**Subject:** ML meets financial infrastructure — payment OS for AI agents

Hi Ankit,

Just submitted our YC application for Sardis.

Your work applying ML to drug discovery at Reverie is an interesting parallel. We're applying AI to financial infrastructure — but with a twist: the AI is the customer, not the tool.

AI agents hallucinate financially. One spent $8,000 on courses autonomously. We built payment infrastructure with natural language policies: a human writes "max $100/tx, only whitelisted vendors" — the system parses it once and enforces deterministically. No AI in the enforcement loop.

Non-custodial MPC wallets, on-chain smart contracts, three protocol implementations. Testnet live.

Best,
Efe
sardis.sh

---

## TRACKING TABLE

| # | Partner | Role | Email | Tier | Angle | Status |
|---|---------|------|-------|------|-------|--------|
| 1 | Harshita Arora | Visiting Partner | harshita@ycombinator.com | 1 | Payment OS parallel (AtoB) | Pending |
| 2 | Jon Xu | General Partner | jon@ycombinator.com | 1 | Fintech/BlackRock | Pending |
| 3 | Andrew Miklas | General Partner | andrew@ycombinator.com | 1 | Infra reliability (PagerDuty) | Pending |
| 4 | Christopher Golda | Visiting Partner | christopher@ycombinator.com | 1 | Distributed systems + Coinbase | Pending |
| 5 | Grey Baker | Visiting Partner | grey@ycombinator.com | 2 | Payments + dev tools | Pending |
| 6 | Nicolas Dessaigne | General Partner | nicolas@ycombinator.com | 2 | Developer API scaling (Algolia) | Pending |
| 7 | Garry Tan | President & CEO | garry@ycombinator.com | 2 | Crypto conviction + CEO | Pending |
| 8 | Diana Hu | General Partner | diana@ycombinator.com | 2 | AI/ML depth | Pending |
| 9 | David Lieb | General Partner | david@ycombinator.com | 2 | AI + product scale | Pending |
| 10 | Christina Gilbert | Visiting Partner | christina@ycombinator.com | 2 | AI dev tools (OneSchema) | Pending |
| 11 | James Evans | Visiting Partner | james@ycombinator.com | 2 | AI agents (Command AI) | Pending |
| 12 | Francois Chaubard | Visiting Group Partner | francois@ycombinator.com | 2 | Applied AI (Focal Systems) | Pending |
| 13 | Jared Friedman | Managing Partner | jared@ycombinator.com | 3 | Infra scaling + senior | Pending |
| 14 | Harj Taggar | Managing Partner | harj@ycombinator.com | 3 | Founder selection + senior | Pending |
| 15 | Gustaf Alströmer | General Partner | gustaf@ycombinator.com | 3 | Growth/flywheel | Pending |
| 16 | Tyler Bosmeny | General Partner | tyler@ycombinator.com | 3 | Compliance-heavy (Clever) | Pending |
| 17 | Ankit Gupta | General Partner | ankit@ycombinator.com | 3 | ML + complex systems | Pending |

---

## GÖNDERIM STRATEJİSİ

**Gün 1 (başvurudan 1 gün sonra):** Tier 1 — Harshita, Jon, Andrew, Christopher
**Gün 2:** Tier 2A — Grey, Nicolas, Garry, Diana
**Gün 3:** Tier 2B — David, Christina, James, Francois
**Gün 4:** Tier 3 — Jared, Harj, Gustaf, Tyler, Ankit

**Kurallar:**
- Başvuruyu ÖNCE yap, email'leri SONRA gönder
- Subject line'da "YC application submitted" veya benzeri referans olsun
- Her email'de aynı core story (OpenClaw $8K, non-custodial, on-chain enforcement) ama farklı açı
- Follow-up: 5 iş günü sonra, sadece 1 kez, yeni bir data point ekleyerek
- Eğer biri cevap verirse, diğerlerine göndermeyi durdurma — hepsine gönder
