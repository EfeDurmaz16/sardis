#!/usr/bin/env python3
"""
Seed script for Sardis demo environment.

Creates demo organizations, agents, and wallets with initial balances.
Run this after setting up the database to populate demo data.

Usage:
    python scripts/seed_demo.py

Environment:
    DATABASE_URL: PostgreSQL connection string
"""
from __future__ import annotations

import asyncio
import os
import sys
from decimal import Decimal
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def seed_database():
    """Seed the database with demo data."""
    import asyncpg
    
    database_url = os.getenv("DATABASE_URL", "postgresql://localhost/sardis")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print(f"Connecting to database...")
    
    try:
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print("\nMake sure DATABASE_URL is set correctly.")
        print("Example: DATABASE_URL=postgresql://user:pass@host/sardis")
        sys.exit(1)
    
    async with pool.acquire() as conn:
        print("✅ Connected to database")
        
        # Check if demo data already exists
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM organizations WHERE external_id = 'demo_org'"
        )
        if existing:
            print("⚠️  Demo data already exists. Skipping seed.")
            print("\nTo reset, run: DELETE FROM organizations WHERE external_id = 'demo_org';")
            return
        
        print("\n📦 Creating demo organization...")
        org_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO organizations (id, external_id, name, settings)
            VALUES ($1, 'demo_org', 'Sardis Demo Organization', '{"tier": "demo"}')
            """,
            org_id,
        )
        print(f"   Created organization: demo_org (ID: {org_id[:8]}...)")
        
        # Create demo agents
        print("\n🤖 Creating demo agents...")
        agents = [
            {
                "external_id": "agent_alice",
                "name": "Alice Agent",
                "description": "Demo AI agent for testing payments",
            },
            {
                "external_id": "agent_bob",
                "name": "Bob Agent",
                "description": "Demo merchant agent",
            },
            {
                "external_id": "agent_charlie",
                "name": "Charlie Agent",
                "description": "Demo service provider agent",
            },
        ]
        
        agent_ids = {}
        for agent in agents:
            agent_id = str(uuid4())
            agent_ids[agent["external_id"]] = agent_id
            await conn.execute(
                """
                INSERT INTO agents (id, external_id, organization_id, name, description)
                VALUES ($1, $2, $3, $4, $5)
                """,
                agent_id,
                agent["external_id"],
                org_id,
                agent["name"],
                agent["description"],
            )
            print(f"   Created agent: {agent['name']} ({agent['external_id']})")
        
        # Create wallets for each agent
        print("\n💰 Creating wallets...")
        for agent_ext_id, agent_id in agent_ids.items():
            wallet_id = str(uuid4())
            wallet_ext_id = f"wallet_{agent_ext_id}"
            
            await conn.execute(
                """
                INSERT INTO wallets (id, external_id, agent_id, chain)
                VALUES ($1, $2, $3, 'base_sepolia')
                """,
                wallet_id,
                wallet_ext_id,
                agent_id,
            )
            
            # Add initial USDC balance
            await conn.execute(
                """
                INSERT INTO token_balances (wallet_id, token, balance, spent_total)
                VALUES ($1, 'USDC', 1000.00, 0.00)
                """,
                wallet_id,
            )
            
            print(f"   Created wallet: {wallet_ext_id} with 1000 USDC")
        
        # Create spending policies
        print("\n📋 Creating spending policies...")
        for agent_ext_id, agent_id in agent_ids.items():
            await conn.execute(
                """
                INSERT INTO spending_policies (agent_id, trust_level, limit_per_tx, limit_total)
                VALUES ($1, 'medium', 100.00, 500.00)
                """,
                agent_id,
            )
            print(f"   Created policy for {agent_ext_id}: $100/tx, $500 total")
        
        # Create a demo API key
        print("\n🔑 Creating demo API key...")
        import hashlib
        import secrets
        
        api_key = f"sk_demo_{secrets.token_urlsafe(24)}"
        key_prefix = api_key[:8]
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        await conn.execute(
            """
            INSERT INTO api_keys (key_prefix, key_hash, organization_id, name, scopes, rate_limit)
            VALUES ($1, $2, $3, 'Demo API Key', ARRAY['read', 'write'], 1000)
            """,
            key_prefix,
            key_hash,
            org_id,
        )
        print(f"   Created API key: {api_key}")
        print(f"\n   ⚠️  Save this key! It won't be shown again.")
        
        # Create a sample transaction for demo
        print("\n💸 Creating sample transaction...")
        alice_wallet = await conn.fetchval(
            "SELECT id FROM wallets WHERE external_id = 'wallet_agent_alice'"
        )
        bob_wallet = await conn.fetchval(
            "SELECT id FROM wallets WHERE external_id = 'wallet_agent_bob'"
        )
        
        tx_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO transactions (
                id, external_id, from_wallet_id, to_wallet_id, 
                amount, token, status, purpose
            )
            VALUES ($1, $2, $3, $4, 25.00, 'USDC', 'completed', 'Demo payment')
            """,
            tx_id,
            f"tx_{tx_id[:8]}",
            alice_wallet,
            bob_wallet,
        )
        
        # Update balances
        await conn.execute(
            "UPDATE token_balances SET balance = balance - 25.00, spent_total = spent_total + 25.00 WHERE wallet_id = $1",
            alice_wallet,
        )
        await conn.execute(
            "UPDATE token_balances SET balance = balance + 25.00 WHERE wallet_id = $1",
            bob_wallet,
        )
        print(f"   Created transaction: Alice → Bob, 25 USDC")
        
        print("\n" + "=" * 60)
        print("✅ Demo data seeded successfully!")
        print("=" * 60)
        print("\nDemo accounts:")
        print("  - Organization: demo_org")
        print("  - Agents: agent_alice, agent_bob, agent_charlie")
        print("  - Wallets: Each agent has 1000 USDC (Alice has 975 after demo tx)")
        print(f"\nAPI Key: {api_key}")
        print("\nYou can now start the API and dashboard!")
    
    await pool.close()


async def init_schema():
    """Initialize the database schema."""
    import asyncpg
    
    database_url = os.getenv("DATABASE_URL", "postgresql://localhost/sardis")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print("Initializing database schema...")
    
    try:
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    # Import schema from database module
    try:
        from sardis_v2_core.database import SCHEMA_SQL
        async with pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
        print("✅ Schema initialized")
    except ImportError:
        print("⚠️  Could not import schema. Make sure sardis-core is installed.")
        print("   Run: pip install -e sardis-core/")
    except Exception as e:
        print(f"❌ Failed to initialize schema: {e}")
    
    await pool.close()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed Sardis demo database")
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Initialize database schema before seeding",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Only initialize schema, don't seed data",
    )
    args = parser.parse_args()
    
    if args.init_schema or args.schema_only:
        await init_schema()
    
    if not args.schema_only:
        await seed_database()


if __name__ == "__main__":
    asyncio.run(main())
