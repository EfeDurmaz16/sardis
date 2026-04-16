-- =============================================================================
-- Sardis Migration: 105_service_directory
-- =============================================================================
--
-- Agent Service Directory — discoverable registry of merchant APIs.
-- sardis-connect merchants auto-register their endpoints here.
-- Agents search by category, capability, or price range.
--
-- Apply: psql $DATABASE_URL -f migrations/105_service_directory.sql
--
-- =============================================================================

CREATE TABLE IF NOT EXISTS service_directory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id),
    service_name VARCHAR(255) NOT NULL,
    description TEXT,
    base_url TEXT NOT NULL,
    category VARCHAR(100),
    pricing_model VARCHAR(32) DEFAULT 'per_call'
        CHECK (pricing_model IN ('per_call', 'per_unit', 'subscription')),
    min_price NUMERIC(20, 6),
    currency VARCHAR(3) DEFAULT 'USD',
    accepts JSONB DEFAULT '["sardis", "x402", "mpp"]',
    endpoints JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    verified BOOLEAN DEFAULT FALSE,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_service_directory_category
    ON service_directory(category) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_service_directory_tags
    ON service_directory USING GIN(tags) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_service_directory_merchant
    ON service_directory(merchant_id);
