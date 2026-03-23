-- Escrow holds and Dispute Protocol tables.
--
-- Escrow lifecycle: HELD → CONFIRMING → RELEASED / DISPUTING
-- Dispute lifecycle: FILED → EVIDENCE_COLLECTION → UNDER_REVIEW → RESOLVED_*

CREATE TABLE IF NOT EXISTS escrow_holds (
    hold_id TEXT PRIMARY KEY,                      -- esc_xxx
    payment_object_id TEXT NOT NULL,
    payer_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL,

    -- Amounts
    amount NUMERIC(20,6) NOT NULL,
    currency TEXT DEFAULT 'USDC',

    -- On-chain
    escrow_contract TEXT,
    escrow_tx_hash TEXT,
    release_tx_hash TEXT,
    chain TEXT DEFAULT 'tempo',

    -- Timelock
    timelock_expires_at TIMESTAMPTZ,
    auto_release BOOLEAN DEFAULT true,

    -- Status
    status TEXT DEFAULT 'held'
        CHECK (status IN ('held', 'confirming', 'released', 'auto_released', 'disputing', 'refunded', 'split', 'cancelled')),
    released_at TIMESTAMPTZ,
    released_to TEXT,
    released_amount NUMERIC(20,6),

    -- Delivery
    delivery_confirmed_at TIMESTAMPTZ,
    delivery_confirmed_by TEXT,
    delivery_evidence JSONB DEFAULT '{}',

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_escrow_po ON escrow_holds(payment_object_id);
CREATE INDEX IF NOT EXISTS idx_escrow_status ON escrow_holds(status);
CREATE INDEX IF NOT EXISTS idx_escrow_timelock ON escrow_holds(timelock_expires_at)
    WHERE status IN ('held', 'confirming') AND auto_release = true;

-- Disputes
CREATE TABLE IF NOT EXISTS disputes (
    dispute_id TEXT PRIMARY KEY,                   -- dsp_xxx
    escrow_hold_id TEXT NOT NULL REFERENCES escrow_holds(hold_id),
    payment_object_id TEXT NOT NULL,

    payer_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL,
    filed_by TEXT NOT NULL,

    reason TEXT DEFAULT 'other'
        CHECK (reason IN ('not_delivered', 'not_as_described', 'unauthorized', 'duplicate', 'service_quality', 'overcharge', 'other')),
    description TEXT,
    amount NUMERIC(20,6) NOT NULL,
    currency TEXT DEFAULT 'USDC',

    status TEXT DEFAULT 'filed'
        CHECK (status IN ('filed', 'evidence_collection', 'under_review', 'resolved_refund', 'resolved_release', 'resolved_split', 'withdrawn')),
    evidence_deadline TIMESTAMPTZ,
    review_deadline TIMESTAMPTZ,

    evidence_count INTEGER DEFAULT 0,
    payer_evidence_count INTEGER DEFAULT 0,
    merchant_evidence_count INTEGER DEFAULT 0,

    resolved_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_disputes_escrow ON disputes(escrow_hold_id);
CREATE INDEX IF NOT EXISTS idx_disputes_status ON disputes(status);
CREATE INDEX IF NOT EXISTS idx_disputes_evidence_deadline ON disputes(evidence_deadline)
    WHERE status = 'evidence_collection';

-- Dispute evidence
CREATE TABLE IF NOT EXISTS dispute_evidence (
    evidence_id TEXT PRIMARY KEY,                  -- evi_xxx
    dispute_id TEXT NOT NULL REFERENCES disputes(dispute_id),
    submitted_by TEXT NOT NULL,
    party TEXT NOT NULL CHECK (party IN ('payer', 'merchant')),
    evidence_type TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_dispute ON dispute_evidence(dispute_id);

-- Dispute resolutions
CREATE TABLE IF NOT EXISTS dispute_resolutions (
    resolution_id TEXT PRIMARY KEY,                -- res_xxx
    dispute_id TEXT NOT NULL REFERENCES disputes(dispute_id),
    outcome TEXT NOT NULL
        CHECK (outcome IN ('resolved_refund', 'resolved_release', 'resolved_split')),
    resolved_by TEXT NOT NULL,
    payer_amount NUMERIC(20,6) DEFAULT 0,
    merchant_amount NUMERIC(20,6) DEFAULT 0,
    reasoning TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_resolutions_dispute ON dispute_resolutions(dispute_id);
