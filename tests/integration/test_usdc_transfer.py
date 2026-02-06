#!/usr/bin/env python3
"""
USDC ERC20 Transfer Test using Turnkey MPC.
Tests ERC20 token transfers on Ethereum Sepolia.
"""
import asyncio
import os
import sys
from pathlib import Path

# Manual / live-network test: skip unless explicitly enabled.
import pytest

if os.getenv("SARDIS_RUN_LIVE_CHAIN_TESTS", "").strip().lower() not in {"1", "true", "yes", "on"}:
    pytest.skip(
        "Live chain integration test disabled (set SARDIS_RUN_LIVE_CHAIN_TESTS=1 to enable).",
        allow_module_level=True,
    )

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "sardis-core" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sardis-chain" / "src"))

# Environment variables must be provided explicitly by the test runner.
os.chdir(project_root)

# USDC Contract on Ethereum Sepolia (Circle official)
USDC_CONTRACT = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
USDC_DECIMALS = 6


def encode_transfer(to_address: str, amount: int) -> bytes:
    """Encode ERC20 transfer function call.
    
    transfer(address,uint256) = 0xa9059cbb
    """
    # Remove 0x prefix and pad to 32 bytes
    to_padded = to_address[2:].lower().zfill(64)
    amount_padded = hex(amount)[2:].zfill(64)
    
    return bytes.fromhex("a9059cbb" + to_padded + amount_padded)


async def get_usdc_balance(rpc_client, address: str) -> float:
    """Get USDC balance for an address."""
    # balanceOf(address) = 0x70a08231
    data = "0x70a08231000000000000000000000000" + address[2:].lower()
    
    result = await rpc_client._call("eth_call", [{"to": USDC_CONTRACT, "data": data}, "latest"])
    return int(result, 16) / 10**USDC_DECIMALS


async def test_usdc_transfer():
    """Test USDC ERC20 transfer via Turnkey MPC."""
    from sardis_chain.executor import TurnkeyMPCSigner, ChainRPCClient, TransactionRequest, CHAIN_CONFIGS
    from sardis_v2_core.config import load_settings
    
    print("\n🪙 USDC Transfer Test (Ethereum Sepolia)\n")
    print("=" * 50)
    
    # Load settings
    settings = load_settings()
    
    if settings.chain_mode != "live":
        print("⚠️  Simulated mode - skipping real transaction")
        return True
    
    # Initialize
    print("\n1. Initializing...")
    signer = TurnkeyMPCSigner(
        api_base=settings.turnkey.api_base,
        organization_id=settings.turnkey.organization_id,
        api_public_key=settings.turnkey.api_public_key,
        api_private_key=settings.turnkey.api_private_key,
    )
    print("   ✅ Turnkey signer ready")
    
    wallet_id = settings.turnkey.default_wallet_id
    address = await signer.get_address(wallet_id, "ethereum_sepolia")
    print(f"   ✅ Wallet: {address}")
    
    chain_config = CHAIN_CONFIGS["ethereum_sepolia"]
    rpc = ChainRPCClient(chain_config["rpc_url"], chain="ethereum_sepolia")
    
    # Check balances
    print("\n2. Checking balances...")
    
    eth_balance = await rpc.get_balance(address)
    usdc_balance = await get_usdc_balance(rpc, address)
    
    print(f"   ETH Balance: {eth_balance / 10**18:.6f} ETH")
    print(f"   USDC Balance: {usdc_balance:.2f} USDC")
    
    if usdc_balance < 1:
        print("\n   ⚠️  USDC balance too low!")
        print("   Please get test USDC from: https://faucet.circle.com/")
        print(f"   Address to fund: {address}")
        await rpc.close()
        return False
    
    if eth_balance < 0.001 * 10**18:
        print("\n   ⚠️  ETH balance too low for gas!")
        await rpc.close()
        return False
    
    # Prepare transfer - send 1 USDC to self
    print("\n3. Creating USDC transfer...")
    
    transfer_amount = 1 * 10**USDC_DECIMALS  # 1 USDC
    transfer_data = encode_transfer(address, transfer_amount)
    
    nonce = await rpc.get_nonce(address)
    
    tx = TransactionRequest(
        chain="ethereum_sepolia",
        to_address=USDC_CONTRACT,  # Call USDC contract
        value=0,  # No ETH sent
        data=transfer_data,
        gas_limit=100000,  # ERC20 transfers need more gas
        max_fee_per_gas=50_000_000_000,
        max_priority_fee_per_gas=1_000_000_000,
        nonce=nonce,
    )
    print(f"   ✅ Transfer: 1 USDC to self")
    
    # Sign with Turnkey
    print("\n4. Signing with Turnkey MPC...")
    try:
        signed_tx = await signer.sign_transaction(address, tx)
        print(f"   ✅ Signed: {signed_tx[:40]}...")
    except Exception as e:
        print(f"   ❌ Signing failed: {e}")
        await rpc.close()
        return False
    
    # Broadcast
    print("\n5. Broadcasting transaction...")
    try:
        tx_hash = await rpc.broadcast_transaction(signed_tx)
        print(f"   ✅ TX Hash: {tx_hash}")
        print(f"\n   🔗 Explorer: https://sepolia.etherscan.io/tx/{tx_hash}")
    except Exception as e:
        print(f"   ❌ Broadcast failed: {e}")
        await rpc.close()
        return False
    
    # Verify
    print("\n6. Verifying...")
    await asyncio.sleep(3)  # Wait for propagation
    
    new_usdc_balance = await get_usdc_balance(rpc, address)
    print(f"   New USDC Balance: {new_usdc_balance:.2f} USDC")
    
    await rpc.close()
    print("\n✨ USDC transfer test completed!")
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_usdc_transfer())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        sys.exit(1)
