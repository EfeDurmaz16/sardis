#!/usr/bin/env python3
"""
API Server Demo
===============

This example demonstrates the full Sardis API workflow:
1. Start the API server
2. Create an agent via REST API
3. Execute a payment via the SDK
4. Query the transaction ledger

Prerequisites:
    pip install httpx uvicorn

Run:
    # Terminal 1: Start the API server
    uvicorn sardis_api.main:create_app --factory --port 8000

    # Terminal 2: Run this demo
    python examples/api_demo.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, ".")

# Check if httpx is available
try:
    import httpx
except ImportError:
    print("Error: httpx not installed")
    print("Run: pip install httpx")
    sys.exit(1)


API_BASE = os.getenv("SARDIS_API_URL", "http://localhost:8000")


async def main():
    print("=" * 60)
    print("Sardis Payment Protocol - API Demo")
    print("=" * 60)
    print()
    print(f"API Base URL: {API_BASE}")
    print()
    
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        
        # =========================================
        # Step 1: Health Check
        # =========================================
        print("STEP 1: Health Check")
        print("-" * 40)
        
        try:
            response = await client.get("/health")
            if response.status_code == 200:
                data = response.json()
                print(f"  Status: {data.get('status', 'unknown')}")
                print(f"  Environment: {data.get('environment', 'unknown')}")
                print(f"  Chain Mode: {data.get('chain_mode', 'unknown')}")
                print("  ✓ API is running!")
            else:
                print(f"  ✗ API returned status {response.status_code}")
                print("  Make sure the API server is running:")
                print("    uvicorn sardis_api.main:create_app --factory --port 8000")
                return
        except httpx.ConnectError:
            print("  ✗ Could not connect to API server")
            print()
            print("  Please start the API server first:")
            print("    uvicorn sardis_api.main:create_app --factory --port 8000")
            print()
            print("  Then run this demo again.")
            return
        print()
        
        # =========================================
        # Step 2: Execute a Payment
        # =========================================
        print("STEP 2: Execute Payment via API")
        print("-" * 40)
        
        import time
        mandate = {
            "mandate_id": f"demo_mandate_{int(time.time())}",
            "issuer": "demo_user",
            "subject": "demo_wallet",
            "destination": "0x742d35Cc6634C0532925a3b844Bc9e7595f8fDB1",
            "amount_minor": 500,  # $5.00 in cents
            "token": "USDC",
            "chain": "base_sepolia",
            "expires_at": int(time.time()) + 300,
        }
        
        print(f"  Mandate ID: {mandate['mandate_id']}")
        print(f"  Amount: ${mandate['amount_minor'] / 100:.2f} USDC")
        print(f"  Destination: {mandate['destination'][:20]}...")
        print()
        
        try:
            response = await client.post(
                "/api/v2/mandates/execute",
                json={"mandate": mandate}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("  ✓ Payment executed!")
                print(f"    Ledger TX: {result.get('ledger_tx_id', 'N/A')}")
                print(f"    Chain TX: {result.get('chain_tx_hash', 'N/A')}")
                print(f"    Chain: {result.get('chain', 'N/A')}")
            else:
                data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                print(f"  Payment response: {response.status_code}")
                print(f"  Details: {data.get('detail', response.text[:100])}")
        except Exception as e:
            print(f"  Error: {e}")
        print()
        
        # =========================================
        # Step 3: Query Ledger
        # =========================================
        print("STEP 3: Query Transaction Ledger")
        print("-" * 40)
        
        try:
            response = await client.get("/api/v2/ledger/recent?limit=5")
            
            if response.status_code == 200:
                data = response.json()
                entries = data.get("entries", [])
                print(f"  Recent transactions: {len(entries)}")
                for entry in entries[:3]:
                    print(f"    • {entry.get('tx_id', 'N/A')[:20]}...")
            else:
                print(f"  Ledger query: {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
        print()
        
        # =========================================
        # Step 4: Check Supported Chains
        # =========================================
        print("STEP 4: Check Supported Chains")
        print("-" * 40)
        
        try:
            response = await client.get("/api/v2/transactions/chains")
            
            if response.status_code == 200:
                data = response.json()
                chains = data.get("chains", [])
                print(f"  Supported chains: {len(chains)}")
                for chain in chains[:5]:
                    print(f"    • {chain.get('name', 'unknown')}: Chain ID {chain.get('chain_id', 'N/A')}")
            else:
                print(f"  Chains query: {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
        print()
        
        # =========================================
        # Summary
        # =========================================
        print("=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print()
        print("The Sardis API provides:")
        print("  • RESTful endpoints for payment execution")
        print("  • Multi-chain stablecoin support")
        print("  • Transaction ledger with audit trail")
        print("  • Policy enforcement and compliance checks")
        print()
        print("API Documentation: http://localhost:8000/api/v2/docs")


if __name__ == "__main__":
    asyncio.run(main())
