-- issuer_funding_attempts table for deterministic provider failover audit history
-- Added in hardening phase: explicit migration (runtime auto-create is dev-only fallback)

CREATE TABLE IF NOT EXISTS issuer_funding_attempts (
    id UUID PRIMARY KEY,
    organization_id TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    attempt_index INT NOT NULL,
    provider TEXT NOT NULL,
    rail TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    amount_minor BIGINT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    connected_account_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, operation_id, attempt_index)
);

CREATE INDEX IF NOT EXISTS idx_funding_attempts_org_created
  ON issuer_funding_attempts(organization_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_funding_attempts_org_operation
  ON issuer_funding_attempts(organization_id, operation_id, attempt_index);
