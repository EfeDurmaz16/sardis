#!/usr/bin/env python3
"""
Test Environment Seed Script

Seeds the database with test data for development and testing.

Usage:
    python scripts/seed_test_data.py

Environment:
    DATABASE_URL - PostgreSQL connection string

WARNING: This script will insert data into the database.
         Only run in development/test environments!
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

# Check environment before proceeding
env = os.getenv("SARDIS_ENVIRONMENT", "development")
if env == "production":
    print("ERROR: Cannot seed production database!")
    print("Set SARDIS_ENVIRONMENT to 'development' or 'test'")
    sys.exit(1)


async def get_connection():
    """Get database connection."""
    import asyncpg

    database_url = os.getenv("DATABASE_URL", "postgresql://sardis:sardis@localhost:5432/sardis")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return await asyncpg.connect(database_url)


async def seed_organizations(conn) -> dict[str, str]:
    """Seed test organizations."""
    orgs = [
        {
            "external_id": "org_demo_corp",
            "name": "Demo Corporation",
            "settings": '{"tier": "enterprise", "max_agents": 100}',
        },
        {
            "external_id": "org_startup_ai",
            "name": "Startup AI Inc",
            "settings": '{"tier": "startup", "max_agents": 10}',
        },
        {
            "external_id": "org_test_user",
            "name": "Test User Org",
            "settings": '{"tier": "free", "max_agents": 3}',
        },
    ]

    org_ids = {}
    for org in orgs:
        row = await conn.fetchrow(
            """
            INSERT INTO organizations (external_id, name, settings)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (external_id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id, external_id
            """,
            org["external_id"],
            org["name"],
            org["settings"],
        )
        org_ids[org["external_id"]] = str(row["id"])

    print(f"Seeded {len(orgs)} organizations")
    return org_ids


async def seed_agents(conn, org_ids: dict) -> dict[str, str]:
    """Seed test agents."""
    agents = [
        {
            "external_id": "agent_demo_001",
            "org_key": "org_demo_corp",
            "name": "Demo Payment Agent",
            "description": "Primary agent for Demo Corporation",
        },
        {
            "external_id": "agent_demo_002",
            "org_key": "org_demo_corp",
            "name": "Demo Secondary Agent",
            "description": "Secondary agent for batch payments",
        },
        {
            "external_id": "agent_startup_001",
            "org_key": "org_startup_ai",
            "name": "Startup AI Assistant",
            "description": "AI assistant with payment capabilities",
        },
        {
            "external_id": "agent_test_001",
            "org_key": "org_test_user",
            "name": "Test Agent",
            "description": "For integration testing",
        },
    ]

    agent_ids = {}
    for agent in agents:
        org_id = org_ids[agent["org_key"]]
        row = await conn.fetchrow(
            """
            INSERT INTO agents (external_id, organization_id, name, description)
            VALUES ($1, $2::uuid, $3, $4)
            ON CONFLICT (external_id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id, external_id
            """,
            agent["external_id"],
            org_id,
            agent["name"],
            agent["description"],
        )
        agent_ids[agent["external_id"]] = str(row["id"])

    print(f"Seeded {len(agents)} agents")
    return agent_ids


async def seed_wallets(conn, agent_ids: dict) -> dict[str, str]:
    """Seed test wallets."""
    wallets = [
        {
            "external_id": "wallet_demo_001",
            "agent_key": "agent_demo_001",
            "chain_address": "0x1234567890123456789012345678901234567890",
            "chain": "base_sepolia",
        },
        {
            "external_id": "wallet_demo_002",
            "agent_key": "agent_demo_002",
            "chain_address": "0x2345678901234567890123456789012345678901",
            "chain": "base_sepolia",
        },
        {
            "external_id": "wallet_startup_001",
            "agent_key": "agent_startup_001",
            "chain_address": "0x3456789012345678901234567890123456789012",
            "chain": "base_sepolia",
        },
        {
            "external_id": "wallet_test_001",
            "agent_key": "agent_test_001",
            "chain_address": "0x4567890123456789012345678901234567890123",
            "chain": "base_sepolia",
        },
    ]

    wallet_ids = {}
    for wallet in wallets:
        agent_id = agent_ids[wallet["agent_key"]]
        row = await conn.fetchrow(
            """
            INSERT INTO wallets (external_id, agent_id, chain_address, chain)
            VALUES ($1, $2::uuid, $3, $4)
            ON CONFLICT (external_id) DO UPDATE SET chain_address = EXCLUDED.chain_address
            RETURNING id, external_id
            """,
            wallet["external_id"],
            agent_id,
            wallet["chain_address"],
            wallet["chain"],
        )
        wallet_ids[wallet["external_id"]] = str(row["id"])

        # Add initial balance
        await conn.execute(
            """
            INSERT INTO token_balances (wallet_id, token, balance)
            VALUES ($1::uuid, 'USDC', 1000.00)
            ON CONFLICT (wallet_id, token) DO UPDATE SET balance = 1000.00
            """,
            str(row["id"]),
        )

    print(f"Seeded {len(wallets)} wallets with balances")
    return wallet_ids


async def seed_spending_policies(conn, agent_ids: dict):
    """Seed spending policies."""
    policies = [
        {
            "agent_key": "agent_demo_001",
            "trust_level": "high",
            "limit_per_tx": Decimal("500.00"),
            "limit_total": Decimal("5000.00"),
        },
        {
            "agent_key": "agent_demo_002",
            "trust_level": "medium",
            "limit_per_tx": Decimal("100.00"),
            "limit_total": Decimal("1000.00"),
        },
        {
            "agent_key": "agent_startup_001",
            "trust_level": "medium",
            "limit_per_tx": Decimal("200.00"),
            "limit_total": Decimal("2000.00"),
        },
        {
            "agent_key": "agent_test_001",
            "trust_level": "low",
            "limit_per_tx": Decimal("50.00"),
            "limit_total": Decimal("500.00"),
        },
    ]

    for policy in policies:
        agent_id = agent_ids[policy["agent_key"]]
        await conn.execute(
            """
            INSERT INTO spending_policies (agent_id, trust_level, limit_per_tx, limit_total)
            VALUES ($1::uuid, $2, $3, $4)
            ON CONFLICT (agent_id) DO UPDATE SET
                trust_level = EXCLUDED.trust_level,
                limit_per_tx = EXCLUDED.limit_per_tx,
                limit_total = EXCLUDED.limit_total
            """,
            agent_id,
            policy["trust_level"],
            policy["limit_per_tx"],
            policy["limit_total"],
        )

    print(f"Seeded {len(policies)} spending policies")


async def seed_api_keys(conn, org_ids: dict):
    """Seed API keys for testing."""
    keys = [
        {
            "org_key": "org_demo_corp",
            "name": "Demo Production Key",
            "scopes": ["read", "write", "admin"],
            "rate_limit": 1000,
        },
        {
            "org_key": "org_startup_ai",
            "name": "Startup Key",
            "scopes": ["read", "write"],
            "rate_limit": 100,
        },
        {
            "org_key": "org_test_user",
            "name": "Test Key",
            "scopes": ["read", "write"],
            "rate_limit": 50,
        },
    ]

    created_keys = []
    for key_data in keys:
        org_id = org_ids[key_data["org_key"]]

        # Generate a test key (in production, use secure random generation)
        full_key = f"sk_test_{secrets.token_urlsafe(24)}"
        prefix = full_key[:12]
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        await conn.execute(
            """
            INSERT INTO api_keys (key_prefix, key_hash, organization_id, name, scopes, rate_limit)
            VALUES ($1, $2, $3::uuid, $4, $5, $6)
            ON CONFLICT DO NOTHING
            """,
            prefix,
            key_hash,
            org_id,
            key_data["name"],
            key_data["scopes"],
            key_data["rate_limit"],
        )

        created_keys.append({
            "name": key_data["name"],
            "key": full_key,
            "org": key_data["org_key"],
        })

    print(f"Seeded {len(keys)} API keys")
    print("\nTest API Keys (save these!):")
    for k in created_keys:
        print(f"  {k['name']} ({k['org']}): {k['key']}")


async def seed_sample_transactions(conn, wallet_ids: dict):
    """Seed sample transactions for history."""
    transactions = [
        {
            "external_id": f"tx_seed_{uuid4().hex[:8]}",
            "from_wallet": "wallet_demo_001",
            "amount": Decimal("25.00"),
            "token": "USDC",
            "purpose": "OpenAI API Credits",
            "status": "completed",
        },
        {
            "external_id": f"tx_seed_{uuid4().hex[:8]}",
            "from_wallet": "wallet_demo_001",
            "amount": Decimal("50.00"),
            "token": "USDC",
            "purpose": "Vercel Pro Subscription",
            "status": "completed",
        },
        {
            "external_id": f"tx_seed_{uuid4().hex[:8]}",
            "from_wallet": "wallet_demo_001",
            "amount": Decimal("100.00"),
            "token": "USDC",
            "purpose": "AWS Services",
            "status": "completed",
        },
        {
            "external_id": f"tx_seed_{uuid4().hex[:8]}",
            "from_wallet": "wallet_demo_002",
            "amount": Decimal("15.00"),
            "token": "USDC",
            "purpose": "GitHub Copilot",
            "status": "completed",
        },
        {
            "external_id": f"tx_seed_{uuid4().hex[:8]}",
            "from_wallet": "wallet_startup_001",
            "amount": Decimal("200.00"),
            "token": "USDC",
            "purpose": "Claude API Credits",
            "status": "completed",
        },
    ]

    for tx in transactions:
        from_wallet_id = wallet_ids[tx["from_wallet"]]
        await conn.execute(
            """
            INSERT INTO transactions (external_id, from_wallet_id, amount, token, purpose, status, completed_at)
            VALUES ($1, $2::uuid, $3, $4, $5, $6, NOW())
            ON CONFLICT (external_id) DO NOTHING
            """,
            tx["external_id"],
            from_wallet_id,
            tx["amount"],
            tx["token"],
            tx["purpose"],
            tx["status"],
        )

    print(f"Seeded {len(transactions)} sample transactions")


async def seed_webhooks(conn, org_ids: dict):
    """Seed webhook subscriptions."""
    webhooks = [
        {
            "external_id": f"wh_{uuid4().hex[:8]}",
            "org_key": "org_demo_corp",
            "url": "https://webhook.site/test-demo-corp",
            "events": ["payment.completed", "payment.failed", "hold.created"],
        },
        {
            "external_id": f"wh_{uuid4().hex[:8]}",
            "org_key": "org_startup_ai",
            "url": "https://webhook.site/test-startup-ai",
            "events": ["payment.completed"],
        },
    ]

    for wh in webhooks:
        secret = secrets.token_urlsafe(32)
        await conn.execute(
            """
            INSERT INTO webhook_subscriptions (external_id, organization_id, url, secret, events)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (external_id) DO NOTHING
            """,
            wh["external_id"],
            org_ids[wh["org_key"]],
            wh["url"],
            secret,
            wh["events"],
        )

    print(f"Seeded {len(webhooks)} webhook subscriptions")


async def main():
    """Main seeding function."""
    print("=" * 60)
    print("Sardis Test Data Seeder")
    print("=" * 60)
    print(f"Environment: {env}")
    print()

    conn = await get_connection()

    try:
        # Seed in order of dependencies
        org_ids = await seed_organizations(conn)
        agent_ids = await seed_agents(conn, org_ids)
        wallet_ids = await seed_wallets(conn, agent_ids)
        await seed_spending_policies(conn, agent_ids)
        await seed_api_keys(conn, org_ids)
        await seed_sample_transactions(conn, wallet_ids)
        await seed_webhooks(conn, org_ids)

        print()
        print("=" * 60)
        print("Seeding complete!")
        print("=" * 60)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
