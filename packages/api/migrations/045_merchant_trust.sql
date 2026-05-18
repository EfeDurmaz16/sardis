-- Migration 045: Merchant trust profiles
-- Tracks per-merchant transaction history and computed trust scores.
-- Used by MerchantTrustService to adjust approval thresholds and flag
-- first-seen or high-dispute merchants for additional scrutiny.

CREATE TABLE IF NOT EXISTS merchant_trust_profiles (
    id                BIGSERIAL PRIMARY KEY,
    merchant_id       TEXT          NOT NULL UNIQUE,
    merchant_name     TEXT,
    category          TEXT,
    mcc_code          TEXT,
    trust_level       TEXT          NOT NULL DEFAULT 'unknown',
    trust_score       DOUBLE PRECISION NOT NULL DEFAULT 0.3,
    first_seen        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    last_seen         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    transaction_count INTEGER       NOT NULL DEFAULT 0,
    total_volume      NUMERIC(20,6) NOT NULL DEFAULT 0,
    dispute_count     INTEGER       NOT NULL DEFAULT 0,
    verified_at       TIMESTAMPTZ,
    verified_by       TEXT,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_merchant_trust_level ON merchant_trust_profiles (trust_level);
CREATE INDEX IF NOT EXISTS idx_merchant_trust_score ON merchant_trust_profiles (trust_score);
