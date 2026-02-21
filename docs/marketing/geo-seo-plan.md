# Sardis GEO & SEO Action Plan

> Goal: When someone asks an AI model or searches Google "How can I make payments with my AI agent?", Sardis should appear in the results.

**Created:** 2026-02-17
**Owner:** Efe Baran Durmaz
**Status:** Active

---

## Current Situation

### What We Have (Done Today)
- [x] `llms.txt` + `llms-full.txt` with Q&A format (14 questions)
- [x] `robots.txt` with LLM bot allowlist (GPTBot, Claude-Web, PerplexityBot, etc.)
- [x] `.well-known/agent.json` + `.well-known/ai-plugin.json`
- [x] JSON-LD structured data: Organization, WebSite, SoftwareApplication, FAQPage (8 Q&A)
- [x] Per-page SEO meta tags on 15 key pages (react-helmet-async)
- [x] BreadcrumbList, TechArticle, HowTo schemas on doc/blog pages
- [x] Expanded FAQ page with 42 Q&A pairs across 9 categories
- [x] Comparison page (`/docs/comparison`) with structured tables
- [x] Pre-rendering script (Puppeteer) ready for local builds
- [x] GEO-optimized README with FAQ format
- [x] Sitemap with 339 URLs

### What's Blocking Us
1. **SPA rendering** — AI crawlers and Googlebot get empty HTML from client-side React
2. **Low Domain Authority** — sardis.sh is new, few backlinks
3. **No off-site presence** — Sardis not mentioned on Reddit, dev blogs, Stack Overflow
4. **Competing with giants** — Mastercard, Visa, Coinbase, Stripe, Google dominate "AI agent payments"

### Where We Can Win
- Long-tail developer keywords (low competition)
- "financial hallucination prevention" (we coined this)
- Developer tutorials and SDK-specific content
- Natural language spending policies (unique positioning)
- MCP integration content (Claude-specific)

---

## Phase 1: Technical Foundation (Week 1-2)

### 1.1 Migrate Landing Page to Astro (SSG)
**Priority:** CRITICAL
**Impact:** 10x SEO improvement — all pages become static HTML
**Effort:** 3-5 days

**Why:** The single biggest technical blocker. Google and AI crawlers get empty `<div id="root"></div>` from our React SPA. Astro outputs zero-JS static HTML by default while supporting React components.

**Steps:**
1. Initialize Astro project in `landing-v2/`
2. Configure Astro with React integration (`@astrojs/react`)
3. Migrate page components from JSX to Astro pages (`.astro` files)
4. Keep interactive components (Playground, Demo) as React islands
5. Move docs to Astro content collections (automatic sitemap, RSS)
6. Add `@astrojs/sitemap` for auto-generated sitemap
7. Add per-page `<head>` with SEO meta tags (native in Astro)
8. Deploy to Vercel with `@astrojs/vercel` adapter
9. Verify with Google Search Console that all pages are indexed
10. Remove old landing/ once verified

**Acceptance Criteria:**
- `curl https://sardis.sh/docs/faq` returns full HTML with FAQ content (not empty div)
- Google Search Console shows all doc/blog pages as "Indexed"
- Lighthouse SEO score > 95 on all pages
- Build time < 30 seconds

### 1.2 Google Search Console Setup
**Priority:** HIGH
**Effort:** 30 minutes

**Steps:**
1. Verify sardis.sh ownership in Google Search Console (already done: `googlefc0184a9112a5361.html`)
2. Submit sitemap: `https://sardis.sh/sitemap.xml`
3. Request indexing for key pages:
   - `/docs/comparison` (new)
   - `/docs/faq` (updated)
   - `/docs/quickstart`
   - `/docs/wallets`
   - `/docs/payments`
   - `/docs/policies`
   - `/docs/mcp-server`
4. Monitor "Coverage" report weekly for crawl errors
5. Check "Performance" report for query impressions

### 1.3 Bing Webmaster Tools Setup
**Priority:** MEDIUM (ChatGPT uses Bing for Browse mode)
**Effort:** 30 minutes

**Steps:**
1. Create account at bing.com/webmasters
2. Verify sardis.sh
3. Submit sitemap
4. Request indexing for key pages
5. This directly impacts ChatGPT Browse results

---

## Phase 2: Content Marketing (Week 2-4)

### 2.1 Dev.to / Medium / Hashnode Articles
**Priority:** HIGH
**Impact:** Backlinks + off-site authority + AI training data
**Effort:** 2-3 hours per article

Write and publish these 5 articles (in order of priority):

#### Article 1: "How to Give Your AI Agent a Wallet in 5 Minutes with Sardis"
- **Platform:** Dev.to + Medium
- **Target keywords:** AI agent wallet, AI agent payments, MCP payment tools
- **Content:** Step-by-step tutorial. Install SDK → create wallet → set policy → make payment
- **Include:** Code snippets (Python + TypeScript), screenshots, MCP config
- **CTA:** Link to sardis.sh/docs/quickstart
- **Tags:** #ai, #fintech, #python, #typescript

#### Article 2: "Preventing Financial Hallucinations in Autonomous AI Agents"
- **Platform:** Dev.to + Medium + Hashnode
- **Target keywords:** financial hallucination, AI agent overspending, AI safety
- **Content:** Define the problem, show real examples, explain how policy firewall works
- **Include:** Before/after comparison, code examples of policy definitions
- **CTA:** Link to sardis.sh/docs/policies

#### Article 3: "Claude MCP + Sardis: 50 Payment Tools for Your AI Agent"
- **Platform:** Dev.to
- **Target keywords:** Claude MCP server, MCP payment tools, Claude Desktop payments
- **Content:** How to set up MCP server, walkthrough of key tools, demo conversation
- **Include:** claude_desktop_config.json, example conversations
- **CTA:** Link to sardis.sh/docs/mcp-server

#### Article 4: "Natural Language Spending Policies: How AI Agents Earn Financial Trust"
- **Platform:** Medium + Hashnode
- **Target keywords:** AI agent spending policy, natural language policy, AI trust
- **Content:** Deep dive into policy engine, NL parsing, enforcement examples
- **Include:** Policy examples, architecture diagram
- **CTA:** Link to sardis.sh/docs/policies

#### Article 5: "Building Agent-to-Agent Payments with A2A Protocol and Sardis"
- **Platform:** Dev.to + Medium
- **Target keywords:** agent to agent payments, A2A protocol, multi-agent payments
- **Content:** How agents discover, negotiate, and pay each other
- **Include:** Code examples, protocol flow diagrams
- **CTA:** Link to sardis.sh/docs/a2a

### 2.2 Reddit Strategy
**Priority:** HIGH
**Impact:** AI models heavily weight Reddit content
**Effort:** Ongoing, 15-30 min/day

**Target Subreddits:**
- r/artificial (1.2M members)
- r/LangChain (50K)
- r/LocalLLaMA (500K)
- r/ChatGPT (5M)
- r/MachineLearning (3M)
- r/cryptocurrency (7M)
- r/defi (300K)
- r/SaaS (100K)

**Strategy:**
1. **Don't spam.** Be genuinely helpful first
2. Monitor these subreddits for questions about AI agent payments
3. When relevant, share Sardis as one solution among others
4. Create 2-3 original posts per month:
   - "I built a payment system for AI agents with spending policies — here's what I learned"
   - "How we prevent AI agents from overspending using natural language policies"
   - "Giving Claude a wallet via MCP — full walkthrough"
5. Comment on threads about:
   - AI agent autonomy
   - LangChain/CrewAI agent building
   - Crypto payments infrastructure
   - MCP server development
6. Always provide value first, mention Sardis naturally

**Rules:**
- Never post just a link. Write substantial content
- Don't mention Sardis in every comment
- Be transparent: "I'm building Sardis" (not astroturfing)
- Engage with replies and feedback

### 2.3 Hacker News Strategy
**Priority:** HIGH
**Impact:** Tech community credibility + major backlinks
**Effort:** 2-3 Show HN posts

**Posts:**
1. **Show HN: Sardis — Non-custodial MPC wallets with NL spending policies for AI agents**
   - Timing: After Astro migration (so the site loads fast and is crawlable)
   - Include: Quick demo, code examples, honest positioning
2. **Blog post submission:** "Preventing Financial Hallucinations in AI Agents"
   - Submit the dev.to article as a link
3. **Comment** on relevant AI/fintech/crypto threads

### 2.4 GitHub README & Presence
**Priority:** MEDIUM
**Effort:** 1 hour

**Steps:**
1. [x] README optimized with FAQ format (done)
2. Add topics/tags to GitHub repo: `ai-agent-payments`, `mpc-wallet`, `spending-policy`, `claude-mcp`, `financial-hallucination`, `stablecoin`, `virtual-cards`, `agent-economy`
3. Add "About" description: "Payment OS for the Agent Economy — Non-custodial MPC wallets with natural language spending policies for AI agents"
4. Pin key discussions in GitHub Discussions
5. Create GitHub Discussions categories: Q&A, Show & Tell, Feature Requests
6. Add CONTRIBUTING.md to attract contributors

---

## Phase 3: Topical Authority (Week 4-8)

### 3.1 Blog Content Calendar (10 posts)
**Priority:** HIGH
**Impact:** Builds topical authority for "AI agent payments" cluster

Create these blog posts on sardis.sh/docs/blog/:

| # | Title | Target Keyword | Type |
|---|-------|---------------|------|
| 1 | "What is an AI Agent Wallet? Complete Guide" | AI agent wallet | Pillar |
| 2 | "AP2 Protocol Explained: How Google, Visa, and Mastercard Enable Agent Payments" | AP2 protocol, agent payment protocol | Deep dive |
| 3 | "Sardis vs Payman vs Skyfire: AI Agent Payment Platforms Compared" | AI agent payment comparison | Comparison |
| 4 | "How to Use Claude MCP for Autonomous Payments" | Claude MCP payments | Tutorial |
| 5 | "The Complete Guide to AI Agent Spending Policies" | AI agent spending policy | Pillar |
| 6 | "x402 Protocol: HTTP-Native Micropayments for AI Agents" | x402 protocol, micropayments | Deep dive |
| 7 | "Multi-Agent Treasury Management: How Agents Share Budgets" | multi-agent treasury, group governance | Feature |
| 8 | "Virtual Cards for AI Agents: Bridging Crypto and Fiat Commerce" | AI agent virtual card | Feature |
| 9 | "ERC-4337 Gasless Wallets for AI Agents" | gasless wallet, ERC-4337 AI agent | Technical |
| 10 | "Building an Autonomous Procurement Agent with Sardis and LangChain" | autonomous procurement agent, LangChain payments | Tutorial |

**Content Rules:**
- Each post minimum 1500 words
- Start with a direct answer to the title question (first paragraph)
- Include code examples (Python + TypeScript)
- Include comparison tables where relevant
- Add FAQ section at bottom of each post (3-5 questions)
- Add TechArticle schema (already automated via SEO component)
- Internal link to at least 3 other Sardis docs/blog pages
- End with CTA to quickstart or playground

### 3.2 Pillar + Cluster Content Strategy
**Priority:** HIGH

**Pillar Page:** `/docs/overview` → "The Complete Guide to AI Agent Payments"
- Comprehensive 3000+ word guide covering all aspects
- Links to every cluster page

**Cluster Pages:** (existing + new)
- Wallets → `/docs/wallets`
- Payments → `/docs/payments`
- Policies → `/docs/policies`
- Virtual Cards → (blog post)
- Protocols → `/docs/protocols`
- Security → `/docs/security`
- MCP Integration → `/docs/mcp-server`
- Comparison → `/docs/comparison`
- FAQ → `/docs/faq`

**Internal Linking Rules:**
- Every cluster page links back to pillar
- Pillar links to every cluster
- Cluster pages cross-link where relevant
- Use keyword-rich anchor text

---

## Phase 4: Authority & Backlinks (Week 6-12)

### 4.1 Product Hunt Launch
**Priority:** HIGH
**Impact:** Major backlink + visibility + AI training data
**Effort:** 1 day prep, 1 day launch

**Prep:**
1. Create Product Hunt profile with full description
2. Prepare launch assets: tagline, description, screenshots, video demo
3. Line up 10+ people to upvote and comment on launch day
4. Write maker comment explaining the vision

**Tagline options:**
- "Give your AI agent a wallet with spending policies"
- "The Payment OS for the Agent Economy"
- "Prevent AI agents from overspending with natural language policies"

**Timing:** After Astro migration and at least 3 dev.to articles published

### 4.2 AI/Fintech Newsletter Outreach
**Priority:** MEDIUM
**Effort:** 2-3 hours

Submit Sardis to these newsletters:
- **The Neuron** (AI newsletter)
- **TLDR AI** (daily AI newsletter)
- **Ben's Bites** (AI newsletter)
- **Fintech Today** (fintech newsletter)
- **The Block** (crypto)
- **Bankless** (crypto/DeFi)
- **a]i weekly** (AI newsletter)

Pitch angle: "Sardis solves the AI agent money problem — how to let agents spend without giving them unlimited access"

### 4.3 Podcast/Interview Appearances
**Priority:** LOW-MEDIUM
**Effort:** Ongoing

Reach out to:
- AI podcasts (Practical AI, AI Engineering, Latent Space)
- Fintech podcasts (Fintech Insider, Plaid's podcast)
- Crypto podcasts (Bankless, The Defiant)

Topic: "Why AI agents need financial guardrails"

### 4.4 Open Source Community Engagement
**Priority:** MEDIUM
**Effort:** Ongoing

1. Contribute to LangChain docs (add Sardis as a payment tool)
2. Create LangChain integration example in their cookbook
3. Submit MCP server to Anthropic's MCP directory (if exists)
4. Add Sardis to "Awesome AI Agents" lists on GitHub
5. Contribute to discussions in AI agent Discord communities

---

## Phase 5: Measurement & Iteration (Ongoing)

### 5.1 Monthly GEO Tracking
**Schedule:** 1st of every month

Ask these exact questions to ChatGPT, Claude, Perplexity, Gemini, and Google AI Overview:

| # | Question | Notes |
|---|----------|-------|
| 1 | "How can I make payments with my AI agent?" | Primary target query |
| 2 | "What is the safest way to give an AI agent access to money?" | Safety angle |
| 3 | "AI agent wallet solutions" | Product discovery |
| 4 | "How to prevent AI agent from overspending?" | Problem-focused |
| 5 | "AI agent payment infrastructure" | Infrastructure angle |
| 6 | "MPC wallet for AI agents" | Technical angle |
| 7 | "Claude MCP payment tools" | Platform-specific |
| 8 | "natural language spending policy AI" | Unique differentiator |
| 9 | "financial hallucination prevention" | Branded term |
| 10 | "Sardis AI payment" | Branded search |

**Track per platform:**
- Does Sardis appear? (Yes/No)
- Position (1st mention, 2nd, etc.)
- Is the description accurate?
- Is sardis.sh linked as source?
- Screenshot for records

**Store results in:** `docs/marketing/geo-tracking.md`

### 5.2 SEO Metrics (Google Search Console)
**Track weekly:**
- Total impressions
- Total clicks
- Average position
- Top queries driving traffic
- Pages indexed vs submitted
- Crawl errors
- Core Web Vitals

### 5.3 Competitor Monitoring
**Track monthly:**
- Search "AI agent payments" — who ranks where?
- Check competitor blogs for new content
- Monitor Payman, Skyfire, Nevermined, Coinbase for new features
- Track their GEO presence (do they appear in AI responses?)

---

## Timeline Summary

| Week | Focus | Key Deliverables |
|------|-------|-----------------|
| 1 | Technical | Google Search Console, Bing Webmaster, GitHub topics |
| 1-2 | Technical | Start Astro migration |
| 2 | Content | Article 1 + 2 on Dev.to/Medium |
| 2-3 | Technical | Complete Astro migration, deploy |
| 3 | Content | Article 3 + 4, start Reddit engagement |
| 4 | Content | Article 5, first GEO measurement |
| 4-6 | Content | Blog posts 1-5 on sardis.sh |
| 6-8 | Content | Blog posts 6-10, Product Hunt prep |
| 8 | Launch | Product Hunt launch |
| 8-10 | Authority | Newsletter outreach, podcast pitches |
| 10-12 | Authority | LangChain integration, community engagement |
| 12+ | Iterate | Monthly GEO tracking, content refresh |

---

## Success Metrics (3-month targets)

| Metric | Current | Target |
|--------|---------|--------|
| Google indexed pages | ~5 (SPA problem) | 50+ |
| Perplexity mentions Sardis | No | Yes (3+ queries) |
| ChatGPT Browse mentions Sardis | No | Yes (2+ queries) |
| Dev.to articles published | 0 | 5 |
| Reddit posts/comments | 0 | 20+ |
| Monthly organic search traffic | ~0 | 500+ visits |
| Domain Authority (Moz) | ~1 | 10+ |
| Backlinks | ~5 | 30+ |
| "financial hallucination prevention" rank | Not indexed | Top 3 |

---

## Budget

| Item | Cost | Notes |
|------|------|-------|
| Domain & Hosting | $0 | Vercel free tier |
| Dev.to / Medium | $0 | Free to publish |
| Product Hunt | $0 | Free to launch |
| Google Search Console | $0 | Free |
| GEO tracking tools (optional) | $50-200/mo | LLMrefs, Profound, or manual |
| Newsletter sponsorship (optional) | $200-500/post | For paid newsletter placement |
| **Total (minimum)** | **$0** | Everything can be done for free |

---

*This plan is designed to be executed by a solo founder. Prioritize Phase 1 (technical) and Phase 2 (content) first — they have the highest ROI. Phase 3 and 4 compound over time.*
