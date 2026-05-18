-- =============================================================================
-- Sardis Migration: 013_ledger_merkle_receipts
-- =============================================================================
--
-- Extends receipts table with Merkle proof columns for cryptographic audit
-- trail, and extends pending_reconciliation with chain-level fields for
-- production reconciliation workflow.
--
-- Apply: psql $DATABASE_URL -f migrations/013_ledger_merkle_receipts.sql
--
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('013', 'Add Merkle proof columns to receipts and chain fields to reconciliation')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Receipts: Add Merkle proof columns
-- -----------------------------------------------------------------------------
ALTER TABLE receipts ADD COLUMN IF NOT EXISTS receipt_id TEXT;
ALTER TABLE receipts ADD COLUMN IF NOT EXISTS mandate_id TEXT;
ALTER TABLE receipts ADD COLUMN IF NOT EXISTS merkle_root TEXT;
ALTER TABLE receipts ADD COLUMN IF NOT EXISTS leaf_hash TEXT;
ALTER TABLE receipts ADD COLUMN IF NOT EXISTS proof_json JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_receipts_receipt_id ON receipts(receipt_id);
CREATE INDEX IF NOT EXISTS idx_receipts_mandate ON receipts(mandate_id);

-- -----------------------------------------------------------------------------
-- Pending Reconciliation: Add chain-level fields for full reconciliation
-- -----------------------------------------------------------------------------
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS chain_tx_hash TEXT;
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS chain TEXT;
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS audit_anchor TEXT;
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS from_wallet TEXT;
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS to_wallet TEXT;
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS amount NUMERIC(20, 6);
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS currency VARCHAR(16);
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS last_retry TIMESTAMPTZ;
ALTER TABLE pending_reconciliation ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}';
