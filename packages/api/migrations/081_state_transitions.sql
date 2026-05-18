-- State Transitions: append-only audit log for payment object lifecycle events.
--
-- Every state change on a payment object is recorded here with the actor,
-- reason, and timestamp. This table is append-only by design — rows are
-- never updated or deleted.
--
-- Used for: compliance audit trails, dispute evidence, debugging,
--           analytics on settlement latency and failure patterns.

CREATE TABLE IF NOT EXISTS payment_state_transitions (
    id TEXT PRIMARY KEY,                         -- pst_xxx
    payment_object_id TEXT NOT NULL REFERENCES payment_objects(object_id),

    -- Transition details
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    transition_name TEXT NOT NULL,                -- e.g. 'present', 'verify', 'lock', 'settle'
    actor TEXT NOT NULL,                          -- agent_id, system, merchant_id, etc.
    reason TEXT,                                  -- human-readable explanation

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_transitions_po ON payment_state_transitions(payment_object_id);
CREATE INDEX IF NOT EXISTS idx_transitions_created ON payment_state_transitions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transitions_actor ON payment_state_transitions(actor);
