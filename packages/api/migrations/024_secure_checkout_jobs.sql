-- 024_secure_checkout_jobs.sql
-- Persistent metadata table for secure checkout jobs.
-- IMPORTANT: This table intentionally stores NO PAN/CVV.

CREATE TABLE IF NOT EXISTS secure_checkout_jobs (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(80) UNIQUE NOT NULL,
    intent_id VARCHAR(120) UNIQUE NOT NULL,
    wallet_id VARCHAR(120) NOT NULL,
    card_id VARCHAR(120) NOT NULL,
    merchant_origin TEXT NOT NULL,
    merchant_mode VARCHAR(40) NOT NULL,
    status VARCHAR(40) NOT NULL,
    amount NUMERIC(20, 6) NOT NULL,
    currency VARCHAR(16) NOT NULL,
    purpose VARCHAR(120) NOT NULL,
    approval_required BOOLEAN NOT NULL DEFAULT FALSE,
    approval_id VARCHAR(120),
    policy_reason TEXT,
    executor_ref TEXT,
    secret_ref VARCHAR(120),
    secret_expires_at TIMESTAMPTZ,
    redacted_card JSONB NOT NULL DEFAULT '{}'::jsonb,
    options JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_code TEXT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_secure_checkout_jobs_wallet
  ON secure_checkout_jobs(wallet_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_secure_checkout_jobs_status
  ON secure_checkout_jobs(status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_secure_checkout_jobs_merchant
  ON secure_checkout_jobs(merchant_origin, created_at DESC);
