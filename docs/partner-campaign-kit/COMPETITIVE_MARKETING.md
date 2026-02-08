# Sardis Competitive Marketing Content

Ready-to-post content highlighting our unique differentiators vs competitors.

---

## Twitter/X Threads

### Thread 1: The Policy Gap (Lead with Differentiation)

**Tweet 1:**
We analyzed every AI agent payment solution: Locus, Payman, Skyfire.

Found a massive gap.

All of them offer basic spending limits.
None of them offer natural language policy enforcement.

Here's why that matters for your agents 🧵

**Tweet 2:**
Basic limits = "$50/day, $500/month"

That's not governance. That's a number.

Real agent governance needs:
- Vendor allowlists
- Category restrictions
- Time windows
- Approval workflows
- Context-aware rules

Natural language gets you there.

**Tweet 3:**
With Sardis, you write policies like this:

"Max $100 per transaction.
Only pay approved vendors in software category.
Require approval for purchases over $50.
Never pay on weekends."

The policy engine handles the rest.

**Tweet 4:**
Why does this matter?

Financial hallucinations are real.

An agent that confidently makes incorrect purchases is dangerous.

Sophisticated policies = guardrails that match real-world business requirements.

**Tweet 5:**
We're building the policy firewall for agent payments.

Non-custodial MPC wallets + natural language policies + virtual cards + multi-chain.

No competitor has all four.

Join the alpha: sardis.sh

---

### Thread 2: Non-Custodial Advantage

**Tweet 1:**
Unpopular opinion: If your agent payment provider holds your keys, you don't own your wallet.

Most "agent wallet" solutions are custodial.

Here's why that's a problem 🧵

**Tweet 2:**
Custodial = someone else controls the keys

When things go wrong:
- Provider goes down → funds frozen
- Regulatory action → accounts frozen
- Hack → funds gone

Non-custodial = you maintain control

**Tweet 3:**
Sardis uses Turnkey's MPC infrastructure.

Key shares distributed across multiple parties.
No single entity can move funds—not even us.

True ownership for your agents.

**Tweet 4:**
Bonus: Non-custodial has regulatory advantages.

In many jurisdictions, we're not a money transmitter because we don't hold your funds.

Less friction. More control.

**Tweet 5:**
We checked the competition:

- Payman: Custodial (they hold your funds)
- Locus: Unclear custody model
- Skyfire: MPC (similar to us)

Know what you're signing up for.

Sardis = non-custodial by design.

sardis.sh

---

### Thread 3: Virtual Cards = Web-Wide Access

**Tweet 1:**
Here's a feature no other agent payment platform has:

Instant virtual card issuance.

Your agent can now pay anywhere Visa is accepted.

Not just crypto. Not just APIs. Anywhere. 🧵

**Tweet 2:**
The problem with crypto-only payments:

Most merchants don't accept USDC.

Your agent can't buy SaaS subscriptions.
Can't book hotels.
Can't order supplies.

Cards bridge the gap.

**Tweet 3:**
With Sardis + Lithic:

- Issue virtual cards on-demand
- Per-card spending limits
- Single-use or recurring
- Works everywhere Visa is accepted

No more "payment method not supported."

**Tweet 4:**
Use cases:

✅ Agent managing SaaS subscriptions
✅ Agent booking travel
✅ Agent purchasing office supplies
✅ Agent buying API credits

All with policy controls. All auditable.

**Tweet 5:**
Competitors checked:

- Locus: No virtual cards
- Payman: No virtual cards
- Skyfire: No virtual cards

Sardis = crypto + cards + policies

The complete agent payment stack.

sardis.sh

---

## LinkedIn Posts

### Post 1: Market Analysis

**The AI Agent Payment Infrastructure Landscape: A Technical Analysis**

I spent the past month analyzing every player in the agent payment space. Here's what I found:

**The Players:**
- Locus (YC F25): Control layer for B2B agentic payments
- Payman AI ($13.8M): Agent-to-human payments, ACH + USDC
- Skyfire ($9.5M): "Visa for the AI Economy," identity-focused

**The Gap:**
All three are building payment rails or identity layers.

None are building comprehensive policy enforcement with natural language interfaces.

This is the critical missing piece.

**Why It Matters:**
Financial hallucinations are the #1 risk in agentic commerce. Basic spending limits ($50/day) aren't sufficient.

Enterprises need:
- Vendor allowlists
- Category restrictions
- Approval workflows
- Time-based rules
- Context-aware governance

**Our Approach:**
Sardis is the policy firewall for agent payments.

- Natural language policy engine
- Non-custodial MPC wallets (Turnkey)
- Virtual cards (Lithic) — unique in the market
- Multi-chain from day one (Base, Polygon, ETH, Arbitrum, Optimism)

We're not competing on payment rails. We're building the intelligence layer that makes agent payments safe.

Read the full analysis: sardis.sh/docs/blog/why-sardis

#AgentEconomy #Fintech #AIAgents #Payments

---

### Post 2: Technical Deep Dive

**How We Enforce Natural Language Policies at Transaction Time**

"Max $100/transaction, only approved vendors, require approval over $50"

This is a natural language policy. Here's how Sardis enforces it:

**Step 1: Policy Parsing**
When you create a wallet with a policy, our LLM-powered parser converts natural language into structured rules:

```json
{
  "max_per_tx": 100.00,
  "vendor_allowlist": ["openai.com", "anthropic.com"],
  "approval_threshold": 50.00
}
```

**Step 2: Pre-Transaction Check**
Every transaction goes through the policy engine BEFORE the MPC signing ceremony begins.

No policy check = no signature = no transaction.

**Step 3: AP2 Mandate Chain**
Your policy becomes an AP2 Intent Mandate—cryptographically signed and verifiable by any party in the payment chain.

Human intent → Agent cart → Payment execution

Each step signed. Each step traceable.

**Step 4: Audit Trail**
Every policy check is logged:
- What was the transaction?
- What policy was applied?
- Was it approved or rejected?
- Why?

Full auditability for compliance.

**Why This Matters:**
Agents can't override policies. The cryptographic enforcement happens at the wallet level.

This is how you give agents financial autonomy without giving them unlimited access.

Learn more: sardis.sh/docs/policies

#TechnicalWriting #Fintech #AIAgents #Blockchain

---

## Reddit Posts

### r/artificial

**Title: Analyzed the AI agent payment space - here's what's missing**

Been building AI agents for 18 months and hit the same wall everyone hits: agents can't complete purchases.

Spent the last month analyzing every solution:

**Locus** (YC F25)
- Control layer for B2B payments
- Budget controls, justification requirements
- Base chain only
- Basic spending limits

**Payman AI** ($13.8M from Visa, Coinbase)
- Agent-to-human payments
- ACH + USDC
- Custodial wallets (they hold your keys)
- No MCP server

**Skyfire** ($9.5M from a16z, Coinbase)
- "Visa for AI Economy"
- Identity-focused (KYA protocol)
- Production-ready
- No natural language policies

**The gap I found:**

All of them offer basic spending limits ("$50/day"). None of them offer sophisticated policy enforcement.

This matters because financial hallucinations are real. An agent that confidently makes incorrect purchases needs more than a spending cap.

That's why I'm building Sardis:
- Natural language policies ("Max $100, only approved vendors, require approval over $50")
- Non-custodial MPC wallets
- Virtual cards (only one offering this)
- Multi-chain (5 chains vs competitors' 1-2)

Not trying to compete on payment rails—building the intelligence layer that makes agent payments safe.

Anyone else hitting this wall with their agents?

---

### r/ChatGPT / r/ClaudeAI

**Title: Finally: payment tools for Claude that actually work**

Been using Claude Desktop for months. Love it. But every time I ask it to buy something, it hits a wall.

"I can't make purchases on your behalf."

Fixed it with an MCP server.

**What it does:**
36+ tools for payments, wallets, virtual cards, holds, and commerce.

**How to set it up:**
Add this to your Claude config:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": { "SARDIS_API_KEY": "sk_..." }
    }
  }
}
```

Restart Claude. Done.

**What Claude can now do:**
- Check wallet balance
- Make payments (within policy limits)
- Issue virtual cards
- Create checkout sessions
- Request human approval for large purchases

**The key:** Policies.

You set spending rules in plain English:
"Max $50 per transaction, only pay openai.com and github.com, require approval for anything over $25"

Claude follows the rules. Can't override them.

Full docs: sardis.sh/docs/mcp-server

Anyone else using MCP servers for payments? Would love to hear what you're building.

---

## Comparison Table (For Blog/Docs)

| Feature | Sardis | Locus | Payman | Skyfire |
|---------|--------|-------|--------|---------|
| **Natural Language Policies** | ✅ Core feature | ❌ Basic limits | ❌ Basic limits | ❌ Spending caps |
| **Non-Custodial MPC** | ✅ Turnkey | ❓ Unknown | ❌ Custodial | ✅ Yes |
| **Virtual Cards** | ✅ Lithic | ❌ No | ❌ No | ❌ No |
| **MCP Server** | ✅ Zero-config, 36+ tools | ⚠️ Demo only | ❌ No | ✅ Yes |
| **Multi-Chain** | ✅ 5 chains | ❌ Base only | ⚠️ ACH + USDC | ⚠️ 2 chains |
| **Protocols** | AP2, UCP, A2A, TAP, x402 | ACP (OpenAI) | Proprietary | KYA, KYAPay |
| **Stage** | Beta | Closed Beta | Invite-only | Production |

---

## Positioning Statement

> For developers building AI agents that need to transact,
> Sardis is the payment OS that prevents financial hallucinations
> through natural language policies and non-custodial MPC wallets.
>
> Unlike Skyfire (identity-focused) or Payman (custodial, ACH-focused),
> Sardis combines policy intelligence, multi-chain crypto, and instant virtual cards
> in a zero-config MCP server that works in 5 lines of code.

---

## Key Messaging

**Tagline Options:**
1. "The Policy Firewall for Agent Payments"
2. "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust."
3. "Prevent Financial Hallucinations"

**Value Props (in order):**
1. Natural language spending policies
2. Non-custodial MPC wallets
3. Virtual cards (unique)
4. Zero-config MCP server
5. Multi-chain support

**Differentiators:**
- Only solution with NL policies + virtual cards + multi-chain
- Protocol agnostic (works with AP2, UCP, A2A, TAP, x402)
- Developer-first experience (5 lines of code)

---

*Last updated: January 2026*
