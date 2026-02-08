# YC 1 Dakikalık Pitch — Sardis
## Interview'ın ilk sorusu: "What are you building?"

> **Kural:** Michael Seibel 2000+ interview yapmış. Diyor ki: "If you can't explain what you do in one sentence, we move on." Kısa, net, jargon'sız. Sonra soru soracaklar — kısa cevapla.

---

## TAM SCRIPT (60 saniye)

### Açılış — Ne yapıyorsun? (10 saniye)

"We're building payment infrastructure for AI agents. Agents can reason and take actions, but they can't be trusted with money. Sardis is the trust layer."

### Problem + Killer Insight (15 saniye)

"Here's the problem: an AI agent recently spent $8,000 on two online courses because it thought they'd be helpful. No human approved it. No 2FA. In the US, most transactions don't even need 3D Secure. The agent just... bought it.

We call these financial hallucinations. Agents WILL make bad spending decisions. The question is who catches it before money moves."

### Çözüm (15 saniye)

"Sardis gives every agent a non-custodial wallet — private keys are split across MPC parties, nobody can drain them. Agents get disposable virtual Visa cards through Lithic. And humans set spending policies in plain English — 'max $100, only cloud providers, no weekends' — we parse it once and enforce it deterministically, both at API level and on-chain through smart contracts."

### Traction (10 saniye)

"Testnet is live on Base Sepolia with the full stack end-to-end. We've done 150-plus outreach conversations, design partners are onboarding now with paid beta at $1.5-2K per month."

### Vision (10 saniye)

"We're building toward agent-to-agent payments. A CFO agent that orchestrates spending across an entire agent swarm — approving, denying, rebalancing budgets autonomously. The financial operating system for the agent economy."

---

## INTERVIEW SORU-CEVAP (Bunlar gelecek — hazır ol)

---

### "Why should we fund you?"

"Because I've built the hardest version of this. Non-custodial, on-chain enforcement, three protocol standards implemented — TAP, AP2, x402 — I'm the only project that has all three. 19 packages, 1,516 lines of Solidity, 77 test files. This isn't a wrapper — it's infrastructure."

---

### "Why now?"

"Two reasons. First, 40-50% of your last batch was agentic AI. Those companies will need agents that spend money — and right now there's no infrastructure for it. Second, Google, Visa, Mastercard, and PayPal just published AP2 — the first industry standard for agent payments. The protocol layer is forming now. Whoever builds the infrastructure layer wins."

---

### "How do you make money?"

"Open-core. SDKs and MCP server are MIT — free to integrate. The managed service — policy engine, MPC custody orchestration, compliance — is paid. Per-transaction fees plus enterprise tiers. Same model as Stripe: client libraries open, backend closed."

---

### "What's your unfair advantage?"

"Depth. I've implemented three protocol standards that nobody else has together. I have Solidity contracts enforcing spending limits on-chain — not just API-level. And I'm non-custodial, which is a regulatory moat. When regulators come for agent payments — and they will — custodial players have a problem. We don't."

---

### "Who are your competitors?"

"Skyfire raised $9.5M, Payman raised $13.8M. Both custodial. Locus is in your current batch — non-custodial, ACP-focused, USDC on Base only. We're multi-protocol, multi-chain, multi-rail — fiat cards plus on-chain. And we're the only one with on-chain policy enforcement through smart contracts."

---

### "You're a solo founder. Why should we bet on you?"

"Speed. Zero coordination overhead. I shipped 19 packages, 3 smart contracts, and 3 protocol implementations as a solo dev. At this stage, velocity matters more than headcount. I'll use YC to find a co-founder — your matching program is exactly what I need."

---

### "You applied twice before and got rejected. What's different?"

"The idea. My previous applications were for agentic memory infrastructure — interesting problem but unclear market. This time the product is real — testnet live, full stack, design partners paying. And the market timing is undeniable — half your batch is building agents that will need payment rails."

---

### "Why Istanbul?"

"That's where I code. Low burn, good timezone overlap with Europe and US East Coast. The entity is a Delaware C-corp. The compliance stack is all US — Persona, Lithic, Elliptic. Istanbul gives me 18+ months of runway on a pre-seed."

---

### "What will you do with YC funding?"

"Three things. First, find a co-founder through YC matching — I need a go-to-market person. Second, move to mainnet — Base first, then Polygon. Third, convert 3-5 design partners to paying production customers by Demo Day."

---

### "What's the biggest risk?"

"Adoption timing. If agent autonomy moves slower than expected, the market takes longer to form. But the direction is clear — every AI lab is pushing agents toward more autonomy. And even in the meantime, the virtual card product works for today's semi-autonomous agents."

---

### "Can you show us a demo?"

"Yes. I can show you wallet creation, policy assignment, virtual card issuing, a transaction that passes policy, and a transaction that gets blocked — all on testnet, all live. Takes about 90 seconds."

*(Eğer demo isterlerse, sardis.sh/demo'yu aç ve göster.)*

---

## DELIVERY KURALLARI

1. **Hız:** Her cevap 1-3 cümle. Uzun konuşma = kötü sinyal.
2. **Sayılar:** "19 packages", "$8,000", "150+ outreach", "1,516 lines" — somut rakamlar kullan.
3. **Jargon yok:** "Non-custodial MPC" yerine "wallets agents can't steal from" de. Teknik detay sorarlarsa o zaman derinleş.
4. **Confidence:** "I think" deme. "We do" de. "We're trying to" deme. "We built" de.
5. **Rehearse etme:** Doğal konuş. Ezberlenmiş pitch YC partner'ları uzaklaştırır.
6. **"I don't know" de:** Bilmediğin soruya "I don't know yet, but here's how I'd figure it out" de.
7. **Enerjin yüksek:** 10 dakikan var, her saniye sayılıyor.

---

## 60 SANİYELİK KISA VERSİYON (Elevator Pitch)

> "AI agents can reason but they hallucinate financially — one recently spent $8,000 on courses it thought would be helpful. Sardis is payment infrastructure that solves this. Non-custodial wallets where agents can't drain funds, disposable virtual Visa cards, and natural language spending policies — 'max $100, only cloud providers' — enforced on-chain through smart contracts, not just our API. Testnet live, design partners paying $1.5-2K/mo. We're building the financial operating system for the agent economy."

*(Bu versiyonu networking event'lerde, YC office hours'da, veya biri "so what do you do?" dediğinde kullan.)*

---

## 30 SANİYELİK ULTRA-KISA VERSİYON

> "Sardis is payment infrastructure for AI agents. Agents hallucinate financially — one spent $8,000 autonomously on courses it thought would help. We give agents wallets they can't drain, virtual Visa cards, and spending policies enforced on-chain. Testnet live, design partners onboarding."

---

## 10 SANİYELİK TEK CÜMLE

> "We're building the Stripe for AI agents — non-custodial wallets and spending policies that prevent financial hallucinations."
