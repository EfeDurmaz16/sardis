# Sardis Production Deployment Guide

Bu rehber, Sardis'i production ortamına deploy etmek için gereken tüm adımları ve environment variable'ları içerir.

## Gerekli Servisler ve API Key'ler

### 1. MPC Wallet Provider: Turnkey

**Nereden Alınır:** https://app.turnkey.com

**Adımlar:**
1. Turnkey hesabı oluştur
2. Organization oluştur
3. API key pair oluştur (P256 key)
4. Organization ID'yi not al

```bash
# .env
TURNKEY_API_PUBLIC_KEY=02abc...def          # API public key (hex)
TURNKEY_API_PRIVATE_KEY=0x123...abc         # API private key (hex)
TURNKEY_ORGANIZATION_ID=org_abc123          # Organization ID
```

**Maliyet:** Pay-as-you-go, ~$0.10/signature

---

### 2. KYC Provider: Persona

**Nereden Alınır:** https://withpersona.com

**Adımlar:**
1. Persona hesabı oluştur (sandbox ile başla)
2. API key al
3. Webhook secret oluştur
4. Template ID'leri konfigüre et

```bash
# .env
PERSONA_API_KEY=persona_sandbox_abc123      # veya persona_live_...
PERSONA_WEBHOOK_SECRET=persona_whs_xyz789   # Webhook signature için
PERSONA_TEMPLATE_ID=tmpl_abc123             # KYC template ID (opsiyonel)
```

**Maliyet:** $3-5/verification (sandbox ücretsiz)

---

### 3. Sanctions Screening: Elliptic

**Nereden Alınır:** https://www.elliptic.co

**Adımlar:**
1. Elliptic hesabı oluştur
2. API credentials al
3. HMAC secret al

```bash
# .env
ELLIPTIC_API_KEY=ek_abc123def456
ELLIPTIC_API_SECRET=es_xyz789...            # HMAC imza için
```

**Maliyet:** Volume-based pricing, enterprise contact

---

### 4. Database: PostgreSQL

**Önerilen Sağlayıcılar:**
- Neon (https://neon.tech) - Serverless, free tier
- Supabase (https://supabase.com) - Free tier + auth
- Railway (https://railway.app) - $5/mo başlangıç
- AWS RDS - Enterprise

```bash
# .env
DATABASE_URL=postgresql://user:password@host:5432/sardis?sslmode=require
```

**Not:** Production'da mutlaka `?sslmode=require` kullanın.

---

### 5. Cache: Redis

**Önerilen Sağlayıcılar:**
- Upstash (https://upstash.com) - Serverless, free tier
- Redis Cloud (https://redis.com) - Free 30MB
- Railway - $5/mo

```bash
# .env
REDIS_URL=redis://default:password@host:6379
# veya TLS ile:
REDIS_URL=rediss://default:password@host:6379
```

---

### 6. Blockchain RPC Providers

**Önerilen Sağlayıcılar:**
- Alchemy (https://alchemy.com) - En iyi DX, free tier
- Infura (https://infura.io) - Güvenilir
- QuickNode (https://quicknode.com) - Hızlı

```bash
# .env - Her chain için ayrı RPC URL
# Base
SARDIS_BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
SARDIS_BASE_SEPOLIA_RPC_URL=https://base-sepolia.g.alchemy.com/v2/YOUR_KEY

# Polygon
SARDIS_POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
SARDIS_POLYGON_AMOY_RPC_URL=https://polygon-amoy.g.alchemy.com/v2/YOUR_KEY

# Ethereum
SARDIS_ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
SARDIS_ETHEREUM_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY

# Arbitrum
SARDIS_ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
SARDIS_ARBITRUM_SEPOLIA_RPC_URL=https://arb-sepolia.g.alchemy.com/v2/YOUR_KEY

# Optimism
SARDIS_OPTIMISM_RPC_URL=https://opt-mainnet.g.alchemy.com/v2/YOUR_KEY
SARDIS_OPTIMISM_SEPOLIA_RPC_URL=https://opt-sepolia.g.alchemy.com/v2/YOUR_KEY
```

---

### 7. OpenAI (NL Policy Parser için)

**Nereden Alınır:** https://platform.openai.com

```bash
# .env
OPENAI_API_KEY=sk-...                       # NL policy parsing için
```

**Not:** Opsiyonel - yoksa regex fallback kullanılır.

---

## Tam .env Dosyası

```bash
# ==============================================================================
# SARDIS PRODUCTION ENVIRONMENT
# ==============================================================================

# ===== CORE SETTINGS =====
SARDIS_ENVIRONMENT=prod                     # dev | staging | prod
SARDIS_SECRET_KEY=your-256-bit-secret-key   # JWT signing, en az 32 karakter
SARDIS_CHAIN_MODE=mainnet                   # simulated | testnet | mainnet

# ===== DATABASE =====
DATABASE_URL=postgresql://user:pass@host:5432/sardis?sslmode=require

# ===== CACHE =====
REDIS_URL=rediss://default:pass@host:6379

# ===== MPC WALLET (Turnkey) =====
TURNKEY_API_PUBLIC_KEY=02abc...
TURNKEY_API_PRIVATE_KEY=0x123...
TURNKEY_ORGANIZATION_ID=org_abc123

# ===== KYC (Persona) =====
PERSONA_API_KEY=persona_live_abc123
PERSONA_WEBHOOK_SECRET=persona_whs_xyz789

# ===== SANCTIONS (Elliptic) =====
ELLIPTIC_API_KEY=ek_abc123
ELLIPTIC_API_SECRET=es_xyz789

# ===== BLOCKCHAIN RPC =====
# Base (Primary Chain)
SARDIS_BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/KEY
SARDIS_BASE_SEPOLIA_RPC_URL=https://base-sepolia.g.alchemy.com/v2/KEY

# Polygon
SARDIS_POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/KEY

# Ethereum
SARDIS_ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/KEY

# Arbitrum
SARDIS_ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/KEY

# Optimism
SARDIS_OPTIMISM_RPC_URL=https://opt-mainnet.g.alchemy.com/v2/KEY

# ===== SMART CONTRACTS =====
# Base Mainnet
SARDIS_BASE_WALLET_FACTORY_ADDRESS=0x...
SARDIS_BASE_ESCROW_ADDRESS=0x...

# Base Sepolia (Testnet)
SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS=0x0922f46cbDA32D93691FE8a8bD7271D24E53B3D7
SARDIS_BASE_SEPOLIA_ESCROW_ADDRESS=0x5cf752B512FE6066a8fc2E6ce555c0C755aB5932

# ===== AI/LLM =====
OPENAI_API_KEY=sk-...                       # Opsiyonel, NL policy parsing için

# ===== API CONFIGURATION =====
SARDIS_API_HOST=0.0.0.0
SARDIS_API_PORT=8000
SARDIS_CORS_ORIGINS=https://sardis.sh,https://app.sardis.sh

# ===== AUTH =====
SARDIS_JWT_SECRET=your-jwt-secret-min-32-chars
SARDIS_ADMIN_PASSWORD=change-this-immediately

# ===== RATE LIMITING =====
SARDIS_RATE_LIMIT_PER_MINUTE=60
SARDIS_RATE_LIMIT_PER_HOUR=1000

# ===== WEBHOOKS =====
SARDIS_WEBHOOK_TIMEOUT=10
SARDIS_WEBHOOK_MAX_RETRIES=3

# ===== MONITORING (Opsiyonel) =====
POSTHOG_API_KEY=phc_...                     # Analytics
SENTRY_DSN=https://...@sentry.io/...        # Error tracking
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Tüm API key'ler alındı ve test edildi
- [ ] PostgreSQL veritabanı oluşturuldu ve migrate edildi
- [ ] Redis cache yapılandırıldı
- [ ] Smart contract'lar deploy edildi (testnet'te test edildi)
- [ ] Turnkey MPC wallet oluşturuldu ve test edildi
- [ ] KYC template'leri Persona'da yapılandırıldı
- [ ] Elliptic sandbox'ta test edildi
- [ ] RPC endpoint'leri tüm chain'ler için çalışıyor

### Security

- [ ] `SARDIS_SECRET_KEY` güçlü ve unique
- [ ] `SARDIS_ADMIN_PASSWORD` değiştirildi
- [ ] Database SSL zorunlu (`sslmode=require`)
- [ ] CORS origin'leri kısıtlandı
- [ ] Rate limiting aktif
- [ ] API key'ler güvenli saklanıyor (Vault, AWS Secrets, etc.)

### Smart Contracts

- [ ] Wallet Factory deploy edildi
- [ ] Escrow contract deploy edildi
- [ ] Contract'lar verify edildi (Etherscan/Basescan)
- [ ] Contract adresleri env'de tanımlı
- [ ] Audit raporu mevcut (mainnet için)

### Monitoring

- [ ] Health check endpoint'i çalışıyor (`/health`)
- [ ] Logging yapılandırıldı (JSON format)
- [ ] Error tracking aktif (Sentry)
- [ ] Metrics dashboard kuruldu

---

## Deployment Komutları

### Docker ile Deploy

```bash
# Build
docker build -t sardis-api:latest .

# Run
docker run -d \
  --name sardis-api \
  --env-file .env.production \
  -p 8000:8000 \
  sardis-api:latest
```

### Railway ile Deploy

```bash
# Railway CLI
railway login
railway link
railway up
```

### Vercel ile Deploy (Landing Page)

```bash
cd landing
vercel --prod
```

---

## Testnet'ten Mainnet'e Geçiş

1. **Staging Environment Oluştur**
   - Testnet contract'larını kullanarak full test
   - Load testing yap

2. **Smart Contract Audit**
   - Mainnet deployment öncesi güvenlik auditi

3. **Gradual Rollout**
   - Önce düşük limitlerle başla
   - Transaction limitlerini yavaş yavaş artır

4. **Monitoring İntensify**
   - İlk hafta 7/24 monitoring
   - Anomaly detection aktif

---

## Sorun Giderme

### Database Bağlantı Hatası
```bash
# SSL sertifikası sorunu
DATABASE_URL=...?sslmode=require&sslrootcert=/path/to/ca.crt
```

### Turnkey Signing Hatası
```bash
# API key format kontrolü
# Public key 02 veya 03 ile başlamalı (compressed P256)
# Private key 0x ile başlamalı (hex)
```

### RPC Rate Limit
```bash
# Birden fazla RPC provider kullan
# Alchemy + Infura fallback
SARDIS_BASE_RPC_URLS=https://alchemy...,https://infura...
```

---

## Destek

- GitHub Issues: https://github.com/sardis-project/sardis/issues
- Discord: https://discord.gg/sardis
- Email: support@sardis.sh
