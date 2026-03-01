# Sardis Production Deployment Guide v2

> **Tarih:** 2026-03-01
> **Hedef:** Base mainnet'te gerçek USDC işlem yapabilir hale gelmek
> **Strateji:** Minimum complexity, tek chain (Base), fiat yolu Coinbase Onramp

---

## BÖLÜM 0: MİMARİ KARAR ÖZETİ

### Neden Stripe Treasury YOK?

Stripe Treasury davetli/özel bir ürün. Normal Stripe hesabıyla erişilemez.
Gereksinimler: Platform partneri başvurusu + sales call + banking partner onayı.
**Sardis için şu an mevcut değil** ve kısa vadede olmayacak.

### Ana Fiat Akışı: Coinbase Onramp/Offramp

```
FIAT → USDC:  Coinbase Onramp (hosted URL, ücretsiz, 100+ ülke)
USDC → FIAT:  Coinbase Offramp (hosted URL)
```

Bu yaklaşımın avantajları:
- Non-custodial (Sardis para tutmuyor, USDC on-chain agent wallet'ta)
- MTL/para lisansı gereksiz (sadece orkestrasyon)
- Coinbase altyapısı üzerinden global erişim
- Zaten entegre (API endpoint'leri hazır)

### Neden Tek Chain (Base)?

- Gas maliyeti: ~$0.001-0.01/tx (en ucuz)
- Coinbase ekosistemi native uyum
- Circle Paymaster mevcut (USDC ile gas)
- Diğer chain'ler sonra CCTP V2 ile eklenir (kod hazır)

### Kart Stratejisi (Post-Launch)

- Day 1: `SARDIS_ENABLE_CARDS=false` — kartlar kapalı
- Stripe Issuing onayı gelince: aktifle, dashboard'dan manual funding
- Lithic: $5M minimum gerekli, şu an erişilemez
- Kartlar gelir/yatırım geldikten sonra aktif edilecek

---

## BÖLÜM 1: DEPLOY EDİLECEK KOMPONENTLER

### 1.1 Tam Liste (Sadece Bunlar)

| # | Komponent | Servis | Maliyet |
|---|-----------|--------|---------|
| 1 | **API Server** | Vercel (serverless) | $0 (hobby) / $20 (pro) |
| 2 | **PostgreSQL** | Neon | $0 (free) / $19 (pro) |
| 3 | **Redis** | Upstash | $0 (free tier) |
| 4 | **RPC Provider** | Alchemy (Base) | $0 (free: 30M CU/ay) |
| 5 | **MPC Signing** | Turnkey | Per-signature (~$0.01-0.10) |
| 6 | **Smart Contracts** | Base mainnet | ~$3-5 (tek sefer gas) |
| 7 | **KYC** | iDenfy | $0.55/doğrulama |
| 8 | **AML/Sanctions** | Scorechain | $0 (free tier) |
| 9 | **Error Tracking** | Sentry | $0 (free: 5K event/ay) |
| 10 | **Landing Page** | Vercel | $0 |
| 11 | **Dashboard** | Vercel | $0 |

**Toplam başlangıç:** ~$5 (gas)
**Toplam aylık:** ~$20-150 (kullanıma bağlı)

### 1.2 Day 1'de OLMAYACAK Komponentler

| Komponent | Neden Yok | Ne Zaman |
|-----------|-----------|----------|
| Stripe Treasury | Erişim yok (davetli ürün) | Stripe onayı gelirse |
| Stripe Issuing | Onay gerekli | Sales call sonrası |
| Lithic Cards | $5M minimum | Yatırım sonrası |
| Multi-chain (Arb/OP/Polygon) | Gereksiz complexity | Talep gelince |
| CCTP Bridge | Tek chain'de anlamsız | İkinci chain eklenince |
| Persona KYC | Başvuru reddedildi | ABD şirketi sonrası |
| Elliptic AML | Enterprise fiyatlandırma | Scorechain yeterli |
| ZeroDev Session Keys | API key + SDK gerekli | İleri faz |

---

## BÖLÜM 2: HER KOMPONENTİN DETAYLI AÇIKLAMASI

### 2.1 API Server (FastAPI → Vercel)

**Ne yapıyor:**
Sardis'in tüm backend mantığı burada. 47+ API endpoint:
- Wallet oluşturma/yönetme
- Spending policy ayarlama (doğal dil)
- Ödeme gönderme/alma
- Agent kayıt/yönetim
- KYC/AML kontrolleri
- Audit log
- WebSocket alert'ler
- Coinbase Onramp/Offramp URL oluşturma

**Nasıl deploy edilir:**
```bash
# Vercel'de Python runtime (serverless)
# packages/sardis-api/src/sardis_api/main.py → create_app()
vercel --prod
```

**Neden Vercel:**
- Zero-config deployment
- Auto-scaling
- Edge network (global)
- Free tier yeterli (başlangıç için)
- Domain yönetimi kolay

**Alternatif:** Railway, Render, Cloud Run — ama Vercel en basit.

### 2.2 PostgreSQL (Neon)

**Ne yapıyor:**
Tüm kalıcı veri burada: wallet'lar, agent'lar, transaction'lar, policy'ler,
spending tracker, audit log, KYC kayıtları, kart bilgileri.

**Neden Neon:**
- Serverless (bağlantı olmayınca para ödemiyorsun)
- Auto-scaling
- Point-in-time recovery (veri kaybı koruması)
- Branching (staging için DB kopyası)
- PostgreSQL 16 (tam uyumluluk)

**Setup:**
1. console.neon.tech → yeni proje oluştur
2. Connection string al: `postgresql://user:pass@ep-xxx.neon.tech/sardis?sslmode=require`
3. Migration çalıştır: `DATABASE_URL="..." alembic upgrade head`
4. ~50 tablo otomatik oluşur

**Dikkat:**
- `sslmode=require` zorunlu
- Connection pool: min=2, max=15
- `statement_cache_size=0` (Neon'un pgbouncer'ı ile uyum)

### 2.3 Redis (Upstash)

**Ne yapıyor:**
- Idempotency (aynı isteğin iki kere işlenmesini engeller)
- Rate limiting (API abuse koruması)
- JWT token revocation (logout sonrası token iptal)
- Webhook replay koruması (Stripe/Lithic aynı event'i tekrar gönderirse)
- Nonce management (blockchain tx ordering)

**Neden Upstash:**
- Serverless Redis (Vercel ile native uyum)
- Per-request fiyatlandırma ($0 başlangıç)
- Global replication
- REST API (serverless ortamda TCP bağlantısı gerekmez)

**Setup:**
1. console.upstash.com → yeni database oluştur
2. URL al: `rediss://default:xxx@xxx.upstash.io:6379`
3. `SARDIS_REDIS_URL` olarak ayarla

### 2.4 RPC Provider (Alchemy)

**Ne yapıyor:**
Blockchain ile konuşmak için. Her on-chain işlem (wallet oluşturma, USDC transfer,
contract okuma) bir RPC çağrısı gerektirir.

**Neden public RPC kullanılMAZ:**
- Rate limit (2-5 req/s)
- Güvenilmez (downtime, yavaşlık)
- Hiçbir SLA yok
- Production trafiği kaldırmaz

**Neden Alchemy:**
- 30M free Compute Unit/ay (~1.2M istek)
- 25 req/s (yeterli)
- 99.9% SLA
- Base mainnet native destek
- Dashboard ile monitoring

**Setup:**
1. dashboard.alchemy.com → yeni app oluştur (Base Mainnet)
2. API key al
3. `SARDIS_BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<KEY>`

**Sadece Base mainnet yeterli.** Diğer chain'ler (Ethereum, Polygon, Arbitrum, Optimism) şu an gereksiz.

### 2.5 MPC Signing (Turnkey)

**Ne yapıyor:**
Private key'leri güvenli şekilde saklar ve imza atar. Sardis hiçbir zaman
private key'e dokunmaz — Turnkey'in HSM'lerinde kalır.

**Bu neden kritik:**
- Non-custodial = Sardis key tutmuyor = lisans gereksiz
- MPC = tek hata noktası yok (key parçalara bölünmüş)
- Turnkey = SOC2 sertifikalı, enterprise-grade

**Setup:**
1. app.turnkey.com → organization oluştur
2. API key pair generate et (P-256 ECDSA)
3. Env vars:
   ```
   SARDIS_MPC__NAME=turnkey
   TURNKEY_API_PUBLIC_KEY=<public-key>
   TURNKEY_API_PRIVATE_KEY=<hex-encoded-private-key>
   TURNKEY_ORGANIZATION_ID=<org-uuid>
   ```

**Test:** Turnkey hesabında bir wallet oluştur, Base Sepolia'da test transaction at.

### 2.6 Smart Contracts (Base Mainnet)

**Ne yapıyor:**
3 kontrat deploy edilecek — Safe Smart Accounts migrasyonu sonrası:

| Kontrat | Satır | Amacı | Audit |
|---------|-------|-------|-------|
| **SardisPolicyModule** | 230 | Safe module: spending policy enforcement | Gereksiz (non-custodial, devre dışı bırakılabilir) |
| **SardisLedgerAnchor** | 41 | Merkle root'ları on-chain'e yazdırma (audit trail) | Gereksiz (41 satır, sadece owner yazabilir) |
| **RefundProtocol** | ~600 | Circle'ın audited escrow kontratı (Apache 2.0) | Zaten audited (Circle) |

**Pre-deployed altyapı (deploy gerekmez):**

| Altyapı | Adres | Audit |
|---------|-------|-------|
| Safe ProxyFactory | `0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2` | OpenZeppelin, Ackee, G0 |
| Safe Singleton | `0x41675C099F32341bf84BFc5382aF534df5C7461a` | OpenZeppelin, Ackee, G0 |
| Safe 4337 Module | `0x75cf11467937ce3F2f357CE24ffc3DBF8fD5c226` | OpenZeppelin |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | Audited, $3M bug bounty |
| EAS (Base) | `0x4200000000000000000000000000000000000021` | Audited, OP Stack predeploy |

**Deploy:**
```bash
cd contracts

# .env hazırla
PRIVATE_KEY=<deployer-key-without-0x>
SARDIS_ADDRESS=<sardis-platform-address>
USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<KEY>
BASESCAN_API_KEY=<key>

# Dry run (hiçbir şey deploy etmez, sadece simüle eder)
forge script script/DeploySafeModules.s.sol:DeploySafeModules \
  --rpc-url $BASE_RPC_URL -vvvv

# Gerçek deployment
forge script script/DeploySafeModules.s.sol:DeploySafeModules \
  --rpc-url $BASE_RPC_URL \
  --broadcast --verify \
  --etherscan-api-key $BASESCAN_API_KEY
```

**Maliyet:** ~$3-5 (Base gas çok ucuz)

**Deployer wallet:** Yeni bir EOA oluştur, ~0.01 ETH fonla (Base mainnet'te).
ETH nereden? Coinbase'den Base'e direkt çek.

### 2.7 KYC (iDenfy)

**Ne yapıyor:**
Kullanıcı kimlik doğrulama: kimlik belgesi + selfie + canlılık testi.

**Neden iDenfy (Persona değil):**
- Persona production trial başvurusu REDDEDİLDİ
- iDenfy: $0.55/doğrulama, zaten tam entegre
- 200+ ülke destekli
- KYB (şirket doğrulama) de var

**Setup:**
1. portal.idenfy.com → hesap oluştur (zaten var)
2. API credentials al
3. Env vars: `IDENFY_API_KEY`, `IDENFY_API_SECRET`

### 2.8 AML/Sanctions (Scorechain)

**Ne yapıyor:**
Blockchain adreslerini OFAC, EU, UN, UK yaptırım listelerine karşı tarar.
"Bu adres kara listede mi?" sorusuna cevap verir.

**Setup:**
1. scorechain.com → ücretsiz hesap aç
2. API key al
3. `SCORECHAIN_API_KEY=<key>`

---

## BÖLÜM 3: AKIŞ ŞEMALARI

### 3.1 Temel Kullanıcı Akışı

```
1. Operator (insan) sardis.sh'de hesap açar
2. Agent oluşturur (isim, açıklama, yetki alanı)
3. Agent için wallet oluşturulur (Turnkey MPC → Base adresi)
4. Spending policy ayarlar: "Günlük max $500, sadece SaaS servislere"
5. Wallet'a USDC yükler:
   a. Direkt USDC transfer (zaten on-chain USDC varsa)
   b. Coinbase Onramp (fiat → USDC, kredi kartı/banka ile)
6. Agent SDK üzerinden ödeme gönderir
7. Sardis: policy check → compliance check → on-chain USDC transfer
8. Audit log'a yazılır + Merkle anchoring
```

### 3.2 Fiat Giriş (Coinbase Onramp)

```
Kullanıcı → sardis.sh "Fund Wallet" butonuna tıklar
         → Sardis API: POST /wallets/{id}/onramp
         → Coinbase hosted URL döner
         → Kullanıcı Coinbase'de kredi kartı/banka ile ödeme yapar
         → USDC agent wallet adresine gönderilir (Base)
         → Sardis deposit monitor tespit eder
         → Bakiye güncellenir
```

**Not:** Coinbase Onramp'ta Sardis'in yapacağı bir şey yok. Coinbase tüm
KYC/AML/ödeme işlemini kendisi halleder. Sardis sadece URL oluşturur.

### 3.3 Fiat Çıkış (Coinbase Offramp)

```
Kullanıcı → sardis.sh "Withdraw" butonuna tıklar
         → Sardis API: POST /wallets/{id}/offramp
         → Coinbase hosted URL döner
         → Kullanıcı banka hesabını bağlar
         → USDC → Coinbase → USD → kullanıcının bankası
```

### 3.4 On-chain Ödeme

```
Agent → SDK: send_payment(to="0x...", amount=50, token="USDC")
     → Sardis API: POST /wallets/{id}/send
     → Spending Policy kontrolü (NL kurallar değerlendirilir)
     → AML/Sanctions kontrolü (Scorechain)
     → Turnkey MPC imza
     → Circle Paymaster (USDC ile gas ödeme)
     → Base mainnet'te USDC transfer
     → Audit log + Merkle tree update
     → WebSocket alert → operator'e bildirim
```

---

## BÖLÜM 4: ADM ADIM DEPLOYMENT

### Gün 1: Hesaplar (2-3 saat)

| Sıra | İş | URL | Süre |
|------|-----|-----|------|
| 1 | Alchemy hesap aç, Base mainnet app oluştur | dashboard.alchemy.com | 5 dk |
| 2 | Basescan hesap aç, API key al | basescan.org/register | 5 dk |
| 3 | Neon PostgreSQL proje oluştur | console.neon.tech | 5 dk |
| 4 | Upstash Redis database oluştur | console.upstash.com | 5 dk |
| 5 | Sentry proje oluştur | sentry.io | 5 dk |
| 6 | Turnkey organization oluştur | app.turnkey.com | 15 dk |
| 7 | iDenfy API credentials al | portal.idenfy.com | 10 dk |
| 8 | Scorechain free tier hesap aç | scorechain.com | 10 dk |
| 9 | Coinbase CDP app oluştur | portal.cdp.coinbase.com | 10 dk |

**Not:** Tüm servisler ücretsiz veya free tier ile başlıyor.

### Gün 2: Smart Contract Deploy (1-2 saat)

```bash
# 1. Deployer wallet oluştur
cast wallet new
# → Address ve private key kaydet

# 2. Base mainnet'te ETH al (gas için)
# Coinbase'den Base'e 0.01 ETH çek (~$25)

# 3. Deploy
cd contracts
cp .env.example .env
# PRIVATE_KEY, BASE_RPC_URL, BASESCAN_API_KEY doldur

# 4. Test (dry run)
forge script script/DeploySafeModules.s.sol:DeploySafeModules \
  --rpc-url $BASE_RPC_URL -vvvv

# 5. Gerçek deploy
forge script script/DeploySafeModules.s.sol:DeploySafeModules \
  --rpc-url $BASE_RPC_URL \
  --broadcast --verify \
  --etherscan-api-key $BASESCAN_API_KEY

# 6. Adresleri kaydet! Çıktıda göreceksin:
# SardisPolicyModule: 0x...
# SardisLedgerAnchor: 0x...
# RefundProtocol: 0x...
# (Safe, EAS, Permit2 zaten pre-deployed)
```

### Gün 2: Database Migration (15 dk)

```bash
# Neon connection string ile migration çalıştır
cd packages/sardis-api
DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/sardis?sslmode=require" \
  alembic upgrade head

# Tablo sayısını doğrula (~50+)
```

### Gün 2-3: Vercel Deploy (30 dk)

```bash
# 1. .env.production hazırla (aşağıdaki BÖLÜM 5'teki template'i kullan)

# 2. Vercel'e env vars ekle
vercel env add SARDIS_ENVIRONMENT production
vercel env add DATABASE_URL production
vercel env add SARDIS_REDIS_URL production
vercel env add SARDIS_SECRET_KEY production
vercel env add SARDIS_BASE_RPC_URL production
vercel env add SARDIS_MPC__NAME production
vercel env add TURNKEY_API_PUBLIC_KEY production
vercel env add TURNKEY_API_PRIVATE_KEY production
vercel env add TURNKEY_ORGANIZATION_ID production
# ... diğer tüm env vars

# 3. Deploy
vercel --prod

# 4. Health check
curl https://api.sardis.sh/api/v2/health
```

### Gün 3: Smoke Test (1-2 saat)

```
1. GET  /api/v2/health         → 200 OK, tüm check'ler yeşil
2. POST /api/v2/organizations  → Org oluştur
3. POST /api/v2/agents         → Agent oluştur
4. POST /api/v2/wallets        → Wallet oluştur (Turnkey MPC)
   → Base mainnet'te gerçek adres dönmeli
5. POST /api/v2/wallets/{id}/policy → NL policy ayarla
   → "Günlük max $100, sadece bilinen adreslere"
6. Base Sepolia'da test USDC gönder wallet adresine
7. POST /api/v2/wallets/{id}/send → Küçük miktar transfer
8. GET  /api/v2/ledger/entries → Audit log'da göründüğünü doğrula
9. POST /api/v2/wallets/{id}/onramp → Coinbase URL döndüğünü doğrula
```

---

## BÖLÜM 5: PRODUCTION ENV VARS (TAM LİSTE)

```bash
# ═══════════════════════════════════════════════════
# ZORUNLU (bunlar olmadan API çalışmaz)
# ═══════════════════════════════════════════════════

# Core
SARDIS_ENVIRONMENT=prod
SARDIS_CHAIN_MODE=live
SARDIS_SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(32))">
JWT_SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
SARDIS_ADMIN_PASSWORD=<güçlü-şifre>

# Database
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/sardis?sslmode=require

# Redis
SARDIS_REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379

# RPC (SADECE BASE — diğer chain'ler gereksiz)
SARDIS_BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<KEY>

# MPC Signing
SARDIS_MPC__NAME=turnkey
TURNKEY_API_PUBLIC_KEY=<key>
TURNKEY_API_PRIVATE_KEY=<hex-private-key>
TURNKEY_ORGANIZATION_ID=<uuid>

# Smart Contract Adresleri (deploy sonrası doldur)
SARDIS_POLICY_MODULE_BASE=0x...
SARDIS_LEDGER_ANCHOR_BASE=0x...
SARDIS_REFUND_PROTOCOL_BASE=0x...

# ═══════════════════════════════════════════════════
# ÖNEMLİ (production'da olması gereken)
# ═══════════════════════════════════════════════════

# API
SARDIS_API_BASE_URL=https://api.sardis.sh
SARDIS_ALLOWED_ORIGINS=https://sardis.sh,https://app.sardis.sh

# KYC
IDENFY_API_KEY=<key>
IDENFY_API_SECRET=<secret>

# AML/Sanctions
SCORECHAIN_API_KEY=<key>

# ERC-4337 (Circle Paymaster — API key gereksiz)
SARDIS_PAYMASTER_PROVIDER=circle

# Ledger Anchoring
SARDIS_ANCHOR_CHAIN=base

# Monitoring
SENTRY_DSN=<sentry-dsn>
SENTRY_ENVIRONMENT=production
LOG_LEVEL=INFO

# Background Jobs
SARDIS_ENABLE_SCHEDULER=1

# Coinbase Onramp/Offramp
COINBASE_APP_ID=<app-id>

# ═══════════════════════════════════════════════════
# KAPALI (Day 1'de aktif değil)
# ═══════════════════════════════════════════════════

SARDIS_ENABLE_CARDS=false
# STRIPE_SECRET_KEY=          ← Issuing onayı gelince
# LITHIC_API_KEY=             ← $5M funding sonrası
# SARDIS_POLYGON_RPC_URL=     ← Tek chain yeterli
# SARDIS_ARBITRUM_RPC_URL=    ← Tek chain yeterli
# SARDIS_OPTIMISM_RPC_URL=    ← Tek chain yeterli
```

---

## BÖLÜM 6: DEPLOYMENT SONRASI — KRİTİK KONTROL LİSTESİ

### Güvenlik
- [ ] SARDIS_SECRET_KEY rastgele ve güçlü (32+ karakter)
- [ ] JWT_SECRET_KEY rastgele ve güçlü
- [ ] SARDIS_ADMIN_PASSWORD güçlü
- [ ] CORS sadece production domain'lere izin veriyor
- [ ] Rate limiting aktif
- [ ] `.env` dosyası `.gitignore`'da
- [ ] Pre-commit secret detection hook aktif
- [ ] Turnkey API key'leri sadece Vercel env vars'da (git'te değil)

### Fonksiyonel
- [ ] `/api/v2/health` → 200 OK
- [ ] Wallet oluşturma çalışıyor
- [ ] USDC transfer çalışıyor (testnet'te test et)
- [ ] Spending policy değerlendirmesi çalışıyor
- [ ] Audit log yazılıyor
- [ ] Coinbase Onramp URL oluşturuluyor
- [ ] KYC flow çalışıyor (iDenfy sandbox ile test)
- [ ] Sanctions check çalışıyor (Scorechain)

### Monitoring
- [ ] Sentry error'ları yakalıyor
- [ ] API logları Vercel'de görünüyor
- [ ] Health check düzenli kontrol ediliyor

---

## BÖLÜM 7: GELECEK ENTEGRASYONLAR (Day 1 SONRASI)

### Hafta 2-3: Stripe Issuing (Kart)
Stripe'a başvur, onay gelince:
1. `STRIPE_SECRET_KEY` ayarla
2. `SARDIS_ENABLE_CARDS=true`
3. `SARDIS_CARDS_PRIMARY_PROVIDER=stripe_issuing`
4. Stripe Dashboard'dan Issuing balance'ı manual fonla
5. Kart oluşturma/harcama test et

### Hafta 4+: İkinci Chain (ihtiyaç olursa)
1. Alchemy'de Polygon/Arbitrum app oluştur
2. `SARDIS_POLYGON_RPC_URL` ayarla
3. Aynı kontratları Polygon'a deploy et
4. CCTP V2 bridge'i aktifle

### Gelecek: Stripe Treasury (erişim olursa)
Stripe partneri olursan:
1. Financial Account oluştur
2. `STRIPE_TREASURY_FINANCIAL_ACCOUNT_ID` ayarla
3. Treasury → Issuing otomatik funding aktif olur
4. ACH/wire girişleri doğrudan Treasury'e gelir

---

## BÖLÜM 8: MALİYET ÖZETİ

### Başlangıç (Tek Sefer)
| Kalem | Maliyet |
|-------|---------|
| Contract deploy gas (Base) | ~$3-5 |
| Deployer wallet ETH | ~$25 (0.01 ETH) |
| **TOPLAM** | **~$30** |

### Aylık (0-1,000 Agent)
| Servis | Maliyet |
|--------|---------|
| Neon PostgreSQL | $0-19 |
| Upstash Redis | $0 |
| Alchemy RPC | $0 |
| Sentry | $0 |
| Vercel | $0-20 |
| iDenfy KYC | ~$0-110 (kullanıma bağlı) |
| Scorechain | $0 |
| Turnkey signing | ~$10-50 |
| Circle Paymaster | $0 |
| Coinbase Onramp | $0 |
| **TOPLAM** | **$10-200/ay** |

### Karşılaştırma: Kendi vs Managed
| | Sardis (şu an) | Tamamen Managed |
|---|---|---|
| Wallet | Turnkey ($0.01/imza) | Circle Wallets ($0.012/MAW) |
| Gas | Circle Paymaster ($0) | Circle Paymaster ($0) |
| KYC | iDenfy ($0.55) | iDenfy ($0.55) |
| AML | Scorechain ($0) | Scorechain ($0) |
| **Fark** | Custom policy+ledger+cards | Bunlar olmaz |

---

## ÖNEMLİ NOTLAR

1. **Stripe Treasury ARAMAYIN** — şu an erişilemez, gelecekte partner olursanız açılır
2. **Tek chain (Base) ile başlayın** — complexity düşük, maliyet düşük
3. **Kartları kapalı başlatın** — Stripe Issuing onayı gelince açın
4. **Coinbase Onramp/Offramp ana fiat yolu** — zaten entegre, çalışıyor
5. **Multi-chain SONRA** — CCTP V2 kodu hazır, talep olunca aktifleyin
6. **Recovery address MUTLAKA Safe multisig olsun** — tek kişilik EOA değil
