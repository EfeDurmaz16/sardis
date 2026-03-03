# Outreach Automation & Growth Plan
# Sardis - Solo Founder Playbook

## Table of Contents

1. Platform Strategy (X, LinkedIn, Threads)
2. Tool Stack & Pricing
3. Email Outreach Setup
4. LinkedIn Outreach Playbook
5. X Growth Playbook
6. Threads Strategy
7. First Customer Acquisition
8. Investor Outreach
9. Hacker News Launch Plan
10. Weekly Operations Calendar
11. Metrics & Tracking

---

## 1. Platform Strategy

### Which platform for what

| Platform | Primary Purpose | Audience | Content Style |
|----------|----------------|----------|---------------|
| X | Developer community, crypto investors, build in public | Engineers, indie hackers, angels | Short, punchy, contrarian, technical |
| LinkedIn | Institutional investors, enterprise customers, B2B credibility | VCs, CTOs, founders, partners | Professional, longer form, problem-framing |
| Threads | Secondary reach, casual audience expansion | Mixed, early adopter tech audience | Shorter than X, casual, crosspost-friendly |
| Hacker News | Launch moments, developer validation | Senior engineers, technical founders | Pure technical, no marketing language |
| Reddit | Community trust building | Subreddit-specific developers | Helpful answers, never promotional |

### Content adaptation rules

Never copy-paste between platforms. Adapt:

**X version:**
"Hot take: AI agent payment policies fail not because of bad code but because the threat model is wrong."

**LinkedIn version:**
"We spent 6 months building payment infrastructure for AI agents. Here is what we learned about why spending policies fail in production: [1500-word breakdown with structured points and specific numbers]"

**Threads version:**
"AI agent payment policies fail because everyone secures against what agents will do. They should secure against what agents will be instructed to do."

Rule: LinkedIn gets the essay. X gets the argument starter. Threads gets the one-liner.

---

## 2. Tool Stack & Pricing

### Tier 1: $37/month (start here)

| Tool | Purpose | Cost | Setup Time |
|------|---------|------|------------|
| Apollo.io Free | Find investor/customer emails, 10K credits/month | $0 | 30 min |
| Woodpecker Starter | Cold email sequences + warmup | $29/month | 2 hours |
| Typefully Starter | Schedule X posts and threads | $8/month | 15 min |
| Buffer Free | Crosspost to Threads + schedule LinkedIn | $0 | 15 min |
| LinkedIn (manual) | 10-15 personalized connections/day | $0 | Daily effort |

**Total: $37/month**

### Tier 2: $133/month (scale up after 30 days)

| Tool | Purpose | Cost |
|------|---------|------|
| Apollo.io Free | Contact database | $0 |
| Instantly.ai Growth | High-volume cold email + unlimited warmup | $37/month |
| Typefully Creator | X scheduling + AI writing assist | $19/month |
| Buffer Essentials | Threads + LinkedIn (3 channels) | $18/month |
| Dripify Basic | LinkedIn automation (conservative, <15 req/day) | $59/month |

**Total: $133/month**

### Tier 3: $182/month (full capacity)

| Tool | Purpose | Cost |
|------|---------|------|
| Apollo.io Basic | More export credits, better data enrichment | $49/month |
| Instantly.ai Growth | Email outreach engine | $37/month |
| Typefully Creator | X content scheduling | $19/month |
| Buffer Essentials | Cross-platform scheduling | $18/month |
| Dripify Basic | LinkedIn automation | $59/month |

**Total: $182/month**

### Tool comparison: email outreach

| Tool | Price | Email Accounts | Warmup | Lead DB | Best For |
|------|-------|---------------|--------|---------|----------|
| Apollo.io Free | $0 | N/A | No | 210M contacts | Finding emails |
| Woodpecker | $29/mo | Unlimited | Yes | 1B+ | Cheapest full tool |
| Instantly.ai | $37/mo | Unlimited | Yes (4.2M network) | Add-on | Volume + deliverability |
| Smartlead | $39/mo | Unlimited | Yes | No built-in | Best deliverability |
| Lemlist Email | $69/mo | Unlimited | Yes | 450M | Personalization |
| Lemlist Multi | $99/mo | Unlimited | Yes | 450M | Email + LinkedIn combo |

### Tool comparison: LinkedIn automation

| Tool | Price | Type | Ban Risk | Notes |
|------|-------|------|----------|-------|
| Manual outreach | $0 | Manual | 0% | Safest, highest quality |
| LinkedHelper | $15/mo | Desktop app | High | Cheapest, requires browser open |
| Dripify | $59/mo | Cloud | Medium | Good customization |
| Waalaxy | $60/mo | Chrome ext | Medium-High | Easy to use, bugs reported |
| Phantombuster | $69/mo | Cloud | Medium | Steep learning curve |
| Expandi | $99/mo | Cloud, dedicated IP | Low-Medium | Safest automation option |

**LinkedIn safety limits (daily):**
- Connection requests: 10-20 max
- Messages: 50-100
- Profile views: 80-100

**Ban risk reality:**
- Browser extension tools: 23% restriction rate within 90 days
- Cloud tools with proper limits: 5-10% restriction rate
- Manual outreach: 0%

### X scheduling tools

| Tool | Price | Platforms | Best For |
|------|-------|-----------|----------|
| Typefully Starter | $8/mo | X, LinkedIn, Bluesky | Thread writing + scheduling |
| Typefully Creator | $19/mo | Same + AI assist | AI-assisted content creation |
| Buffer Free | $0 | X, LinkedIn, Threads, IG | Crossposting (10 scheduled/channel) |
| Buffer Essentials | $6/mo/channel | Same | More scheduling capacity |
| Hypefury | $19/mo | X | Auto-retweet, engagement pods |
| Tweet Hunter | $49-99/mo | X | Viral tweet database, AI writing |

**Winner:** Typefully ($8) for X writing/scheduling + Buffer (free) for Threads crossposting.

---

## 3. Email Outreach Setup

### Week 1-2: Infrastructure (do this before sending a single email)

**Step 1: Buy 2-3 outreach domains**
Do NOT use sardis.sh for cold email. If your outreach domain gets flagged, it does not affect your main domain.

Options:
- sardis-team.com
- trysardis.com
- sardishq.com

Cost: ~$10-15/year each on Namecheap or Cloudflare.

**Step 2: Set up email accounts**
Create 2-3 email accounts per domain:
- efe@sardis-team.com
- hello@sardis-team.com

Use Google Workspace ($6/user/month) or Zoho Mail (free for 5 users).

**Step 3: Configure DNS records**
For each domain, set up:
- SPF record
- DKIM record
- DMARC record

Most email providers have step-by-step guides. This takes 30 min per domain.

**Step 4: Connect to Woodpecker/Instantly and start warmup**
Let warmup run for 14 days minimum before sending any outreach.

Warmup sends fake emails between accounts in the warmup network to build sender reputation. Instantly has a 4.2M account warmup network.

**Step 5: Build contact lists in Apollo**

List 1 - Potential customers:
- Title: CTO, VP Engineering, Head of AI, Technical Founder
- Industry: AI/ML, SaaS, Fintech, Developer Tools
- Company size: 10-200 employees
- Keywords: "AI agent", "LLM", "autonomous agent"

List 2 - Investors:
- Use OpenVC (openvc.app/investor-lists/pre-seed-investors) for VCs accepting cold outreach
- Title: Partner, Principal, Associate
- Fund focus: AI infrastructure, fintech, developer tools
- Stage: Pre-seed, Seed

### Email sequence templates

**Sequence 1: Potential customers (AI agent builders)**

Email 1 (Day 0):
```
Subject: Quick question about [Company]'s agent payments

Hi [Name],

I noticed [Company] is building [specific agent feature from their site/product].

Quick question: how are you handling payments when your agents need to transact? Most teams I talk to are using raw API keys with no spending controls.

I built Sardis specifically for this. Non-custodial MPC wallets with natural language spending policies. "Max $100 per transaction, only verified vendors" enforced before any money moves.

Would a 15-min demo be useful?

Efe
```

Email 2 (Day 4):
```
Subject: Re: Quick question about [Company]'s agent payments

Hi [Name],

Following up. One thing I forgot to mention: Sardis ships as an MCP server (52 tools), so your agents in Claude/Cursor can create wallets, send payments, and set policies without writing code.

Happy to show you in 15 min if useful. If not, no worries at all.

Efe
```

Email 3 (Day 9):
```
Subject: Re: Quick question about [Company]'s agent payments

Hi [Name],

Last note from me. If the timing isn't right, totally understand.

Sardis is open source if you ever want to poke around: sardis.sh

Happy to reconnect whenever agent payments become relevant for [Company].

Efe
```

**Sequence 2: Investors**

Email 1 (Day 0):
```
Subject: Sardis - agent payment infrastructure

Hi [Name],

Building Sardis: payment OS for the agent economy. Non-custodial MPC wallets with policy enforcement for AI agents.

Traction: [specific number - downloads, beta users, transaction volume].
Stack: 6 chains, 52-tool MCP server, Python + TypeScript SDKs.
Market: $66M+ raised by competitors (Skyfire, Payman, Paid) in last 6 months.

Raising pre-seed. Aligns with [Fund]'s focus on [their thesis area].

Deck: [link]

Worth 15 minutes?

Efe Baran Durmaz
sardis.sh
```

Email 2 (Day 5):
```
Subject: Re: Sardis - agent payment infrastructure

Hi [Name],

Quick update: [new traction milestone or product update since last email].

Happy to walk through the architecture if helpful. Also available async if a call doesn't fit your schedule.

Efe
```

Email 3 (Day 10):
```
Subject: Re: Sardis - agent payment infrastructure

Hi [Name],

Closing the loop. If timing isn't right, completely understand.

Will keep shipping and would love to reconnect when agent payments moves higher on [Fund]'s radar.

Efe
```

### Volume targets

- Week 3-4 (ramp up): 10-15 emails/day
- Week 5+: 20-30 customer emails/day + 5-10 investor emails/day
- Never exceed 50 emails/day per mailbox
- Rotate across 2-3 mailboxes

---

## 4. LinkedIn Outreach Playbook

### Profile optimization (do this first)

Your LinkedIn profile is your landing page. Before any outreach:

**Headline:**
```
Building Sardis - Payment OS for the Agent Economy | Non-custodial MPC wallets for AI agents | Solo founder, Delaware C-Corp
```

**About section (first 3 lines are critical, rest is behind "see more"):**
```
AI agents will move more money than humans within 5 years. Zero infrastructure exists for this today.

I'm building Sardis: non-custodial MPC wallets with natural language spending policies for AI agents. 6 chains, 52-tool MCP server, Python + TypeScript SDKs.

Also building: CoPU (hardware accelerator for LLM context, 99-614x faster than GPU), AgentGit (version control for agent state), FIDES (decentralized agent identity), RustShell (natural language terminal in Rust).

All open source. All shipping. Solo founder.
```

**Featured section:**
- Pin your best LinkedIn post
- Link to sardis.sh
- Link to CoPU GitHub repo

### Content calendar (3x/week)

| Day | Format | Topic |
|-----|--------|-------|
| Monday | Long-form text (1500+ chars) | Industry problem, contrarian take, or market analysis |
| Wednesday | Carousel (8-12 slides) | Technical education (how MPC works, what CCTP is, policy engine architecture) |
| Friday | Short text (500 chars) | Traction update, milestone, or founder reflection |

### LinkedIn algorithm rules

- Carousels/PDFs get 11.2x more impressions than text
- Text posts need 1500+ chars for best performance
- First 60 minutes are critical (early engagement triggers amplification)
- Comments of 15+ words get 2.5x algorithmic weight
- Never put links in post body. Always first comment.
- 3-5 niche hashtags max: #AIAgents #PaymentInfrastructure #DeveloperTools #AgentEconomy #BuildInPublic
- Posts Tue-Wed 8-9 AM and Thu 6-8 PM perform best

### Investor outreach sequence

**Phase 1: Warm up (Week 1-2)**
Engage with target investor's content. Comment substantively on 2-3 posts over 1-2 weeks. Not "Great post!" but a genuine technical addition or data point. This makes you visible before you reach out.

**Phase 2: Connection request (300 char limit)**

Template A - Thesis alignment:
```
Hi [Name] - your piece on [specific thesis/post] maps closely to what we're building at Sardis. Non-custodial payments for AI agents. Would love to be connected.
```

Template B - Mutual connection:
```
Hi [Name] - [mutual connection] suggested we connect. Building payment infrastructure for the agent economy. Your portfolio [company X] is in adjacent space.
```

Template C - Shared context:
```
Hi [Name] - been following your thinking on [topic]. Building Sardis, payment OS for AI agents. Would value being connected.
```

**Phase 3: First DM (after acceptance, wait 1-2 days)**
```
Thanks for connecting. Quick context: Sardis is the payment OS for the agent economy. Non-custodial MPC wallets with natural language spending policies.

[Specific traction number, e.g. "12 dev teams in closed beta" or "9,880 npm downloads last month"].

Not asking for anything yet. Just wanted to be on your radar as this space develops. Happy to share more when timing is right.
```

**Phase 4: Follow-up (5-7 days later, only if they engaged)**
```
Quick update since we connected: [new milestone, e.g. "shipped Arc chain support" or "first mainnet transaction"].

Would love 15 minutes to walk through what we're seeing in the agent payments space. [Calendly link in a separate message or next reply]
```

**Phase 5: Soft ask (7-10 days later, only if warm signals)**
```
[Name], we're wrapping up our pre-seed raise. Based on [Fund]'s focus on [their thesis], I think there's strong alignment.

Happy to send over our deck or jump on a 15-min call. What works better?
```

### Daily LinkedIn operations

- 10-15 personalized connection requests
- Reply to every comment on your posts
- Comment substantively on 5-10 posts from target investors/customers
- Post 3x/week (Mon, Wed, Fri)
- Never accept generic connection requests without checking the profile

---

## 5. X Growth Playbook

Covered in detail in x-content-week1.md and x-content-weeks2-4.md.

### Quick reference

- 3-5 posts/day, spaced 2-3 hours apart
- 30-50 replies to other accounts daily (this is more important than your own posts at 0 followers)
- Reply to every comment on your posts (75x algorithm weight)
- Text-only outperforms images by 30%
- Zero hashtags
- No external links in post body
- Get X Premium ($8/month for 4x visibility)
- Join "Build in Public" X Community
- Post 9 AM - 2 PM ET peak + one evening post

### Growth timeline (realistic)

- Month 1: 100-300 followers
- Month 2-3: 500-1,000 followers
- Month 4-6: 1,000-3,000 followers
- Requires daily effort, no breaks

---

## 6. Threads Strategy

### How to use Threads

Threads is a secondary channel. Do not invest separate content creation time. Use it for incremental reach.

**Workflow:**
1. Write content in Typefully for X
2. Crosspost to Threads via Buffer (free tier supports this)
3. Post on Threads 30-60 minutes after X (not simultaneously)
4. Adapt: shorten to under 200 characters when possible

**What works on Threads:**
- "Things I believe about..." format
- Numbered lists
- Short contrarian takes
- Personal/vulnerability posts
- One-liners with strong opinion

**What doesn't work:**
- Long threads (Threads favors single posts)
- Heavy technical content (audience is more casual)
- Anything that reads like it was written for X

---

## 7. First Customer Acquisition

### Channel ranking by effectiveness for developer infrastructure

| Channel | Cost | Time to First User | Quality |
|---------|------|-------------------|---------|
| Hacker News (Show HN) | $0 | 1 day (if launch goes well) | Very high |
| X build in public | $0 | 30-90 days | High |
| Cold email (personalized) | $37/mo | 14-30 days | Medium-High |
| Reddit communities | $0 | 30-60 days | Medium |
| LinkedIn outreach | $0 | 14-30 days | High for enterprise |
| Discord communities | $0 | 30-60 days | Medium |
| Product Hunt | $0 | 1 day (launch day spike) | Medium (lots of tourists) |
| Context7 / MCP distribution | $0 | Passive, ongoing | Very high (intent-driven) |

### Cold email for first customers

Target profile:
- Companies building AI agents that need to make payments or purchases
- Teams using LangChain, CrewAI, OpenAI Agents, Claude with tool use
- Fintech startups building agent-powered products

Where to find them:
- Apollo.io search: "AI agent" + CTO/VP Eng + 10-200 employees
- GitHub: repos with agent frameworks, stars > 100
- X: people posting about agent projects
- YC company directory: AI companies from recent batches

Conversion math:
- 300 cold emails = ~1 B2B lead (0.3% conversion rate for generic)
- 100 personalized cold emails = ~17 replies (17% for well-researched)
- Target: 20-30 emails/day = 600-900/month = 2-15 qualified conversations

### Community-led approach

Reddit (do not pitch, be helpful):
- r/MachineLearning
- r/LangChain
- r/artificial
- r/fintech
- r/cryptocurrency (for stablecoin/CCTP discussions)

Discord servers:
- LangChain Discord
- CrewAI Discord
- AI Agent builders communities
- Vercel/Next.js Discord (for SDK users)

Strategy: Answer questions. Share knowledge. Link to Sardis only when directly relevant to someone's specific problem.

---

## 8. Investor Outreach

### Where to find investors who accept cold outreach

| Source | URL | Notes |
|--------|-----|-------|
| OpenVC | openvc.app/investor-lists/pre-seed-investors | VCs who explicitly accept cold emails |
| NFX Signal | signal.nfx.com/investor-lists/top-ai-pre-seed-investors | AI-focused pre-seed investors |
| Outlander VC List | outlander.vc/fieldguide | 25 enterprise AI VCs at pre-seed |
| AngelList | angellist.com | Angel investors, rolling funds |
| YC | ycombinator.com/apply | $500K for 7% equity if accepted |

### Pre-seed fundraising reality (2025 data)

- Average AI pre-seed valuation: $17.9M (42% higher than non-AI)
- Most US pre-seed rounds: $1-2M
- 44% of Q4 2024 pre-seed rounds were under $250K
- Solo founders: 35% of new startups but only 17% of VC-funded startups
- Solo founders: 52.3% of successful exits (they do succeed)

### What VCs want from solo technical founders

1. Working product (not a pitch deck, not a prototype)
2. Early traction (users, downloads, LOIs, waitlist)
3. Clear plan for first hire
4. Proof of community engagement (not building in isolation)
5. Deep understanding of the problem space (not just the solution)

### Investor email cadence

- 5-10 targeted investor emails per day (not 50 generic ones)
- Each email takes 15-20 min of research and personalization
- Subject line: "[Company] - [one specific traction metric]"
- Body: 5 sentences max. Problem, solution, traction, ask, deck link
- Never attach a deck. Link to it.
- Follow up once at day 5-7 with a new data point
- Final follow-up at day 10-12 (breakup email)
- Stop at 3 touches. Move on.

### YC application

YC is the highest-ROI move for a solo technical founder.

What they offer:
- $500K ($125K for 7% equity + $375K uncapped SAFE with MFN)
- Demo Day access to 1000+ investors
- Alumni network, office hours, brand credibility

Apply at: ycombinator.com/apply

YC application tips for Sardis:
- Lead with traction, not vision
- Show the product working (screen recording)
- Explain why you specifically are the right person
- Be concise. YC partners read thousands of applications.
- Apply early in the batch cycle

---

## 9. Hacker News Launch Plan

### Pre-launch (1-2 weeks before)

- Clean up README for all repos (Sardis, CoPU, AgentGit, FIDES, RustShell)
- Make sure sardis.sh loads fast and looks professional
- Prepare a founder comment (300-500 words) explaining who you are and why you built this
- Have 2-3 friends ready to ask genuine technical questions in the comments

### Launch day

**Timing:** Monday or Tuesday, 8-9 AM US Eastern.

**Title format:** "Show HN: Sardis - Payment infrastructure for AI agents (open source)"

Keep the title factual and specific. No marketing language. HN readers hate superlatives.

**Founder comment (post immediately after submission):**
```
Hey HN, I'm Efe. Solo founder building payment infrastructure for AI agents.

The problem: AI agents increasingly need to make financial transactions (buy API credits, pay for services, purchase resources). Current approach is giving agents raw API keys or credit cards with no controls.

Sardis gives every agent a non-custodial MPC wallet with natural language spending policies. "Max $100 per transaction, only verified vendors" gets parsed into deterministic rules and enforced before any money moves.

Stack: Python (FastAPI), TypeScript SDKs, Solidity smart contracts on 6 EVM chains, MCP server with 52 tools.

All open source. I've been building this solo for 5 months.

I also built some adjacent projects:
- CoPU: hardware accelerator for LLM context (SystemVerilog, 99-614x faster than GPU)
- AgentGit: version control for agent state (Rust core)
- FIDES: decentralized identity for agents (Ed25519 DIDs)

Happy to answer any questions about the architecture, business model, or why I think agent payments is a category worth building for.
```

**Post-launch:**
- Reply to every single comment within 30 minutes
- Be genuine, technical, and humble
- Admit what's not built yet
- Never be defensive about criticism
- Stay on HN for the entire day

### Expected outcomes

Good launch: 500-5,000 unique visitors, 50-500 signups/stars
Great launch: front page, 10,000+ visitors, 500+ stars
Average launch: 100-500 visitors, 10-50 signups

Even an "average" launch produces more qualified developer interest than weeks of cold email.

### Multiple launches

You can do separate Show HN launches for:
1. Sardis (payment infra)
2. CoPU (hardware, different audience)
3. RustShell (developer tool, broad appeal)

Space them 4-6 weeks apart. Each launch reaches a somewhat different audience.

---

## 10. Weekly Operations Calendar

### Daily (every single day, no exceptions)

| Time (TR) | Activity | Platform | Duration |
|-----------|----------|----------|----------|
| 09:00 | Check analytics, plan day's content | All | 15 min |
| 10:00 | Reply to overnight comments/DMs | X, LinkedIn | 20 min |
| 14:00 | Post 1 | X (via Typefully) | 5 min |
| 14:15 | LinkedIn engagement (comment on 5-10 posts) | LinkedIn | 30 min |
| 16:30 | Post 2 | X | 5 min |
| 17:00 | Reply to X comments, engage with 10-15 accounts | X | 30 min |
| 19:00 | Post 3 | X | 5 min |
| 19:30 | LinkedIn outreach (10-15 connection requests) | LinkedIn | 30 min |
| 22:00 | Post 4 (optional) | X | 5 min |
| 22:30 | Send cold emails (batch from Apollo lists) | Email | 30 min |

### Weekly

| Day | Special Activity |
|-----|------------------|
| Monday | Write and schedule week's X content in Typefully |
| Monday | LinkedIn long-form post |
| Wednesday | LinkedIn carousel post |
| Wednesday | Review email outreach metrics (open rates, reply rates) |
| Friday | LinkedIn traction update post |
| Friday | Week recap post on X |
| Saturday | Content planning for next week |
| Sunday | Batch research: find new target accounts, update Apollo lists |

### Monthly

- Review all platform analytics
- Adjust content strategy based on what performed
- Update email sequences based on reply patterns
- Clean up Apollo lists (remove bounced, update roles)
- Write one long-form technical piece (for HN or blog)

---

## 11. Metrics & Tracking

### Track weekly

| Metric | X | LinkedIn | Email | Goal (Month 1) |
|--------|---|---------|-------|-----------------|
| Followers/Connections | | | N/A | X: 300, LI: +100 |
| Impressions | | | N/A | X: 50K, LI: 10K |
| Engagement rate | | | N/A | X: 3%, LI: 5% |
| Replies sent | | | N/A | X: 200/wk, LI: 50/wk |
| DMs received | | | N/A | 5-10 total |
| Emails sent | N/A | N/A | | 400-600 |
| Email open rate | N/A | N/A | | >50% |
| Email reply rate | N/A | N/A | | >10% |
| Meetings booked | | | | 3-5 total |
| GitHub stars gained | | | | 50-100 |

### Success signals (first 90 days)

- 3+ inbound investor conversations
- 5+ qualified customer conversations
- 1,000+ X followers
- 1,500+ LinkedIn connections
- First design partner signed
- HN front page (at least once)
- First beta user on mainnet

### Failure signals (adjust strategy if)

- Email open rate below 30% (fix subject lines or sender reputation)
- Email reply rate below 3% (fix personalization or targeting)
- X growth stalls below 50 followers/month (increase reply volume)
- LinkedIn posts getting <500 impressions (fix content format or timing)
- Zero inbound DMs after 30 days (content is not resonating, adjust angle)

---

## Quick Reference: What NOT to Do

### Email
- Never use sardis.sh domain for cold email
- Never send more than 50 emails/day per mailbox
- Never skip 14-day warmup period
- Never attach pitch decks (link to them)
- Never follow up more than 3 times without a response
- Never use "synergy", "revolutionary", or "disruptive" in emails

### LinkedIn
- Never pitch in a connection request
- Never mass-message identical text (LinkedIn detects this)
- Never use more than 5 hashtags
- Never put external links in post body
- Never use automation tools without understanding ban risk
- Never follow up more than 3 times without a response

### X
- Never put links in the main post
- Never use hashtags (zero is optimal for dev content)
- Never burst-post 5+ tweets in quick succession
- Never use engagement bait ("Like if you agree")
- Never copy-paste content from LinkedIn without adapting
- Never ask people to "follow for more"

### General
- Never pitch before providing value
- Never be defensive about criticism
- Never ignore comments/replies on your own posts
- Never stop posting for more than 2 consecutive days
- Never compare your month 1 to someone else's month 36
