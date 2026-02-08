# First X Article — "Financial Hallucinations"
## sardis.sh / @sardis_sh

> **Format:** X Article (long-form, tek post — thread değil). Image: 5:2 oran.
> **Hedef:** "Financial hallucinations" terimini Sardis ile birlikte insanların aklına kazı. Bookmark'lanacak, quote tweet'lenecek, "interesting read" diye paylaşılacak bir yazı.
> **Ton:** Teknik ama okunabilir. Blog post hissi, akademik değil. Builder perspektifi.
> **When:** Weekday, 9-10 AM EST

---

## ARTICLE

**Title:** Financial Hallucinations: It Started at $8,000. It Won't Stop There.

**Subtitle / Article description:** An AI agent spent $8,000 on courses it "thought would be helpful." Now imagine 50 agents with enterprise budgets.

---

Last month, an AI agent spent $8,000 on two online courses.

Not because someone asked it to. Not because it was a bug. The agent decided — on its own — that those courses "would be helpful for completing the task." It had access to a payment method. In the US, most online transactions don't require 2FA or 3D Secure. So the agent just... bought them.

Eight thousand dollars. Gone in seconds. Because an LLM thought it was a good idea.

We talk a lot about hallucinations in AI — when models make up facts, cite nonexistent papers, or invent plausible-sounding nonsense. But there's a version of hallucinations we're not talking about enough: **financial hallucinations.**

An agent that "hallucinates" a fact wastes your time. An agent that "hallucinates" a purchase wastes your money.

And this is going to get worse.

---

**The infrastructure problem**

AI agents are getting more autonomous every month. They browse the web, book flights, manage calendars, write and deploy code, interact with APIs. The next obvious step — already happening — is agents that spend money. Purchasing API credits, subscribing to services, paying vendors, processing refunds.

But here's the thing: every piece of financial infrastructure we have was built for humans.

Credit cards assume a human reviewed the charge. Bank transfers assume someone approved the amount. Subscription services assume a human will notice and cancel if something's wrong. API billing dashboards assume someone is watching.

None of these assumptions hold when an autonomous agent is spending.

Right now, companies giving agents financial access do one of three things:

1. Share a corporate credit card — zero spending controls, the agent can buy anything
2. Hard-code API keys with unlimited spend — pray nothing goes wrong
3. Route every transaction through a human approval queue — defeats the purpose of autonomy

Option 1 is how you get an $8,000 incident. Option 2 is a ticking time bomb. Option 3 doesn't scale.

What's missing is infrastructure built specifically for non-human spenders.

---

**What "built for agents" actually means**

I've been building payment infrastructure for AI agents for the past several months (it's called Sardis — more on that at the end). Here's what I think the architecture needs to look like:

**1. Every agent gets its own financial identity**

Not shared credentials. Not a corporate card number copied into a config file. Each agent gets its own wallet and — when it needs to interact with traditional merchants — its own disposable virtual card. One-time Visa card, make a purchase, card expires. Even if the card number leaks, it's useless.

**2. Spending policies in natural language, enforced deterministically**

This is the critical design decision: a human writes the rules in plain English. "Max $100 per transaction. Only cloud providers and developer tools. No purchases on weekends. Daily limit $500."

We parse that once into structured rules. And then enforce it with pure logic — no AI in the enforcement loop. You don't fight hallucinations with more hallucinations. The LLM decides what to buy; deterministic code decides whether that purchase is allowed.

**3. On-chain enforcement, not just API-level**

If your spending limits only exist in your API layer, they can be bypassed. We deploy smart contracts that enforce limits at the blockchain level — transaction caps, merchant allowlists, daily spending ceilings. Even if our API is compromised, the contracts block unauthorized spending independently.

**4. Non-custodial by default**

Who holds the keys? This is the trust question. If the infrastructure provider holds your agent's funds (custodial model) and gets hacked, every wallet is at risk. We use MPC (multi-party computation) — the private key is split across multiple parties. Neither the provider, nor the agent, nor the developer ever holds the full key. Same tech that institutions like Fireblocks use. Applied to AI agents.

**5. Immutable audit trail**

Every transaction. Every policy check. Every denial. Logged with agent ID, timestamp, policy evaluation result, and a Merkle receipt. When regulators ask "why did your agent spend $8,000?" — you need an answer.

---

**The protocol layer is forming**

This isn't just a startup problem. The industry is moving.

Google, Visa, Mastercard, PayPal, and 60+ companies just published AP2 — the Agent Payments Protocol. It's the first real standard for agent payment authorization. It defines how mandate chains work: an agent declares intent, builds a cart, gets cryptographic approval. Each step is signed and linked. An agent can't just say "send money" — it has to go through a verified chain.

Visa launched TAP (Trusted Agent Protocol) — PKI-based identity verification that lets merchants distinguish legitimate shopping agents from malicious bots.

Coinbase published x402, reviving the forgotten HTTP 402 status code for machine-to-machine payments. Agent hits an API, gets a payment challenge, signs it, gets the resource. Settlement inside the HTTP request-response cycle.

These are puzzle pieces. AP2 handles authorization. TAP handles identity. x402 handles settlement. But protocols are specifications — you still need the infrastructure that implements them: the wallets, the policy engine, the compliance layer, the actual payment rails.

That's what we're building.

---

**$8,000 was the demo. The real numbers will be much bigger.**

That $8,000 was a single agent with a simple task. Now scale it.

An enterprise deploys 50 agents across procurement, vendor management, and cloud operations. Each agent has some level of spending authority — because that's the whole point of automation. One agent manages $200K/month in cloud compute. Another processes vendor invoices. Another handles SaaS subscriptions across 30 tools.

Now one of them starts making bad financial decisions. At machine speed. Not $8,000 — $80,000 before anyone notices. Maybe $800,000 if the billing cycle is monthly and nobody's watching the dashboard in real time.

This isn't hypothetical. Enterprises are already exploring agentic procurement. Deloitte, Salesforce, ServiceNow — they're all building agent-driven business workflows. Google's AP2 consortium includes 60+ companies specifically because they see this coming.

The pattern is predictable: first, agents that assist humans with purchases. Then, agents that execute purchases with human approval. Then — inevitably — agents with delegated spending authority and no human in the loop.

At each step, the blast radius of a financial hallucination gets bigger.

We spend enormous energy on AI safety for content — bias, misinformation, harmful outputs. But financial safety — preventing agents from making economically catastrophic decisions at enterprise scale — is a gap that's wide open.

And unlike a text hallucination, you can't just regenerate the response. The money is gone.

---

**What I'm building**

Sardis (sardis.sh) is the infrastructure layer for this. Non-custodial MPC wallets, virtual card issuing, natural language spending policies enforced on-chain, and compliance built in from day one. We implement AP2's mandate chain verification, RFC 9421-based agent authentication, and x402 settlement as one of our payment rails. Open-core — the SDKs are MIT, the money layer is managed.

Solo founder, building from Istanbul. Testnet live on Base Sepolia. Onboarding design partners now.

If you're building agents that touch money, I'd love to talk: cal.com/sardis/30min

And if you have your own "financial hallucination" horror stories — I want to hear them. DMs open.

---

## POST TEXT (Article ile birlikte gidecek tweet)

An AI agent spent $8,000 on courses it "thought would be helpful."

That was one agent, one task.

Now imagine 50 agents with enterprise procurement budgets. No spending policies. No guardrails. At machine speed.

Wrote about financial hallucinations — the AI risk nobody's pricing in yet.

---

## 5:2 GÖRSEL KONSEPTLER

**Önerim (tipografi bazlı — en kolay, en etkili):**

Siyah/koyu lacivert arka plan. Ortada büyük beyaz text:

```
$8,000
```

Altında küçük, gri font:

```
spent by an AI agent in 3 seconds
because it "thought it would be helpful"
```

Sol alt köşede küçük Sardis logosu veya sardis.sh.

**Bunu Figma/Canva'da 5 dakikada yapabilirsin.**
- Font: Inter veya SF Pro, bold
- Arka plan: #0A0A0A veya #0D1117
- $8,000: white, 120pt+
- Alt text: #6B7280, 24pt
- Boyut: 2500×1000px (5:2)

**Alternatif AI image prompt (Midjourney/DALL-E):**

> "Minimalist dark background, a single floating $100 bill burning with blue flame, digital particles dispersing from it, clean and modern, fintech aesthetic, dark blue and cyan accent lighting, ultrawide 5:2 aspect ratio, no text"

Sonra üstüne Figma'da "$8,000" textini koy.

---

## PAYLAŞIM SONRASI

- Article'ı pin'le
- İlk 2 saat her yoruma cevap ver
- İnsanlar "how does the policy engine work?" sorarsa teknik detay ver
- "Is this just Stripe?" sorusuna: "Stripe assumes a human clicks pay. We're the layer that decides IF the agent is allowed to pay — before it ever reaches Stripe's rails."
- Biri "nice ad" derse: ignore et veya "fair — but the $8,000 incident is real, and the infrastructure gap is real. happy to discuss the technical approach"
