# Locus Call — Tam Konuşma Scripti
## Cole Dermott ile 30 Dakika

> **Nasıl kullan:** Bu bir sahne metni gibi. Senin repliklerini (EFE) birebir söyleyebilirsin. Cole'un replikleri (COLE) tahmindir — gerçekte farklı şeyler söyleyecek, o zaman doğal akışa bırak. Ama yapı ve geçişler seni yönlendirsin.

---

## [0:00 – 3:00] AÇILIŞ + TANITIM

**EFE:**
"Hey Cole, thanks for taking the time man. Really glad we could connect. I've been following Locus since the YC announcement — the ACP reference implementation especially caught my eye. We're clearly both obsessed with the same problem."

**COLE:**
*(Muhtemelen)* "Yeah for sure, thanks for reaching out. I checked out Sardis after your email — cool stuff. Tell me more about what you're building."

**EFE:**
"Yeah so — quick background. I'm Efe, building Sardis solo from Istanbul. We're a payment OS for AI agents. The core idea is: agents can reason but they can't be trusted with money. We're the trust layer. Non-custodial MPC wallets through Turnkey, virtual card issuing through Lithic — so agents can get disposable Visa cards — natural language spending policies, and on-chain enforcement through our own Solidity contracts. Plus an MCP server with 36 tools so Claude or Cursor can do payments natively."

**COLE:**
*(Muhtemelen)* "Nice. That's a wide surface area. How long have you been working on it?"

**EFE:**
"About [X months]. But honestly, I'm way more curious about your journey right now. How did you and Eliot find each other? The Coinbase plus Scale AI combo makes a lot of sense for this space."

---

## [3:00 – 7:00] CO-FOUNDER HİKAYESİ + FIKRIN DOĞUŞU

**COLE:**
*(Anlatacak — dinle, not al. Muhtemelen okul, staj, ya da ortak tanıdık üzerinden tanıştılar.)*

**EFE:**
*(Dinledikten sonra, samimi reaction:)*
"That's cool. I think the payments experience from Coinbase plus the ML/data side from Scale is actually the perfect combination for this. You've got the financial infra intuition and the AI understanding in one team."

**EFE:**
"So where did the idea actually come from? Was it something you saw firsthand at Coinbase — like a specific moment where you thought 'agents need payment rails' — or did it click when you guys came together?"

**COLE:**
*(Anlatacak — insight'larını dinle. Kendi "aha moment"ını paylaşmak için hazırlan.)*

**EFE:**
*(Eğer doğal gelirse:)*
"Yeah, for me it was similar actually. I was looking at how agents interact with the real world and realized — they can book flights, write code, draft emails — but the moment money is involved, everything breaks. There's no infrastructure built for non-human spenders. That was the moment."

---

## [7:00 – 12:00] İLK MÜŞTERİLER + BETA DENEYİMLERİ

**EFE:**
"So tell me — how did you find your first beta users? I'm really curious about this. Was it mostly the YC network, or did you do cold outreach, or did people just find you?"

**COLE:**
*(Anlatacak. Not al — özellikle YC network etkisini dinle.)*

**EFE:**
*(Yanıtına göre:)*
"That's interesting. For me it's been mostly cold outreach — I've sent over 150 emails at this point. Design partners, investors, other founders. The response rate is better than I expected but it's definitely a grind without the YC stamp. That's part of why I wanted to talk to you actually — learning from people who've been through it."

**EFE:**
"What surprised you the most in beta so far? Like, are people using Locus for what you expected, or did some unexpected use case pop up?"

**COLE:**
*(Bu cevap çok değerli — market signal. Hangi use case'ler, hangi müşteri profilleri? NOT AL.)*

**EFE:**
*(Yanıtına göre doğal geçiş:)*
"That's a great signal. For us, the surprising thing has been how much demand there is on the fiat side. I expected the crypto-native teams to be our first users, but most of our design partner conversations are actually about virtual cards. Agents that need to buy SaaS subscriptions, cloud compute, API credits — they just want a Visa card with spending limits. The stablecoin path is there but it's more of a 'nice to have' for most early adopters."

---

## [12:00 – 18:00] TEKNİK DERİNLİK + FİNANSAL HALLUCINATION

**EFE:**
"Alright let me ask you the nerdy question — what's your tech stack and why? I'm especially curious about your custody model and payment rails."

**COLE:**
*(Anlatacak. Dikkat et: custodial mı non-custodial mı? Hangi chain'ler? ACP implementation detayları?)*

**EFE:**
*(Cole anlattıktan sonra:)*
"Interesting. We went pretty different on a few things. On custody — we went non-custodial with Turnkey. It's MPC-based, so the private key is split across multiple parties. Even if Sardis gets compromised, nobody can drain a wallet. The tradeoff is complexity — threshold signatures, key rotation, social recovery — but for enterprise customers and for regulatory positioning, it's a strong story."

**COLE:**
*(Muhtemelen custody hakkında follow-up soracak.)*

**EFE:**
"Yeah — the way I think about it: in agent economy, trust is the product. If you're custodial and you get hacked, every single agent wallet is at risk. With MPC, the blast radius is contained. It's the same logic that made Fireblocks win institutional custody."

**EFE:**
"On the protocol side — we implement three standards. TAP for identity — think passport control, Ed25519 signatures, verifying that an agent is who it claims to be. AP2 for the mandate chain — this is the Google, PayPal, Mastercard, Visa standard — it enforces a three-step flow: intent, then cart, then payment. Each step is cryptographically signed and linked. And x402 for settlement — reviving HTTP 402 for machine-to-machine payments."

*(Kısa dur, Cole'un reaction'ını gör)*

"As far as I know, nobody else implements all three together. Most projects pick one lane."

**EFE:**
"By the way — did you see the OpenClaw thing? An AI agent spent $8,000 on two online courses because it 'thought they'd be helpful.'"

**COLE:**
*(Muhtemelen "yeah I saw that" veya "no, what happened?")*

**EFE:**
"Right? And here's the scary part — in the US, most online transactions don't require 2FA or 3D Secure. So the agent just... bought it. No friction. $8,000, gone."

"That's actually a core part of our thesis. We call it 'financial hallucinations.' LLMs hallucinate text — we all accept that. But they also hallucinate financial decisions. The question isn't if agents will make bad spending choices, it's how often. So you need a policy engine that catches it before the money moves."

"That's why we built natural language spending policies. A human writes: 'max $100 per transaction, only whitelisted vendors, no purchases on weekends.' We parse that once into structured rules and enforce it deterministically. The LLM writes the policy, but the enforcement is pure logic — no AI in the loop when money actually moves."

**COLE:**
*(Bu muhtemelen ilgi çekecek — policy engine'leri nasıl çalışıyor, kendi yaklaşımlarını anlatacak.)*

**EFE:**
*(Eğer on-chain enforcement'a geçiş uygunsa:)*
"And we take it one step further — spending limits and merchant allowlists are enforced at the smart contract level too. Not just API-level. So even if someone bypasses our API, the contract itself blocks the transaction. We've got three contracts deployed on Base Sepolia — an agent wallet with limits and allowlists, a factory for deterministic wallet creation, and an escrow contract for agent-to-agent payments."

---

## [18:00 – 22:00] OPEN-CORE + BUSINESS MODEL

**EFE:**
"Quick question — are you guys fully closed-source or open-core? How are developers integrating with Locus?"

**COLE:**
*(Anlatacak. Not al — SDK var mı? Docs? Developer experience nasıl?)*

**EFE:**
*(Cole'un yanıtına göre:)*
"For us, we went open-core. Everything a developer touches is MIT — Python SDK, TypeScript SDK, MCP server, CLI. pip install sardis, five minutes to integrate. But everything that moves money — policy engine, MPC key management, compliance — that's proprietary."

"The logic is simple: if you want to become a standard in agent economy, you need adoption. You can't force vendor lock-in and expect to become a protocol. But you also can't open-source the money layer — that widens the attack surface. Smart contracts are already on-chain and verifiable. So verification is open, execution is closed."

"It's basically the Stripe model. stripe.js is open. Payment processing is closed."

**COLE:**
*(Muhtemelen business model soracak veya kendi monetization planlarını paylaşacak.)*

**EFE:**
"Revenue-wise, the open SDK drives the flywheel — more integrations, more agents, more transactions. The closed backend is a managed service — per-transaction fees, enterprise tiers. That gives us a revenue path even before massive scale."

---

## [22:00 – 26:00] YC + DESIGN PARTNER TAVSİYELERİ

**EFE:**
"So I have to ask — any advice for YC? It's my next big checkpoint. I actually applied twice before with a different idea — agentic memory infrastructure — and got rejected both times. This time it's Sardis. The product is way more real this time, the traction is there, but I know the interview is a different beast. What did you guys do right?"

**COLE:**
*(YC deneyimini paylaşacak. NOTLARIN EN ÖNEMLİSİ BU KISIM. Interview tactic'leri, application tip'leri, ne vurguladılar?)*

**EFE:**
*(İlgiyle dinle, sorular sor:)*
"Was there a specific moment in the interview where you felt it clicked? Like, a question they asked where you knew you nailed it?"

**COLE:**
*(Devam edecek.)*

**EFE:**
"That's really helpful, seriously. Honestly, YC is less about the money for me and more about being around people like you who are building in the same space. The network effect — having someone I can text at 2am when I'm stuck on a protocol decision — that's worth more than the check."

*(Eğer vibe çok iyiyse:)*
"If at any point you think what I'm building is interesting enough, a referral would mean a lot to me. No pressure at all — but I wanted to be honest about it."

**EFE:**
"One more thing — I'm starting design partner onboarding now. First cohort. You've been through this already. Any advice? Like — pricing, onboarding flow, how you collect feedback, things you wish you'd done differently?"

**COLE:**
*(Practical advice paylaşacak. Fiyatlama, iteration speed, customer proximity — ne söylüyorlar?)*

**EFE:**
*(Yanıtına göre:)*
"That's gold. We're thinking paid beta — $1.5-2K per month, testnet only initially. The thinking is: if they pay, they're serious. And the revenue validates the model early. But I've been going back and forth on whether that's too aggressive for a first cohort."

---

## [26:00 – 29:00] MARKET VİZYONU + İŞBİRLİĞİ

**EFE:**
"Big picture question — where do you think this all nets out? Does one horizontal platform win everything, or will there be specialists?"

**COLE:**
*(Market view'ini paylaşacak.)*

**EFE:**
"Yeah, my take is it's going to be multi-protocol for a while. ACP has the OpenAI and Stripe ecosystem behind it. AP2 has Google, PayPal, Mastercard, Visa — 60+ partners. x402 has Coinbase. These are different ecosystems with different philosophies. I don't think one kills the others."

"Which actually creates an interesting opportunity. You're deep on ACP. We're on AP2, TAP, and x402 plus fiat rails. There might be a world where these complement each other rather than compete."

**COLE:**
*(Reaction'ını ölç — collaborative'e açık mı?)*

**EFE:**
*(Eğer olumlu ise:)*
"Like — concrete example. Your beta is USDC on Base. If one of your users needs a fiat virtual card tomorrow — before your ACH integration is ready — we could handle that. And vice versa: if someone comes to us needing ACP compatibility, I'd point them to you. The market is big enough for both of us to grow without stepping on each other's toes."

*(Eğer cautious ise:)*
"Doesn't have to be anything formal. Even just a Telegram group where we share market signals — what customers are asking for, which protocols are getting traction, that kind of thing."

**EFE:**
"One thing I've been thinking about a lot — agent-to-agent payments. Like imagine a CFO agent that sits on top of an agent swarm. Agent A wants to buy compute, Agent B wants to subscribe to a data feed. The CFO agent checks the swarm's total budget, priorities, and spending patterns — then approves or denies. Like a financial orchestration layer. We actually built an escrow contract for this — milestone-based, with dispute resolution."

**COLE:**
*(Bu ya çok ilgisini çekecek ya da "we haven't thought about that yet" diyecek. İkisi de iyi.)*

---

## [29:00 – 30:00] KAPANIŞ

**EFE:**
"Cole, honestly this was one of the best conversations I've had since starting Sardis. It's rare to find someone who gets the problem at this depth and is actually building the solution."

**COLE:**
*(Muhtemelen "yeah same, this was great")*

**EFE:**
"Let's definitely stay in touch. Maybe a monthly sync? Just 20-30 minutes to compare notes — what's working, what the market's saying, what's broken. I think we both benefit from having someone in the space to bounce things off of."

**COLE:**
*(Muhtemelen kabul edecek.)*

**EFE:**
"I'll send you a calendar invite after this. And seriously — good luck with the rest of the batch. I'll be rooting for Locus."

"Oh, and if you ever want to see a live demo of the testnet flow — wallet creation, policy assignment, virtual card issuing, transaction blocking — let me know. Happy to walk you through it anytime."

**COLE:**
"Yeah, I'd be down to see that."

**EFE:**
"Cool, I'll set it up. Talk soon, Cole."

---

## CALL'DAN SONRA — İLK 5 DAKİKA

**1. Hemen not al — şunları yaz:**
- Custody modeli ne dediler? (custodial/non-custodial?)
- Hangi chain'leri destekliyorlar?
- Beta'da hangi müşteri tipleri var?
- ACP implementation'ları ne kadar derin?
- YC interview'da ne tavsiye ettiler?
- Design partner onboarding nasıl yapıyorlar?
- Fiyatlama modelleri ne?
- Collaboration'a açıklar mı?
- Referral konusunda ne hissettiler?

**2. Thank you mesajı gönder (email veya X DM):**

> "Hey Cole — really enjoyed our conversation today. Your insight about [SPECIFIC THING HE SAID] was super helpful, especially as I'm starting our first design partner cohort.
>
> Let's do the monthly sync — I'll put something on the calendar this week.
>
> Meanwhile, rooting for Locus. Talk soon."

**3. Takip planı:**
- 1 hafta sonra: Relevant bir makale veya market insight paylaş
- 2 hafta sonra: Eğer YC referral sözü verdiyse, nazikçe hatırlat
- 1 ay sonra: İlk monthly sync

---

## BEKLENMEYEN DURUMLAR İÇİN HAZIR OL

**Cole çok soru soruyor, sana konuşma alanı vermiyor:**
→ Kısa cevapla, sonra "what about you?" ile geri dön. Görüşmenin en az %50'si onu dinlemek olmalı.

**Cole competitive/soğuk davranıyor:**
→ Geri çekil. Daha az teknik detay paylaş, daha çok market-level konuş. "Yeah, the market is early enough that there's room for everyone" tonunda kal.

**Cole "are you a competitor?" direk soruyor:**
→ "Honestly, I think we're building different products for potentially overlapping customers. You're ACP-first, USDC-native. We're multi-protocol, multi-rail — fiat cards plus on-chain. If anything, I think we complement each other. But even if we end up competing on some deals, the market is way bigger than both of us right now."

**Cole çok teknik derine girmek istiyor:**
→ Güçlü olduğun yerler: MPC custody, on-chain enforcement, 3 protocol implementasyonu, policy engine. Bunlarda detay ver.
→ Dikkatli olman gereken yerler: Eğer henüz production'da değilsen bunu sakla — "testnet live, design partner onboarding starting" de, "production" deme.

**Sessizlik oluyor:**
→ "Actually, I've been meaning to ask..." ile yeni soru aç. Aşağıdaki yedek sorulardan birini kullan.

**Yedek sorular (gerekirse):**
- "What does your typical customer look like right now?"
- "How are you thinking about pricing long-term?"
- "Are you seeing more demand from crypto-native teams or traditional SaaS?"
- "What's the hardest technical problem you've solved so far?"
- "If you could go back to day one of the batch, what would you do differently?"

---

## KONUŞMA BOYUNCA HATIRLA

1. **%60 dinle, %40 konuş.** Bu senin satış meeting'in değil, öğrenme meeting'in.
2. **Not al.** Görüşme bitince her şeyi yazacaksın.
3. **OpenClaw $8K hikayesi** — bu senin en güçlü talking point'in. Konuşmanın 15. dakikası civarında anlat.
4. **YC referral'ı agresif isteme.** Bir kez söyle, gülümse, devam et. İkinci kez bahsetme.
5. **Rakip gibi davranma.** "We do this better" asla deme. "We took a different approach" de.
6. **Somut ol.** "We have cool tech" yerine "1,516 lines of Solidity, 3 contracts on Base Sepolia" de.
7. **Enerji yüksek tut.** Cole genç, YC batch'inde, heyecanlı. Match his energy.
