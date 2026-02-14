# Product Hunt Launch Playbook

## Positioning

**Stage:** Developer Preview (Testnet)
**Goal:** Find design partners — teams building AI agents that need payment capabilities
**What's live:** SDKs, MCP server, testnet wallets, policy engine, group governance
**What's coming:** Mainnet deployment, Lithic virtual cards (production), KYC/AML (Persona + Elliptic), fiat on/off ramp (Bridge.xyz)

---

## Tagline Options

1. **"The Payment OS for the Agent Economy"** (primary — matches brand)
2. **"Stop AI agents from hallucinating your money away"** (provocative, click-driving)
3. **"Stripe + IAM for AI agents — non-custodial wallets with NL policies"** (technical)

**Recommended:** Option 2 as PH tagline (max 60 chars), Option 1 as subtitle.

---

## First Comment (Founder Story)

> Hey PH! I'm Efe, founder of Sardis.
>
> **The problem:** AI agents can now reason, browse, and code — but money handling has failure modes: retry loops that overspend, decimal normalization mistakes, and merchant/domain mismatches. We call this **financial hallucination**.
>
> **What we built:** Sardis gives AI agents non-custodial MPC wallets with natural language spending policies. Instead of writing code for spending rules, you just say: *"Max $100/day, only SaaS vendors, block weekends."*
>
> Every transaction goes through our policy firewall before the MPC signing ceremony begins. If it violates the policy, it's blocked — no money moves.
>
> **Where we are:** We're live on **testnet** (Base Sepolia) with full SDK coverage across Python and TypeScript. 19 packages published on npm + PyPI, 52 MCP tools working. We're looking for **design partners** — teams building AI agents that need payment capabilities. If that's you, let's build together.
>
> **What makes us different:**
> - Natural language policy engine (not just spending caps)
> - Non-custodial MPC wallets (Turnkey) — we never hold your keys
> - MCP native — one command to add payments to Claude/Cursor
> - Group governance — shared budgets across agent teams
> - 5 chains planned (Base, Polygon, Ethereum, Arbitrum, Optimism)
>
> We're open-core: SDKs and MCP server are MIT licensed.
>
> **What's next:** Mainnet deployment, virtual cards (Lithic), and KYC/AML integration are in progress.
>
> Would love your feedback! If you're building agents that need to handle money — I'd love to talk. Ask me anything.

---

## Feature Highlight Bullets

- Non-custodial MPC wallets (Turnkey) — your keys, always
- Natural language spending policies: "Max $100/day for SaaS only"
- Financial hallucination firewall — blocks bad transactions before they execute
- MCP native: `npx @sardis/mcp-server start` — zero-config for Claude/Cursor
- Group governance: shared budgets across multi-agent teams
- 5 blockchain networks planned: Base, Polygon, Ethereum, Arbitrum, Optimism
- 5 protocols: AP2, TAP, UCP, A2A, x402
- Open-core: 19 packages on npm + PyPI, MIT licensed SDKs
- **Currently on testnet** — looking for design partners for mainnet launch

---

## Media Assets Checklist

- [ ] Logo — 240x240px PNG (transparent background)
- [ ] Gallery image 1 — Hero shot with tagline (1270x760px)
- [ ] Gallery image 2 — Architecture diagram (Agent → Policy Engine → MPC Wallet → Chain)
- [ ] Gallery image 3 — Policy firewall in action (code screenshot)
- [ ] Gallery image 4 — MCP server setup (terminal screenshot)
- [ ] Gallery image 5 — Group governance diagram
- [ ] Demo GIF — Terminal showing payment flow (simple_payment.py output)
- [ ] OG image — 1200x630px for social sharing
- [ ] Maker photo — Professional headshot

---

## Maker's Comment Templates

### When asked "How is this different from Stripe?"
> Great question! Stripe is for human-initiated payments through web forms. Sardis is for AI agent-initiated payments via API/MCP. The key difference: agents need a policy firewall (natural language spending rules) because they can hallucinate financial decisions. Stripe doesn't have this because humans make the decisions. We're the IAM + risk engine layer that sits between the agent and the payment rails.

### When asked "Why not just use a regular wallet?"
> Regular wallets have no policy enforcement. An agent with a regular wallet private key could drain the entire balance in one bad decision. Sardis uses MPC wallets where the signing ceremony only proceeds if the transaction passes the policy check. The policy is enforced cryptographically, not just in application code.

### When asked "What about security?"
> Non-custodial is our foundation. We never store private keys — Turnkey's MPC infrastructure splits keys across multiple parties. No single entity (not even Sardis) can move funds unilaterally. The policy engine adds another layer — even if an agent is compromised, it can only operate within the spending rules you set.

### When asked "Is this production-ready? / Can I use real money?"
> We're currently live on **testnet** (Base Sepolia) — you can try everything with test tokens, no real money involved. Mainnet deployment is coming soon. We're looking for **design partners** right now — teams that want to shape the product alongside us. If you're building AI agents that will need payment capabilities, we'd love to work with you before mainnet goes live. Reach out at sardis.sh.

### When asked "What's the business model?"
> Open-core: SDKs and MCP server are MIT licensed and free forever. The hosted platform will have transaction-based pricing (like Stripe) plus premium features like compliance, analytics, and multi-org management. We're finalizing pricing with our design partners.

---

## Launch Day Timeline

### Day Before (Monday)
- [ ] Submit PH listing (scheduled for 12:01 AM PT Tuesday)
- [ ] Prepare all social media posts (see social-launch-kit.md)
- [ ] Brief supporters — ask them to upvote + comment at launch
- [x] Test all links: website, docs, GitHub, npm, PyPI

### Link + Badge Validation Snapshot (2026-02-13)

- Scope: README + launch/marketing URLs and badge targets
- Result: 24 URLs validated with `200 OK`
- npm package pages (`/package/@sardis/*`) return `403` to `curl` due bot/WAF behavior, but npm badges resolve (`200`) and pages load in browser
- Broken links detected: `0`

Verified categories:
- Shields.io badges
- sardis.sh + docs
- GitHub repo + Actions
- Discord invite
- Context7
- PyPI
- modelcontextprotocol.io
- Placeholder logo SVG URLs in README comment block

### Launch Day (Tuesday)
| Time (PT) | Action |
|-----------|--------|
| 12:01 AM | PH goes live — post first comment immediately |
| 6:00 AM | Tweet launch announcement + thread |
| 7:00 AM | Post to Reddit (r/artificial, r/programming) |
| 8:00 AM | Post to Hacker News |
| 9:00 AM | LinkedIn post |
| 10:00 AM | Reply to all PH comments |
| 12:00 PM | Discord announcement |
| 2:00 PM | Second round of PH comment replies |
| 4:00 PM | Share milestone updates on X |
| 6:00 PM | Thank supporters, share final ranking |

### Day After (Wednesday)
- [ ] Follow up with everyone who commented/upvoted
- [ ] Write "What we learned" thread on X
- [ ] Update README with PH badge
- [ ] Send thank-you to supporters

---

## Recommended Launch Day

**Tuesday, February 18** — highest PH traffic day.

**Why launch now:**
- 19 packages live on npm + PyPI
- 52 MCP tools working
- Full SDK coverage (Python + TypeScript)
- Policy engine + group governance working on testnet
- Landing page + docs complete
- Release-readiness checks are green

**What we're transparent about:**
- Testnet only (Base Sepolia) — mainnet coming soon
- Lithic virtual cards in sandbox — production onboarding in progress
- KYC/AML (Persona + Elliptic) integrated in dev — production credentials pending
- Fiat on/off ramp (Bridge.xyz) architecture complete — partnership finalizing

**This is normal for PH.** Linear, Supabase, and Resend all launched in beta/alpha. PH is for finding early users and design partners, not for announcing production-ready products.
