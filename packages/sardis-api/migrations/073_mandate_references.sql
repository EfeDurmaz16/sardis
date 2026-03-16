-- Add mandate_id references to transaction and audit tables.
-- Links every payment to the spending mandate that authorized it.

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS mandate_id TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS mandate_version INTEGER;

CREATE INDEX IF NOT EXISTS idx_transactions_mandate
    ON transactions(mandate_id) WHERE mandate_id IS NOT NULL;
