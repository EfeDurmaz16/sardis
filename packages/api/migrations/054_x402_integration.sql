-- x402 policy-gated payment layer integration
-- Extends existing x402_settlements table with control plane tracking fields
-- and adds pricing rules for server-side middleware.

-- Add control plane integration columns to existing x402_settlements table
DO $$
BEGIN
    -- source: server (middleware charges), client (agent pays), facilitator (third party)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='source') THEN
        ALTER TABLE x402_settlements ADD COLUMN source TEXT NOT NULL DEFAULT 'server';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='agent_id') THEN
        ALTER TABLE x402_settlements ADD COLUMN agent_id TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='org_id') THEN
        ALTER TABLE x402_settlements ADD COLUMN org_id TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='wallet_id') THEN
        ALTER TABLE x402_settlements ADD COLUMN wallet_id TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='intent_id') THEN
        ALTER TABLE x402_settlements ADD COLUMN intent_id TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='resource_uri') THEN
        ALTER TABLE x402_settlements ADD COLUMN resource_uri TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='network') THEN
        ALTER TABLE x402_settlements ADD COLUMN network TEXT DEFAULT 'base';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='amount') THEN
        ALTER TABLE x402_settlements ADD COLUMN amount TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='currency') THEN
        ALTER TABLE x402_settlements ADD COLUMN currency TEXT DEFAULT 'USDC';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='scheme') THEN
        ALTER TABLE x402_settlements ADD COLUMN scheme TEXT DEFAULT 'exact';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='upto_max_amount') THEN
        ALTER TABLE x402_settlements ADD COLUMN upto_max_amount TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='upto_consumed') THEN
        ALTER TABLE x402_settlements ADD COLUMN upto_consumed TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='dry_run') THEN
        ALTER TABLE x402_settlements ADD COLUMN dry_run BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='x402_settlements' AND column_name='updated_at') THEN
        ALTER TABLE x402_settlements ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_x402_agent ON x402_settlements(agent_id);
CREATE INDEX IF NOT EXISTS idx_x402_status ON x402_settlements(status);
CREATE INDEX IF NOT EXISTS idx_x402_source ON x402_settlements(source);
CREATE INDEX IF NOT EXISTS idx_x402_org ON x402_settlements(org_id);

-- Pricing rules for server-side middleware
CREATE TABLE IF NOT EXISTS x402_pricing_rules (
    rule_id TEXT PRIMARY KEY DEFAULT 'rule_' || substr(gen_random_uuid()::text, 1, 16),
    org_id TEXT NOT NULL,
    path_prefix TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT DEFAULT 'USDC',
    network TEXT DEFAULT 'base',
    token_address TEXT,
    scheme TEXT DEFAULT 'exact',
    ttl_seconds INT DEFAULT 300,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, path_prefix)
);
