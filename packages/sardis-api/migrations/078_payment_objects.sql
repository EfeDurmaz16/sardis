-- Payment Objects: signed, one-time, merchant-bound payment tokens.
--
-- A payment object is a cryptographically signed authorization that binds
-- a spending mandate to a specific merchant, amount, and session. It is
-- the atomic unit of payment in the Sardis protocol — presented to
-- merchants, verified on-chain or off-chain, and settled exactly once.
--
-- Lifecycle: minted → presented → verified → locked → settling → settled
--            (with escrow, dispute, and refund branches)

CREATE TABLE IF NOT EXISTS payment_objects (
    object_id TEXT PRIMARY KEY,                  -- po_xxx
    mandate_id TEXT NOT NULL,                    -- FK to spending_mandates(id)
    cell_ids TEXT[] DEFAULT '{}',                -- funding cells backing this object
    merchant_id TEXT NOT NULL,                   -- merchant receiving payment

    -- Amount & currency
    exact_amount NUMERIC(20,6) NOT NULL,         -- exact payment amount
    currency TEXT DEFAULT 'USDC',

    -- Authorization properties
    one_time_use BOOLEAN DEFAULT true,           -- single-use by default
    signature_chain JSONB DEFAULT '[]',          -- ordered list of signatures (agent, policy, mandate)
    session_hash TEXT NOT NULL,                  -- SHA-256 session binding for replay protection

    -- Privacy
    privacy_tier TEXT DEFAULT 'transparent'
        CHECK (privacy_tier IN ('transparent', 'hybrid', 'full_zk')),

    -- Lifecycle state
    status TEXT DEFAULT 'minted'
        CHECK (status IN (
            'minted', 'presented', 'verified', 'locked',
            'settling', 'settled', 'fulfilled',
            'escrowed', 'confirming', 'auto_releasing', 'released',
            'disputing', 'arbitrating',
            'resolved_refund', 'resolved_release', 'resolved_split',
            'revoked', 'expired', 'failed', 'refunded',
            'partial_settled', 'unlocking', 'cancelled'
        )),

    -- Integrity
    object_hash TEXT,                            -- SHA-256 of canonical object fields

    -- Timestamps
    presented_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_po_mandate ON payment_objects(mandate_id);
CREATE INDEX IF NOT EXISTS idx_po_merchant ON payment_objects(merchant_id);
CREATE INDEX IF NOT EXISTS idx_po_status ON payment_objects(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_po_session_hash ON payment_objects(session_hash);
CREATE INDEX IF NOT EXISTS idx_po_created ON payment_objects(created_at DESC);
