# Locus Call Prep — 30 Dakika
## Cole Dermott ile Görüşme

**Tarih:** Bugün
**Süre:** 30 dakika
**Hedef:** Builder-to-builder. Öğren, paylaş, bağlantı kur. Rakip koklaşması değil.

---

## LOCUS HAKKINDA

**Ne yapıyorlar:** AI agent'lar için ödeme altyapısı. Governance layer — spending policies, audit trail, reconciliation.
**Founders:** Cole Dermott (UWaterloo 3. sınıf, Coinbase B2B payments stajı) + Eliot Lee (Scale AI)
**Tech:** USDC on Base (aktif), ACH/Wire (coming soon), ACP reference impl, MCP server, Node.js/TS
**Custody:** Muhtemelen custodial — hiçbir yerde "non-custodial" demiyorlar
**Stage:** YC F25, closed beta, $10 USDC trial credit

---

## SARDİS vs LOCUS (Özet)

| | Sardis | Locus |
|---|--------|-------|
| **Custody** | Non-custodial (MPC/Turnkey) | Muhtemelen custodial |
| **Fiat** | Virtual cards (Lithic) — CANLI | ACH/Wire — coming soon |
| **Crypto** | Multi-chain (5 EVM chain) | Sadece Base |
| **Protocols** | AP2 + TAP + x402 (üçü birden) | ACP (OpenAI/Stripe) |
| **On-chain** | Solidity contracts (1,516 lines) | Muhtemelen API-level |
| **Policy** | Natural language → deterministic | Structured |
| **KYC/AML** | Persona + Elliptic, fail-closed | Yok |
| **Licensing** | Open-core (MIT SDK) | Bilinmiyor |
| **Codebase** | 19 packages, 77+ tests | Bilinmiyor |

*(Detaylı karşılaştırma tablosu aşağıda "Teknik Cheat Sheet" bölümünde)*

---

## 30 DAKİKA — KONUŞMA AKIŞI

---

### [0:00 - 3:00] AÇILIŞ

**Sen:**
> "Hey Cole, thanks for taking the time. Really glad we could connect — I've been following what you guys are building, especially the ACP reference implementation. We're clearly both obsessed with the same problem from different angles."

**Kısa tanıtım (30 sn, casual):**
> "Quick background on me — I'm Efe, building Sardis from Istanbul. Payment OS for AI agents. We use Turnkey for MPC wallets — non-custodial — Lithic for virtual card issuing, natural language spending policies, and we have an MCP server with 36 tools. Both fiat and on-chain rails."

**Geçiş — hemen ona ver:**
> "But honestly I'm super curious about your journey. How did you and Eliot find each other?"

---

### [3:00 - 12:00] ONLARI DİNLE — Founder Journey + Learnings

Bu kısım görüşmenin kalbi. Samimi sorular sor, ilgiyle dinle.

**Soru 1 — Co-founder story:**
> "How did you and Eliot find each other as co-founders? That Coinbase + Scale AI combo makes a lot of sense for this space."

*Neden önemli: Co-founder dinamiklerini anlamak, sen solo founder'sın — bu hikayeden öğreneceklerin var.*

**Soru 2 — Idea origin:**
> "Where did the agent payments idea come from? Was it something you saw at Coinbase, or did it click when you guys came together?"

*Neden önemli: Onların "aha moment"ını öğren. Seninle aynı insight mı, farklı bir açı mı?*

**Soru 3 — First customers:**
> "How did you find your first beta users? What actually worked — was it the YC network, cold outreach, or something else?"

*Neden önemli: Sen 150+ cold email attın. Onlar nasıl yaptı? YC network advantage'ı ne kadar fark yarattı?*

**Soru 4 — Beta surprises:**
> "What's surprised you the most in beta? Like, are people using it for what you expected, or did some unexpected use case show up?"

*Neden önemli: Market signal. Senin ICP assumption'ların doğru mu?*

---

### [12:00 - 18:00] TECH DEEP DIVE — Karşılıklı Paylaşım

Burada doğal olarak "so what are you guys using for X" tarzı karşılıklı teknik tartışma olacak.

**Soru 5 — Tech stack:**
> "What's your tech stack and why? I'm curious about the architecture decisions — especially around custody and payment rails."

*Dinle, sonra paylaş:*

> "Interesting. We went a different direction on a few things. For custody, we chose Turnkey for MPC — the key is split across multiple parties, so even if Sardis gets compromised, nobody can drain wallets. The tradeoff is complexity, but for enterprise it's a strong security story."

> "For fiat, we integrated Lithic for virtual card issuing — an agent gets a one-time Visa card, makes a purchase, card expires. It's live now. Most of our design partner conversations are actually about the fiat path."

**Financial hallucination angle (SENİN KİLLER İNSİGHT):**
> "By the way — did you see the OpenClaw thing last week? An AI agent spent $8,000 on two online courses because it 'thought they'd be helpful.' In the US, most transactions don't even need 2FA or 3D Secure. That's terrifying."

> "That's actually a huge part of our thesis. Financial hallucinations. Agents WILL make bad spending decisions. The question isn't if, it's how often. So you need a policy engine that catches it before the money moves. Natural language policies — 'max $100 per transaction, only whitelisted vendors' — parsed once, enforced deterministically."

*Neden önemli: Bu real-world example (OpenClaw $8K) çok güçlü bir talking point. Tüm görüşmenin en akılda kalıcı anı bu olabilir.*

**A2A vision (eğer doğal gelirse):**
> "One thing we're exploring is agent-to-agent payments — like a CFO agent that orchestrates spending across an agent swarm. Agent A wants to buy something, asks the CFO agent, CFO checks the swarm's budget and priorities, approves or denies. Like a financial orchestration layer on top of the wallets."

---

### [18:00 - 24:00] YC + ADVICE + DESIGN PARTNERS

**Soru 6 — Design partner advice:**
> "I'm starting my design partner onboarding process now — about to bring on the first cohort. You've been through this. Any advice? What worked, what didn't?"

*Neden önemli: Practical advice. Fiyatlama, onboarding flow, feedback loops — ne öğrendiler?*

**Soru 7 — YC advice (samimi ol):**
> "I have to ask — any advice for YC? It's my next big checkpoint. I applied before with a different idea — agentic memory infrastructure — got rejected twice. This time it's Sardis. What did you guys do right in the application or interview?"

*Neden önemli: YC'ye gerçekten girmek istiyorsun. Cole'dan birinci elden deneyim al. Ayrıca bu soru "I respect what you've achieved" mesajı veriyor.*

**Follow-up eğer vibe iyiyse:**
> "Honestly, YC is less about the money for me and more about being around people like you who are building in the same space. If at any point you think Sardis is doing something interesting, a referral would mean a lot. No pressure at all."

---

### [24:00 - 28:00] COLLABORATION + MARKET

**Market view:**
> "Where do you think this all nets out? One horizontal platform wins, or there'll be specialists?"

**Complementary framing:**
> "The way I see it — ACP, AP2, x402... there'll be multiple standards. You're deep on ACP with the OpenAI/Stripe ecosystem. We're more on the AP2/TAP side plus fiat rails. There might be a world where these integrate rather than compete."

**Concrete collaboration ideas (eğer receptive ise):**
> "Like — your beta is USDC on Base. If one of your users needs fiat virtual cards before ACH is ready, we could be a partner for that. And vice versa — if someone comes to us needing ACP compatibility, I'd send them your way."

---

### [28:00 - 30:00] KAPANIŞ

> "Cole, this was genuinely one of the best conversations I've had since starting Sardis. It's rare to talk to someone who actually gets the problem at this depth."

**Next step:**
> "Let's stay in touch. Maybe a monthly sync to compare notes — what's working, what the market's telling us. I think we both benefit from having someone in the space to bounce ideas off of."

> "And seriously — good luck with the rest of the batch. I'll be following Locus's journey."

---

## TEKNİK CHEAT SHEET — Görüşmede Referans İçin

Bu bölümü görüşme sırasında hızlıca göz atmak için kullan. Cole teknik detay sorarsa veya sen anlatırken, burada her şey hazır.

---

### Sardis Mimari — 30 Saniyede Anlatım

> "Let me walk you through our stack quickly. At the top, we have SDKs — Python, TypeScript, and an MCP server. These talk to our FastAPI backend which has 21 router modules — wallets, payments, policies, cards, compliance, ledger, everything. Below that, three layers: protocol layer handling AP2/TAP/x402, a chain executor for multi-chain EVM, and a compliance engine with Persona KYC and Elliptic sanctions. At the bottom, Solidity smart contracts on Base Sepolia — 1,516 lines — and Turnkey MPC for non-custodial custody."

Eğer "that's a lot for a solo founder" derse:
> "Yeah, 19 packages, 77+ test files, 15,752 lines of test code. I'm not sleeping much. But the moat is real — you can't build this stack in a weekend."

---

### 3 Protokol — Hızlı Açıklama (Cole Sorarsa)

Eğer "which protocols do you support?" veya "what's AP2?" derse:

> "We implement three protocols — think of them as layers:
>
> **TAP** is the identity layer. Think passport control. When an agent sends a payment request, TAP verifies its identity cryptographically — Ed25519 signatures, nonce replay protection, 8-minute timestamp window. It answers: 'Is this agent who it claims to be?'
>
> **AP2** is the mandate layer. Think customs declaration. It enforces a three-step chain: intent → cart → payment. Each step is cryptographically signed and linked. An agent can't just say 'send 1000 USDC' — it has to declare intent, build a cart, then get payment approval. This is the Google/PayPal/Mastercard/Visa standard.
>
> **x402** is the settlement layer. Think cash register. It revives HTTP 402 — the forgotten status code — for machine-to-machine payments. Agent hits an API, gets a 402 challenge, signs a payment, gets the resource. Payment happens within the HTTP request-response cycle.
>
> As far as I know, nobody else implements all three. Most do just identity OR just settlement."

Locus'a sor:
> "Which protocol standards are you guys implementing? Are you doing AP2 mandate chain verification, or is it more API-level enforcement?"

---

### Open-Core — Neden Böyle Yaptığımızı Anlatma

Bu konu çıkarsa (developer adoption, business model, veya "are you open source?" sorusu gelirse):

**Kısa versiyon (15 saniye):**
> "We're open-core. Everything a developer touches — Python SDK, TypeScript SDK, MCP server, CLI — is MIT licensed. Everything that moves money — policy engine, MPC key management, compliance — is proprietary. Think Stripe: stripe.js is open, payment processing is closed."

**Uzun versiyon — 3 açı (eğer ilgilenirse):**

1. **Developer adoption:**
> "If you want to be a standard in agent economy, you need adoption. pip install sardis, 5 minutes to integrate. You can't force vendor lock-in and expect to become a protocol."

2. **Security:**
> "But you can't open-source the money layer. Policy engine, MPC signing, compliance — opening those widens the attack surface. Smart contracts are already on-chain and verified. So verification is open, execution is closed."

3. **Business model:**
> "Open SDK drives the flywheel — more integrations, more agents, more transactions. Closed backend is the managed service — that's where revenue comes from. Per-transaction fees, enterprise tiers."

Locus'a sor:
> "Are you guys fully closed-source or open-core? How are developers integrating?"

---

### Karşılaştırma Tablosu — Sardis vs Locus (Genişletilmiş)

| Alan | Sardis | Locus |
|------|--------|-------|
| **Custody** | Non-custodial (Turnkey MPC) | Muhtemelen custodial |
| **Fiat** | Virtual cards (Lithic) — CANLI | ACH/Wire — coming soon |
| **Crypto** | 5 EVM chain (Base, Polygon, ETH, Arbitrum, Optimism) | Sadece Base |
| **Stablecoins** | USDC, USDT, EURC, PYUSD | USDC |
| **Protocols** | AP2 + TAP + x402 (üçü birden) | ACP (OpenAI/Stripe) |
| **On-chain enforcement** | Solidity contracts (1,516 lines) | Muhtemelen API-level |
| **Policy** | Natural language → deterministic | Structured |
| **KYC/AML** | Persona + Elliptic, fail-closed | Yok |
| **Smart contracts** | Factory + Wallet + Escrow | Bilinmiyor |
| **SDK** | Python + TypeScript + CLI (MIT) | Bilinmiyor |
| **MCP Server** | 36 tools | Var (boyutu bilinmiyor) |
| **Licensing** | Open-core (MIT SDK, proprietary backend) | Bilinmiyor |
| **Codebase** | 19 packages, 77+ test files | Bilinmiyor |

---

### Codebase Metrikleri — İmpressive Stat'ler

Cole'un "what have you built so far?" sorusuna:

> "19 packages — 14 Python, 4 TypeScript, 1 mixed. 3 smart contracts with 1,516 lines of Solidity. 21 FastAPI router modules. 77+ test files with 15,752 lines of test code. 3 protocol implementations — TAP, AP2, x402. 6 external service integrations live, 3 more interface-ready."

---

### Demo Kartları — Gösterebileceklerin

Eğer "can you show me?" derse:

1. **sardis.sh/demo** — Simulated + live mode
2. **Base Sepolia** — Gerçek USDC transfer, TAP-signed, policy-enforced
3. **Dashboard wizard** — Wallet oluştur → policy ata → kart bas → ödeme → block
4. **Smart contracts** — Testnet'te deploy edilmiş factory + wallet + escrow

> "I can show you a live testnet transaction right now if you want — wallet creation, policy assignment, payment, policy block. Takes about 2 minutes."

---

### Ödeme Akışı — 7 Adım (Teknik Tartışmada Kullan)

Eğer "how does a payment actually work?" derse:

> "Seven steps. TAP verifies agent identity — Ed25519 signature, nonce check. AP2 validates the mandate chain — intent, cart, payment, all cryptographically linked. Policy engine evaluates natural language rules — 'max $100, only cloud providers.' Compliance runs KYC and sanctions checks — fail-closed by default. On-chain enforcement checks spending limits and merchant allowlists in the Solidity contract. Chain executor does gas estimation, tx simulation, multi-RPC with failover. Finally, ledger entry with append-only Merkle receipt."

> "The whole thing is designed so that financial hallucinations get caught at step 3, 4, or 5 — before money moves. That OpenClaw $8,000 thing? Would've been blocked at the policy engine."

---

## HAZIR OL — SORULACAK OLASI SORULAR VE YANITLAR

**"Are you worried about being a solo founder?"**
> "Not really. Speed is my advantage right now — zero coordination overhead. I can ship a feature at 2am and it's live by morning. The bandwidth tradeoff is real, but at pre-seed, velocity matters more than headcount. And honestly, talking to people like you helps with the loneliness part."

**"Why non-custodial? Seems harder."**
> "It is harder. But the OpenClaw $8K incident is exactly why it matters. If we're custodial and we get hacked, every agent wallet is drained. With MPC, the key is split — no single party holds the full key. Enterprise CISOs need that story. It's the same reason Fireblocks won institutional custody."

**"Why not just build on ACP?"**
> "We probably will support ACP. But the market will be multi-protocol — ACP for OpenAI/Stripe, AP2 for Google's 60+ partners, x402 for Coinbase. We're building protocol-agnostic. The wallet and policy layer shouldn't care which commerce protocol the agent uses."

**"What's your tech stack exactly?"**
> "Turnkey for MPC wallet creation — their threshold signature architecture. Lithic for virtual card issuing — Visa/Mastercard rails. Persona for KYC, Elliptic for AML. On-ramp and off-ramp to bridge between fiat and stablecoins. Natural language policy engine that parses rules from plain English and enforces them deterministically. MCP server with 36 tools. Python + TypeScript SDKs."

**"Why Istanbul?"**
> "It's where I am. Low burn rate, good timezone overlap with Europe and partially US East Coast. Company will be Delaware C-corp. The compliance stack is all US — Persona, Lithic, Elliptic. Istanbul is where I code, not where the entity lives."

**"What traction do you have?"**
> "150+ cold outreach to design partners and investors. Testnet live with full stack end-to-end. Starting design partner onboarding now — paid beta, $1.5-2K/month, testnet only. Raising $1.5-2M pre-seed."

**"Have you talked to Skyfire / Payman?"**
> "Yeah, I know the landscape well. Skyfire raised $9.5M, Payman raised $13.8M. Both custodial. My thesis is that non-custodial wins long-term, especially for enterprise. When your agent handles $50K/day, 'trust us with the keys' isn't a pitch that works."

---

## CALL'DAN SONRA — 5 DAKİKA İÇİNDE

1. **Thank you mesajı (email veya X DM):**
   > "Really enjoyed the conversation, Cole. Your insight about [specific thing] was super helpful. Let's do the monthly sync — I'll put something on the calendar. Meanwhile, rooting for Locus."

2. **Not al:** Her şeyi yaz — custody modeli, ACP adoption, beta learnings, YC advice, customer profili

3. **Eğer YC referral sözü verdiyse:** 1 hafta sonra nazikçe hatırlat

4. **1 hafta sonra:** Relevant bir makale veya insight paylaş — ilişkiyi sıcak tut

---

## SON NOTLAR

**Bu görüşme satış değil, ilişki kurma.** Cole UWaterloo 3. sınıf, senin yaşına yakın, aynı problemle obsess. Bu bir peer conversation — ikisi de early stage, ikisi de öğreniyor.

**En güçlü anlar:**
1. OpenClaw $8K hikayesi — financial hallucination thesis'ini somutlaştırıyor
2. Virtual cards (Lithic) live — somut bir avantaj, demo edilebilir
3. A2A / CFO agent vision — forward-thinking, onları düşündürür
4. YC advice sorusu — saygı gösterir, gerçek değer alırsın

**Kural: Rakip gibi davranma. Ally gibi davran. Market herkes için yeterince büyük.**
