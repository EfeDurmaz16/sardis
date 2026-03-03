# Incubator Application Kit: Sardis
# YC, Techstars, and Other Top Programs

---

## 1. One-Sentence Pitch (memorize this)

**Version A (simplest):**
"We're building the payment operating system that lets AI agents spend money safely, with programmable spending policies and non-custodial wallets."

**Version B (with analogy):**
"We're Stripe for AI agents, but instead of humans clicking Buy, software makes 10,000 purchase decisions per hour with policy controls on every single one."

**Version C (problem-first):**
"AI agents can reason, but they can't be trusted with money. Sardis is how they earn that trust."

**Parent test:** "You know how AI assistants like ChatGPT are getting smarter? Soon they'll need to buy things on your behalf. Sardis makes sure they can only spend what you allow, on what you approve, with a full record of everything."

---

## 2. Founder Story

```
I watched a demo where an AI agent booked flights, hotels, and rental cars
autonomously. Impressive. Then I asked the builder: "What stops it from
booking 50 flights?"

The answer was "nothing."

That was the moment. I realized the entire AI agent ecosystem was being
built without financial guardrails. Agents can reason, plan, and execute.
But nobody built the infrastructure to let them handle money safely.

I spent the next 5 months building it. Solo. 190,000 lines of code.
Smart contracts on 6 blockchains. SDKs in Python and TypeScript. An MCP
server with 52 tools. A CLI. A policy engine that turns plain English
into deterministic spending rules.

I also realized agent payments can't exist in isolation. Agents need
identity (I built FIDES, a decentralized trust protocol), state management
(I built AgentGit, version control for agent decisions), and faster
inference infrastructure (I designed CoPU, a context processing chip
with 99-614x speedup over GPU, published as an IEEE paper).

I'm not building one product. I'm building the infrastructure layer
the agent economy needs to function.
```

**What this story does:**
- Identifies a clear, visceral problem (agent with no spending limits)
- Shows the "aha moment" was real and specific
- Demonstrates extreme execution velocity (190K lines, 5 months, solo)
- Positions the founder as someone who sees the full system, not just one feature
- Shows pattern: every project was born from necessity, not ambition

---

## 3. Unfair Advantage

### Technical depth across the full stack

Most founders in agent payments are business people who hire engineers. I designed the chip, wrote the smart contracts, built the API, and published the academic paper. There is no translation layer between vision and execution.

**Specific proof points:**

| Credential | Evidence |
|-----------|----------|
| Full-stack engineering | 7 languages in production (SystemVerilog, Rust, Python, TypeScript, Solidity, C++, SQL) |
| Hardware design | Designed CoPU from scratch in SystemVerilog, wrote IEEE paper with 99-614x speedup benchmarks |
| Crypto/blockchain | Smart contracts on 6 EVM chains, CCTP V2 bridge integration, Circle Paymaster |
| Security engineering | MPC custody integration, Ed25519 identity protocol, RFC 9421 HTTP signatures |
| Execution speed | 190K lines of production code in 5 months, solo |
| Open source traction | 9,880 npm downloads/month, zero marketing spend |
| Multi-project vision | 6 shipping open-source projects, all interconnected |

### Why me specifically

"The agent economy needs someone who understands payments, cryptography, hardware, and developer tools simultaneously. Most teams specialize in one. I built production systems in all four. Not because I wanted to prove something, but because each missing piece blocked the next."

---

## 4. Market Size (TAM)

### The short version (for applications)

"AI agents will process $3.6 trillion in transactions by 2030 (Gartner). The infrastructure layer capturing 1-3% of transaction value represents a $36-108B opportunity. Our initial segment, developer teams building AI agents that need programmatic spending (estimated 500K+ developers today, growing 200%+ annually), represents a $2.4B near-term market."

### The detailed breakdown

**Total Addressable Market: $108B**
- Global AI agent market: $3.6T in agent-processed transactions by 2030 (Gartner/McKinsey estimates)
- Infrastructure take rate: 1-3% of transaction value (comparable to Stripe's 2.9%)
- TAM: $36-108B

**Serviceable Addressable Market: $12B**
- Enterprise AI agent deployments with financial capabilities
- Agent-to-agent commerce (API purchases, compute, data)
- Autonomous procurement and expense management

**Serviceable Obtainable Market (Year 1-3): $2.4B**
- Developer teams building AI agents on major frameworks (LangChain: 100K+ weekly downloads, CrewAI: 50K+, OpenAI Agents: millions of API users)
- Initial focus: API credit purchases, SaaS subscriptions, compute procurement by AI agents
- Average transaction: $50-500, frequency: daily to hourly per agent

### Why now

1. **AI agents just got tool use.** Claude, GPT-4, Gemini all shipped tool calling in 2024-2025. Agents can now interact with external systems, but have zero financial infrastructure.

2. **Google, PayPal, Mastercard, Visa co-developing AP2.** The biggest payment companies on earth are betting agents will transact. The protocol standard is being written now. Sardis already implements AP2 mandate verification.

3. **$66M+ raised by competitors in 6 months.** Skyfire ($9.5M, a16z), Payman ($13.8M, Visa), Paid ($33.3M, Lightspeed), Natural ($9.8M). The category is real and being defined right now.

4. **Stablecoin infrastructure matured.** Circle CCTP V2 enables cross-chain USDC transfers natively. Paymasters enable gasless transactions. The rails exist. The governance layer doesn't.

---

## 5. Traction & Execution Metrics

### What we have (use the strongest ones)

| Metric | Number | Why It Matters |
|--------|--------|----------------|
| Lines of production code | 190,000+ | Extreme execution velocity |
| npm downloads | 9,880/month | Organic developer adoption, zero marketing |
| Published packages | 23 | Full ecosystem (SDKs, CLI, MCP server, contracts) |
| MCP server tools | 52 | Deepest agent integration in the category |
| Supported blockchains | 6 (Base, Polygon, Ethereum, Arbitrum, Optimism, Arc) | Multi-chain from day 1 |
| Framework integrations | 9 (across AgentGit) | Claude SDK, OpenAI, LangGraph, CrewAI, Google ADK, Vercel AI, MCP, A2A, FIDES |
| Smart contracts deployed | 7 | On-chain infrastructure, not just API wrappers |
| API endpoints | 300+ | Production-grade backend |
| Database tables | 50+ | Real data model, not a prototype |
| Open source projects | 6 shipping | Broad infrastructure vision |
| Time to build | 5 months | Solo founder velocity |
| Marketing spend | $0 | All growth is organic |

### One impressive metric (pick one for the application)

**Option A:** "9,880 npm downloads last month with zero marketing. Our docs are indexed by AI coding assistants, so when developers ask 'how do I add payments to my AI agent,' the AI recommends Sardis. Agents are selling our product to developers."

**Option B:** "190,000 lines of production code in 5 months. Solo. Not a prototype. 300+ API endpoints, 7 smart contracts, SDKs in 2 languages, an MCP server with 52 tools, and a CLI. Shipping, not pitching."

**Option C:** "52-tool MCP server. The deepest AI agent payment integration in existence. Any agent running in Claude, Cursor, or Windsurf can create wallets, send payments, check balances, and set spending policies without writing a single line of code."

---

## 6. Application Answers (YC format)

### "Describe what your company does in 50 characters or less."

```
Payment infrastructure for AI agents.
```
(38 characters)

### "What is your company going to make?"

```
Sardis is the payment operating system for AI agents. We provide non-custodial MPC wallets with natural language spending policies that are enforced before any money moves.

When a developer writes "Max $100 per transaction, only pay verified API providers," our policy engine parses this into deterministic constraints and blocks any transaction that violates them. The agent never touches private keys. Turnkey's MPC network handles signing. The developer gets a full audit trail.

We ship as an MCP server (52 tools), Python SDK, TypeScript SDK, CLI, and smart contracts on 6 EVM chains. An AI agent in Claude or Cursor can create a wallet, set a spending policy, and make a payment in under 60 seconds without writing code.
```

### "Why did you pick this idea to work on? Do you have domain expertise in this area?"

```
I watched an AI agent demo where the agent booked flights, hotels, and cars autonomously. I asked what stops it from booking 50 flights. The answer was nothing.

That moment revealed a gap: the entire agent ecosystem is being built without financial guardrails. Hundreds of companies build agent frameworks. Almost nobody builds the infrastructure agents need to handle money.

My domain expertise: I've built production systems across the full stack this problem requires. Smart contracts on 6 blockchains (Solidity). MPC custody integration (Turnkey). Cryptographic identity protocols (Ed25519, RFC 9421). Policy engines (Python/FastAPI). Developer SDKs (TypeScript). I also designed a hardware accelerator for LLM context operations from scratch in SystemVerilog and published an IEEE paper on it.

I'm not a business person who hired engineers to build this. I wrote every line of code. 190,000 lines in 5 months.
```

### "What's new about what you're making? What substitutes do people resort to today?"

```
Today, developers giving agents financial capabilities use one of three approaches:

1. Raw API keys to payment services (Stripe, PayPal). The agent has full access with no per-transaction controls. One bad decision means unlimited spending.

2. Hardcoded limits in application code. Fragile, not auditable, trivially bypassable by the agent itself.

3. Human-in-the-loop approval. Defeats the purpose of autonomous agents. Doesn't scale.

Sardis is different in three ways:

First, policies are enforced at the wallet level, not the application level. The agent cannot bypass them because the MPC signing infrastructure won't sign a transaction that violates policy. Fail-closed by design.

Second, policies are written in plain English, not code. "Only pay verified SaaS vendors, max $200/day" is a real policy that works today.

Third, we're multi-chain and multi-token from day one. USDC on Base, USDT on Polygon, EURC on Ethereum. Same policy, same SDK, same audit trail regardless of chain.

Our competitors (Skyfire, Payman, Paid) focus on the payment rail. We focus on the governance layer: who can spend, how much, on what, and who audits it. Rails are a commodity. Governance is the moat.
```

### "How far along are you?"

```
Sardis is a working product, not a prototype.

- 190,000 lines of production code
- 300+ API endpoints (FastAPI)
- 7 deployed smart contracts on 6 EVM chains
- 52-tool MCP server (deepest agent payment integration in the category)
- Python SDK, TypeScript SDK, CLI published on PyPI and npm
- 9,880 npm downloads/month with $0 marketing spend
- 50+ database tables with 17 migrations (PostgreSQL)
- KYC (iDenfy), AML (Elliptic), virtual cards (Stripe Issuing) integrated
- Policy engine with 150+ tests and fuzz testing

Built solo in 5 months. Incorporating as a Delaware C-Corp now.

We also built three adjacent infrastructure projects, all open source and shipping:
- AgentGit: version control for agent state (Rust core, 9 framework integrations)
- FIDES: decentralized identity/trust for agents (Ed25519 DIDs)
- CoPU: hardware accelerator for LLM context (SystemVerilog RTL, IEEE paper, 99-614x speedup vs GPU)
```

### "How will you make money?"

```
Three revenue streams, in order of implementation:

1. Transaction fees (1-2% of processed volume). Every agent payment through Sardis generates revenue. As agents process more transactions, revenue scales linearly. This is the Stripe model applied to agent commerce.

2. Platform fees for enterprise features. Policy management dashboard, multi-agent governance, compliance reporting, SSO, audit exports. $500-5,000/month per organization.

3. Virtual card issuance. When agents need to pay vendors that don't accept crypto (most of them today), we issue virtual Visa/Mastercard cards with per-card spending limits. Revenue from interchange (1-2%) plus card issuance fees.

Near-term economics: if 1,000 agents process an average of $500/month in transactions (conservative for API credits, compute, and SaaS subscriptions), that's $500K/month in volume and $5-10K/month in transaction fee revenue. At 10,000 agents, we hit $50-100K MRR.
```

### "Who are your competitors?"

```
Direct competitors (agent payments, raised $66M+ combined):

- Skyfire ($9.5M, a16z): crypto rails for AI agents. Focus on the payment rail, not governance. No policy engine. No multi-chain.
- Payman ($13.8M, Visa-backed): fiat-first agent payments. Custodial wallets. Limited to USD. No on-chain execution.
- Paid ($33.3M, Lightspeed): agent commerce platform. Broader scope but less technical depth on the payment infrastructure.
- Natural ($9.8M): AI-native financial operations. Focus on expense management.

Our advantage over all of them: governance, not just rails.

Rails are commoditizing. Stablecoins, CCTP, paymasters make moving money easy. The hard problem is: who controls what the agent can spend? How do you audit it? How do you enforce policies across chains?

Sardis is the only solution with:
- Natural language policy engine (not code-based rules)
- Non-custodial MPC wallets (not custodial)
- Multi-chain, multi-token support (6 chains, 5 stablecoins)
- 52-tool MCP server (deepest agent integration)
- AP2 protocol verification (Google/PayPal/Mastercard/Visa standard)
- Open source core (competitors are closed source)
```

### "How do or will you get users?"

```
Three channels, in priority order:

1. Agent-native distribution (already working). Our docs are indexed on Context7. When a developer asks an AI coding assistant "how do I add payments to my AI agent," the assistant recommends Sardis and shows implementation examples. This generated 9,880 npm downloads last month with zero marketing. Agents are selling our product to developers. This channel scales as AI coding assistants become more prevalent.

2. Developer community (starting now). Build-in-public content on X and LinkedIn. Hacker News launches (Show HN for Sardis, CoPU, and RustShell). Direct engagement in AI agent framework communities (LangChain, CrewAI, OpenAI, Google ADK Discords and forums).

3. Framework partnerships. AgentGit already integrates with 9 agent frameworks. Each integration is a distribution channel. When a LangGraph tutorial shows agent state management with AgentGit, Sardis becomes the natural payment layer.

Long-term: the AP2 protocol (Google, PayPal, Mastercard, Visa) will standardize agent payment flows. Sardis implements AP2 today. When the standard is adopted, every agent framework will need AP2-compatible payment infrastructure.
```

### "Why should we fund you? (the most important question)"

```
Three reasons:

1. I've already built it. This isn't a pitch deck. It's 190,000 lines of production code, 7 smart contracts, SDKs in 2 languages, and an MCP server with 52 tools. Solo. In 5 months. Most teams with 5 engineers and $2M in funding haven't shipped this much.

2. I see the full stack. Agent payments can't work without agent identity (FIDES), agent state management (AgentGit), and faster inference (CoPU). I didn't just identify these dependencies. I built production solutions for each one. This systems-level thinking is what separates infrastructure companies from feature companies.

3. The timing is perfect. Google, PayPal, Mastercard, and Visa are building the AP2 standard. Competitors raised $66M+ in 6 months. The category is being defined right now. I'm the only founder in this space who has shipped a working multi-chain, multi-token, policy-enforced, non-custodial payment system for agents. Today.

If this specific idea needed to pivot, I'd still be the right person to fund. I've demonstrated I can identify infrastructure gaps and build production solutions faster than most funded teams. The agent economy needs builders, not pitchers. I build.
```

---

## 7. Video Application Tips (YC requires a 1-min video)

### Script (60 seconds)

```
[0-5s] "Hey, I'm Efe. I'm building Sardis, the payment OS for AI agents."

[5-15s] "Here's the problem: AI agents are getting tool use, browsing,
and autonomy. But nobody built the financial infrastructure for them.
Right now, giving an agent spending access means giving it a credit card
with no limits. That's insane."

[15-30s] "Sardis gives every agent a non-custodial wallet with policy
controls. 'Max $100 per transaction, only verified vendors.' Written
in English. Enforced on-chain. If the policy says no, no money moves."

[30-45s] "I built this solo in 5 months. 190K lines of code.
Smart contracts on 6 chains. MCP server with 52 tools.
Python and TypeScript SDKs. 9,880 npm downloads last month,
zero marketing spend."

[45-55s] "The competitors raised $66M combined. I've shipped more
product than all of them with zero funding. I'm the only founder
in this space who's built across payments, crypto, identity,
and hardware."

[55-60s] "The agent economy is coming. I'm building its financial
infrastructure. That's Sardis."
```

### Video tips
- Record in good lighting, plain background
- Look at the camera, not the screen
- Speak naturally, not rehearsed
- No slides, no demos. Just you talking.
- Energy matters. Sound like you believe this.
- Record 10 takes. Use the best one.

---

## 8. Interview Prep (10-minute YC interview)

### Expected questions and answers

**"What are you building?"**
"Payment infrastructure for AI agents. Non-custodial wallets with natural language spending policies. The agent writes 'max $100, only SaaS vendors.' We enforce it before any money moves."

**"Who are your customers?"**
"Developer teams building AI agents that need financial capabilities. Think: an agent that buys API credits, pays for compute, or manages SaaS subscriptions. Today they use raw API keys with no controls. We give them policy-enforced wallets."

**"Why hasn't someone solved this before?"**
"Two reasons. First, agents couldn't use tools until 2024. No tool use means no financial transactions. Second, this requires expertise across payments, crypto, security, and developer tools simultaneously. Most teams specialize in one. I built production systems in all four."

**"What's your unfair advantage?"**
"I'm the only founder in this space who's shipped across the full stack. Smart contracts, MPC integration, policy engine, SDKs, MCP server, CLI. Solo. Plus I built three adjacent projects: agent identity, agent state versioning, and a hardware chip for LLM context. I see the whole system."

**"How do you make money?"**
"1-2% transaction fee on every agent payment. As agent transaction volume grows from thousands to millions per day, revenue scales with it."

**"What if agents don't transact as much as you think?"**
"Google, PayPal, Mastercard, and Visa are co-building the AP2 agent payment standard. $66M was invested in agent payment startups in the last 6 months. The biggest payment companies on earth are betting on this. I trust their judgment."

**"Why should we pick you over a team?"**
"Look at what I shipped solo in 5 months. 190K lines, 6 chains, 52 MCP tools, SDKs in 2 languages. Most funded teams with 5 engineers haven't done this. I don't have a communication overhead problem. I don't have an alignment problem. I build."

**"What's your biggest risk?"**
"Adoption timing. Agent commerce might take 2 years instead of 1. But the infrastructure needs to exist before the transactions happen, not after. Stripe was founded 4 years before e-commerce hit mainstream. I'd rather be early than late."

**"What do you need from us?"**
"Credibility, network, and the pre-seed capital to hire my first engineer and go full-time. The product is built. Now I need distribution velocity."

### Interview rules
- Answer in the first sentence. Then provide evidence.
- Never say "that's a great question"
- If challenged, don't get defensive. Say "that's fair" and address it directly
- Keep answers under 30 seconds each
- Have specific numbers ready for everything
- If you don't know something, say "I don't know yet, but here's how I'd find out"

---

## 9. Target Incubators

| Program | Deadline | Check Size | Notes |
|---------|----------|------------|-------|
| Y Combinator | Rolling (batches W26, S26) | $500K | Accepts solo founders. Highest ROI. |
| Techstars | Varies by program | $120K | Look for fintech or AI-specific programs |
| a]cdl (Antler) | Rolling | $100-150K | Present in many cities, AI focus |
| Entrepreneur First | Rolling | Pre-team, $100K+ | For solo founders specifically |
| Neo | Invitation/application | $100K+ | YC alternative for technical founders |
| South Park Commons | Rolling | Community + funding | Good for pre-idea/early founders |
| On Deck | Rolling | Community + $100K | Strong network effects |
| Pear VC | Rolling | Pre-seed focus | Developer tools thesis |

### Priority order
1. **YC** (highest impact, accepts solo founders, $500K)
2. **Techstars Fintech** (if YC timing doesn't work)
3. **Entrepreneur First** (designed for solo founders)
4. **Antler** (rolling, fast, AI-focused)

---

## 10. Application Timeline

### 4 weeks before deadline

- [ ] Finalize one-sentence pitch (test on 10 non-technical people)
- [ ] Record practice video (10 takes)
- [ ] Draft all application answers
- [ ] Get feedback from 3-5 founders who've been through YC/Techstars
- [ ] Update traction metrics to latest numbers
- [ ] Clean up sardis.sh, README files, demo videos

### 2 weeks before deadline

- [ ] Revise application based on feedback
- [ ] Record final video (another 10 takes)
- [ ] Have 2 more people review final draft
- [ ] Prepare 1-page deck (backup, not required)
- [ ] Practice interview answers with a timer (30 sec max per answer)

### 1 week before deadline

- [ ] Final proofread
- [ ] Submit
- [ ] Prepare interview (if invited, usually 1-2 weeks after submission)

### After submission

- [ ] Continue building and shipping
- [ ] Update application metrics if they improve significantly before review
- [ ] Do not wait. Keep executing.
