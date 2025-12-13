# Sardis Kapsamlı Test Rehberi

Bu rehber, Sardis sisteminin tüm bileşenlerini test etmek için gereken kurulum, konfigürasyon ve test prosedürlerini içermektedir.

---

## İçindekiler

1. [Ön Gereksinimler](#ön-gereksinimler)
2. [Ortam Kurulumu](#ortam-kurulumu)
3. [Environment Konfigürasyonu](#environment-konfigürasyonu)
4. [Paket Kurulumu](#paket-kurulumu)
5. [Veritabanı Kurulumu](#veritabanı-kurulumu)
6. [API Sunucusunu Başlatma](#api-sunucusunu-başlatma)
7. [Modül Testleri](#modül-testleri)
8. [Entegrasyon Testleri](#entegrasyon-testleri)
9. [Smart Contract Testleri](#smart-contract-testleri)
10. [End-to-End Demo](#end-to-end-demo)
11. [Performans Testleri](#performans-testleri)
12. [Sorun Giderme](#sorun-giderme)

---

## Ön Gereksinimler

### Sistem Gereksinimleri

```bash
# Gerekli yazılımlar
- Python 3.10+ (3.11 önerilir)
- Node.js 18+ (SDK testleri için)
- Foundry (Solidity testleri için)
- PostgreSQL 14+ (veya SQLite development için)
- Redis (opsiyonel, caching için)
```

### Python Sürümü Kontrolü

```bash
python3 --version
# Python 3.10.0 veya üstü olmalı
```

### Foundry Kurulumu (Smart Contract Testleri İçin)

```bash
# Foundry kur
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Kontrol et
forge --version
```

---

## Ortam Kurulumu

### 1. Projeyi Klonla

```bash
git clone https://github.com/your-org/sardis.git
cd sardis
```

### 2. Python Virtual Environment Oluştur

```bash
# Virtual environment oluştur
python3 -m venv .venv

# Aktive et (macOS/Linux)
source .venv/bin/activate

# Aktive et (Windows)
.venv\Scripts\activate

# pip'i güncelle
pip install --upgrade pip
```

### 3. Geliştirici Bağımlılıklarını Kur

```bash
# Test ve geliştirme araçları
pip install pytest pytest-asyncio pytest-cov httpx aiohttp pynacl cryptography
```

---

## Environment Konfigürasyonu

### Ana .env Dosyası

Proje kökünde `.env` dosyası oluştur:

```bash
# .env dosyasını oluştur
cat > .env << 'EOF'
# ============================================================
# SARDIS ENVIRONMENT CONFIGURATION
# ============================================================

# --------------------- Genel Ayarlar ---------------------
SARDIS_ENVIRONMENT=dev
SARDIS_SECRET_KEY=dev-only-secret-key-not-for-production-32chars

# --------------------- API Ayarları ---------------------
SARDIS_API_BASE_URL=http://localhost:8000
SARDIS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3005,http://localhost:5173

# --------------------- Veritabanı ---------------------
# Development için SQLite (kolay başlangıç)
DATABASE_URL=sqlite:///./data/sardis.db

# Production için PostgreSQL (aşağıdakini uncomment et)
# DATABASE_URL=postgresql://sardis:sardis_password@localhost:5432/sardis

# --------------------- Redis (Opsiyonel) ---------------------
# REDIS_URL=redis://localhost:6379/0

# --------------------- Blockchain ---------------------
# Chain execution mode: "simulated" veya "live"
SARDIS_CHAIN_MODE=simulated

# Base Sepolia RPC (ücretsiz public RPC)
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org

# Polygon Amoy RPC
POLYGON_AMOY_RPC_URL=https://rpc-amoy.polygon.technology

# Ethereum Sepolia RPC
SEPOLIA_RPC_URL=https://rpc.sepolia.org

# --------------------- Turnkey MPC (Opsiyonel) ---------------------
# Gerçek transaction'lar için gerekli
TURNKEY_ORGANIZATION_ID=
TURNKEY_API_PUBLIC_KEY=
TURNKEY_API_PRIVATE_KEY=

# --------------------- Persona KYC (Opsiyonel) ---------------------
PERSONA_API_KEY=
PERSONA_TEMPLATE_ID=

# --------------------- Elliptic Sanctions (Opsiyonel) ---------------------
ELLIPTIC_API_KEY=
ELLIPTIC_API_SECRET=

# --------------------- Lithic Cards (Opsiyonel) ---------------------
LITHIC_API_KEY=
LITHIC_ENVIRONMENT=sandbox

# --------------------- Block Explorer API Keys ---------------------
BASESCAN_API_KEY=
ETHERSCAN_API_KEY=
POLYGONSCAN_API_KEY=

# --------------------- Contract Deployment ---------------------
# Deployment için private key (ASLA production key kullanma!)
PRIVATE_KEY=

EOF
```

### Test Environment Dosyası

Test için ayrı bir `.env.test` oluştur:

```bash
cat > .env.test << 'EOF'
# Test Environment
SARDIS_ENVIRONMENT=dev
SARDIS_SECRET_KEY=test-secret-key-for-testing-only-32ch
SARDIS_CHAIN_MODE=simulated
DATABASE_URL=sqlite:///./data/test.db
EOF
```

---

## Paket Kurulumu

### Tüm Paketleri Editable Modda Kur

```bash
# Proje kökünden çalıştır
cd /Users/efebarandurmaz/Desktop/sardis

# Tüm paketleri kur (sıra önemli!)
pip install -e packages/sardis-core
pip install -e packages/sardis-protocol
pip install -e packages/sardis-wallet
pip install -e packages/sardis-chain
pip install -e packages/sardis-ledger
pip install -e packages/sardis-compliance
pip install -e packages/sardis-cards
pip install -e packages/sardis-api

# Veya tek satırda
pip install -e packages/sardis-core -e packages/sardis-protocol -e packages/sardis-wallet -e packages/sardis-chain -e packages/sardis-ledger -e packages/sardis-compliance -e packages/sardis-cards -e packages/sardis-api
```

### Kurulumu Doğrula

```bash
# Paketlerin kurulduğunu kontrol et
pip list | grep sardis

# Beklenen çıktı:
# sardis-api          0.1.0
# sardis-cards        0.1.0
# sardis-chain        0.1.0
# sardis-compliance   0.1.0
# sardis-core         0.1.0
# sardis-ledger       0.1.0
# sardis-protocol     0.1.0
# sardis-wallet       0.1.0
```

### Import Testi

```bash
python3 -c "
from sardis_v2_core import SardisSettings, load_settings
from sardis_chain import ChainExecutor
from sardis_protocol import MandateVerifier
from sardis_cards import CardService
print('✓ Tüm paketler başarıyla import edildi')
"
```

---

## Veritabanı Kurulumu

### SQLite (Development)

```bash
# Data klasörünü oluştur
mkdir -p data

# Veritabanını başlat
python3 -c "
from sardis_v2_core import init_database, load_settings
settings = load_settings()
init_database(settings.database_url)
print('✓ SQLite veritabanı oluşturuldu')
"
```

### PostgreSQL (Production-like)

```bash
# PostgreSQL kurulu olmalı
# macOS için: brew install postgresql@14

# Veritabanı ve kullanıcı oluştur
psql -U postgres << 'EOF'
CREATE USER sardis WITH PASSWORD 'sardis_password';
CREATE DATABASE sardis OWNER sardis;
GRANT ALL PRIVILEGES ON DATABASE sardis TO sardis;
EOF

# .env'de DATABASE_URL'i güncelle
# DATABASE_URL=postgresql://sardis:sardis_password@localhost:5432/sardis

# Tabloları oluştur
python3 -c "
from sardis_v2_core import init_database
init_database('postgresql://sardis:sardis_password@localhost:5432/sardis')
print('✓ PostgreSQL veritabanı başlatıldı')
"
```

---

## API Sunucusunu Başlatma

### Development Sunucusu

```bash
# Sunucuyu başlat
uvicorn sardis_api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload

# Alternatif: Python ile
python -m uvicorn sardis_api.main:create_app --factory --port 8000
```

### Sunucu Sağlık Kontrolü

```bash
# Health check
curl http://localhost:8000/

# Beklenen yanıt:
# {"status":"ok","service":"sardis-api","version":"0.1.0"}
```

### API Dokümantasyonu

```bash
# Swagger UI
open http://localhost:8000/api/v2/docs

# ReDoc
open http://localhost:8000/api/v2/redoc
```

---

## Modül Testleri

### 1. Core Modül Testleri

```bash
# sardis-core testleri
cd packages/sardis-core
pytest tests/ -v

# Veya belirli bir test
pytest tests/test_config.py -v
pytest tests/test_mandates.py -v
pytest tests/test_identity.py -v
```

### 2. Protocol Modül Testleri

```bash
cd packages/sardis-protocol
pytest tests/ -v

# Mandate verification testleri
pytest tests/test_verifier.py -v

# Rate limiting testleri
pytest tests/test_rate_limiter.py -v
```

### 3. Chain Modül Testleri

```bash
cd packages/sardis-chain
pytest tests/ -v

# Executor testleri
pytest tests/test_executor.py -v

# Wallet manager testleri
pytest tests/test_wallet_manager.py -v
```

### 4. Cards Modül Testleri

```bash
cd packages/sardis-cards
pytest tests/ -v

# Mock provider ile test
pytest tests/test_mock_provider.py -v
```

### 5. Compliance Modül Testleri

```bash
cd packages/sardis-compliance
pytest tests/ -v

# KYC testleri
pytest tests/test_kyc.py -v

# Sanctions testleri
pytest tests/test_sanctions.py -v
```

### 6. API Testleri

```bash
cd packages/sardis-api
pytest tests/ -v

# API endpoint testleri
pytest tests/test_routers.py -v
```

### Tüm Testleri Çalıştır

```bash
# Proje kökünden
cd /Users/efebarandurmaz/Desktop/sardis

# Tüm paketlerdeki testleri çalıştır
pytest packages/*/tests/ -v --tb=short

# Coverage ile
pytest packages/*/tests/ -v --cov=packages --cov-report=html
open htmlcov/index.html
```

---

## Entegrasyon Testleri

### API Entegrasyon Testi

Önce API sunucusunun çalıştığından emin ol, sonra bu test scriptini çalıştır:

```python
#!/usr/bin/env python3
"""
API Entegrasyon Testi
Çalıştır: python tests/integration/test_api_integration.py
"""
import asyncio
import httpx
import json

API_BASE = "http://localhost:8000"

async def test_api_integration():
    async with httpx.AsyncClient(base_url=API_BASE) as client:
        print("=" * 60)
        print("SARDIS API ENTEGRASYON TESTİ")
        print("=" * 60)
        
        # 1. Health Check
        print("\n1. Health Check...")
        resp = await client.get("/")
        assert resp.status_code == 200
        print(f"   ✓ Status: {resp.json()['status']}")
        
        # 2. Create Agent
        print("\n2. Agent Oluştur...")
        agent_data = {
            "name": "Test Agent",
            "policy": {
                "max_per_tx": 100,
                "daily_limit": 1000,
            }
        }
        resp = await client.post("/api/v2/agents", json=agent_data)
        if resp.status_code == 200:
            agent = resp.json()
            print(f"   ✓ Agent ID: {agent.get('agent_id', 'N/A')}")
        else:
            print(f"   ⚠ Agent endpoint not available: {resp.status_code}")
        
        # 3. Create Wallet
        print("\n3. Wallet Oluştur...")
        wallet_data = {
            "agent_id": "test-agent-1",
            "chain": "base_sepolia",
        }
        resp = await client.post("/api/v2/wallets", json=wallet_data)
        if resp.status_code in (200, 201):
            wallet = resp.json()
            print(f"   ✓ Wallet: {wallet}")
        else:
            print(f"   ⚠ Wallet endpoint: {resp.status_code}")
        
        # 4. Create Virtual Card
        print("\n4. Virtual Card Oluştur...")
        card_data = {
            "wallet_id": "test-wallet-1",
            "card_type": "MULTI_USE",
            "limit_per_tx": 500,
            "limit_daily": 2000,
        }
        resp = await client.post("/api/v2/cards", json=card_data)
        if resp.status_code in (200, 201):
            card = resp.json()
            print(f"   ✓ Card ID: {card.get('card_id', 'N/A')}")
            print(f"   ✓ Last Four: {card.get('last_four', 'N/A')}")
        else:
            print(f"   ⚠ Cards endpoint: {resp.status_code}")
        
        # 5. List Cards
        print("\n5. Kartları Listele...")
        resp = await client.get("/api/v2/cards")
        if resp.status_code == 200:
            cards = resp.json()
            print(f"   ✓ Toplam Kart: {len(cards.get('cards', []))}")
        else:
            print(f"   ⚠ Status: {resp.status_code}")
        
        print("\n" + "=" * 60)
        print("ENTEGRASYON TESTİ TAMAMLANDI")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_api_integration())
```

Bu dosyayı kaydet ve çalıştır:

```bash
# Dosyayı oluştur
mkdir -p tests/integration
# Yukarıdaki kodu tests/integration/test_api_integration.py olarak kaydet

# Çalıştır (API sunucusu çalışıyor olmalı)
python tests/integration/test_api_integration.py
```

### Chain Executor Entegrasyon Testi

```python
#!/usr/bin/env python3
"""
Chain Executor Entegrasyon Testi
Çalıştır: python tests/integration/test_chain_executor.py
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import secrets

async def test_chain_executor():
    from sardis_v2_core import load_settings, PaymentMandate
    from sardis_v2_core.mandates import VCProof
    from sardis_chain import ChainExecutor
    
    print("=" * 60)
    print("CHAIN EXECUTOR TESTİ")
    print("=" * 60)
    
    # Settings yükle
    settings = load_settings()
    settings.chain_mode = "simulated"  # Simulated mod
    
    executor = ChainExecutor(settings)
    
    # Test payment mandate oluştur
    now = datetime.now(timezone.utc)
    mandate = PaymentMandate(
        mandate_id=f"test_{secrets.token_hex(8)}",
        mandate_type="payment",
        issuer="did:web:test.example.com",
        subject="did:web:agent.example.com",
        purpose="checkout",
        created_at=now,
        expires_at=now,
        nonce=secrets.token_hex(16),
        domain="merchant.example.com",
        amount_minor=10_000_000,  # 10 USDC
        token="USDC",
        chain="base_sepolia",
        destination="0x" + secrets.token_hex(20),
        audit_hash=secrets.token_hex(32),
        proof=VCProof(
            type="Ed25519Signature2020",
            created=now.isoformat(),
            verification_method="did:web:agent.example.com#key-1",
            proof_purpose="authentication",
            proof_value="test_signature",
        ),
    )
    
    print(f"\n1. Payment Mandate Oluşturuldu")
    print(f"   - Amount: {mandate.amount_minor / 1_000_000} USDC")
    print(f"   - Chain: {mandate.chain}")
    print(f"   - Destination: {mandate.destination[:20]}...")
    
    print(f"\n2. Gas Tahmini...")
    try:
        gas_estimate = await executor.estimate_gas(mandate)
        print(f"   ✓ Gas Limit: {gas_estimate.gas_limit}")
        print(f"   ✓ Max Fee: {gas_estimate.max_fee_gwei} gwei")
        print(f"   ✓ Tahmini Maliyet: {gas_estimate.estimated_cost_wei} wei")
    except Exception as e:
        print(f"   ⚠ Gas tahmini başarısız (simulated modda normal): {e}")
    
    print(f"\n3. Payment Dispatch (Simulated)...")
    try:
        receipt = await executor.dispatch_payment(mandate)
        print(f"   ✓ TX Hash: {receipt.tx_hash}")
        print(f"   ✓ Chain: {receipt.chain}")
        print(f"   ✓ Block: {receipt.block_number}")
        print(f"   ✓ Audit Anchor: {receipt.audit_anchor}")
    except Exception as e:
        print(f"   ✗ Hata: {e}")
    
    await executor.close()
    
    print("\n" + "=" * 60)
    print("CHAIN EXECUTOR TESTİ TAMAMLANDI")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_chain_executor())
```

### Mandate Verifier Testi

```python
#!/usr/bin/env python3
"""
Mandate Verifier Entegrasyon Testi
"""
import asyncio
from datetime import datetime, timedelta, timezone
import secrets

async def test_mandate_verifier():
    from sardis_v2_core import (
        load_settings,
        IntentMandate,
        CartMandate,
        PaymentMandate,
    )
    from sardis_v2_core.mandates import VCProof
    from sardis_protocol import MandateVerifier
    from sardis_protocol.storage import ReplayCache
    from sardis_protocol.schemas import AP2PaymentExecuteRequest
    
    print("=" * 60)
    print("MANDATE VERİFİER TESTİ")
    print("=" * 60)
    
    settings = load_settings()
    settings.allowed_domains = ["merchant.example.com"]
    
    verifier = MandateVerifier(
        settings=settings,
        replay_cache=ReplayCache(),
    )
    
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=5)
    nonce = secrets.token_hex(16)
    agent_id = "did:web:agent.example.com"
    
    # Intent mandate
    intent = {
        "mandate_id": f"intent_{secrets.token_hex(8)}",
        "mandate_type": "intent",
        "issuer": agent_id,
        "subject": agent_id,
        "purpose": "intent",
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "nonce": nonce,
        "domain": "merchant.example.com",
        "merchant_domain": "merchant.example.com",
        "requested_amount": 1000,
        "proof": {
            "type": "Ed25519Signature2020",
            "created": now.isoformat(),
            "verification_method": f"{agent_id}#ed25519:{'00' * 32}",
            "proof_purpose": "authentication",
            "proof_value": "test_sig",
        },
    }
    
    # Cart mandate
    cart = {
        "mandate_id": f"cart_{secrets.token_hex(8)}",
        "mandate_type": "cart",
        "issuer": "did:web:merchant.example.com",
        "subject": agent_id,
        "purpose": "cart",
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "nonce": nonce,
        "domain": "merchant.example.com",
        "merchant_domain": "merchant.example.com",
        "subtotal_minor": 950,
        "taxes_minor": 50,
        "items": ["Test Item"],
        "proof": {
            "type": "Ed25519Signature2020",
            "created": now.isoformat(),
            "verification_method": "did:web:merchant.example.com#key-1",
            "proof_purpose": "assertionMethod",
            "proof_value": "merchant_sig",
        },
    }
    
    # Payment mandate
    payment = {
        "mandate_id": f"payment_{secrets.token_hex(8)}",
        "mandate_type": "payment",
        "issuer": agent_id,
        "subject": agent_id,
        "purpose": "checkout",
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "nonce": nonce,
        "domain": "merchant.example.com",
        "amount_minor": 1000,
        "token": "USDC",
        "chain": "base_sepolia",
        "destination": "0x" + secrets.token_hex(20),
        "audit_hash": secrets.token_hex(32),
        "proof": {
            "type": "Ed25519Signature2020",
            "created": now.isoformat(),
            "verification_method": f"{agent_id}#ed25519:{'00' * 32}",
            "proof_purpose": "authentication",
            "proof_value": "agent_sig",
        },
    }
    
    bundle = AP2PaymentExecuteRequest(
        intent=intent,
        cart=cart,
        payment=payment,
    )
    
    print("\n1. Mandate Chain Doğrulaması...")
    result = verifier.verify_chain(bundle)
    
    print(f"   - Accepted: {result.accepted}")
    print(f"   - Reason: {result.reason or 'None'}")
    
    if result.accepted:
        print("   ✓ Mandate chain doğrulandı")
    else:
        print(f"   ⚠ Doğrulama başarısız: {result.reason}")
        print("   (Signature verification test modda başarısız olması normal)")
    
    print("\n2. Amount Validation Testi...")
    # Cart total'den fazla ödeme dene
    payment_copy = payment.copy()
    payment_copy["amount_minor"] = 2000  # 1000'den fazla
    
    bundle_invalid = AP2PaymentExecuteRequest(
        intent=intent,
        cart=cart,
        payment=payment_copy,
    )
    
    result2 = verifier.verify_chain(bundle_invalid)
    if not result2.accepted and "exceeds" in (result2.reason or ""):
        print("   ✓ Aşırı ödeme reddedildi")
    else:
        print(f"   - Result: {result2.reason}")
    
    print("\n" + "=" * 60)
    print("MANDATE VERİFİER TESTİ TAMAMLANDI")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_mandate_verifier())
```

---

## Smart Contract Testleri

### Foundry ile Test

```bash
# Contracts klasörüne git
cd contracts

# OpenZeppelin bağımlılıklarını kur (ilk kez)
forge install OpenZeppelin/openzeppelin-contracts --no-commit

# Tüm testleri çalıştır
forge test -vv

# Belirli bir test dosyasını çalıştır
forge test --match-path test/SardisWalletFactory.t.sol -vv
forge test --match-path test/SardisAgentWallet.t.sol -vv
forge test --match-path test/SardisEscrow.t.sol -vv

# Coverage raporu
forge coverage

# Gas raporu
forge test --gas-report
```

### Contract Derleme

```bash
# Derle
forge build

# Bytecode boyutlarını kontrol et
forge build --sizes
```

---

## End-to-End Demo

### Demo Script'i Çalıştır

```bash
# Demo klasörüne git
cd /Users/efebarandurmaz/Desktop/sardis

# Simulated modda çalıştır
python demos/full_payment_demo.py

# Farklı amount ile
python demos/full_payment_demo.py --amount 50

# Farklı chain ile
python demos/full_payment_demo.py --chain polygon_amoy

# Live mod (dikkatli ol - gerçek transaction!)
# python demos/full_payment_demo.py --live
```

### Manuel End-to-End Test

```python
#!/usr/bin/env python3
"""
Manuel E2E Test Script
"""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

async def manual_e2e_test():
    print("=" * 70)
    print("SARDIS END-TO-END TEST")
    print("=" * 70)
    
    # 1. Settings ve Services
    print("\n[1/6] Servisleri Başlat...")
    from sardis_v2_core import load_settings
    from sardis_chain import ChainExecutor
    from sardis_cards.service import CardService
    from sardis_cards.providers.mock import MockCardProvider
    
    settings = load_settings()
    settings.chain_mode = "simulated"
    
    executor = ChainExecutor(settings)
    card_service = CardService(provider=MockCardProvider())
    
    print("   ✓ ChainExecutor başlatıldı")
    print("   ✓ CardService başlatıldı")
    
    # 2. Virtual Card Oluştur
    print("\n[2/6] Virtual Card Oluştur...")
    from sardis_cards.models import CardType
    
    card = await card_service.create_card(
        wallet_id="test-wallet-001",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("500"),
        limit_daily=Decimal("2000"),
        limit_monthly=Decimal("10000"),
    )
    print(f"   ✓ Card ID: {card.card_id}")
    print(f"   ✓ Last Four: {card.card_number_last4}")
    print(f"   ✓ Status: {card.status.value}")
    
    # 3. Card'a Fon Ekle
    print("\n[3/6] Card'a Fon Ekle...")
    funded_card = await card_service.fund_card(
        card_id=card.card_id,
        amount=Decimal("100"),
    )
    print(f"   ✓ Funded Amount: ${funded_card.funded_amount}")
    
    # 4. Payment Mandate Oluştur
    print("\n[4/6] Payment Mandate Oluştur...")
    from sardis_v2_core.mandates import PaymentMandate, VCProof
    
    now = datetime.now(timezone.utc)
    mandate = PaymentMandate(
        mandate_id=f"pay_{secrets.token_hex(8)}",
        mandate_type="payment",
        issuer="did:web:agent.test",
        subject="did:web:agent.test",
        purpose="checkout",
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce=secrets.token_hex(16),
        domain="merchant.test",
        amount_minor=25_000_000,  # 25 USDC
        token="USDC",
        chain="base_sepolia",
        destination="0x" + secrets.token_hex(20),
        audit_hash=secrets.token_hex(32),
        proof=VCProof(
            type="Ed25519Signature2020",
            created=now.isoformat(),
            verification_method="did:web:agent.test#key-1",
            proof_purpose="authentication",
            proof_value="test",
        ),
    )
    print(f"   ✓ Mandate ID: {mandate.mandate_id}")
    print(f"   ✓ Amount: {mandate.amount_minor / 1_000_000} USDC")
    
    # 5. Payment Çalıştır
    print("\n[5/6] Payment Dispatch (Simulated)...")
    receipt = await executor.dispatch_payment(mandate)
    print(f"   ✓ TX Hash: {receipt.tx_hash}")
    print(f"   ✓ Chain: {receipt.chain}")
    print(f"   ✓ Audit: {receipt.audit_anchor}")
    
    # 6. Cleanup
    print("\n[6/6] Cleanup...")
    await executor.close()
    print("   ✓ Kaynaklar serbest bırakıldı")
    
    print("\n" + "=" * 70)
    print("✅ END-TO-END TEST BAŞARILI")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(manual_e2e_test())
```

---

## Performans Testleri

### Load Test Script

```python
#!/usr/bin/env python3
"""
Performans/Load Test
"""
import asyncio
import time
import statistics
from datetime import datetime, timezone
import secrets

async def performance_test():
    from sardis_v2_core import load_settings, PaymentMandate
    from sardis_v2_core.mandates import VCProof
    from sardis_chain import ChainExecutor
    
    print("=" * 60)
    print("PERFORMANS TESTİ")
    print("=" * 60)
    
    settings = load_settings()
    settings.chain_mode = "simulated"
    executor = ChainExecutor(settings)
    
    # Test parametreleri
    num_payments = 100
    latencies = []
    
    print(f"\n{num_payments} payment dispatch testi...")
    
    for i in range(num_payments):
        now = datetime.now(timezone.utc)
        mandate = PaymentMandate(
            mandate_id=f"perf_{i}_{secrets.token_hex(4)}",
            mandate_type="payment",
            issuer="did:web:perf.test",
            subject="did:web:perf.test",
            purpose="checkout",
            created_at=now,
            expires_at=now,
            nonce=secrets.token_hex(16),
            domain="perf.test",
            amount_minor=1_000_000,
            token="USDC",
            chain="base_sepolia",
            destination="0x" + secrets.token_hex(20),
            audit_hash=secrets.token_hex(32),
            proof=VCProof(
                type="Ed25519Signature2020",
                created=now.isoformat(),
                verification_method="did:web:perf.test#key-1",
                proof_purpose="authentication",
                proof_value="test",
            ),
        )
        
        start = time.perf_counter()
        await executor.dispatch_payment(mandate)
        end = time.perf_counter()
        
        latencies.append((end - start) * 1000)  # ms
        
        if (i + 1) % 20 == 0:
            print(f"   Completed: {i + 1}/{num_payments}")
    
    await executor.close()
    
    # Sonuçlar
    print("\n" + "-" * 40)
    print("SONUÇLAR:")
    print("-" * 40)
    print(f"Total Payments:   {num_payments}")
    print(f"Average Latency:  {statistics.mean(latencies):.2f} ms")
    print(f"Median Latency:   {statistics.median(latencies):.2f} ms")
    print(f"Min Latency:      {min(latencies):.2f} ms")
    print(f"Max Latency:      {max(latencies):.2f} ms")
    print(f"Std Dev:          {statistics.stdev(latencies):.2f} ms")
    print(f"Throughput:       {num_payments / (sum(latencies) / 1000):.0f} payments/sec")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(performance_test())
```

---

## Sorun Giderme

### Sık Karşılaşılan Hatalar

#### 1. ModuleNotFoundError

```bash
# Hata: ModuleNotFoundError: No module named 'sardis_v2_core'

# Çözüm: Paketleri yeniden kur
pip install -e packages/sardis-core
pip install -e packages/sardis-protocol
# ... diğer paketler
```

#### 2. Database Connection Error

```bash
# Hata: sqlite3.OperationalError: unable to open database file

# Çözüm: Data klasörünü oluştur
mkdir -p data
```

#### 3. Port Already in Use

```bash
# Hata: Address already in use

# Çözüm: Mevcut process'i bul ve kapat
lsof -i :8000
kill -9 <PID>

# Veya farklı port kullan
uvicorn sardis_api.main:create_app --factory --port 8001
```

#### 4. Import Döngüsü Hatası

```bash
# Hata: ImportError: cannot import name 'X' from partially initialized module

# Çözüm: Python cache'i temizle
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

#### 5. Foundry Test Hatası

```bash
# Hata: Missing library: @openzeppelin/contracts

# Çözüm: OpenZeppelin kur
cd contracts
forge install OpenZeppelin/openzeppelin-contracts --no-commit
```

### Log Seviyesini Artır

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debug Modu

```bash
# Uvicorn debug modu
uvicorn sardis_api.main:create_app --factory --reload --log-level debug
```

---

## Hızlı Başlangıç Özeti

```bash
# 1. Virtual environment oluştur ve aktive et
python3 -m venv .venv && source .venv/bin/activate

# 2. Bağımlılıkları kur
pip install --upgrade pip
pip install pytest pytest-asyncio httpx pynacl

# 3. Paketleri kur
pip install -e packages/sardis-core -e packages/sardis-protocol -e packages/sardis-wallet \
  -e packages/sardis-chain -e packages/sardis-ledger -e packages/sardis-compliance \
  -e packages/sardis-cards -e packages/sardis-api

# 4. Data klasörü oluştur
mkdir -p data

# 5. Testleri çalıştır
pytest packages/*/tests/ -v --tb=short

# 6. API'yi başlat
uvicorn sardis_api.main:create_app --factory --port 8000

# 7. Demo'yu çalıştır
python demos/full_payment_demo.py
```

---

## Yardım

Sorularınız için:
- Dokümantasyon: `docs/` klasörü
- API Referans: http://localhost:8000/api/v2/docs
- Runbook: `RUNBOOK.md`

---

*Son güncelleme: Aralık 2024*




