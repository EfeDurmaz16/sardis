-- =============================================================================
-- Sardis Migration: 031_checkout_hardening
-- =============================================================================
--
-- Hardening improvements for "Pay with Sardis" checkout:
-- - Client secret for public access (prevents session enumeration)
-- - Idempotency key (prevents duplicate payments on retry)
-- - Platform fee tracking (amount breakdown)
-- - Embed origin validation
-- - Checkout links (reusable payment URLs)
-- - Webhook delivery tracking (deduplication)
--
-- Apply: psql $DATABASE_URL -f migrations/031_checkout_hardening.sql
--
-- =============================================================================

-- Client secret for public access
ALTER TABLE merchant_checkout_sessions
  ADD COLUMN IF NOT EXISTS client_secret TEXT;
UPDATE merchant_checkout_sessions SET client_secret = encode(gen_random_bytes(24), 'base64') WHERE client_secret IS NULL;
ALTER TABLE merchant_checkout_sessions ALTER COLUMN client_secret SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mcs_client_secret ON merchant_checkout_sessions(client_secret);

-- Idempotency key
ALTER TABLE merchant_checkout_sessions
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mcs_idempotency ON merchant_checkout_sessions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- Platform fee tracking
ALTER TABLE merchant_checkout_sessions
  ADD COLUMN IF NOT EXISTS platform_fee_amount NUMERIC(20,6) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS net_amount NUMERIC(20,6),
  ADD COLUMN IF NOT EXISTS embed_origin TEXT;

-- Checkout links
CREATE TABLE IF NOT EXISTS merchant_checkout_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  link_id TEXT NOT NULL UNIQUE,
  merchant_id UUID NOT NULL REFERENCES merchants(id),
  amount NUMERIC(20,6) NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USDC',
  description TEXT,
  slug TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(merchant_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_mcl_merchant ON merchant_checkout_links(merchant_id);
CREATE INDEX IF NOT EXISTS idx_mcl_slug ON merchant_checkout_links(slug);

-- Webhook delivery tracking
CREATE TABLE IF NOT EXISTS merchant_webhook_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT NOT NULL UNIQUE,
  merchant_id UUID NOT NULL REFERENCES merchants(id),
  event_type TEXT NOT NULL,
  payload JSONB DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_attempt_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mwd_merchant ON merchant_webhook_deliveries(merchant_id);
CREATE INDEX IF NOT EXISTS idx_mwd_event_type ON merchant_webhook_deliveries(event_type);
