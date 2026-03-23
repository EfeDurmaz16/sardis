-- Mandate Trees: hierarchical delegation for spending mandates.
--
-- Enables parent mandates to delegate sub-authority to child mandates,
-- forming a tree of scoped spending permissions. A child mandate can
-- never exceed the scope, limits, or lifetime of its parent.
--
-- Example: CFO mandate → department mandate → agent mandate
--
-- Invariants:
--   - delegation_depth <= max allowed depth (enforced in application)
--   - child amount limits <= parent amount limits
--   - child expires_at <= parent expires_at
--   - revoking a parent cascades to all descendants

ALTER TABLE spending_mandates
    ADD COLUMN IF NOT EXISTS parent_mandate_id TEXT REFERENCES spending_mandates(id);

ALTER TABLE spending_mandates
    ADD COLUMN IF NOT EXISTS delegation_depth INTEGER DEFAULT 0;

ALTER TABLE spending_mandates
    ADD COLUMN IF NOT EXISTS root_mandate_id TEXT;

-- Indexes for tree traversal
CREATE INDEX IF NOT EXISTS idx_mandates_parent ON spending_mandates(parent_mandate_id)
    WHERE parent_mandate_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mandates_root ON spending_mandates(root_mandate_id)
    WHERE root_mandate_id IS NOT NULL;
