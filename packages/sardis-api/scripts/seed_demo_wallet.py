#!/usr/bin/env python3
"""
Seed Script: Populate a test wallet with $500 USDC for demo purposes.

Usage:
    python scripts/seed_demo_wallet.py

This script creates a demo agent and wallet with a $500 USDC balance
for demonstration and testing purposes.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def seed_demo_wallet():
    """Create a demo wallet with $500 USDC balance."""

    # Configuration
    DEMO_AGENT_ID = "agent_demo_001"
    DEMO_WALLET_ID = "wallet_demo_001"
    DEMO_BALANCE = Decimal("500.000000")  # $500 USDC

    database_url = os.getenv("DATABASE_URL", "memory://")

    print("=" * 60)
    print("SARDIS DEMO WALLET SEED SCRIPT")
    print("=" * 60)
    print(f"Database: {database_url}")
    print(f"Agent ID: {DEMO_AGENT_ID}")
    print(f"Wallet ID: {DEMO_WALLET_ID}")
    print(f"Balance: ${DEMO_BALANCE} USDC")
    print("=" * 60)

    # Check if using PostgreSQL
    use_postgres = database_url.startswith("postgresql://") or database_url.startswith("postgres://")

    if use_postgres:
        try:
            import asyncpg

            dsn = database_url
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)

            conn = await asyncpg.connect(dsn)

            # Create demo organization if not exists
            org_id = uuid.uuid4()
            await conn.execute("""
                INSERT INTO organizations (id, name, created_at)
                VALUES ($1, 'Demo Organization', NOW())
                ON CONFLICT DO NOTHING
            """, org_id)

            # Create demo agent
            print(f"\n[1/4] Creating demo agent: {DEMO_AGENT_ID}")
            await conn.execute("""
                INSERT INTO agents (id, organization_id, external_id, name, public_key, key_algorithm, is_active, created_at)
                VALUES (gen_random_uuid(), $1, $2, 'Demo Agent', 'demo_public_key', 'ed25519', TRUE, NOW())
                ON CONFLICT (external_id) DO UPDATE SET is_active = TRUE
            """, org_id, DEMO_AGENT_ID)
            print("   [OK] Agent created")

            # Get agent internal ID
            agent_row = await conn.fetchrow(
                "SELECT id FROM agents WHERE external_id = $1",
                DEMO_AGENT_ID
            )
            agent_internal_id = agent_row["id"]

            # Create demo wallet
            print(f"\n[2/4] Creating demo wallet: {DEMO_WALLET_ID}")
            await conn.execute("""
                INSERT INTO wallets (id, agent_id, external_id, chain_address, mpc_provider, status, created_at)
                VALUES (gen_random_uuid(), $1, $2, '0x' || encode(gen_random_bytes(20), 'hex'), 'turnkey', 'active', NOW())
                ON CONFLICT (external_id) DO UPDATE SET status = 'active'
            """, agent_internal_id, DEMO_WALLET_ID)
            print("   [OK] Wallet created")

            # Get wallet internal ID
            wallet_row = await conn.fetchrow(
                "SELECT id FROM wallets WHERE external_id = $1",
                DEMO_WALLET_ID
            )
            wallet_internal_id = wallet_row["id"]

            # Set wallet balance
            print(f"\n[3/4] Setting balance: ${DEMO_BALANCE} USDC")
            await conn.execute("""
                INSERT INTO token_balances (wallet_id, token, chain, balance, last_updated)
                VALUES ($1, 'USDC', 'base_sepolia', $2, NOW())
                ON CONFLICT (wallet_id, token, chain) DO UPDATE SET balance = $2, last_updated = NOW()
            """, wallet_internal_id, DEMO_BALANCE)
            print("   [OK] Balance set")

            # Create demo spending policy
            print("\n[4/4] Creating spending policy")
            await conn.execute("""
                INSERT INTO spending_policies (id, wallet_id, trust_level, single_tx_limit, daily_limit, allowed_tokens, allowed_chains, created_at)
                VALUES (gen_random_uuid(), $1, 'standard', 100.00, 1000.00, ARRAY['USDC', 'USDT', 'DAI'], ARRAY['base_sepolia', 'base', 'ethereum'], NOW())
                ON CONFLICT (wallet_id) DO UPDATE SET
                    single_tx_limit = 100.00,
                    daily_limit = 1000.00
            """, wallet_internal_id)
            print("   [OK] Spending policy created")

            await conn.close()

            print("\n" + "=" * 60)
            print("SEED COMPLETE!")
            print("=" * 60)
            print(f"\nDemo wallet ready with ${DEMO_BALANCE} USDC")
            print(f"\nAPI endpoints to test:")
            print(f"  GET  /api/v2/wallets/{DEMO_WALLET_ID}")
            print(f"  GET  /api/v2/wallets/{DEMO_WALLET_ID}/balance")
            print(f"  POST /api/v2/mandates/execute")
            print("\nExample mandate payload:")
            print("""
{
  "mandate": {
    "mandate_id": "mnd_demo_001",
    "subject": "wallet_demo_001",
    "destination": "0x742d35Cc6634C0532925a3b844Bc9e7595f0aB00",
    "amount_minor": "1000000",
    "token": "USDC",
    "chain": "base_sepolia",
    "purpose": "Demo payment"
  }
}
            """)

        except ImportError:
            print("\nERROR: asyncpg not installed. Install with: pip install asyncpg")
            sys.exit(1)
        except Exception as e:
            print(f"\nERROR: {e}")
            sys.exit(1)

    else:
        # In-memory mode - create mock data
        print("\n[INFO] Using in-memory storage (no persistent database)")
        print("[INFO] Demo data will be created when the API starts")

        # Generate seed data configuration
        seed_config = {
            "agent_id": DEMO_AGENT_ID,
            "wallet_id": DEMO_WALLET_ID,
            "balance": str(DEMO_BALANCE),
            "token": "USDC",
            "chain": "base_sepolia",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        print("\nSeed configuration:")
        for key, value in seed_config.items():
            print(f"  {key}: {value}")

        # Write seed config to file for API to pick up
        config_path = os.path.join(os.path.dirname(__file__), "..", "demo_seed.json")
        import json
        with open(config_path, "w") as f:
            json.dump(seed_config, f, indent=2)
        print(f"\n[OK] Seed config written to: {config_path}")

    print("\n" + "=" * 60)
    print("Ready for demo!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_demo_wallet())
