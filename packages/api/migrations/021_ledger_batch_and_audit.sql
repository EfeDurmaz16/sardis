-- Migration 021: Ledger batch and audit tables
-- Required by PostgresLedgerEngine (sardis-ledger v0.4.2)
-- These tables are referenced in db_engine.py but were never migrated.

-- Table 1: ledger_batches
-- Referenced at db_engine.py line 463-468 (INSERT) and line 501-506 (UPDATE)
-- Columns from usage: batch_id TEXT, status TEXT, created_at TIMESTAMPTZ, completed_at TIMESTAMPTZ
-- Also from rollback logic: is_rolled_back BOOLEAN, rollback_reason TEXT, rollback_at TIMESTAMPTZ
CREATE TABLE IF NOT EXISTS ledger_batches (
    batch_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    entry_count INTEGER DEFAULT 0,
    total_amount NUMERIC(38,18),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    is_rolled_back BOOLEAN DEFAULT FALSE,
    rollback_reason TEXT,
    rollback_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

-- Table 2: ledger_batch_entries
-- Referenced at db_engine.py line 493-498
-- Junction table linking batches to their entries
CREATE TABLE IF NOT EXISTS ledger_batch_entries (
    batch_id TEXT NOT NULL REFERENCES ledger_batches(batch_id),
    entry_id TEXT NOT NULL,
    entry_index INTEGER NOT NULL,
    PRIMARY KEY (batch_id, entry_id)
);

-- Table 3: ledger_audit_log
-- Referenced at db_engine.py line 742-757
-- Hash-chained audit log for immutable audit trail
CREATE TABLE IF NOT EXISTS ledger_audit_log (
    audit_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    actor_id TEXT,
    actor_type TEXT,
    old_value JSONB,
    new_value JSONB,
    request_id TEXT,
    previous_hash TEXT,
    entry_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ledger_batches_status ON ledger_batches(status);
CREATE INDEX IF NOT EXISTS idx_ledger_batches_created ON ledger_batches(created_at);
CREATE INDEX IF NOT EXISTS idx_ledger_batch_entries_batch ON ledger_batch_entries(batch_id);
CREATE INDEX IF NOT EXISTS idx_ledger_audit_log_entity ON ledger_audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_ledger_audit_log_action ON ledger_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_ledger_audit_log_created ON ledger_audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_ledger_audit_log_actor ON ledger_audit_log(actor_id);
