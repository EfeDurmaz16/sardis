-- Shared Payment Tokens (SPT): agent-granted, mandate-backed payment credentials.
--
-- An SPT is the cleanest expression of a Sardis spending mandate as a bounded,
-- revocable credential a seller can use to pull payment (via Stripe). Persisting
-- it locally makes grants auditable, enforceable, and revocable on the Sardis
-- side rather than trusting Stripe usage_limits alone.
--
-- Lifecycle: active -> used / revoked / expired

CREATE TABLE IF NOT EXISTS shared_payment_tokens (
    token_id TEXT PRIMARY KEY,                  -- spt_xxx (Sardis-side id)
    org_id TEXT NOT NULL,
    mandate_id TEXT NOT NULL,                   -- backing spending mandate
    agent_id TEXT,

    -- Stripe linkage (null until/unless a Stripe SPT is created)
    stripe_spt_id TEXT,
    payment_method TEXT,

    -- Bounds derived from the mandate (smallest currency unit for max_amount)
    currency TEXT NOT NULL DEFAULT 'usd',
    max_amount BIGINT NOT NULL DEFAULT 0,       -- per-use cap, cents
    expires_at BIGINT NOT NULL DEFAULT 0,       -- unix ts, 0 = none

    -- Seller scoping
    seller_network_id TEXT NOT NULL DEFAULT 'internal',
    seller_external_id TEXT NOT NULL DEFAULT '',

    -- Spend tracking against this SPT (smallest currency unit)
    spent_amount BIGINT NOT NULL DEFAULT 0,
    use_count INTEGER NOT NULL DEFAULT 0,

    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'used', 'revoked', 'expired')),
    revoked_reason TEXT,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_spt_org ON shared_payment_tokens (org_id);
CREATE INDEX IF NOT EXISTS idx_spt_mandate ON shared_payment_tokens (mandate_id);
CREATE INDEX IF NOT EXISTS idx_spt_status ON shared_payment_tokens (status);
