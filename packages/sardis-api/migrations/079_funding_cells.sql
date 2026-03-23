-- Funding Cells: pre-committed, splittable units of value for payment objects.
--
-- A funding commitment represents a vault-backed pool of value that an
-- organization has reserved for agent spending. Cells are carved from
-- commitments (fixed denomination or proportional) and claimed by
-- individual spending mandates to back payment objects.
--
-- Flow: commitment created → cells minted → cell claimed by mandate →
--       cell attached to payment object → cell spent on settlement

-- Top-level commitment pool
CREATE TABLE IF NOT EXISTS funding_commitments (
    commitment_id TEXT PRIMARY KEY,              -- fc_xxx
    org_id TEXT NOT NULL,
    vault_ref TEXT NOT NULL,                     -- reference to funding source (wallet, bank, etc.)

    -- Value tracking
    total_value NUMERIC(20,6) NOT NULL,          -- original committed amount
    remaining_value NUMERIC(20,6) NOT NULL,      -- unallocated value left
    currency TEXT DEFAULT 'USDC',

    -- Cell creation strategy
    cell_strategy TEXT DEFAULT 'fixed'
        CHECK (cell_strategy IN ('fixed', 'proportional')),
    cell_denomination NUMERIC(20,6),             -- per-cell value for fixed strategy

    -- Settlement
    settlement_preferences JSONB DEFAULT '{}',   -- chain, token, timing preferences

    -- Lifecycle state
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'exhausted', 'expired', 'cancelled')),

    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Individual funding cells carved from commitments
CREATE TABLE IF NOT EXISTS funding_cells (
    cell_id TEXT PRIMARY KEY,                    -- cell_xxx
    commitment_id TEXT NOT NULL REFERENCES funding_commitments(commitment_id),

    -- Value
    value NUMERIC(20,6) NOT NULL,
    currency TEXT DEFAULT 'USDC',

    -- Lifecycle state
    status TEXT DEFAULT 'available'
        CHECK (status IN ('available', 'claimed', 'spent', 'returned', 'merged', 'expired')),

    -- Ownership
    owner_mandate_id TEXT,                       -- FK to spending_mandates(id), nullable until claimed
    claimed_at TIMESTAMPTZ,
    spent_at TIMESTAMPTZ,

    -- Payment binding
    payment_object_id TEXT,                      -- FK to payment_objects(object_id), nullable until spent

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for funding_cells
CREATE INDEX IF NOT EXISTS idx_cells_commitment ON funding_cells(commitment_id);
CREATE INDEX IF NOT EXISTS idx_cells_status ON funding_cells(status);
CREATE INDEX IF NOT EXISTS idx_cells_mandate ON funding_cells(owner_mandate_id)
    WHERE owner_mandate_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cells_available ON funding_cells(currency, status, value DESC)
    WHERE status = 'available';
CREATE INDEX IF NOT EXISTS idx_cells_po ON funding_cells(payment_object_id)
    WHERE payment_object_id IS NOT NULL;

-- Indexes for funding_commitments
CREATE INDEX IF NOT EXISTS idx_commitments_org ON funding_commitments(org_id);
CREATE INDEX IF NOT EXISTS idx_commitments_status ON funding_commitments(status);
