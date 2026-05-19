-- Migration 035: Transaction caps configuration
-- Stores per-scope spend limits (global, org, agent)

CREATE TABLE IF NOT EXISTS transaction_caps (
  id TEXT PRIMARY KEY DEFAULT 'cap_' || replace(gen_random_uuid()::text, '-', ''),
  scope TEXT NOT NULL CHECK (scope IN ('global', 'org', 'agent')),
  scope_id TEXT,
  daily_limit NUMERIC,
  per_tx_limit NUMERIC,
  monthly_limit NUMERIC,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(scope, scope_id)
);

CREATE INDEX IF NOT EXISTS idx_transaction_caps_scope ON transaction_caps(scope, scope_id);
