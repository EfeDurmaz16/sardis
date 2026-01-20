#!/usr/bin/env python3
"""
Simple ETH transfer test using Turnkey MPC.
This test sends a tiny amount of ETH to verify Turnkey signing works.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "sardis-core" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sardis-chain" / "src"))

# Load environment variables
os.chdir(project_root)
from dotenv import load_dotenv
load_dotenv()

async def test_simple_eth_transfer():
    """Test a simple ETH transfer via Turnkey."""
    from sardis_chain.executor import TurnkeyMPCSigner, ChainRPCClient, TransactionRequest, CHAIN_CONFIGS
    from sardis_v2_core.config import load_settings
    
    print("\n🧪 Simple ETH Transfer Test\n")
    print("=" * 50)
    
    # Load settings
    settings = load_settings()
    
    print(f"Turnkey Org ID: {settings.turnkey.organization_id}")
    print(f"Turnkey Wallet ID: {settings.turnkey.default_wallet_id}")
    print(f"Chain Mode: {settings.chain_mode}")
    
    if settings.chain_mode != "live":
        print("\n⚠️  Simulated mode - skipping real transaction")
        return True
    
    # Initialize Turnkey signer
    print("\n1. Initializing Turnkey signer...")
    try:
        signer = TurnkeyMPCSigner(
            api_base=settings.turnkey.api_base,
            organization_id=settings.turnkey.organization_id,
            api_public_key=settings.turnkey.api_public_key,
            api_private_key=settings.turnkey.api_private_key,
        )
        print("   ✅ Signer initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize signer: {e}")
        return False
    
    # Get wallet address
    print("\n2. Getting wallet address...")
    try:
        wallet_id = settings.turnkey.default_wallet_id
        address = await signer.get_address(wallet_id, "ethereum_sepolia")
        print(f"   ✅ Address: {address}")
    except Exception as e:
        print(f"   ❌ Failed to get address: {e}")
        return False
    
    # Check balance
    print("\n3. Checking balance...")
    chain_config = CHAIN_CONFIGS["ethereum_sepolia"]
    rpc_client = ChainRPCClient(chain_config["rpc_url"], chain="ethereum_sepolia")
    
    try:
        balance = await rpc_client.get_balance(address)
        balance_eth = balance / 10**18
        print(f"   ✅ Balance: {balance_eth:.6f} ETH")
        
        if balance_eth < 0.001:
            print("   ⚠️  Balance too low for test")
            await rpc_client.close()
            return False
    except Exception as e:
        print(f"   ❌ Failed to get balance: {e}")
        await rpc_client.close()
        return False
    
    # Get nonce
    print("\n4. Getting nonce...")
    try:
        nonce = await rpc_client.get_nonce(address)
        print(f"   ✅ Nonce: {nonce}")
    except Exception as e:
        print(f"   ❌ Failed to get nonce: {e}")
        await rpc_client.close()
        return False
    
    # Get gas price
    print("\n5. Getting gas parameters...")
    try:
        gas_data = await rpc_client.get_gas_price()
        print(f"   ✅ Base Fee: {gas_data.get('base_fee', 0) / 10**9:.4f} gwei")
        print(f"   ✅ Max Fee: {gas_data.get('max_fee', 0) / 10**9:.4f} gwei")
    except Exception as e:
        print(f"   ⚠️  Could not get gas price: {e}")
        gas_data = {"max_fee": 50_000_000_000, "max_priority_fee": 1_000_000_000}
    
    # Create transaction request - send 0.0001 ETH to self
    print("\n6. Creating transaction...")
    tx = TransactionRequest(
        chain="ethereum_sepolia",
        to_address=address,  # Send to self
        value=100000000000000,  # 0.0001 ETH in wei
        data=b"",
        gas_limit=21000,  # Standard ETH transfer
        max_fee_per_gas=gas_data.get("max_fee", 50_000_000_000),
        max_priority_fee_per_gas=gas_data.get("max_priority_fee", 1_000_000_000),
        nonce=nonce,
    )
    print(f"   ✅ TX: Send 0.0001 ETH to self")
    
    # Sign transaction
    print("\n7. Signing transaction with Turnkey...")
    try:
        # Turnkey signWith accepts address (case-sensitive) or private key ID
        signed_tx = await signer.sign_transaction(address, tx)  # Use address, not wallet_id
        print(f"   ✅ Signed TX: {signed_tx[:40]}...")
    except Exception as e:
        print(f"   ❌ Failed to sign: {e}")
        await rpc_client.close()
        return False
    
    # Broadcast transaction
    print("\n8. Broadcasting transaction...")
    try:
        tx_hash = await rpc_client.broadcast_transaction(signed_tx)
        print(f"   ✅ TX Hash: {tx_hash}")
        print(f"\n   🔗 Explorer: https://sepolia.etherscan.io/tx/{tx_hash}")
    except Exception as e:
        print(f"   ❌ Failed to broadcast: {e}")
        await rpc_client.close()
        return False
    
    await rpc_client.close()
    print("\n✨ Test completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_simple_eth_transfer())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        sys.exit(1)
