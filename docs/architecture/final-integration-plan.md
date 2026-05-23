# Sardis — Final Integration Architecture v2
## Pre-Seed Partner Stack & Implementation Plan

**Date:** 2026-02-28
**Stage:** Pre-Seed → $6M Seed
**Estimated Monthly Cost:** $0–$199 (excluding transaction fees)
**Primary Infrastructure Partner:** Stripe (fiat rail) + Turnkey (crypto rail)

---

## Architecture Overview

```
                          SARDIS PAYMENT OS
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
  │  │  IDENTITY     │  │  POLICY       │  │  LEDGER         │  │
  │  │  ERC-8004     │  │  ENGINE       │  │  sardis-ledger  │  │
  │  │  FIDES DIDs   │  │  NL → Rules   │  │  Merkle proofs  │  │
  │  │  Stripe ID    │  │  Real-time    │  │  Hash chain     │  │
  │  └──────┬────────┘  └──────┬────────┘  └────────┬────────┘  │
  │         │                  │                     │           │
  │  ┌──────┴──────────────────┴─────────────────────┴────────┐  │
  │  │               SARDIS CORE ENGINE                       │  │
  │  │   Wallet Mgmt / Tx Orchestration / Events / Webhooks    │  │
  │  └──┬──────────┬──────────┬──────────┬──────────┬─────────┘  │
  │     │          │          │          │          │            │
  └─────┼──────────┼──────────┼──────────┼──────────┼────────────┘
        │          │          │          │          │
   ═══ FIAT RAIL ═══════    ══ CRYPTO RAIL ═══   ══ PROTOCOLS ══
        │          │          │          │          │
  ┌─────┴────┐ ┌───┴──────┐ ┌┴────────┐ ┌┴───────┐ ┌┴──────────┐
  │ STRIPE   │ │ STRIPE   │ │ TURNKEY │ │ ON-    │ │ x402     │
  │ ISSUING  │ │ TREASURY │ │ MPC     │ │ CHAIN  │ │ ACP      │
  │ Cards    │ │ FA/ACH   │ │ Wallets │ │ USDC   │ │ AP2      │
  │ Auth     │ │ Wire     │ │ ZeroDev │ │ Bridge │ │ ERC-8004 │
  │ SPT/ACP  │ │ Payouts  │ │ Pimlico │ │ CCTP   │ │          │
  └──────────┘ └──────────┘ └─────────┘ └────────┘ └──────────┘
```

**Dual-Rail Architecture:** Her işlem fiat veya crypto rail'den geçer. Sardis policy engine her iki rail'de de enforcement noktasıdır.

---

## Layer 1: Key Management & Wallets (Crypto Rail)

### Primary: Turnkey (CURRENT — KEEP)
- **Role:** TEE-based key management, MPC signing
- **Pricing:** Free (100 wallets, 25 tx/mo) → Pro $99/mo ($0.01/sig)
- **Why keep:** Already integrated, fastest signing (50-100ms), Coinbase veteran team
- **Status:** LIVE

### Smart Accounts: ZeroDev (ADD)
- **Role:** ERC-4337 Kernel smart accounts on top of Turnkey keys
- **Features:** Session keys (delegated agent signing with spending limits), ERC-7579 modular plugins
- **Pricing:** Free testnet, mainnet gas + fees
- **Why:** Session keys = per-agent spending limits enforced at smart contract level
- **Status:** TO INTEGRATE
- **Priority:** HIGH

### Gas Abstraction: Pimlico (ADD)
- **Role:** Bundler + ERC-20 Paymaster
- **Features:** Agents pay gas in USDC instead of ETH
- **Pricing:** 10% surcharge on gas cost
- **Status:** TO INTEGRATE
- **Priority:** MEDIUM

### Alternative: Coinbase CDP
- **Pricing:** $0.005/wallet operation, 5K ops/mo free
- **Action:** Apply for Builder Grant ($30K) regardless

---

## Layer 2: Card Issuing & Fiat Spending (Fiat Rail)

### Stripe Issuing (PRIMARY)
- **Role:** Virtual & physical Visa/Mastercard cards for agent spending
- **Pricing:** $0.10/virtual card, $3.50/physical, 0.2% + $0.20/tx (first $500K waived)
- **Revenue:** Interchange revenue share (negotiated)
- **Requirements:** No minimum revenue/investment. Use case approval 3-6 weeks.
- **Card limits:** 20 virtual per cardholder, 100 per account

**Spending Controls (Sardis policy engine compiles NL rules to these):**

| Control | Detail |
|---------|--------|
| **Amount limits** | `per_authorization`, `daily`, `weekly`, `monthly`, `yearly`, `all_time` |
| **MCC whitelist** | `allowed_categories` — only these MCCs permitted |
| **MCC blacklist** | `blocked_categories` — these MCCs denied |
| **Country whitelist** | `allowed_merchant_countries` |
| **Country blacklist** | `blocked_merchant_countries` |
| **Hard cap** | $10,000 per authorization (unconfigurable) |
| **Default** | $500/day on new cards (overridable) |
| **Aggregation delay** | Up to 30 seconds between limit checks |

**Real-Time Authorization (Policy Engine Integration Point):**
```
Agent uses card → Stripe sends issuing_authorization.request webhook
    → Sardis has 2 SECONDS to respond
    → Policy engine evaluates: amount, MCC, merchant, country, NL rules
    → Response: { approved: true/false, amount: partial_ok?, metadata: audit_trail }
    → Timeout fallback: configurable (auto-approve or auto-decline)
```

Available data in webhook: `pending_request.amount`, `currency`, `merchant_data` (name, MCC, city, country), `card`, `cardholder`, `is_amount_controllable` (partial approval).

**Digital Wallet Support (PAN'sız Ödeme):**

| Wallet | Manual Provisioning | Push Provisioning | In-Store NFC |
|--------|-------------------|-------------------|-------------|
| Apple Pay | ✅ (OTP verify) | ✅ (entitlement gerekli) | ✅ |
| Google Pay | ✅ (no extra steps) | ✅ (allowlist gerekli) | ✅ |
| Samsung Pay | ✅ | ❌ (Stripe desteklemiyor) | ✅ |

Push provisioning gereksinimleri:
- iOS: `com.apple.developer.payment-pass-provisioning` entitlement (1-2 hafta Apple onayı)
- Android: Google Pay push provisioning allowlist + TapAndPay SDK v18+
- Backend: Ephemeral key endpoint (15 dakika TTL)
- React Native: `<AddToWalletButton />` component hazır

**PCI Scope = SIFIR (Issuing Elements kullanarak):**
- PAN Sardis sunucusuna hiç gelmiyor — Stripe iframe'inde render
- Ephemeral key nonce + 15 dakika TTL
- Copy button, number display, CVC display, expiry display, PIN display (2FA zorunlu)

**Token Management (Cihaz Kontrolü):**
- Her dijital cüzdan token'ı API'den yönetilebilir
- `suspend` / `active` / `deleted` durumları
- `network_data`: device type, IP, trust score, account score (24 saat)
- Otomatik senkronizasyon: kart iptal → tüm token'lar iptal

**3D Secure (Agent Kartları İçin):**
- Stripe issuer olarak OTP gönderiyor (SMS veya email)
- Agent'lar için sorun: OTP'yi kim girecek?
- US'de çoğu low-value işlem 3DS gerektirmez
- Stripe Autopilot: timeout/error durumunda otomatik karar
- Çözüm: OTP'yi agent operatörüne yönlendir veya low-value exemption'a güven

**Stablecoin-Backed Issuing (Private Preview):**
```
Agent USDC Wallet (MPC) → Stripe Financial Account (USDC tutuluyor)
    → Kart kullanıldığında Bridge otomatik USDC→fiat çeviriyor
    → Merchant normal USD alıyor (standard Visa işlemi)
    → Offramp adımı ORTADAN KALKIYOR
```
- Bridge (Stripe $1.1B acquisition) otomatik dönüşüm yapıyor
- 8 chain: Arbitrum, Avalanche, Base, Ethereum, Optimism, Polygon, Solana, Stellar
- Ramp, Squads, Airtm early adopter
- Bridge OCC conditional approval (Feb 2026) — national trust bank charter

### EU Market: Wallester (DEFERRED)
- **Coverage:** 35 countries (EEA + UK + Switzerland)
- **Limitation:** CANNOT issue to US cardholders
- **Status:** Post-seed EU expansion

### Rejected
- ~~Highnote~~ — Rejected
- ~~Lithic~~ — Requires $5M+
- ~~Rain~~ — Unresponsive (retry later as backup)
- ~~Marqeta / Galileo / i2c~~ — Enterprise-focused

---

## Layer 3: Agentic Commerce Protocol (WATCH — Phase 3+)

### ACP (Agentic Commerce Protocol)
- **Co-maintainers:** OpenAI + Stripe
- **Status:** Beta, spec version 2026-01-30
- **What:** Açık standart — AI agent'ların merchant'larla alışveriş yapması için

**Protokol Akışı (4 endpoint):**
1. `Create` — Ürün seçimi, sepet oluşturma (SKU bazlı)
2. `Update` — Miktar, teslimat, müşteri bilgisi güncelleme
3. `Complete` — SharedPaymentToken ile ödeme
4. `Cancel` — İptal, envanter serbest bırakma

### Shared Payment Tokens (SPT) — Sardis İçin Şu An Gerekli DEĞİL

SPT, agent PLATFORM'lar (ChatGPT, Claude) için tasarlanmış bir ödeme primi. Sardis infrastructure provider olduğu için SPT oluşturucu değil, altında çalışan katman.

| Özellik | Virtual Card | SPT |
|---------|-------------|-----|
| Merchant kabulü | **50M+ merchant** (Visa) | Sadece ACP-enrolled (birkaç bin) |
| Amazon/Uber/SaaS | ✅ EVET | ❌ HAYIR |
| Kim oluşturur? | Sardis (infrastructure) | Agent platform (ChatGPT, Claude) |
| Credential exposure | PAN (Elements ile gizli) | Sıfır |
| Scope | Per-card, spending controls ile | Per-seller, per-transaction |

**Neden şu an gerekli değil:**
- SPT sadece ACP-enrolled merchant'larda çalışır (Etsy, Shopify, URBN, Coach) — Amazon, Uber, %99 merchant'ta çalışmaz
- Virtual card HER YERDE çalışır — Sardis'in güçlü yanı bu
- SPT, agent platform'ların işi (OpenAI, Anthropic) — Sardis infrastructure layer
- ACP merchant sayısı milyonlara ulaşırsa Phase 3-4'te ek rail olarak eklenir

**İzle:** Shopify 1M+ merchant'a ACP rollout yapıyor. Wix, WooCommerce, BigCommerce de eklenecek. Visa/Mastercard kendi agentic token standartlarını geliştiriyor. 1-2 yıl içinde SPT önemli olabilir.

### Stripe Agent Toolkit
- **Packages:** `stripe-agent-toolkit` (Python), `@stripe/agent-toolkit` (TS)
- **Frameworks:** OpenAI Agents SDK, Vercel AI SDK, LangChain, CrewAI
- **Auth:** Restricted API keys (`rk_*`) — tool availability key permissions'a bağlı
- **MCP Server:** `https://mcp.stripe.com` veya `npx @stripe/mcp@latest`

### Sardis vs Stripe Agentic Commerce

```
Stripe: Infrastructure (cards, SPT, checkout)
Sardis: Intelligence layer on top (policy, identity, audit, crypto)

Stripe eksikleri:           Sardis karşılığı:
  No NL policy engine    →    ✅ "Max $500/day, only SaaS"
  No crypto/on-chain     →    ✅ 5 EVM chains, USDC native
  No non-custodial       →    ✅ Agent-owned MPC wallets
  No agent identity      →    ✅ ERC-8004 + FIDES DIDs
  No Merkle audit trail  →    ✅ Cryptographic proofs
  Fiat only              →    ✅ Fiat + crypto dual-rail
```

---

## Layer 4: Compliance & Identity

### Stripe Baseline KYC/AML (INCLUDED with Issuing)
- **Role:** Cardholder KYC, AML, OFAC screening — handled by Stripe automatically
- **Pricing:** Included
- **Note:** Stripe manages bank relationship, regulatory compliance, BSA/AML

### Persona (CONFIRMED — PRIMARY for operator KYC)
- **Role:** Operator identity verification (the human behind the agent)
- **Pricing:** Startup program — **500 free verifications/mo**
- **Status:** READY TO INTEGRATE
- **Action:** Apply to fintech startup cohort
- **Priority:** HIGH — free and confirmed

### Stripe Identity (DEFERRED — Series A)
- **Role:** Same as Persona but single-vendor with Stripe
- **Pricing:** $1.50/verification — too expensive at pre-seed
- **Coverage:** 120+ countries, document + selfie + ID number
- **Decision:** Use Persona now (free). Re-evaluate Stripe Identity when volume justifies the cost or single-vendor simplification matters.

### ComplyAdvantage (CONFIRMED)
- **Role:** Enhanced transaction monitoring, sanctions, PEP checks
- **Pricing:** ComplyLaunch — FREE 12 months

### Elliptic (CURRENT — KEEP)
- **Role:** On-chain address sanctions screening (crypto rail specific)

### KYA: Sumsub
- **Role:** AI agent identity verification
- **Status:** Live Jan 2026

### Compliance Decision Matrix

| Check | Provider | Rail |
|-------|----------|------|
| Cardholder KYC/AML | Stripe (included) | Fiat |
| Operator identity | Persona (free 500/mo) → Stripe Identity at scale | Both |
| On-chain address screening | Elliptic | Crypto |
| Enhanced AML/PEP | ComplyAdvantage (free 12mo) | Both |
| Agent identity | ERC-8004 + Sumsub | Both |

---

## Layer 5: Stablecoin Operations & Ledger

### Ledger: sardis-ledger (BUILD — COMPETITIVE MOAT)

sardis-ledger v0.5.0 (78 tests, 1,342 lines test code):

| Feature | sardis-ledger | Formance | Modern Treasury | Stripe Transaction |
|---------|--------------|----------|-----------------|-------------------|
| Append-only immutability | ✅ | ✅ | ✅ | ✅ |
| Merkle tree proofs | ✅ | ❌ | ❌ | ❌ |
| Blockchain anchoring | ⚠️ Framework | ❌ | ❌ | ❌ |
| Hash chain audit trail | ✅ | ❌ | ❌ | ❌ |
| immudb hybrid | ✅ | ❌ | ❌ | ❌ |
| Multi-currency Decimal(38,18) | ✅ | ✅ | ✅ | ✅ |
| Batch + rollback | ✅ | ✅ | ✅ | ✅ |

**Merkle proofs + blockchain anchoring = NO external provider offers this.** This is "provable compliance" — not just "we logged it" but "here's the SHA-256 proof."

**Production needs:**
1. Chain provider implementations (connect to sardis-chain)
2. Blockchain anchoring deployment (anchor smart contract)
3. PostgreSQL as default backend
4. Load testing 1000+ concurrent accounts

### USDC Operations: Circle Programmable Wallets (EVALUATE)
- **Pricing:** 1K wallets FREE, then $0.038/wallet
- **Priority:** LOW — Turnkey handles this

---

## Layer 6: Banking & Treasury (Fiat Rail)

### Company Banking: Mercury (KEEP)
- **Role:** Sardis corporate accounts
- **Features:** 4.47% yield, FDIC up to $5M

### Customer Fund Custody: On-Chain Stablecoins (NOW)
- **Model:** Non-custodial MPC wallets, USDC/USDT on-chain
- **Legal basis:** GENIUS Act (July 2025, effective Jan 2027)
- **Decision:** Primary model. On-chain custody IS the product.

### Stripe Financial Accounts / Treasury (APPLY EARLY — no formal funding requirement)

**Resmi gelir/yatırım şartı YOK.** Gereksinimler: US-based, B2B, Custom Connect, fraud risk docs. Treasury limited public preview'da — Stripe manuel onay yapıyor, traction'lı şirketleri tercih edebilir ama bu resmi bir engel değil. Şirket açılınca başvur.

**Her agent'a kendi banka hesabı:**

| Feature | Detail |
|---------|--------|
| **What** | FDIC-insured financial account with route_registry/account numbers |
| **Bank partner** | Fifth Third Bank (FDIC pass-through up to $250K) |
| **Inbound** | ACH (2-5 days, free), Wire (same day, ~$2), Stripe Network (instant, free) |
| **Outbound** | ACH (1-2 days, free), Same-day ACH, Wire (~$2), Stripe Network (instant) |
| **Stablecoin** | USDC + USDB via Bridge on 8 chains |
| **Card funding** | Financial Account → Issuing card (native integration) |
| **Platform review** | `requires_confirmation` state — Sardis reviews before funds release |
| **Pull limits** | $50K/day, $100K/week |
| **Cost** | No account fees, no storage fees, no minimum balance |
| **Availability** | US + UK only, B2B only |

**Key API Objects:**
- `FinancialAccount` — holds funds, has route_registry/account numbers
- `InboundTransfer` — ACH pull from external bank
- `OutboundPayment` — ACH/wire push to third party
- `ReceivedCredit` — incoming ACH/wire
- `Transaction` / `TransactionEntry` — append-only history

**Risk:** "Money services business" prohibition. Get Stripe's explicit sign-off on agent payment use case before activating.

### Stripe Financial Connections (NEW — Bank Account Linking)
- **Role:** User's bank account linking for ACH funding of agent wallets
- **How:** Stripe-hosted UI → OAuth bank login → account verification → tokenize for ACH
- **Institutions:** 5,000+ US financial institutions
- **Data:** Balance checks, transaction history, ownership verification
- **Pricing:** Free when used with Stripe payments
- **Availability:** US bank accounts only
- **Sardis use:**
  - Verify operator's bank account before allowing withdrawals
  - Balance check before initiating agent funding
  - Ownership verification for KYC

### Stripe Global Payouts (NEW — Cross-Border)
- **Role:** Send funds to 50+ countries in local currency
- **Recipients:** No Stripe account needed
- **Integration:** No-code (dashboard), low-code (hosted forms), or full API
- **Sardis use:** Agent-to-contractor payments, operator withdrawals worldwide
- **When:** Series A — when international customers arrive

### Treasury Evolution Timeline

| Stage | Fiat Solution | Crypto Solution | Trigger |
|-------|--------------|-----------------|---------|
| **Pre-seed** | — | On-chain stablecoin custody | Default |
| **Seed** | Stripe Issuing (standalone funding) | + ZeroDev smart accounts | Agent virtual cards |
| **Series A** | + Stripe Financial Accounts + Financial Connections | + CCTP bridging | Enterprise fiat on-ramp demand |
| **Series B** | + Global Payouts + Modern Treasury | + Cross-chain routing | International expansion |
| **Scale** | Evaluate GENIUS Act charter | Full multi-chain | Own the banking relationship |

---

## Layer 7: On-Ramp / Off-Ramp

### Fiat → Crypto: Coinbase Onramp (PRIMARY)
- **Pricing:** ZERO FEE on all USDC
- **Chains:** Base, Polygon, Ethereum, Arbitrum, Optimism
- **Status:** Integrated (CoinbaseOnrampProvider exists)
- **Priority:** HIGH

### Fiat → Crypto: Onramper (FALLBACK)
- **Role:** Aggregator of 30+ providers
- **Pricing:** Zero added fees
- **Status:** Integrated (Onramper widget exists)

### Fiat → Agent Account: Stripe Financial Connections + ACH (SERIES A)
- **Role:** Direct bank account → Financial Account funding
- **When:** When Financial Accounts activated

### Crypto → Fiat: Stripe/Bridge (SERIES A)
- **Role:** USDC → USD automatic conversion
- **How:** Stablecoin Financial Account handles this natively

---

## Layer 8: Cross-Chain Bridges

### Circle CCTP V2 (USDC)
- **Pricing:** ZERO FEE
- **Chains:** All Sardis chains
- **Priority:** HIGH

### Across Protocol (USDT/Multi-Token)
- **Pricing:** 0.04–0.12%
- **Priority:** MEDIUM

---

## Layer 9: Protocols

### x402 (HTTP Payment Protocol)
- **Status:** 60-70% implemented
- **Missing:** On-chain settlement, Redis storage, signature generation
- **Ecosystem:** Google, Visa, AWS, Circle, Anthropic, Cloudflare, Stripe
- **Priority:** HIGH — complete remaining 30%

### ACP (Agentic Commerce Protocol) — Stripe + OpenAI
- **Status:** NEW — evaluate integration
- **Role:** Open standard for agent-to-merchant commerce
- **Integration:** Sardis policy engine wraps ACP transactions
- **Priority:** MEDIUM — after Stripe Issuing is live

### ERC-8004 (Trustless Agent Identity)
- **Status:** Ahead of competitors
- **Missing:** Spec alignment, on-chain registry client
- **Priority:** MEDIUM

### AP2 (Agent Payment Protocol)
- **Status:** Implemented
- **Priority:** MAINTAIN

---

## Complete Money Flow Architecture

```
═══════════════════════════════════════════════════════════════
              USER → AGENT FUNDING (3 paths)
═══════════════════════════════════════════════════════════════

Path A: Crypto On-Ramp (NOW)
  User bank card → Coinbase Onramp (%0 fee) → USDC → Agent MPC wallet

Path B: Direct Stablecoin (NOW)
  User crypto wallet → USDC transfer → Agent MPC wallet
  → DepositMonitor → AML screen → Ledger CREDIT → Webhook

Path C: ACH / Bank Transfer (SERIES A)
  User bank account → Financial Connections → ACH → Financial Account
  → Agent fund available → Card or stablecoin


═══════════════════════════════════════════════════════════════
              AGENT → SPENDING (4 channels)
═══════════════════════════════════════════════════════════════

Channel 1: Stripe Issuing Virtual Card (Fiat Rail)
  Agent wallet → [offramp or stablecoin-backed] → Prepaid Visa
  → Online: Amazon, SaaS, any merchant
  → NFC: Apple Pay, Google Pay (tokenized, PAN-less)
  → In-app: mobile payments
  → Policy: Real-time auth webhook (2s) → Sardis approve/decline

Channel 2: ACP / Shared Payment Token (Fiat Rail)
  Agent → ACP checkout with merchant → SPT issued
  → Per-seller, time-limited, amount-bounded
  → Sardis policy engine wraps the transaction
  → Merchant gets paid via standard Stripe PaymentIntent

Channel 3: Direct Stablecoin Transfer (Crypto Rail)
  Agent wallet → Policy check → Compliance check → On-chain USDC
  → Agent-to-agent (~2-5s on L2)
  → Crypto-accepting merchant
  → x402 micropayment (HTTP 402)

Channel 4: Global Payout (Fiat Rail, Series A)
  Agent Financial Account → ACH/wire → Contractor/vendor bank
  → 50+ countries, local currency


═══════════════════════════════════════════════════════════════
              AGENT ← RECEIVING PAYMENTS (reverse flow)
═══════════════════════════════════════════════════════════════

Path A: On-Chain Deposit (NOW — IMPLEMENTED ✅)
  External → USDC to agent address → DepositMonitor
  → AML screen (fail-closed) → Ledger CREDIT
  → Auto-reconcile payment requests/invoices
  → Webhooks: DEPOSIT_CONFIRMED, WALLET_FUNDED, PAYMENT_RECEIVED

Path B: Payment Request / Invoice (NOW — IMPLEMENTED ✅)
  Agent creates payment request (amount, token, chain)
  → Returns receive address + QR (EIP-681)
  → Payer sends USDC → auto-reconciliation

Path C: x402 Payee (70% IMPLEMENTED)
  Agent generates x402 challenge → Payer sends payment payload
  → Agent verifies → On-chain settlement

Path D: ACH/Wire Inbound (SERIES A)
  External → ACH/wire → Financial Account → Agent balance


═══════════════════════════════════════════════════════════════
              WITHDRAW — AGENT → USER BANK (implemented ✅)
═══════════════════════════════════════════════════════════════

Path A: USDC → USD → Bank (Bridge.xyz — NOW ✅)
  POST /v2/ramp/withdraw
  Agent USDC Wallet → Bridge deposit address (on-chain tx)
      → Bridge converts USDC → USD
      → ACH/wire to user's bank account
  Controls:
      → Policy enforcement before withdrawal
      → KYC check for amounts ≥ $1,000
      → Velocity limits: $10K/day, $50K/week, $200K/month
  Requires: BRIDGE_API_KEY

Path B: USD → Bank (Lithic ACH — NOW ✅)
  POST /v2/treasury/withdraw
  Agent fiat sub-ledger balance → Lithic ACH → User bank
  Controls:
      → Rate limits: $2.5M/payment, $10M/day per org
      → ACH state machine: initiated → reviewed → processed → settled
      → Auto bank account pausing on ACH return codes (R02, R03, R29)
  Methods: ACH_NEXT_DAY, ACH_SAME_DAY

Path C: Financial Account → Bank (SERIES A)
  Stripe OutboundTransfer or OutboundPayment
      → ACH (1-2 days, free) or Wire (same day, ~$2)
      → Stripe Network between FAs (minutes, free)

Full Round-Trip Verified:
  IN:   User card → Coinbase → USDC → Agent wallet         ✅
  USE:  Agent wallet → Virtual card → Amazon/Apple Pay      ✅
  OUT:  Agent wallet → Bridge → USD → User bank account     ✅


═══════════════════════════════════════════════════════════════
              POLICY ENFORCEMENT (both rails)
═══════════════════════════════════════════════════════════════

Fiat Rail:
  Stripe spending_controls (hard limits: MCC, country, amount)
  + issuing_authorization.request webhook (2s)
  + Sardis NL policy engine (smart, context-aware)
  = Two-layer enforcement

Crypto Rail:
  sardis-core policy check (SpendingPolicy evaluation)
  + On-chain smart contract limits (ZeroDev session keys)
  + AML/sanctions screening (Elliptic)
  = Three-layer enforcement
```

---

## Pricing Summary

### Fixed Costs (Monthly)

| Component | Provider | Cost | Notes |
|-----------|----------|------|-------|
| Key Management | Turnkey Free | $0 | 100 wallets, 25 tx/mo |
| Key Management | Turnkey Pro | $99 | When >100 wallets |
| Smart Accounts | ZeroDev | $0 | Gas costs only |
| Card Issuing platform | Stripe Issuing | $0 | No monthly fee |
| KYC (baseline) | Stripe (included) | $0 | Included with Issuing |
| AML (enhanced) | ComplyAdvantage | $0 | Free 12 months |
| On-chain sanctions | Elliptic | current | Already integrated |
| Database | Neon PostgreSQL | current | Already integrated |
| Corporate banking | Mercury | current | Already integrated |
| **TOTAL FIXED** | | **$0–$99/mo** | |

### Per-Transaction Costs

| Action | Provider | Cost |
|--------|----------|------|
| Virtual card creation | Stripe | $0.10/card |
| Card transaction (first $500K) | Stripe | FREE |
| Card transaction (after $500K) | Stripe | 0.2% + $0.20 |
| International card tx | Stripe | +1% + $0.30 |
| KYC verification | Persona | Free (500/mo startup) |
| KYC verification (at scale) | Stripe Identity | $1.50/verification |
| USDC on-ramp | Coinbase | FREE |
| USDC bridging | Circle CCTP | FREE |
| Multi-token bridge | Across | 0.04–0.12% |
| Gas (ERC-20 paymaster) | Pimlico | 10% surcharge |
| MPC signature | Turnkey Pro | $0.01/sig |
| ACH transfer | Stripe Treasury | FREE |
| Wire transfer | Stripe Treasury | ~$2 |

---

## Build vs Buy Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Policy Engine** | BUILD | Core IP. NL-to-deterministic rules. No competitor has this. |
| **sardis-ledger** | BUILD | Merkle proofs + blockchain anchoring = unique moat. |
| **Agent Identity (ERC-8004)** | BUILD | First-mover. Solidity + Python + API exist. |
| **x402 Protocol** | BUILD (complete) | 60-70% done. Foundation alignment. |
| **Core Engine** | BUILD | Tx orchestration, event bus, wallet management. |
| **Key Management** | BUY (Turnkey) | TEE/MPC is infrastructure. 50ms signing. |
| **Card Issuing** | BUY (Stripe) | Regulatory licensing impossible pre-seed. |
| **KYC/AML** | BUY (Stripe + supplements) | Included with Issuing. |
| **KYC (operator)** | BUY (Persona now, Stripe Identity at scale) | Free 500/mo now, $1.50 when volume justifies. |
| **On-Ramp** | BUY (Coinbase) | Zero-fee USDC. No reason to build. |
| **USDC Bridge** | BUY (Circle CCTP) | Zero-fee. Issuer's own bridge. |
| **Fiat Treasury** | BUY later (Stripe FA) | Not needed until Series A. |
| **ACP integration** | INTEGRATE | Stripe/OpenAI open protocol. Wrap with policy engine. |

**Rule:** Build what differentiates (policy, ledger, identity, protocols). Buy commodity infrastructure (keys, cards, ramps, bridges, banking).

---

## Competitive Moat

```
What ONLY Sardis provides (no single competitor has all of these):

 1. NL spending policy engine      ← "Max $500/day, only SaaS" → deterministic rules
 2. Non-custodial MPC wallets      ← Agent-owned, not platform-custodied
 3. Cryptographic audit trail      ← Merkle proofs + blockchain anchoring (UNIQUE)
 4. ERC-8004 agent identity        ← On-chain trustless identity
 5. x402 native support            ← HTTP micropayments
 6. Dual-rail execution            ← Fiat (Stripe) + Crypto (on-chain) unified
 7. Real-time policy enforcement   ← 2s auth webhook + on-chain limits
 8. Inbound payments               ← Agents receive money, not just spend
 9. Virtual card issuing           ← Stripe Issuing, Apple/Google Pay
10. 9 framework SDKs               ← LangChain, CrewAI, OpenAI, Google ADK...
11. MCP server (52 tools)          ← Claude/Cursor native
12. ACP protocol support           ← Stripe/OpenAI merchant checkout

Competitors: Crossmint ~5, Skyfire ~3, Payman ~3. Sardis has all 12.

Key differentiator: sardis-ledger Merkle tree proofs + hash chain + blockchain
anchoring = cryptographically verifiable transaction history. "Provable compliance"
— not "we logged it" but "here's the SHA-256 proof."
```

---

## Stripe vs Sardis: Where Sardis Adds Value

Stripe's Agentic Commerce Suite is infrastructure. Sardis is the intelligence layer on top.

| Capability | Stripe Provides | Sardis Adds |
|-----------|----------------|-------------|
| Card issuing | ✅ Virtual/physical cards | Policy engine deciding approve/decline |
| Spending controls | ✅ MCC, amount, country limits | NL rules ("only SaaS under $200") |
| Auth webhook | ✅ 2-second window | Context-aware policy evaluation |
| Payment tokens (SPT) | ✅ Scoped, time-limited | Agent identity verification (ERC-8004) |
| ACP checkout | ✅ Merchant protocol | Policy wrapping + audit trail |
| Financial Accounts | ✅ ACH/wire/FDIC | Non-custodial alternative (on-chain) |
| Agent toolkit | ✅ Stripe API tools | 52-tool MCP server with full policy |
| Fraud detection | ✅ Radar | Sardis kill switch + agent reputation |
| Transaction history | ✅ Append-only | Merkle proofs + blockchain anchoring |
| Identity | ✅ Document + selfie | ERC-8004 on-chain agent identity |
| Stablecoin | ✅ Bridge (USDC/USDB) | Multi-chain execution (5 EVM chains) |
| Crypto-native | ❌ Fiat only | ✅ On-chain wallets, DeFi, agent-to-agent |

---

## Key Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Stripe rejects agent use case | HIGH | Frame as "B2B expense management." Rain.xyz backup. |
| Stripe pricing changes | MEDIUM | Provider abstractions in sardis-cards. Wallester EU backup. |
| Stablecoin-backed issuing stays preview | MEDIUM | Standard Issuing works. Fund via ACH. |
| Stripe becomes competitor (Agentic Commerce) | MEDIUM | Sardis = non-custodial + crypto + policy. Different value prop. |
| Single-vendor Stripe dependency | MEDIUM | Clean provider abstractions. Card/treasury/KYC all swappable. |
| GENIUS Act delayed | LOW | Architecture works regardless. Non-custodial is defensive. |
| Turnkey pricing increases | LOW | CDP ($0.005/op) or Dfns ($50/mo). |
| Coinbase zero-fee ends | LOW | Onramper aggregator fallback. |
| ERC-8004 spec changes | LOW | Already ahead. Adjust contract to match. |
| sardis-ledger scaling | LOW | PostgreSQL advisory locks tested. Sharding path exists. |
| 3DS blocks agent cards | LOW | US low-value exempt. Autopilot fallback. OTP routing. |

---

## Implementation Phases

### Phase 1: Revenue Enablers (Week 1-4)
1. **Stripe Issuing** — Apply. Build sandbox integration. Frame as B2B expense management.
2. **Coinbase Onramp** — Integrate zero-fee USDC funding
3. **Persona** — Operator KYC (free 500/mo startup program)
4. **ComplyAdvantage** — Apply to ComplyLaunch

### Phase 2: Protocol & Policy (Week 4-8)
5. **Real-time auth webhook** — Connect Sardis policy engine to `issuing_authorization.request`
6. **x402 settlement** — Complete on-chain settlement + Redis storage
7. **Circle CCTP V2** — Native USDC bridging
8. **ZeroDev** — Smart accounts with session keys

### Phase 3: Scale (Week 8-16)
9. **ACP integration** — Wrap Stripe ACP with Sardis policy engine
10. **Digital wallets** — Apple Pay / Google Pay push provisioning
11. **Pimlico** — Gas abstraction (pay in USDC)
12. **sardis-ledger** — Blockchain anchoring deployment

### Phase 4: Enterprise (Post-Seed)
13. **Stripe Financial Accounts** — FDIC-insured agent accounts
14. **Financial Connections** — Bank account linking
15. **Global Payouts** — 50+ country disbursements
16. **Wallester** — EU card issuing
17. **Stablecoin-backed Issuing** — When generally available

---

## Stripe Issuing: Getting Started

**No minimum revenue, investment, or transaction volume required.**

| Step | Timeline | Action |
|------|----------|--------|
| 1. Sandbox | Immediate | Start building. No approval needed. |
| 2. Intake form | Day 1 | `stripe.com/contact/sales` — "B2B commercial expense management for AI agents" |
| 3. Sales call | ~5 days | Supportability assessment. Discuss use case. |
| 4. Use case approval | 5-10 days | Stripe + bank partner review |
| 5. Legal agreements | 1 week | Sign Issuing terms, bank terms |
| 6. Compliance review | ~2 weeks | Submit screenshots, marketing materials, complaint channels |
| 7. Live mode access | After approval | Bank partner grants live access |
| **Total** | **3-6 weeks** | Optimistic. 6-10 weeks if revisions needed. |

**Compliance obligations (ongoing):**
- 5-year recordkeeping (UX screenshots, marketing, complaints)
- All customer-facing copy pre-approved by Stripe Compliance
- Monthly reporting
- Customer complaint resolution process

---

## Next Actions (Immediate)

1. **Stripe Issuing** — Submit intake form at `stripe.com/contact/sales`
2. **Stripe stablecoin-backed issuing** — Request private preview access
3. **Sandbox integration** — Build Issuing + real-time auth webhook in test mode
4. **Persona** — Apply to fintech startup cohort (free 500/mo)
5. **ComplyAdvantage** — Apply to ComplyLaunch (12 months free)
6. **Coinbase Onramp** — Complete zero-fee USDC integration
7. **sardis-ledger** — Connect anchoring to sardis-chain. Deploy anchor contract.
8. **x402** — Complete on-chain settlement (30% remaining)
9. **Coinbase CDP** — Apply for Builder Grant ($30K)
10. **Stripe Financial Accounts** — Apply when US company is registered (no formal funding requirement)

## Existing Infrastructure Status

| Capability | Status | Endpoint | Provider |
|-----------|--------|----------|----------|
| Agent wallet creation | ✅ LIVE | `POST /v2/wallets` | Turnkey MPC |
| Multi-chain balance | ✅ LIVE | `GET /v2/wallets/{id}/balances` | On-chain query |
| On-chain payment (outbound) | ✅ LIVE | `POST /v2/wallets/{id}/transfer` | Turnkey + policy engine |
| Deposit monitoring (inbound) | ✅ LIVE | `GET /v2/wallets/{id}/deposits` | DepositMonitor |
| Payment requests | ✅ LIVE | `POST /v2/wallets/{id}/payment-request` | Auto-reconcile |
| Invoice system | ✅ LIVE | `POST /v2/invoices` | Auto-reconcile with deposits |
| Card issuing | ✅ LIVE | `POST /v2/cards` | Lithic (Stripe migration planned) |
| Card funding | ✅ LIVE | `POST /v2/cards/{id}/fund` | Offramp USDC→USD |
| USDC on-ramp | ✅ LIVE | `POST /v2/ramp/onramp/widget` | Coinbase (%0 fee) |
| USDC off-ramp / withdraw | ✅ LIVE | `POST /v2/ramp/withdraw` | Bridge.xyz (USDC→USD→bank) |
| Fiat withdraw (ACH) | ✅ LIVE | `POST /v2/treasury/withdraw` | Lithic ACH |
| Policy enforcement | ✅ LIVE | Every transaction | SpendingPolicy engine |
| AML/sanctions screening | ✅ LIVE | Every deposit | Elliptic (on-chain) |
| Webhook events | ✅ LIVE | 6+ event types | HMAC-signed delivery |
| x402 protocol | ⚠️ 70% | `POST /v2/wallets/{id}/x402/*` | Challenge/verify done, settlement TODO |
| Stripe Issuing integration | ⚠️ Provider exists | sardis-cards | Migration from Lithic needed |
| Real-time auth webhook | ❌ TODO | — | Phase 2 (connect policy engine) |
| Apple Pay / Google Pay | ❌ TODO | — | Phase 3 (push provisioning) |
| CCTP bridging | ❌ TODO | — | Phase 2 |
| ZeroDev smart accounts | ❌ TODO | — | Phase 2 |
| Stripe Financial Accounts | ❌ TODO | — | Apply when US company registered |
