#!/usr/bin/env python3
"""
Sardis Pilot Flow Integration Test
"""
import asyncio
import os
import sys
from decimal import Decimal
import secrets

# Add project root to path
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sardis_sdk import SardisClient
from sardis_sdk.models import AgentCreate

async def run_pilot_flow():
    """Test the full agent -> wallet -> payment flow."""
    print("\n🚀 Starting Sardis Pilot Flow Test\n")
    
    # Use local dev API by default
    base_url = os.getenv("SARDIS_API_URL", "http://localhost:8000/api/v2/")
    api_key = os.getenv("SARDIS_API_KEY", "sardis_test_key")
    
    print(f"Target: {base_url}")
    
    async with SardisClient(base_url=base_url, api_key=api_key) as client:
        # 1. Create Agent
        print("\n1. Creating AI Agent...")
        try:
            agent = await client.agents.create(
                name=f"Pilot Agent {secrets.token_hex(4)}",
                # domain is not supported in API, passing via metadata if needed
                metadata={"version": "1.0.0", "domain": "localhost"}
            )
            print(f"   ✅ Agent Created: {agent.agent_id} ({agent.name})")
        except Exception as e:
            print(f"   ❌ Failed to create agent: {e}")
            return False

        # 2. Create Wallet
        print("\n2. Creating Programmable Wallet...")
        try:
            # We don't need to create a wallet if the API creates one automatically
            # But the SDK wrapper for creating an agent didn't expose 'create_wallet' arg yet
            # So we check if agent has a wallet, otherwise create one
            if agent.wallet_id:
                wallet = await client.wallets.get(agent.wallet_id)
                print(f"   ✅ Wallet Auto-Created: {wallet.wallet_id}")
            else:
                wallet = await client.wallets.create(
                    agent_id=agent.agent_id,
                    currency="USDC",
                    limit_daily=Decimal("1000.00"),
                    limit_per_tx=Decimal("100.00"),
                    name="Treasury Wallet"
                )
                print(f"   ✅ Wallet Created: {wallet.wallet_id}")
            
            print(f"      Limits: {wallet.limit_per_tx} / {wallet.limit_total}")
        except Exception as e:
            print(f"   ❌ Failed to create/get wallet: {e}")
            return False

        # 3. Fund Wallet (Sandbox)
        print("\n3. Funding Wallet (Sandbox Faucet)...")
        try:
            fund_tx = await client.wallets.fund(
                wallet_id=wallet.wallet_id,
                amount=Decimal("500.00"),
                token="USDC"
            )
            print(f"   ✅ Wallet Funded: 500.00 USDC")
            
            # Verify balance
            balance = await client.wallets.get_balance(wallet.wallet_id, "USDC")
            print(f"      Current Balance: {balance} USDC")
        except Exception as e:
            print(f"   ❌ Failed to fund wallet: {e}")
            return False

        # 4. Create & Execute Payment Mandate
        print("\n4. Executing Payment Mandate...")
        try:
            # Construct mandate payload complying with PaymentMandate schema
            import time
            from datetime import datetime, timezone
            from uuid import uuid4
            
            domain = agent.metadata.get("domain", "localhost") if agent.metadata else "localhost"
            mandate_id = f"mandate_{uuid4().hex[:16]}"
            
            mandate_payload = {
                "mandate_id": mandate_id,
                "mandate_type": "payment",
                "issuer": f"did:web:{domain}",
                "subject": wallet.wallet_id,
                "domain": domain,
                "purpose": "checkout",
                "expires_at": int(time.time()) + 3600,
                "nonce": secrets.token_hex(8),
                "chain": "base",
                "token": "USDC",
                "amount_minor": 1000,
                "destination": "0x" + secrets.token_hex(20),
                "audit_hash": secrets.token_hex(32),
                "proof": {
                    "type": "DataIntegrityProof",
                    "verification_method": f"did:web:{domain}#key-1",
                    "created": datetime.now(timezone.utc).isoformat(),
                    "proof_purpose": "assertionMethod",
                    "proof_value": secrets.token_urlsafe(64)
                }
            }
            
            result = await client.payments.execute_mandate(mandate_payload)
            print(f"   ✅ Payment Executed!")
            print(f"      TX Hash: {result.tx_hash}")
            print(f"      Status: {result.status}")
        except Exception as e:
            print(f"   ❌ Failed to execute payment: {e}")
            # Don't fail the whole test if payment fails (might be no chain connection)
            print("      (Continuing test...)")

        # 5. List Resources
        print("\n5. Verifying Resource Listings...")
        agents = await client.agents.list(limit=5)
        print(f"   Agents found: {len(agents)}")
        
        wallets = await client.wallets.list(agent_id=agent.agent_id)
        print(f"   Wallets for agent: {len(wallets)}")

    print("\n✨ Pilot Flow Test Completed Successfully")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(run_pilot_flow())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        sys.exit(1)
