#!/usr/bin/env python3
"""
API Entegrasyon Testi

Bu script, Sardis API'nin temel endpointlerini test eder.

Kullanım:
    1. API sunucusunu başlat: uvicorn sardis_api.main:create_app --factory --port 8000
    2. Bu scripti çalıştır: python tests/integration/test_api_integration.py

Gereksinimler:
    - httpx paketi: pip install httpx
    - Çalışan API sunucusu
"""
import asyncio
import sys
from datetime import datetime

try:
    import httpx
except ImportError:
    print("httpx paketi gerekli: pip install httpx")
    sys.exit(1)

API_BASE = "http://localhost:8000"


async def test_health_check():
    """Health check endpoint testi."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        try:
            resp = await client.get("/")
            return resp.status_code == 200, resp.json()
        except httpx.ConnectError:
            return False, {"error": "API sunucusuna bağlanılamadı"}


async def test_api_docs():
    """API dokümantasyonu endpoint testi."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        try:
            resp = await client.get("/api/v2/docs")
            return resp.status_code == 200, {"docs_available": True}
        except Exception as e:
            return False, {"error": str(e)}


async def test_cards_endpoint():
    """Cards endpoint testi."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        # List cards
        try:
            resp = await client.get("/api/v2/cards")
            if resp.status_code == 200:
                return True, resp.json()
            return False, {"status_code": resp.status_code}
        except Exception as e:
            return False, {"error": str(e)}


async def test_create_card():
    """Kart oluşturma testi."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        card_data = {
            "wallet_id": f"test-wallet-{datetime.now().timestamp()}",
            "card_type": "MULTI_USE",
            "limit_per_tx": 500,
            "limit_daily": 2000,
            "limit_monthly": 10000,
        }
        
        try:
            resp = await client.post("/api/v2/cards", json=card_data)
            if resp.status_code in (200, 201):
                return True, resp.json()
            return False, {"status_code": resp.status_code, "detail": resp.text}
        except Exception as e:
            return False, {"error": str(e)}


async def run_all_tests():
    """Tüm testleri çalıştır."""
    print("=" * 70)
    print("SARDIS API ENTEGRASYON TESTLERİ")
    print("=" * 70)
    print(f"\nAPI Base: {API_BASE}")
    print(f"Zaman: {datetime.now().isoformat()}")
    print("-" * 70)
    
    tests = [
        ("Health Check", test_health_check),
        ("API Docs", test_api_docs),
        ("Cards List", test_cards_endpoint),
        ("Create Card", test_create_card),
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"\n📋 {name}...")
        try:
            success, data = await test_func()
            results.append((name, success))
            
            if success:
                print(f"   ✅ BAŞARILI")
                if isinstance(data, dict):
                    for key, value in list(data.items())[:3]:
                        print(f"      {key}: {value}")
            else:
                print(f"   ❌ BAŞARISIZ")
                print(f"      {data}")
        except Exception as e:
            results.append((name, False))
            print(f"   ❌ HATA: {e}")
    
    # Özet
    print("\n" + "=" * 70)
    print("ÖZET")
    print("-" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status}  {name}")
    
    print("-" * 70)
    print(f"Sonuç: {passed}/{total} test başarılı")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    print("\n⚠️  Not: API sunucusunun çalıştığından emin olun!")
    print("   Başlatmak için: uvicorn sardis_api.main:create_app --factory --port 8000\n")
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)






