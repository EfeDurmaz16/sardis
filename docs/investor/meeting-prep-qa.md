# Sardis: Investor Meeting Prep Q&A
## March 2026

Prepared answers to the hardest questions investors will ask. Practice these out loud before every meeting. The goal is to answer in 2-3 sentences max, then stop talking.

---

## 1. "Stripe just announced MPP. What stops them from building controls?"

**Answer:** Sardis works across Stripe, Base, Tempo, and Visa simultaneously. Stripe only controls Stripe. The CFO wants one policy layer, not four.

**Extended context (if pressed):** Stripe's incentive is to maximize volume on Stripe rails. They will never build a governance layer that helps enterprises route payments through Coinbase or Visa instead. Sardis is rail-agnostic by design -- that is the structural moat. We are listed on mpp.dev/services because Stripe needs us in their ecosystem, not the other way around.

---

## 2. "You're 20. How do you convince a 50-year-old CFO?"

**Answer:** I do not. The $3M buys the Enterprise GTM Lead who does. My job is to keep the infrastructure 2 years ahead of everyone else.

**Extended context (if pressed):** The hiring plan is specific: Forward Deployed Engineer + Enterprise GTM Lead. The FDE converts design partners on-site. The GTM Lead runs the enterprise sales cycle. I built the product. I am not pretending I can also sell it to Fortune 500 procurement. That is what the raise is for.

---

## 3. "Why $3M not $1M?"

**Answer:** I can build anything for $0. But enterprise deals require SOC2 ($15K), security audits ($50K), and a GTM lead ($200K/yr). Credibility costs money.

**Extended context (if pressed):** The breakdown: ~$600K for 18 months of GTM Lead + FDE salaries. ~$100K for SOC2 + PCI + security audit + E&O insurance. ~$200K for infrastructure scaling (Alchemy RPC, Turnkey MPC, Neon Postgres, monitoring). ~$100K for 18 months of runway buffer. The rest is operating capital for enterprise pilot support. Every dollar goes to converting developer pull into enterprise paid seats.

---

## 4. "50K installs -- hobbyists or enterprise?"

**Answer:** Currently developer-heavy. That is why the raise funds GTM: converting developer pull into enterprise paid seats.

**Extended context (if pressed):** The 50K installs are real, verified on npm and PyPI. They are primarily individual developers and small teams experimenting with agent payments. The pattern we are betting on is bottom-up adoption: developers try the SDK, build an agent with payment capabilities, then their company needs governance when it goes to production. The Business tier ($199/seat/mo) captures that conversion. We do not have enterprise logos yet -- that is the honest answer. The raise funds the people who get us enterprise logos.

---

## 5. "Why wouldn't a top FDE leave Stripe for you?"

**Answer:** Because this is the infrastructure layer that Stripe, Coinbase, and Google all need but cannot build across each other's rails. The FDE who joins now defines the category.

**Extended context (if pressed):** Stripe FDEs are smart. They know Stripe will never build cross-rail governance. They also know the agent payments category is forming right now. The pitch to an FDE is: you can be employee #300 at Stripe maintaining existing products, or you can be employee #2 at the company that defines how AI agents interact with money. The equity upside and category-defining opportunity is the draw. We are also incorporated as a Delaware C-corp via Stripe Atlas, so the equity structure is clean.

---

## 6. "Bug in policy engine, enterprise loses $500K. Who's liable?"

**Answer:** Sardis is non-custodial. We enforce policy, we do not hold funds. The SOC2 audit and $1M E&O insurance (from the raise) cover operational liability.

**Extended context (if pressed):** The architecture is specifically designed for this. Sardis never touches private keys (Turnkey MPC), never holds funds (Safe Smart Accounts), and never processes payments directly (routes to licensed rails). Our liability is limited to the policy enforcement layer. The SOC2 Type II certification provides the audit evidence that our controls work as documented. The E&O insurance covers the gap. Enterprise contracts will include liability caps and SLA terms -- standard for infrastructure providers.

---

## 7. "What if an agent framework just builds payments in-house?"

**Answer:** They have tried. CrewAI, LangChain, and AutoGPT all have basic tool integrations. None of them have built a 12-check deterministic policy engine, spending mandates, or compliance infrastructure. They are orchestration frameworks, not financial infrastructure companies. They will integrate Sardis the same way they integrate OpenAI -- as a specialized primitive.

---

## 8. "What is your unfair advantage?"

**Answer:** I shipped the cross-rail governance standard while the market was still debating whether agents should have wallets. 50K installs, 7 protocol implementations, 15 framework integrations, listed on mpp.dev/services -- all with $0 in funding. The incumbents are 12-18 months behind on the governance layer specifically because it is not their core business.

---

## 9. "What happens if agent payments take 5 years instead of 2?"

**Answer:** The Business tier ($199/seat/mo) generates SaaS revenue from day one. Any company deploying AI agents needs mandate management and audit trails regardless of payment volume. We do not need agent payments to be mainstream to have a business -- we need enterprises to be worried about agent payments, which they already are.

---

## 10. "Why not raise more? Category leaders raise $10M+ seeds."

**Answer:** I have proven I can build with zero capital. $3M is enough to prove enterprise GTM works. If it does, the Series A will be on much better terms. I would rather own more of the company at that point than dilute now for capital I do not need yet.

---

## 11. "Are you the long-term CEO or the best CTO you've ever met?"

**Answer:** I am the CEO. The product is the moat, and I am the only person who can build it at this speed. But I am not pretending I can also run enterprise sales. The raise funds a GTM lead who handles the boardroom while I handle the protocol.

**Extended context (if pressed):** The best technical founders stay CEO when the product IS the moat. Sardis is not a sales-led company -- it is a protocol company with an enterprise wrapper. The CEO needs to be the person who understands the intersection of cryptography, compliance, and agent infrastructure at the deepest level. That is me. I will hire a CRO before I hire a COO.

---

## 12. "Can developers bypass Sardis and hit Stripe directly?"

**Answer:** Yes, and that is the point. Sardis is not a payment processor. We are the governance layer that sits above Stripe, Coinbase, and every other rail. Developers can always hit Stripe directly -- but then their CFO has no audit trail, no policy enforcement, and no kill switch. We are the reason the CFO says yes to letting agents spend.

**Extended context (if pressed):** We are deliberately non-custodial and rail-agnostic. The developer can always route around us for the payment itself. But the enterprise buyer cannot get compliance sign-off without us. That is the lock-in: not technical dependency, but compliance dependency. Once Sardis is in the audit trail, removing it means re-certifying with the compliance team.

---

## 13. "How do you manage a 45-year-old VP of Sales?"

**Answer:** I do not manage their sales process -- I give them the best product to sell and stay out of their way. My job is to make sure the product is so far ahead of the market that the VP of Sales has unfair ammunition in every deal. Their job is to close. I have never managed a 45-year-old, but I have shipped more code than most 45-year-old engineering teams. I will earn their respect the same way -- by being undeniably good at my part.

**Extended context (if pressed):** The hiring plan is specific: I am looking for someone who has done $100K+ ACV enterprise sales and wants to define a category, not maintain a quota. The equity and the category-defining opportunity attract the right person. I am not looking for someone I need to manage -- I am looking for a partner who runs GTM autonomously while I run product and engineering autonomously.

---

## Quick Reference: Key Numbers

Use these in conversation. Do not read from a slide.

- 50K+ SDK installs, $0 marketing spend
- 21 published packages at v1.1.0
- 47+ production API endpoints
- 15 framework integrations
- 7 protocol implementations
- 1,800+ commits, solo
- Listed on mpp.dev/services
- Stripe MPP early access
- sardis.pay() Phase 1-3 shipped
- Agent Auth Protocol support
- SOC2/PCI in progress ($15K via DSALTA)
- Delaware C-corp via Stripe Atlas

---

## Meeting Logistics

- Always have the live dashboard ready at app.sardis.sh
- Always have the SDK docs ready at sardis.sh/docs
- Always have the mpp.dev/services listing open
- Prepare a 60-second live demo: create agent, set policy, execute payment, show audit trail
- End every meeting with: "What would you need to see in 30 days to move forward?"
