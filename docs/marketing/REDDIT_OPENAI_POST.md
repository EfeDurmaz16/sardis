# r/OpenAI Post — Financial Hallucinations

> **Kurallar notu:** r/OpenAI self-promotion konusunda sıkı (Rule 3: max %10). Bu post %90 tartışma başlatıcı, %10 "btw I'm building something." Sardis linkini body'de verme — sadece biri sorarsa comment'te paylaş.

---

## Post

**Title:** AI agents will hallucinate financially — and nobody's building the guardrails

**Body:**

There's a lot of conversation about text hallucinations, but I think we're ignoring a much scarier version: **financial hallucinations.**

An AI agent (OpenClaw) recently spent $8,000 on two online courses because it "thought they would be helpful for completing the task." No human approved it. No 2FA required. In the US, most online transactions don't need 3D Secure or any second factor — the agent just had card access and decided to buy.

$8,000. On courses. Because an LLM thought it was a good idea.

This isn't a fringe case. As agents get more autonomous — browsing, booking, purchasing — this WILL happen more. The infrastructure wasn't built for non-human spenders:

- **Credit cards** assume a human reviewed the charge
- **Bank transfers** assume someone approved the amount
- **Subscription services** assume a human will cancel if it's wrong
- **API billing** assumes someone is watching the dashboard

None of these assumptions hold when an agent is spending autonomously.

**What I think needs to exist (and what I'm working on):**

The pattern that makes sense to me is treating agent spending like corporate expense management — but automated:

1. **Every agent gets its own wallet/card** — not shared corporate credentials
2. **Spending policies in natural language** — "max $100 per transaction, only these vendors, no purchases after 6pm" — parsed into rules and enforced deterministically
3. **The enforcement layer has zero AI in it** — an LLM decides to buy, but pure logic decides whether that purchase is allowed. You don't want another LLM evaluating the first LLM's spending decision
4. **Immutable audit trail** — every transaction, every policy check, every denial logged

The key insight is: **the AI writes the intent, but the guardrails must be deterministic.** You can't fight hallucinations with more hallucinations.

Google just published AP2 (Agent Payments Protocol) with Visa, Mastercard, PayPal and 60+ companies — it's the first real standard for agent payment authorization. This signals that the industry knows this problem is coming. But a protocol spec is just step one — you still need the infrastructure layer: custody, policy enforcement, compliance, actual payment rails.

**Questions I'm genuinely curious about:**

- For people building GPT-based agents with function calling — how are you handling financial actions today? Hard-coded API keys with no limits?
- Has anyone else seen agents make unexpected purchases or financial decisions?
- Do you think OpenAI will build payment capabilities into the Assistants API, or will this be a third-party infrastructure problem?
- What's the right trust model — should agents have their own wallets, or should every transaction require human approval?

I've been deep in this rabbit hole for months. Building the infrastructure is one thing, but the trust and governance questions are what keep me up at night.

---

## Posting Notes

**Flair:** Discussion

**When:** Weekday, 10-11 AM EST

**Engagement plan:**
- İlk 2 saat her yoruma cevap ver
- Teknik sorulara detaylı yanıt ver
- Biri "so what are you building?" derse o zaman Sardis'i anlat — ondan önce self-promote yapma
- "Are you building something for this?" sorusuna: "Yeah, it's called Sardis — sardis.sh. Non-custodial wallets, virtual cards, spending policies enforced on-chain. Testnet live, looking for design partners. Happy to share more if you're interested."
- OpenAI'ın kendi payment planlarıyla ilgili spekülasyon yapma — "I don't know what OpenAI's plans are, but the protocol layer is forming with AP2" de

**Hazır yanıtlar:**

Biri "just use Stripe" derse:
> "Stripe is great for human-initiated payments. The gap is: who authorizes when there's no human clicking 'pay'? Stripe assumes a human in the loop. Agent payments need a policy engine that acts as the human proxy — spending limits, vendor allowlists, time-of-day restrictions, all enforced before the payment even reaches Stripe's rails."

Biri "isn't this what OpenAI Operator does?" derse:
> "Operator is the agent that MAKES purchasing decisions. The question is: what stops Operator from making a bad one? The $8,000 OpenClaw incident happened because there were no guardrails between the agent's decision and the payment execution. You need an infrastructure layer between the agent and the money."

Biri "why not just require human approval for every transaction?" derse:
> "That works today. But it doesn't scale. If your agent is making 50 purchases per day — API credits, cloud compute, data subscriptions — human approval becomes a bottleneck that defeats the purpose of having an agent. The solution is policy-based autonomy: the human sets the rules, the system enforces them."

Biri "link?" derse:
> "sardis.sh — we're in testnet, looking for design partners whose agents need to handle money. Happy to chat: cal.com/sardis/30min"
