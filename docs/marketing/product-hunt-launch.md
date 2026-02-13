# Product Hunt Launch Playbook

## Tagline Options

1. **"The Payment OS for the Agent Economy"** (primary — matches brand)
2. **"Stop AI agents from hallucinating your money away"** (provocative, click-driving)
3. **"Stripe + IAM for AI agents — non-custodial wallets with NL policies"** (technical)

**Recommended:** Option 2 as PH tagline (max 60 chars), Option 1 as subtitle.

---

## First Comment (Founder Story)

> Hey PH! I'm Efe, founder of Sardis.
>
> **The problem:** AI agents can now reason, browse, and code — but when they handle money, things go wrong fast. Retry loops that spend $10k instead of $100. Decimal errors. Agents confidently purchasing from the wrong merchant. We call this **financial hallucination**.
>
> **What we built:** Sardis gives AI agents non-custodial MPC wallets with natural language spending policies. Instead of writing code for spending rules, you just say: *"Max $100/day, only SaaS vendors, block weekends."*
>
> Every transaction goes through our policy firewall before the MPC signing ceremony begins. If it violates the policy, it's blocked — no money moves.
>
> **What makes us different:**
> - Natural language policy engine (not just spending caps)
> - Non-custodial MPC wallets (Turnkey) — we never hold your keys
> - Virtual cards via Lithic — agents can pay anywhere Visa is accepted
> - 5 chains (Base, Polygon, Ethereum, Arbitrum, Optimism)
> - MCP native — one command to add payments to Claude/Cursor
> - Group governance — shared budgets across agent teams
>
> We're open-core: SDKs and MCP server are MIT licensed, 19 packages live on npm + PyPI, 46 MCP tools.
>
> Would love your feedback! Ask me anything about agent payments, MPC wallets, or the agent economy.

---

## Feature Highlight Bullets

- Non-custodial MPC wallets (Turnkey) — your keys, always
- Natural language spending policies: "Max $100/day for SaaS only"
- Financial hallucination firewall — blocks bad transactions before they execute
- Virtual cards (Lithic) — agents pay anywhere Visa is accepted
- 5 blockchain networks: Base, Polygon, Ethereum, Arbitrum, Optimism
- MCP native: `npx @sardis/mcp-server start` — zero-config for Claude/Cursor
- Group governance: shared budgets across multi-agent teams
- 5 protocols: AP2, TAP, UCP, A2A, x402
- KYC/AML compliance built-in (Persona, Elliptic)
- Open-core: 19 packages on npm + PyPI

---

## Media Assets Checklist

- [ ] Logo — 240x240px PNG (transparent background)
- [ ] Gallery image 1 — Hero shot with tagline (1270x760px)
- [ ] Gallery image 2 — Architecture diagram
- [ ] Gallery image 3 — Policy firewall in action (code screenshot)
- [ ] Gallery image 4 — MCP server setup (terminal screenshot)
- [ ] Gallery image 5 — Group governance dashboard
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
> Non-custodial is our foundation. We never store private keys — Turnkey's MPC infrastructure splits keys across multiple parties. No single entity (not even Sardis) can move funds unilaterally. Add KYC/AML (Persona + Elliptic), HMAC webhook signatures, rate limiting, and an append-only audit ledger.

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

**Tuesday or Wednesday** — highest PH traffic days.

**Why launch now:**
- 19 packages live on npm + PyPI
- 46 MCP tools working
- 5 chains, 5 protocols
- Full SDK coverage (Python + TypeScript)
- Group governance (differentiator)
- Virtual cards + fiat rails
- Landing page + docs complete
- 404 commits of substance

Waiting longer gives diminishing returns. Launch, get feedback, iterate.
