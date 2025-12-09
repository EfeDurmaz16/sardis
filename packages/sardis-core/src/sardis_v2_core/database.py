"""Database connection and session management for Sardis."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool


class Database:
    """PostgreSQL database connection manager."""
    
    _pool: Optional[Pool] = None
    
    @classmethod
    async def get_pool(cls) -> Pool:
        """Get or create the connection pool."""
        if cls._pool is None:
            database_url = os.getenv("DATABASE_URL", "postgresql://localhost/sardis")
            # Convert postgres:// to postgresql:// if needed (Heroku/Railway style)
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            cls._pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
        return cls._pool
    
    @classmethod
    async def close(cls) -> None:
        """Close the connection pool."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
    
    @classmethod
    @asynccontextmanager
    async def connection(cls) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a connection from the pool."""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            yield conn
    
    @classmethod
    @asynccontextmanager
    async def transaction(cls) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a connection with an active transaction."""
        async with cls.connection() as conn:
            async with conn.transaction():
                yield conn
    
    @classmethod
    async def execute(cls, query: str, *args) -> str:
        """Execute a query and return status."""
        async with cls.connection() as conn:
            return await conn.execute(query, *args)
    
    @classmethod
    async def fetch(cls, query: str, *args) -> list:
        """Fetch all rows from a query."""
        async with cls.connection() as conn:
            return await conn.fetch(query, *args)
    
    @classmethod
    async def fetchrow(cls, query: str, *args):
        """Fetch a single row from a query."""
        async with cls.connection() as conn:
            return await conn.fetchrow(query, *args)
    
    @classmethod
    async def fetchval(cls, query: str, *args):
        """Fetch a single value from a query."""
        async with cls.connection() as conn:
            return await conn.fetchval(query, *args)


async def init_database() -> None:
    """Initialize database schema."""
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        # Create tables if they don't exist
        await conn.execute(SCHEMA_SQL)


# Production-ready schema
SCHEMA_SQL = """
-- =============================================================================
-- Sardis Production Schema
-- =============================================================================

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agents
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    public_key BYTEA,
    key_algorithm VARCHAR(20) DEFAULT 'ed25519',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_org ON agents(organization_id);
CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active) WHERE is_active = TRUE;

-- Wallets
CREATE TABLE IF NOT EXISTS wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    agent_id UUID REFERENCES agents(id) NOT NULL,
    chain_address VARCHAR(66),
    chain VARCHAR(20) DEFAULT 'base',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wallets_agent ON wallets(agent_id);
CREATE INDEX IF NOT EXISTS idx_wallets_chain ON wallets(chain, chain_address);

-- Token Balances
CREATE TABLE IF NOT EXISTS token_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES wallets(id) NOT NULL,
    token VARCHAR(10) NOT NULL,
    balance NUMERIC(20,6) DEFAULT 0,
    spent_total NUMERIC(20,6) DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(wallet_id, token)
);

CREATE INDEX IF NOT EXISTS idx_balances_wallet ON token_balances(wallet_id);

-- Spending Policies
CREATE TABLE IF NOT EXISTS spending_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) UNIQUE NOT NULL,
    trust_level VARCHAR(20) DEFAULT 'low',
    limit_per_tx NUMERIC(20,6) DEFAULT 100,
    limit_total NUMERIC(20,6) DEFAULT 1000,
    require_preauth BOOLEAN DEFAULT FALSE,
    allowed_scopes VARCHAR[] DEFAULT ARRAY['all'],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Time Window Limits
CREATE TABLE IF NOT EXISTS time_window_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES spending_policies(id) NOT NULL,
    window_type VARCHAR(20) NOT NULL,
    limit_amount NUMERIC(20,6) NOT NULL,
    current_spent NUMERIC(20,6) DEFAULT 0,
    window_start TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(policy_id, window_type)
);

-- Merchant Rules
CREATE TABLE IF NOT EXISTS merchant_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES spending_policies(id) NOT NULL,
    rule_type VARCHAR(10) NOT NULL,
    merchant_id VARCHAR(64),
    category VARCHAR(50),
    max_per_tx NUMERIC(20,6),
    daily_limit NUMERIC(20,6),
    reason TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_merchant_rules_policy ON merchant_rules(policy_id);
CREATE INDEX IF NOT EXISTS idx_merchant_rules_merchant ON merchant_rules(merchant_id);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    from_wallet_id UUID REFERENCES wallets(id),
    to_wallet_id UUID REFERENCES wallets(id),
    amount NUMERIC(20,6) NOT NULL,
    fee NUMERIC(20,6) DEFAULT 0,
    token VARCHAR(10) NOT NULL,
    purpose TEXT,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    idempotency_key VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tx_from ON transactions(from_wallet_id);
CREATE INDEX IF NOT EXISTS idx_tx_to ON transactions(to_wallet_id);
CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_tx_created ON transactions(created_at DESC);

-- On-Chain Records
CREATE TABLE IF NOT EXISTS on_chain_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id) NOT NULL,
    chain VARCHAR(20) NOT NULL,
    tx_hash VARCHAR(66) NOT NULL,
    block_number BIGINT,
    from_address VARCHAR(66),
    to_address VARCHAR(66),
    status VARCHAR(20) DEFAULT 'pending',
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chain_records_tx ON on_chain_records(transaction_id);
CREATE INDEX IF NOT EXISTS idx_chain_records_hash ON on_chain_records(chain, tx_hash);

-- Holds (Pre-authorization)
CREATE TABLE IF NOT EXISTS holds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    wallet_id UUID REFERENCES wallets(id) NOT NULL,
    merchant_id VARCHAR(64),
    amount NUMERIC(20,6) NOT NULL,
    token VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    purpose TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    captured_amount NUMERIC(20,6),
    captured_at TIMESTAMPTZ,
    capture_tx_id UUID REFERENCES transactions(id),
    voided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_holds_wallet ON holds(wallet_id);
CREATE INDEX IF NOT EXISTS idx_holds_status ON holds(status);

-- Mandates (AP2)
CREATE TABLE IF NOT EXISTS mandates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mandate_id VARCHAR(64) UNIQUE NOT NULL,
    mandate_type VARCHAR(20) NOT NULL,
    issuer VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    payload JSONB NOT NULL,
    proof JSONB,
    expires_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    transaction_id UUID REFERENCES transactions(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mandates_subject ON mandates(subject);
CREATE INDEX IF NOT EXISTS idx_mandates_type ON mandates(mandate_type);

-- Mandate Chains
CREATE TABLE IF NOT EXISTS mandate_chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id UUID REFERENCES mandates(id),
    cart_id UUID REFERENCES mandates(id),
    payment_id UUID REFERENCES mandates(id) NOT NULL,
    verified_at TIMESTAMPTZ DEFAULT NOW(),
    executed_at TIMESTAMPTZ,
    transaction_id UUID REFERENCES transactions(id)
);

-- Replay Cache
CREATE TABLE IF NOT EXISTS replay_cache (
    mandate_id VARCHAR(64) PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_replay_expires ON replay_cache(expires_at);

-- Ledger Entries (append-only audit log)
CREATE TABLE IF NOT EXISTS ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tx_id VARCHAR(64) UNIQUE NOT NULL,
    mandate_id VARCHAR(64),
    from_wallet VARCHAR(255),
    to_wallet VARCHAR(255),
    amount NUMERIC(20,6) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    chain VARCHAR(20),
    chain_tx_hash VARCHAR(66),
    audit_anchor TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ledger_created ON ledger_entries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_from ON ledger_entries(from_wallet);
CREATE INDEX IF NOT EXISTS idx_ledger_to ON ledger_entries(to_wallet);

-- Webhook Subscriptions
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    organization_id VARCHAR(64) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    secret VARCHAR(64) NOT NULL,
    events VARCHAR[] DEFAULT ARRAY[]::VARCHAR[],
    is_active BOOLEAN DEFAULT TRUE,
    total_deliveries INTEGER DEFAULT 0,
    successful_deliveries INTEGER DEFAULT 0,
    failed_deliveries INTEGER DEFAULT 0,
    last_delivery_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_subs_org ON webhook_subscriptions(organization_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subs_active ON webhook_subscriptions(is_active) WHERE is_active = TRUE;

-- Webhook Deliveries (delivery attempt log)
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    subscription_id VARCHAR(64) NOT NULL,
    event_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    status_code INTEGER,
    response_body TEXT,
    error TEXT,
    duration_ms INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT FALSE,
    attempt_number INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deliveries_subscription ON webhook_deliveries(subscription_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_event ON webhook_deliveries(event_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_created ON webhook_deliveries(created_at DESC);

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type VARCHAR(20) NOT NULL,
    actor_id VARCHAR(64) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(64) NOT NULL,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_type, actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);

-- API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_prefix VARCHAR(8) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    organization_id UUID REFERENCES organizations(id) NOT NULL,
    name VARCHAR(255),
    scopes VARCHAR[] DEFAULT ARRAY['read'],
    rate_limit INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_org ON api_keys(organization_id);

-- Marketplace Services
CREATE TABLE IF NOT EXISTS marketplace_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    provider_agent_id VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    tags VARCHAR[] DEFAULT ARRAY[]::VARCHAR[],
    price_amount NUMERIC(20,6) NOT NULL,
    price_token VARCHAR(10) DEFAULT 'USDC',
    price_type VARCHAR(20) DEFAULT 'fixed',
    capabilities JSONB DEFAULT '{}',
    api_endpoint VARCHAR(2048),
    status VARCHAR(20) DEFAULT 'draft',
    total_orders INTEGER DEFAULT 0,
    completed_orders INTEGER DEFAULT 0,
    rating NUMERIC(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketplace_services_provider ON marketplace_services(provider_agent_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_services_category ON marketplace_services(category);
CREATE INDEX IF NOT EXISTS idx_marketplace_services_status ON marketplace_services(status);

-- Marketplace Offers
CREATE TABLE IF NOT EXISTS marketplace_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    service_id VARCHAR(64) NOT NULL,
    provider_agent_id VARCHAR(64) NOT NULL,
    consumer_agent_id VARCHAR(64) NOT NULL,
    total_amount NUMERIC(20,6) NOT NULL,
    token VARCHAR(10) DEFAULT 'USDC',
    status VARCHAR(20) DEFAULT 'pending',
    escrow_tx_hash VARCHAR(66),
    escrow_amount NUMERIC(20,6) DEFAULT 0,
    released_amount NUMERIC(20,6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_marketplace_offers_service ON marketplace_offers(service_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_offers_provider ON marketplace_offers(provider_agent_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_offers_consumer ON marketplace_offers(consumer_agent_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_offers_status ON marketplace_offers(status);

-- Marketplace Reviews
CREATE TABLE IF NOT EXISTS marketplace_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    offer_id VARCHAR(64) NOT NULL,
    service_id VARCHAR(64) NOT NULL,
    reviewer_agent_id VARCHAR(64) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketplace_reviews_service ON marketplace_reviews(service_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_reviews_offer ON marketplace_reviews(offer_id);
"""
