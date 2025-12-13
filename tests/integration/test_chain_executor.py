#!/usr/bin/env python3
"""
Chain Executor Entegrasyon Testi

Bu script, ChainExecutor'ın temel fonksiyonlarını test eder.

Kullanım:
    python tests/integration/test_chain_executor.py

Modlar:
    - Simulated (varsayılan): Gerçek blockchain işlemi yapılmaz
    - Live: Gerçek testnet işlemleri (--live flag ile)
"""
import asyncio
import argparse
import secrets
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Proje kökünü path'e ekle
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def print_header(title: str):
    width = 70
    print("\n" + "=" * width)
    print(f"  {title}".center(width))
    print("=" * width)


def print_section(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


async def test_chain_executor(live_mode: bool = False, chain: str = "base_sepolia"):
    """Chain Executor testleri."""
    print_header("CHAIN EXECUTOR ENTEGRASYON TESTİ")
    
    print(f"\n  Mode: {'🔴 LIVE' if live_mode else '🟢 SIMULATED'}")
    print(f"  Chain: {chain}")
    
    # Import
    try:
        from sardis_v2_core import load_settings, PaymentMandate
        from sardis_v2_core.mandates import VCProof
        from sardis_chain import ChainExecutor, CHAIN_CONFIGS, STABLECOIN_ADDRESSES
    except ImportError as e:
        print(f"\n❌ Import hatası: {e}")
        print("   Paketlerin kurulu olduğundan emin olun:")
        print("   pip install -e packages/sardis-core packages/sardis-chain")
        return False
    
    # Settings
    print_section("1. Konfigürasyon")
    settings = load_settings()
    settings.chain_mode = "live" if live_mode else "simulated"
    
    print(f"  Environment: {settings.environment}")
    print(f"  Chain Mode: {settings.chain_mode}")
    
    # Chain info
    chain_config = CHAIN_CONFIGS.get(chain, {})
    print(f"  Chain ID: {chain_config.get('chain_id', 'N/A')}")
    print(f"  RPC URL: {chain_config.get('rpc_url', 'N/A')[:50]}...")
    
    # Token addresses
    tokens = STABLECOIN_ADDRESSES.get(chain, {})
    print(f"  Tokens: {', '.join(tokens.keys()) if tokens else 'None'}")
    
    # Create executor
    print_section("2. ChainExecutor Oluştur")
    try:
        executor = ChainExecutor(settings)
        print("  ✓ ChainExecutor başarıyla oluşturuldu")
    except Exception as e:
        print(f"  ❌ ChainExecutor oluşturulamadı: {e}")
        return False
    
    # Create test mandate
    print_section("3. Test Payment Mandate")
    now = datetime.now(timezone.utc)
    destination = "0x" + secrets.token_hex(20)
    amount = 10_000_000  # 10 USDC
    
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
        amount_minor=amount,
        token="USDC",
        chain=chain,
        destination=destination,
        audit_hash=secrets.token_hex(32),
        proof=VCProof(
            type="Ed25519Signature2020",
            created=now.isoformat(),
            verification_method="did:web:agent.example.com#key-1",
            proof_purpose="authentication",
            proof_value="test_signature",
        ),
    )
    
    print(f"  Mandate ID: {mandate.mandate_id}")
    print(f"  Amount: {mandate.amount_minor / 1_000_000} USDC")
    print(f"  Token: {mandate.token}")
    print(f"  Chain: {mandate.chain}")
    print(f"  Destination: {destination[:20]}...")
    
    # Gas estimation (only works with live RPC)
    print_section("4. Gas Tahmini")
    try:
        gas_estimate = await executor.estimate_gas(mandate)
        print(f"  ✓ Gas Limit: {gas_estimate.gas_limit}")
        print(f"  ✓ Gas Price: {gas_estimate.gas_price_gwei} gwei")
        print(f"  ✓ Max Fee: {gas_estimate.max_fee_gwei} gwei")
        print(f"  ✓ Priority Fee: {gas_estimate.max_priority_fee_gwei} gwei")
        print(f"  ✓ Estimated Cost: {gas_estimate.estimated_cost_wei} wei")
    except Exception as e:
        print(f"  ⚠ Gas tahmini başarısız: {e}")
        print("    (Simulated modda veya RPC bağlantı hatası olabilir)")
    
    # Dispatch payment
    print_section("5. Payment Dispatch")
    try:
        receipt = await executor.dispatch_payment(mandate)
        print(f"  ✅ Payment başarılı!")
        print(f"  TX Hash: {receipt.tx_hash}")
        print(f"  Chain: {receipt.chain}")
        print(f"  Block: {receipt.block_number}")
        print(f"  Audit Anchor: {receipt.audit_anchor}")
        
        if live_mode:
            explorer = chain_config.get("explorer", "")
            if explorer:
                print(f"\n  🔗 Explorer: {explorer}/tx/{receipt.tx_hash}")
    except Exception as e:
        print(f"  ❌ Payment başarısız: {e}")
        await executor.close()
        return False
    
    # Transaction status check (live mode only)
    if live_mode and receipt.tx_hash:
        print_section("6. Transaction Status")
        try:
            status = await executor.get_transaction_status(receipt.tx_hash, chain)
            print(f"  Status: {status.value}")
        except Exception as e:
            print(f"  ⚠ Status kontrol edilemedi: {e}")
    
    # Cleanup
    print_section("7. Cleanup")
    await executor.close()
    print("  ✓ Kaynaklar serbest bırakıldı")
    
    print_header("TEST TAMAMLANDI")
    
    if not live_mode:
        print("\n⚠️  Not: Bu bir SIMULATED test idi.")
        print("   Gerçek transaction için --live flag kullanın.")
    
    return True


async def test_rpc_connectivity():
    """RPC bağlantı testi."""
    print_header("RPC BAĞLANTI TESTİ")
    
    from sardis_chain.executor import CHAIN_CONFIGS, ChainRPCClient
    
    results = {}
    
    for chain_name, config in CHAIN_CONFIGS.items():
        if config.get("is_solana"):
            continue  # Solana'yı atla
        
        rpc_url = config.get("rpc_url", "")
        print(f"\n  {chain_name}...")
        
        try:
            client = ChainRPCClient(rpc_url, chain=chain_name)
            block = await client.get_block_number()
            await client.close()
            
            print(f"    ✅ Block #{block}")
            results[chain_name] = True
        except Exception as e:
            print(f"    ❌ {str(e)[:50]}")
            results[chain_name] = False
    
    print_header("ÖZET")
    
    for chain, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {chain}")
    
    return all(results.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chain Executor Entegrasyon Testi")
    parser.add_argument("--live", action="store_true", help="Live mod (gerçek transaction)")
    parser.add_argument("--chain", default="base_sepolia", help="Hedef chain")
    parser.add_argument("--rpc-test", action="store_true", help="Sadece RPC bağlantı testi")
    
    args = parser.parse_args()
    
    if args.rpc_test:
        success = asyncio.run(test_rpc_connectivity())
    else:
        if args.live:
            print("\n⚠️  UYARI: LIVE mod seçildi!")
            print("   Gerçek testnet transaction'ı yapılacak.")
            confirm = input("   Devam etmek istiyor musunuz? (yes/no): ")
            if confirm.lower() != "yes":
                print("   İptal edildi.")
                sys.exit(0)
        
        success = asyncio.run(test_chain_executor(
            live_mode=args.live,
            chain=args.chain,
        ))
    
    sys.exit(0 if success else 1)




