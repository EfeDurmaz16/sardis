-- Spending mandates: machine-readable payment authorization primitives.
--
-- A spending mandate defines the scoped, time-limited, revocable authority
-- an AI agent has to spend money. It is the authorization layer between
-- agent identity and payment execution.
--
-- Lifecycle: draft → active → suspended/revoked/expired/consumed

CREATE TABLE IF NOT EXISTS spending_mandates (
    id TEXT PRIMARY KEY,                        -- mandate_xxx
    org_id TEXT NOT NULL,
    agent_id TEXT,
    wallet_id TEXT,

    -- Principal & authority
    principal_id TEXT NOT NULL,                 -- user/org who authorized this mandate
    issuer_id TEXT NOT NULL,                    -- who created the mandate

    -- Scope: what can be purchased
    merchant_scope JSONB DEFAULT '{}',         -- {allowed: [...], blocked: [...], mcc_codes: [...]}
    purpose_scope TEXT,                         -- natural language description of allowed purposes

    -- Amount limits
    amount_per_tx NUMERIC(20,6),               -- max per single transaction
    amount_daily NUMERIC(20,6),                -- max daily aggregate
    amount_weekly NUMERIC(20,6),               -- max weekly aggregate
    amount_monthly NUMERIC(20,6),              -- max monthly aggregate
    amount_total NUMERIC(20,6),                -- lifetime cap for this mandate
    currency TEXT DEFAULT 'USDC',

    -- Spent tracking
    spent_total NUMERIC(20,6) DEFAULT 0,       -- total spent under this mandate
    spent_today NUMERIC(20,6) DEFAULT 0,       -- reset daily at midnight UTC
    last_spend_reset TIMESTAMPTZ DEFAULT now(), -- when daily counter was last reset

    -- Rail permissions
    allowed_rails TEXT[] DEFAULT '{card,usdc,bank}',  -- card, usdc, bank, any
    allowed_chains TEXT[],                     -- base, polygon, ethereum, etc.
    allowed_tokens TEXT[],                     -- USDC, USDT, EURC, etc.

    -- Time bounds
    valid_from TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,

    -- Approval controls
    approval_threshold NUMERIC(20,6),          -- amount above which human approval required
    approval_mode TEXT DEFAULT 'auto'           -- auto, threshold, always_human
        CHECK (approval_mode IN ('auto', 'threshold', 'always_human')),

    -- Lifecycle state
    status TEXT DEFAULT 'active'
        CHECK (status IN ('draft', 'active', 'suspended', 'revoked', 'expired', 'consumed')),
    revoked_at TIMESTAMPTZ,
    revoked_by TEXT,
    revocation_reason TEXT,

    -- Integrity & versioning
    version INTEGER DEFAULT 1,
    policy_hash TEXT,                           -- SHA-256 of mandate rules for tamper detection
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_mandates_org ON spending_mandates(org_id);
CREATE INDEX IF NOT EXISTS idx_mandates_agent ON spending_mandates(agent_id);
CREATE INDEX IF NOT EXISTS idx_mandates_wallet ON spending_mandates(wallet_id);
CREATE INDEX IF NOT EXISTS idx_mandates_status ON spending_mandates(status);
CREATE INDEX IF NOT EXISTS idx_mandates_expires ON spending_mandates(expires_at)
    WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mandates_active_agent ON spending_mandates(agent_id, status)
    WHERE status = 'active';
